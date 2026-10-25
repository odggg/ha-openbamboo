"""Machine commands over the existing, printer-scoped Open Bamboo transport.

Native publish acceptance is not a firmware execution acknowledgement.
No command is retried, persisted or replayed by this controller.
"""
from __future__ import annotations

import json
import math
import threading
import time
import uuid

MAX_GCODE_BYTES = 16 * 1024
STATUS_MAX_AGE = 30
IDLE_STATES = {"IDLE", "FINISH", "FAILED"}


class MachineError(ValueError):
    """A safe, user-facing validation or delivery error."""


def number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MachineError(f"{name} must be a number")
    if not math.isfinite(value) or not low <= value <= high:
        raise MachineError(f"{name} must be between {low} and {high}")
    return value


def normalize_gcode(value):
    if not isinstance(value, str):
        raise MachineError("G-code must be text")
    value = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not value or not any(line.split(";", 1)[0].strip() for line in value.splitlines()):
        raise MachineError("Enter at least one G-code command")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise MachineError("G-code contains control characters")
    value += "\n"
    if len(value.encode("utf-8")) > MAX_GCODE_BYTES:
        raise MachineError("G-code is limited to 16 KiB per submission")
    return value


def _read(obj, key, default=None):
    try:
        return getattr(obj, key, default)
    except (AttributeError, KeyError, TypeError):
        return default


def telemetry(client):
    device = client.owner._device
    temp = _read(device, "temperature")
    job = _read(device, "print_job")
    info = _read(device, "info")
    connected = client.is_connected()
    fresh = (connected and bool(client.machine_status_at)
             and time.monotonic() - client.machine_status_at <= STATUS_MAX_AGE
             and client.machine_state is not None
             and bool(_read(device, "has_full_printer_data", False)))
    required = bool(_read(_read(device, "print_fun"), "_encryption_enabled", True))
    ready = connected and (not required or client.signed_ready)
    def numeric(obj, key):
        value = _read(obj, key)
        return value if isinstance(value, (int, float)) and math.isfinite(value) else None
    return {
        "connected": connected, "ready": ready, "fresh": fresh,
        "state": client.machine_state or "UNKNOWN",
        "model": str(_read(info, "device_type", "Unknown")),
        "nozzle": numeric(temp, "active_nozzle_temperature"),
        "nozzle_target": numeric(temp, "active_nozzle_target_temperature"),
        "bed": numeric(temp, "bed_temp"), "bed_target": numeric(temp, "target_bed_temp"),
        "progress": numeric(job, "print_percentage"),
        "transport": "lan" if client.owner._local_mqtt else "cloud",
    }


def build_command(action, params, status):
    """Validate structured controls on the server, never trust panel limits."""
    if not isinstance(params, dict):
        raise MachineError("Command parameters must be an object")
    allowed = {
        "jog": {"axis", "distance", "speed"}, "home": set(),
        "extrude": {"distance"}, "temperature": {"heater", "value"},
        "fan": {"value"}, "gcode": {"gcode", "allow_during_print"},
        "pause": set(), "resume": set(), "stop": set(),
    }
    if action not in allowed or set(params) - allowed[action]:
        raise MachineError("Unknown action or parameter")
    state = status["state"]
    idle = state in IDLE_STATES
    if action in ("jog", "home", "extrude") and not idle:
        raise MachineError("Motion controls require an idle printer; paused prints are also locked")
    if action == "jog":
        axis = params.get("axis")
        if axis not in ("X", "Y", "Z"):
            raise MachineError("Axis must be X, Y or Z")
        limit = 10 if axis == "Z" else 100
        distance = number(params.get("distance"), -limit, limit, "Distance")
        if distance == 0:
            raise MachineError("Distance must not be zero")
        speed = number(params.get("speed", 600 if axis == "Z" else 3000),
                       60, 1200 if axis == "Z" else 6000, "Feed rate")
        # Same save/restore + soft-endstop sequence as ha-bambulab v2.2.26.
        gcode = ("M211 S\nM211 X1 Y1 Z1\nM1002 push_ref_mode\nG91\n"
                 f"G1 {axis}{distance:g} F{speed:g}\nM1002 pop_ref_mode\nM211 R\n")
    elif action == "home":
        gcode = "G28\n"
    elif action == "extrude":
        if status["nozzle"] is None or status["nozzle"] < 170:
            raise MachineError("Heat the active nozzle to at least 170 °C before extruding/retracting")
        distance = number(params.get("distance"), -20, 20, "Extrusion distance")
        if distance == 0:
            raise MachineError("Distance must not be zero")
        # Matches upstream extrusion mode; only permitted outside prints.
        gcode = f"M83\nG0 E{distance:g} F300\n"
    elif action == "temperature":
        heater = params.get("heater")
        if heater not in ("nozzle", "bed"):
            raise MachineError("Heater must be nozzle or bed")
        value = number(params.get("value"), 0, 300 if heater == "nozzle" else 120, "Temperature")
        gcode = f"{'M104' if heater == 'nozzle' else 'M140'} S{value:g}\n"
    elif action == "fan":
        value = number(params.get("value"), 0, 100, "Fan percentage")
        gcode = f"M106 P1 S{math.ceil(255 * value / 100)}\n"
    elif action == "gcode":
        override = params.get("allow_during_print", False)
        if type(override) is not bool:
            raise MachineError("allow_during_print must be true or false")
        if not idle and not override:
            raise MachineError("Printer is busy. Explicitly enable G-code during a print to continue")
        gcode = normalize_gcode(params.get("gcode"))
    else:
        if action == "pause" and state != "RUNNING":
            raise MachineError("Only a running print can be paused")
        if action == "resume" and state != "PAUSE":
            raise MachineError("Only a paused print can be resumed")
        if action == "stop" and state not in ("RUNNING", "PAUSE", "PREPARE", "SLICING"):
            raise MachineError("No active print to stop")
        return {"command": action}
    return {"command": "gcode_line", "param": gcode}


class MachineController:
    def __init__(self, patch):
        self.patch = patch
        self._locks = {}
        self._locks_lock = threading.Lock()

    def client(self, serial):
        if not self.patch.active:
            raise MachineError("Bambu Open Network is unloaded")
        clients = [client for client in self.patch.snapshot_clients()
                   if client.owner._serial == serial and client.is_connected()
                   and _read(client.owner, "client") is client]
        if len(clients) != 1:
            raise MachineError("Printer has no unique active Open Bamboo connection")
        return clients[0]

    def status(self, serial):
        try:
            return telemetry(self.client(serial))
        except MachineError:
            return {"connected": False, "ready": False, "fresh": False, "state": "UNKNOWN"}

    def execute(self, serial, action, params):
        with self._locks_lock:
            lock = self._locks.setdefault(serial, threading.Lock())
        if not lock.acquire(blocking=False):
            raise MachineError("Another machine command is still being transmitted")
        try:
            client = self.client(serial)
            status = telemetry(client)
            if not status["ready"]:
                raise MachineError("Printer command signing is not ready")
            if not status["fresh"]:
                raise MachineError("Waiting for fresh printer status; reconnect or refresh the printer")
            command = build_command(action, params, status)
            command["sequence_id"] = str(uuid.uuid4().int % 2_000_000_000 + 1)
            payload = json.dumps({"print": command})
            # Expire before transmission if the existing transport queue is busy.
            result = client.publish(f"device/{serial}/request", payload,
                                    expires_at=time.monotonic() + 2)
            result.wait_for_publish(client.rpc_timeout + 3)
            if not result._done.is_set() or result.rc == 4:
                raise MachineError("Delivery is unknown or disconnected. Check the printer; no automatic retry")
            if result.rc == 16:
                raise MachineError("Command expired before transmission; it was not sent")
            if not result.is_published():
                raise MachineError("Open Bamboo rejected the command; check connection and signing")
            return {"sequence_id": command["sequence_id"], "status": "accepted",
                    "message": "Accepted by Open Bamboo; firmware execution is not confirmed"}
        finally:
            lock.release()
