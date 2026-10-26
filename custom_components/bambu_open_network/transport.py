"""Paho-shaped transport backed exclusively by an Open Bamboo subprocess.

Each printer gets a separate process: OBN has process-global configuration
and one LAN session per agent. No credentials are put on the command line.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time
from types import SimpleNamespace
from typing import Any, Callable

from .cloud_camera import CloudFrames, ERRORS
from .command_feedback import CommandReplies

_LOGGER = logging.getLogger(__name__)
MAX_LINE = 4 * 1024 * 1024

@dataclass
class PublishResult:
    rc: int
    mid: int = 0
    expires_at: float = 0
    sequence_id: str | None = None
    _done: threading.Event = field(default_factory=threading.Event, repr=False)

    def wait_for_publish(self, timeout: float | None = None) -> None:
        self._done.wait(timeout)

    def is_published(self) -> bool:
        return self._done.is_set() and self.rc == 0

class OpenBambooClient:
    """The small Paho surface used by ha-bambulab, not a general MQTT client."""

    def __init__(self, owner: Any, command: list[str], state_root: Path,
                 credentials: Path, *, rpc_timeout: float = 12):
        self.owner, self.command = owner, list(command)
        self.state_root, self.credentials = Path(state_root), Path(credentials)
        self.rpc_timeout = rpc_timeout
        self.on_connect: Callable | None = None
        self.on_disconnect: Callable | None = None
        self.on_message: Callable | None = None
        self.signed_ready = False
        self.machine_status_at = 0.0
        self.machine_state = None
        self._connected = False
        self._process: subprocess.Popen | None = None
        self._reader: threading.Thread | None = None
        self._callbacks: threading.Thread | None = None
        self._events: queue.Queue = queue.Queue(maxsize=1024)
        self._pending: dict[int, queue.Queue] = {}
        self._pending_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._counter = 0
        self._stop = threading.Event()
        self._session: tempfile.TemporaryDirectory | None = None
        self._outgoing: queue.Queue = queue.Queue(maxsize=64)
        self._sender: threading.Thread | None = None
        self._ca_pem = ""
        self._username = ""
        self._password = ""
        self._disconnect_sent = False
        self.camera = CloudFrames()
        self.command_replies = CommandReplies()
        self._camera_request_lock = threading.Lock()
        self._camera_requested_at = 0.0

    def enable_logger(self, *args, **kwargs):
        pass

    def reconnect_delay_set(self, **kwargs):
        pass  # libmosquitto manages reconnect inside the worker.

    def tls_set_context(self, context):
        import ssl
        self._outgoing: queue.Queue = queue.Queue(maxsize=64)
        self._sender: threading.Thread | None = None
        self._ca_pem = "".join(ssl.DER_cert_to_PEM_cert(cert)
                              for cert in context.get_ca_certs(binary_form=True))

    def tls_insecure_set(self, value=True):
        if bool(value) != bool(self.owner._disable_ssl_verify):
            raise ValueError("TLS setting differs from the upstream printer configuration")

    def tls_set(self, *args, **kwargs):
        pass  # OBN verifies cloud TLS with the bundled CA set.

    def username_pw_set(self, username, password=None):
        self._username, self._password = username, password or ""

    def _put_event(self, event):
        try:
            self._events.put_nowait(event)
        except queue.Full:
            # Never drop RPC replies; those are delivered directly by _read.
            # If HA cannot keep up with telemetry, reconnect for a fresh snapshot.
            _LOGGER.error("Open Bamboo callback queue exhausted")
            if self._process is not None:
                self._process.terminate()

    def connect(self, host, port=8883, keepalive=30):
        if port != 8883:
            raise ValueError("Only TLS MQTT port 8883 is supported")
        if self._process is not None:
            self.disconnect()
            self.loop_stop()
        self._stop.clear()
        self.command_replies.reset()
        self.machine_status_at = 0.0
        self.machine_state = None
        self.camera = CloudFrames()
        self._camera_requested_at = 0.0
        self._disconnect_sent = False
        self._events = queue.Queue(maxsize=1024)
        self._outgoing = queue.Queue(maxsize=64)
        self.state_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._session = tempfile.TemporaryDirectory(prefix="session-", dir=self.state_root)
        state = Path(self._session.name)
        state.chmod(0o700)
        ca = state / "printer-ca.pem"
        if self._ca_pem:
            ca.write_text(self._ca_pem, encoding="ascii")
        # Restrict credentials to explicit signing files; no arbitrary config injection.
        lines = ["log_level = error", "log_stderr = 0", "log_to_file = 0",
                 "patch_mqtt_home_flag = 0", "mqtt_keep_connection = 0",
                 "client_name = BambuStudio", "prefer_lan_over_tutk = 0",
                 f"block_cloud = {int(self.owner._local_mqtt)}",
                 f"lan_tls_skip_verify = {int(self.owner._disable_ssl_verify and self.owner._local_mqtt)}"]
        for name in ("slicer_key.pem", "slicer_cert.pem", "slicer_crl.pem"):
            path = (self.credentials / name).resolve()
            if path.is_file():
                if any(char in str(path) for char in "\r\n"):
                    raise ValueError("Invalid credential path")
                key = name.replace(".pem", "_pem")
                lines.append(f"{key} = {path}")
        (state / "obn.conf").write_text("\n".join(lines) + "\n")
        env = os.environ.copy()
        # Upstream environment overrides must not change our configured transport.
        for key in list(env):
            if key.startswith("OBN_"):
                env.pop(key)
        runtime_root = Path(self.command[0]).parent
        bundle = runtime_root / "ca-bundle.pem"
        if bundle.is_file():
            env["SSL_CERT_FILE"] = str(bundle)
            env["CURL_CA_BUNDLE"] = str(bundle)
        try:
            self._process = subprocess.Popen(
                self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                bufsize=1, env=env,
            )
            self._reader = threading.Thread(target=self._read, name="OBN-RPC", daemon=True)
            self._reader.start()
            response = self._request("init", {
                "serial": self.owner._serial, "host": str(host),
                "local": bool(self.owner._local_mqtt),
                "username": self._username, "password": self._password,
                "state_directory": str(state), "ca_file": str(ca) if self._ca_pem else "",
                "country": "CN" if self.owner.settings.get("region", "").lower() in ("china", "cn") else "US",
            }, timeout=30)
            if response["rc"] != 0:
                raise ConnectionError(f"Open Bamboo initialization failed ({response['rc']})")
        except BaseException:
            self.disconnect()
            self.loop_stop()
            raise
        self._sender = threading.Thread(target=self._send, name="OBN-Publish", daemon=True)
        self._sender.start()
        return 0

    def _request(self, method: str, params=None, *, timeout=None, fatal_timeout=True):
        if self._stop.is_set() or self._process is None or self._process.poll() is not None:
            raise ConnectionError("Open Bamboo worker is disconnected")
        waiter: queue.Queue = queue.Queue(maxsize=1)
        with self._pending_lock:
            self._counter += 1
            mid = self._counter
            self._pending[mid] = waiter
        try:
            line = json.dumps({"id": mid, "method": method, "params": params or {}},
                              separators=(",", ":")) + "\n"
            if len(line.encode("utf-8")) > MAX_LINE:
                raise ValueError("Open Bamboo request is too large")
            with self._write_lock:
                self._process.stdin.write(line)
                self._process.stdin.flush()
            result = waiter.get(timeout=timeout or self.rpc_timeout)
            if isinstance(result, Exception):
                raise result
            return result
        except queue.Empty as err:
            # A timed-out motion/print command has an unknown outcome. Kill the
            # session and never retry the command on another transport.
            if fatal_timeout:
                self.disconnect()
            raise TimeoutError(f"Open Bamboo {method} timed out") from err
        finally:
            with self._pending_lock:
                self._pending.pop(mid, None)

    def _read(self):
        try:
            while not self._stop.is_set():
                line = self._process.stdout.readline(MAX_LINE + 1)
                if not line:
                    break
                if len(line) > MAX_LINE or not line.endswith("\n"):
                    raise ValueError("Oversized native response")
                event = json.loads(line)
                if "id" in event:
                    with self._pending_lock:
                        waiter = self._pending.get(event["id"])
                    if waiter:
                        waiter.put_nowait(event)
                else:
                    kind = event.get("event")
                    if kind in ("camera_frame", "camera_state"):
                        if event.get("serial") == self.owner._serial:
                            if kind == "camera_frame":
                                self.camera.feed(event)
                            else:
                                self.camera.set_state(event.get("state"))
                        continue
                    if event.get("event") == "disconnected":
                        self.camera.set_state("disconnected")
                        self._connected = self.signed_ready = False
                        self._discard_queued()
                    self._put_event(event)
        except (OSError, ValueError, queue.Full):
            _LOGGER.error("Open Bamboo native protocol failed")
        finally:
            self._connected = self.signed_ready = False
            self.camera.set_state("disconnected")
            self._put_event({"event": "disconnected", "rc": 7})
            with self._pending_lock:
                for waiter in self._pending.values():
                    try:
                        waiter.put_nowait(ConnectionError("Open Bamboo worker exited"))
                    except queue.Full:
                        pass
            if not self._stop.is_set() and self._process.poll() is None:
                self._process.terminate()

    def _dispatch(self, event):
        kind = event.get("event")
        if kind == "connected":
            self.command_replies.reset()
            self.machine_status_at = 0.0
            self.machine_state = None
            self._connected = True
            if self.on_connect:
                self.on_connect(self, None, {}, 0)
        elif kind == "disconnected":
            self.command_replies.reset()
            self.machine_status_at = 0.0
            self.machine_state = None
            self._connected = self.signed_ready = False
            self._discard_queued()
            if self.on_disconnect and not self._disconnect_sent:
                self._disconnect_sent = True
                self.on_disconnect(self, None, int(event.get("rc", 7)))
        elif kind == "capabilities":
            previous = self.signed_ready
            self.signed_ready = bool(event.get("signed_ready")) and self._connected
            if previous != self.signed_ready and self.owner._callback:
                self.owner.callback("event_printer_data_update")
                if self.signed_ready and getattr(self.owner._device, "has_full_printer_data", False):
                    # ha-bambulab omits control entities while signing is
                    # unavailable. Recreate them after the certificate ACK.
                    self.owner.callback("event_printer_ready")
        elif kind == "message":
            if event.get("serial") != self.owner._serial:
                return
            payload = event.get("payload", "")
            if not isinstance(payload, str):
                return
            # Observe authorization failures without suppressing printer feedback.
            try:
                body = json.loads(payload)
                self.command_replies.observe(body)
                if any(isinstance(item, dict) and item.get("err_code") in
                       (84033543, 84033545) for item in body.values()):
                    self.signed_ready = False
            except ValueError:
                return
            if self.on_message:
                self.on_message(self, None, SimpleNamespace(
                    topic=f"device/{self.owner._serial}/report",
                    payload=payload.encode("utf-8"), qos=0, retain=False))
                report = body.get("print")
                if isinstance(report, dict) and report.get("command") == "push_status":
                    if isinstance(report.get("gcode_state"), str):
                        self.machine_state = report["gcode_state"].upper()
                    self.machine_status_at = time.monotonic()
        elif kind == "error":
            _LOGGER.error("Open Bamboo worker reported an error (code %s)", event.get("rc"))

    def loop_forever(self, **kwargs):
        self._disconnect_sent = False
        while not self._stop.is_set():
            try:
                event = self._events.get(timeout=0.25)
            except queue.Empty:
                if not self._stop.is_set() and self._reader and not self._reader.is_alive():
                    raise ConnectionError("Open Bamboo worker stopped")
                continue
            try:
                if event.get("event") == "connected":
                    self._disconnect_sent = False
                self._dispatch(event)
            except Exception:
                _LOGGER.exception("ha-bambulab callback failed")
            if (not self._stop.is_set() and event.get("event") == "disconnected"
                    and self._reader and not self._reader.is_alive()):
                raise ConnectionError("Open Bamboo worker stopped")
        return 0

    def _background_loop(self):
        try:
            self.loop_forever()
        except ConnectionError:
            if not self._stop.is_set():
                _LOGGER.warning("Open Bamboo connection test worker stopped")

    def loop_start(self):
        if self._callbacks is None or not self._callbacks.is_alive():
            self._callbacks = threading.Thread(target=self._background_loop,
                                               name="OBN-Callbacks", daemon=True)
            self._callbacks.start()
        return 0

    def loop_stop(self):
        self.disconnect()
        self.camera.close()
        if self._callbacks and self._callbacks is not threading.current_thread():
            self._callbacks.join(timeout=3)
        if self._reader and self._reader is not threading.current_thread():
            self._reader.join(timeout=3)
        if self._process is not None and self._process.poll() is None:
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)
        if self._sender and self._sender is not threading.current_thread():
            self._sender.join(timeout=3)
        if self._process is not None and self._process.poll() is not None:
            if self._reader and self._reader is not threading.current_thread():
                self._reader.join(timeout=1)
            for stream in (self._process.stdin, self._process.stdout):
                if stream is not None and not stream.closed:
                    stream.close()
        if self._session is not None and (self._process is None or self._process.poll() is not None):
            self._session.cleanup()
            self._session = None

    def disconnect(self):
        self.camera.close(wait=False)
        self._stop.set()
        self.command_replies.reset()
        self._connected = self.signed_ready = False
        self._discard_queued()
        process = self._process
        if process is not None and process.poll() is None:
            # EOF asks the worker to gracefully destroy OBN and free MQTT slots.
            try:
                with self._write_lock:
                    process.stdin.close()
            except OSError:
                pass
        return 0

    def request_camera(self):
        """Start/renew a cloud session on demand; camera failures don't stop MQTT."""
        import time
        if self.owner._local_mqtt or not self._connected or self._stop.is_set():
            return
        with self._camera_request_lock:
            now = time.monotonic()
            if now - self._camera_requested_at < 10:
                return
            self._camera_requested_at = now
            if self.camera.state in ERRORS or self.camera.state in ("idle", "disconnected"):
                self.camera.set_state("connecting")
            try:
                result = self._request("camera_start", timeout=5, fatal_timeout=False)
                if result.get("rc") != 0:
                    self.camera.set_state("camera_failed")
            except (OSError, ValueError, TimeoutError):
                self.camera.set_state("camera_failed")

    def is_connected(self):
        return self._connected

    def subscribe(self, topic, qos=0):
        if topic != f"device/{self.owner._serial}/report":
            raise ValueError("Unexpected subscription")
        # The worker automatically subscribes before it emits connected.
        return (0, 1)

    def publish(self, topic, payload, qos=0, retain=False, *, expires_at=0):
        """Queue without blocking HA, matching Paho's accepted-for-delivery rc."""
        if topic != f"device/{self.owner._serial}/request" or retain or qos not in (0, 1):
            raise ValueError("Unsupported publish")
        result = PublishResult(rc=4, expires_at=expires_at)
        if not self._connected or self._stop.is_set():
            result._done.set()
            return result
        body = json.loads(payload)
        if not isinstance(body, dict):
            raise ValueError("MQTT payload must be an object")
        if len(payload.encode("utf-8")) > MAX_LINE // 2:
            raise ValueError("Payload too large")
        original_required = bool(self.owner._device.print_fun._encryption_enabled)
        if ("print" in body or "liveview" in body) and original_required and not self.signed_ready:
            _LOGGER.error("Signed commands need valid credentials and printer certificate acknowledgement")
            result._done.set()
            return result
        try:
            result.rc = 0
            self._outgoing.put_nowait((result, payload, qos))
        except queue.Full:
            result.rc = 15
            result._done.set()
        return result

    def _discard_queued(self):
        while True:
            try:
                result, _, _ = self._outgoing.get_nowait()
            except queue.Empty:
                break
            result.rc = 4
            result._done.set()

    def _send(self):
        try:
            while not self._stop.is_set():
                try:
                    result, payload, qos = self._outgoing.get(timeout=0.25)
                except queue.Empty:
                    continue
                try:
                    if result.expires_at and time.monotonic() >= result.expires_at:
                        result.rc = 16
                        continue
                    if not self._connected:
                        raise ConnectionError("Printer disconnected before publish")
                    reply = self._request("publish", {"payload": payload, "qos": qos})
                    result.rc, result.mid = int(reply["rc"]), int(reply["id"])
                    raw_sequence = reply.get("sequence_id")
                    if isinstance(raw_sequence, (str, int)) and not isinstance(raw_sequence, bool):
                        result.sequence_id = str(raw_sequence)
                    if result.rc != 0:
                        _LOGGER.error("Open Bamboo rejected queued publish (rc=%s)", result.rc)
                        if result.rc == -26:
                            self.signed_ready = False
                except (OSError, ValueError, TimeoutError):
                    result.rc = 4
                    _LOGGER.error("Open Bamboo publish failed; command was not retried")
                finally:
                    result._done.set()
        finally:
            # Never replay buffered control actions after a disconnect.
            while True:
                try:
                    result, _, _ = self._outgoing.get_nowait()
                except queue.Empty:
                    break
                result.rc = 4
                result._done.set()
