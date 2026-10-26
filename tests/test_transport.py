import support
"""Protocol, isolation, fail-closed signing and process lifecycle regression tests."""
import importlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Load transport without importing Home Assistant, which is Linux-only.
pkg = ModuleType("custom_components.bambu_open_network")
pkg.__path__ = [str(ROOT / "custom_components/bambu_open_network")]
sys.modules.setdefault("custom_components", ModuleType("custom_components"))
sys.modules["custom_components.bambu_open_network"] = pkg
transport = importlib.import_module("custom_components.bambu_open_network.transport")
runtime = importlib.import_module("custom_components.bambu_open_network.runtime")

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clients = []

    def tearDown(self):
        for client in self.clients:
            client.disconnect()
            client.loop_stop()
        self.tmp.cleanup()

    def make(self, mode="normal", serial="TEST123", required=False):
        owner = SimpleNamespace(
            _serial=serial, _local_mqtt=True, _disable_ssl_verify=False,
            settings={}, _callback=None,
            _device=SimpleNamespace(print_fun=SimpleNamespace(_encryption_enabled=required)),
        )
        client = transport.OpenBambooClient(
            owner, [sys.executable, str(ROOT / "tests/fake_worker.py"), mode],
            Path(self.tmp.name) / "state", Path(self.tmp.name) / "credentials",
            rpc_timeout=0.2 if mode == "hang" else 2,
        )
        owner.client = client
        client.username_pw_set("bblp", "private-code")
        self.clients.append(client)
        return client

    def start(self, client):
        ready = threading.Event()
        client.on_connect = lambda *args: ready.set()
        client.connect("192.0.2.1", 8883)
        client.loop_start()
        self.assertTrue(ready.wait(3))

    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.01)
        self.fail("Asynchronous condition timed out")

    def test_roundtrip_with_publish_inside_callback(self):
        client = self.make()
        received = threading.Event()
        results = []
        def connected(*args):
            results.append(client.publish("device/TEST123/request", '{"info": {"command": "get_version"}}').rc)
        client.on_connect = connected
        client.on_message = lambda *args: received.set()
        client.connect("192.0.2.1")
        client.loop_start()
        self.assertTrue(received.wait(3))
        self.assertEqual(results, [0])

    def test_missing_credentials_do_not_unlock_signed_commands(self):
        client = self.make(required=True)
        self.start(client)
        result = client.publish("device/TEST123/request", '{"print":{"command":"pause"}}')
        self.assertNotEqual(result.rc, 0)
        self.assertFalse(client.signed_ready)

    def test_acknowledged_signer_unlocks_and_revokes_on_disconnect(self):
        client = self.make("signed", required=True)
        self.start(client)
        self.wait_for(lambda: client.signed_ready)
        result = client.publish("device/TEST123/request", '{"print":{"command":"pause"}}')
        result.wait_for_publish(3)
        self.assertEqual(result.rc, 0)
        self.assertTrue(result.is_published())
        client.disconnect()
        self.assertFalse(client.signed_ready)

    def test_real_pipe_returns_wire_id_and_early_firmware_rejection(self):
        client = self.make("firmware_reject")
        self.start(client)
        result = client.publish("device/TEST123/request",
            '{"print":{"command":"gcode_line","param":"M105\\n","sequence_id":"1999999999"}}')
        result.wait_for_publish(3)
        self.assertTrue(result.is_published())
        self.assertTrue(20000 <= int(result.sequence_id) < 30000)
        reply = client.command_replies.wait("print", "gcode_line", result.sequence_id, 1)
        self.assertEqual(reply["status"], "rejected")
        self.assertEqual(reply["error_code"], 84033544)
        self.assertNotIn("reason", reply)

    def test_worker_rejection_is_recorded(self):
        client = self.make("reject")
        self.start(client)
        result = client.publish("device/TEST123/request", '{"print":{}}')
        result.wait_for_publish(3)
        self.assertEqual(result.rc, -26)

    def test_unknown_outcome_disconnects_without_retry(self):
        client = self.make("hang")
        self.start(client)
        result = client.publish("device/TEST123/request", '{"print":{}}')
        result.wait_for_publish(3)
        self.assertNotEqual(result.rc, 0)
        self.assertFalse(client.is_connected())
        self.assertTrue(client._stop.is_set())

    def test_two_printers_have_separate_processes_and_state(self):
        one, two = self.make(serial="ONE"), self.make(serial="TWO")
        self.start(one)
        self.start(two)
        self.assertNotEqual(one._process.pid, two._process.pid)
        self.assertNotEqual(one._session.name, two._session.name)
        with self.assertRaises(ValueError):
            one.publish("device/TWO/request", "{}")
        one.disconnect()
        self.assertTrue(two.is_connected())

    def test_mismatched_serial_is_not_forwarded(self):
        client = self.make()
        events = []
        client.on_message = lambda *args: events.append(args)
        client._dispatch({"event": "message", "serial": "OTHER", "payload": "{}"})
        self.assertEqual(events, [])

    def test_firmware_signature_error_revokes_readiness(self):
        client = self.make()
        client._connected = client.signed_ready = True
        client._dispatch({"event": "message", "serial": "TEST123",
                          "payload": '{"print":{"err_code":84033543}}'})
        self.assertFalse(client.signed_ready)

    def test_credentials_are_absent_from_command_line(self):
        client = self.make()
        self.start(client)
        self.assertNotIn("private-code", " ".join(client._process.args))

    def test_stop_reaps_worker_and_removes_session(self):
        client = self.make()
        self.start(client)
        session = Path(client._session.name)
        process = client._process
        client.disconnect()
        client.loop_stop()
        self.assertIsNotNone(process.poll())
        self.assertFalse(session.exists())

    def test_publish_returns_before_slow_native_reply(self):
        client = self.make("hang")
        self.start(client)
        result = client.publish("device/TEST123/request", '{"info":{}}')
        # The hanging worker cannot acknowledge this yet; publish still returns.
        self.assertEqual(result.rc, 0)
        self.assertFalse(result._done.is_set())
        result.wait_for_publish(3)

    def test_disconnect_drops_buffered_actions(self):
        client = self.make()
        client._connected = True
        result = client.publish("device/TEST123/request", '{"print":{}}')
        self.assertFalse(result._done.is_set())
        client.disconnect()
        self.assertEqual(result.rc, 4)
        self.assertTrue(result._done.is_set())
        self.assertTrue(client._outgoing.empty())

    def test_cloud_mqtt_uses_account_token_without_lan_code(self):
        client = self.make("cloudcheck")
        client.owner._local_mqtt = False
        client.owner._disable_ssl_verify = True
        client.username_pw_set("u_12345", "account-token")
        self.start(client)
        configuration = Path(client._session.name, "obn.conf").read_text()
        self.assertIn("block_cloud = 0", configuration)
        # A LAN-only verify override must never disable cloud TLS verification.
        self.assertIn("lan_tls_skip_verify = 0", configuration)
        self.assertNotIn("account-token", " ".join(client._process.args))

    def test_reject_retained_motion_and_non_tls_port(self):
        client = self.make()
        with self.assertRaises(ValueError):
            client.publish("device/TEST123/request", "{}", retain=True)
        with self.assertRaises(ValueError):
            client.connect("192.0.2.1", 1883)

    def test_cloud_camera_uses_existing_worker_without_lan_code(self):
        client = self.make("camera")
        client.owner._local_mqtt = False
        self.start(client)
        client.request_camera()
        image = client.camera.image(3)
        self.assertIsNotNone(image)
        self.assertTrue(image.startswith(b"\xff\xd8"))
        self.assertEqual(client.camera.state, "streaming")
        self.assertTrue(client.is_connected())
        client.disconnect()
        self.assertIsNone(client.camera.image())

    def test_camera_missing_credentials_does_not_disable_control_transport(self):
        client = self.make()
        client.owner._local_mqtt = False
        self.start(client)
        client.request_camera()
        self.wait_for(lambda: client.camera.state == "missing_signing_credentials")
        result = client.publish("device/TEST123/request", '{"info":{}}')
        result.wait_for_publish(3)
        self.assertEqual(result.rc, 0)
        self.assertTrue(client.is_connected())

    def test_signed_readiness_recreates_previously_missing_controls(self):
        client = self.make()
        events = []
        client.owner._callback = True
        client.owner.callback = events.append
        client.owner._device.has_full_printer_data = True
        client._connected = True
        client._dispatch({"event": "capabilities", "signed_ready": True})
        self.assertIn("event_printer_ready", events)
        events.clear()
        client._dispatch({"event": "capabilities", "signed_ready": True})
        self.assertEqual(events, [])

    def test_platform_selection(self):
        self.assertEqual(runtime.architecture("x86_64"), "amd64")
        self.assertEqual(runtime.architecture("arm64"), "aarch64")
        with self.assertRaises(runtime.RuntimeUnavailable):
            runtime.architecture("armv7l")

if __name__ == "__main__":
    unittest.main()
