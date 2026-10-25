"""Validate real command building, interlocks, transport expiry and isolation."""
import support
import importlib
import json
from pathlib import Path
import sys
import threading
import time
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
if "custom_components.bambu_open_network" not in sys.modules:
    pkg = ModuleType("custom_components.bambu_open_network")
    pkg.__path__ = [str(ROOT / "custom_components/bambu_open_network")]
    sys.modules.setdefault("custom_components", ModuleType("custom_components"))
    sys.modules["custom_components.bambu_open_network"] = pkg
machine = importlib.import_module("custom_components.bambu_open_network.machine")
transport = importlib.import_module("custom_components.bambu_open_network.transport")


def device():
    return NS(
        has_full_printer_data=True,
        print_fun=NS(_encryption_enabled=True),
        temperature=NS(active_nozzle_temperature=210, active_nozzle_target_temperature=215,
                       bed_temp=58, target_bed_temp=60),
        print_job=NS(print_percentage=0), info=NS(device_type="P1S"))


def fixture(serial="ONE"):
    owner = NS(_serial=serial, _local_mqtt=False, _device=device())
    client = NS(owner=owner, signed_ready=True, rpc_timeout=0,
                is_connected=lambda: True, machine_status_at=time.monotonic(),
                machine_state="IDLE")
    owner.client = client
    def publish(*args, **kwargs):
        result = transport.PublishResult(rc=0)
        result._done.set()
        return result
    client.publish = Mock(side_effect=publish)
    patch = NS(active=True, snapshot_clients=lambda: [client])
    return machine.MachineController(patch), client


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.client = fixture()
        self.status = machine.telemetry(self.client)

    def test_camera_health_is_metadata_only_and_printer_scoped(self):
        self.client.camera = NS(frame_age=2.5, state="streaming")
        status = self.manager.status("ONE")
        self.assertEqual(status["camera_frame_age"], 2.5)
        self.assertEqual(status["camera_status"], "streaming")
        self.assertNotIn("camera_frame_age", self.manager.status("OTHER"))
        self.assertNotIn("access_token", status)

    def test_newlines_multiline_and_comments(self):
        self.assertEqual(machine.normalize_gcode(" M105\r\nM114\r\n"), "M105\nM114\n")
        self.assertEqual(machine.normalize_gcode("M105"), "M105\n")
        for invalid in ("", " ; comment only\n", "M105\0", 12, "G1 X1\n" * 4000):
            with self.subTest(invalid=str(invalid)[:20]), self.assertRaises(machine.MachineError):
                machine.normalize_gcode(invalid)

    def test_jog_preserves_decimal_and_reference_mode(self):
        cmd = machine.build_command("jog", {"axis": "X", "distance": -0.1}, self.status)
        self.assertIn("G1 X-0.1 F3000\n", cmd["param"])
        self.assertTrue(cmd["param"].startswith("M211 S\nM211 X1 Y1 Z1\nM1002 push_ref_mode\n"))
        self.assertTrue(cmd["param"].endswith("M1002 pop_ref_mode\nM211 R\n"))

    def test_motion_limits_reject_injection_nonfinite_and_wrong_types(self):
        for params in (
            {"axis": "X\nG28", "distance": 1},
            {"axis": "X", "distance": 101}, {"axis": "Z", "distance": 11},
            {"axis": "X", "distance": 0}, {"axis": "X", "distance": True},
            {"axis": "X", "distance": float("nan")},
            {"axis": "X", "distance": 1, "speed": float("inf")},
            {"axis": "Z", "distance": 1, "speed": 3000},
            {"axis": "X", "distance": "10"}, {"axis": "X", "distance": 1, "extra": 1},
        ):
            with self.subTest(params=params), self.assertRaises(machine.MachineError):
                machine.build_command("jog", params, self.status)

    def test_running_paused_preparing_and_unknown_all_block_motion(self):
        for state in ("RUNNING", "PAUSE", "PREPARE", "SLICING", "UNKNOWN"):
            status = {**self.status, "state": state}
            for action, params in (("jog", {"axis": "X", "distance": 1}),
                                   ("home", {}), ("extrude", {"distance": 5})):
                with self.subTest(state=state, action=action), self.assertRaises(machine.MachineError):
                    machine.build_command(action, params, status)

    def test_extrusion_requires_hot_active_nozzle(self):
        for temp in (None, 0, 169):
            with self.assertRaises(machine.MachineError):
                machine.build_command("extrude", {"distance": 5}, {**self.status, "nozzle": temp})
        self.assertEqual(machine.build_command("extrude", {"distance": -5}, self.status)["param"],
                         "M83\nG0 E-5 F300\n")

    def test_heaters_and_part_fan(self):
        self.assertEqual(machine.build_command("temperature", {"heater": "nozzle", "value": 200}, self.status)["param"], "M104 S200\n")
        self.assertEqual(machine.build_command("temperature", {"heater": "bed", "value": 0}, self.status)["param"], "M140 S0\n")
        self.assertEqual(machine.build_command("fan", {"value": 50}, self.status)["param"], "M106 P1 S128\n")
        for action, params in (("temperature", {"heater": "nozzle", "value": 301}),
                               ("temperature", {"heater": "bed", "value": 121}),
                               ("temperature", {"heater": "chamber", "value": 50}),
                               ("fan", {"value": -1}), ("fan", {"value": 101})):
            with self.assertRaises(machine.MachineError):
                machine.build_command(action, params, self.status)

    def test_raw_gcode_busy_override_is_explicit_boolean(self):
        status = {**self.status, "state": "RUNNING"}
        for params in ({"gcode": "M105"}, {"gcode": "M105", "allow_during_print": "false"}):
            with self.assertRaises(machine.MachineError):
                machine.build_command("gcode", params, status)
        self.assertEqual(machine.build_command("gcode", {"gcode": "M105", "allow_during_print": True}, status)["param"], "M105\n")

    def test_print_controls_check_state(self):
        self.assertEqual(machine.build_command("pause", {}, {**self.status, "state": "RUNNING"}), {"command": "pause"})
        self.assertEqual(machine.build_command("resume", {}, {**self.status, "state": "PAUSE"}), {"command": "resume"})
        for action in ("pause", "resume", "stop"):
            with self.assertRaises(machine.MachineError):
                machine.build_command(action, {}, self.status)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.client = fixture()

    def test_printer_scoped_payload_unique_sequence_and_native_acceptance(self):
        one = self.manager.execute("ONE", "gcode", {"gcode": "M105\r\nM114"})
        two = self.manager.execute("ONE", "gcode", {"gcode": "M105"})
        args, kwargs = self.client.publish.call_args_list[0]
        self.assertEqual(args[0], "device/ONE/request")
        self.assertEqual(json.loads(args[1])["print"]["param"], "M105\nM114\n")
        self.assertGreater(kwargs["expires_at"], time.monotonic())
        self.assertNotEqual(one["sequence_id"], two["sequence_id"])
        self.assertEqual(one["status"], "accepted")
        self.assertIn("not confirmed", one["message"])
        with self.assertRaises(machine.MachineError):
            self.manager.execute("TWO", "home", {})
        self.assertEqual(self.client.publish.call_count, 2)

    def test_signing_stale_initial_and_unloaded_states_never_publish(self):
        for change in ("signer", "stale", "initial", "unloaded", "replaced"):
            manager, client = fixture()
            if change == "signer":
                client.signed_ready = False
            elif change == "stale":
                client.machine_status_at -= 31
            elif change == "initial":
                client.machine_state = None
            elif change == "unloaded":
                manager.patch.active = False
            else:
                client.owner.client = object()
            with self.subTest(change=change), self.assertRaises(machine.MachineError):
                manager.execute("ONE", "home", {})
            client.publish.assert_not_called()

    def test_duplicate_live_workers_are_rejected(self):
        _, other = fixture()
        self.manager.patch.snapshot_clients = lambda: [self.client, other]
        with self.assertRaises(machine.MachineError):
            self.manager.execute("ONE", "home", {})
        self.client.publish.assert_not_called()

    def test_failure_and_timeout_never_retry(self):
        for rc, done, expected in ((-26, True, "rejected"), (4, True, "unknown"),
                                   (0, False, "unknown"), (16, True, "expired")):
            result = NS(rc=rc, _done=NS(is_set=lambda: done),
                        wait_for_publish=Mock(), is_published=lambda: done and rc == 0)
            self.client.publish = Mock(return_value=result)
            with self.subTest(rc=rc, done=done), self.assertRaisesRegex(machine.MachineError, expected):
                self.manager.execute("ONE", "home", {})
            self.client.publish.assert_called_once()

    def test_concurrent_command_is_rejected_without_queueing(self):
        entered, finish = threading.Event(), threading.Event()
        result = transport.PublishResult(rc=0)
        def wait(timeout):
            entered.set()
            finish.wait(2)
            result._done.set()
        result.wait_for_publish = wait
        self.client.publish = Mock(return_value=result)
        thread = threading.Thread(target=self.manager.execute, args=("ONE", "home", {}))
        thread.start()
        self.assertTrue(entered.wait(1))
        try:
            with self.assertRaisesRegex(machine.MachineError, "still"):
                self.manager.execute("ONE", "home", {})
        finally:
            finish.set()
            thread.join(3)
        self.client.publish.assert_called_once()

    def test_expired_transport_queue_command_is_not_written(self):
        client = transport.OpenBambooClient(
            self.client.owner, [], ROOT / ".test-tmp/state", ROOT / ".test-tmp/credentials")
        client._connected = True
        client.signed_ready = True
        client._request = Mock()
        result = client.publish("device/ONE/request", '{"print":{"command":"gcode_line","param":"G28\\n"}}',
                                expires_at=time.monotonic() - 1)
        thread = threading.Thread(target=client._send)
        thread.start()
        result.wait_for_publish(1)
        client._stop.set()
        thread.join(2)
        self.assertEqual(result.rc, 16)
        client._request.assert_not_called()
        client.camera.close()

    def test_status_is_bound_to_matching_printer_and_new_connection(self):
        client = transport.OpenBambooClient(self.client.owner, [], ROOT, ROOT)
        client.on_message = lambda *args: None
        report = {"event": "message", "serial": "TWO",
                  "payload": '{"print":{"command":"push_status","gcode_state":"IDLE"}}'}
        client._dispatch(report)
        self.assertEqual(client.machine_status_at, 0)
        report["serial"] = "ONE"
        client._dispatch(report)
        self.assertEqual(client.machine_state, "IDLE")
        client._dispatch({"event": "connected"})
        self.assertIsNone(client.machine_state)
        self.assertEqual(client.machine_status_at, 0)
        client.camera.close()
