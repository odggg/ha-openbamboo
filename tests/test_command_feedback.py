"""Firmware replies are not MQTT enqueue acknowledgements or execution proof."""
import support
import importlib
import json
from pathlib import Path
import sys
import threading
from types import ModuleType
import unittest

ROOT = Path(__file__).resolve().parents[1]
if "custom_components.bambu_open_network" not in sys.modules:
    pkg = ModuleType("custom_components.bambu_open_network")
    pkg.__path__ = [str(ROOT / "custom_components/bambu_open_network")]
    sys.modules.setdefault("custom_components", ModuleType("custom_components"))
    sys.modules["custom_components.bambu_open_network"] = pkg
module = importlib.import_module("custom_components.bambu_open_network.command_feedback")


class ReplyTests(unittest.TestCase):
    def setUp(self):
        self.replies = module.CommandReplies()

    def reply(self, **fields):
        return {"print": {"command": "gcode_line", "sequence_id": "20010", **fields}}

    def test_echo_and_push_status_do_not_confirm_execution(self):
        self.replies.observe(self.reply(param="M104 S200\n"))
        self.replies.observe({"print": {"command": "push_status", "sequence_id": "20010", "err_code": 0}})
        self.assertIsNone(self.replies.wait("print", "gcode_line", "20010", 0))
        self.assertIsNone(self.replies.latest())

    def test_reply_before_publish_return_is_preserved_and_redacted(self):
        self.replies.observe(self.reply(result="FAIL", err_code=84033544,
                                       reason="token=private", param="private-gcode", access_code="secret"))
        reply = self.replies.wait("print", "gcode_line", "20010", 0)
        self.assertEqual(reply["status"], "rejected")
        self.assertEqual(reply["error_code"], 84033544)
        serialized = json.dumps(reply)
        for secret in ("private", "secret", "token", "param", "access_code", "reason"):
            self.assertNotIn(secret, serialized)

    def test_numeric_id_and_string_error_correlate(self):
        self.replies.observe(self.reply(sequence_id=20010, err_code="84033545"))
        self.assertEqual(self.replies.wait("print", "gcode_line", "20010", 0)["status"], "rejected")
        self.assertIsNone(self.replies.wait("system", "gcode_line", "20010", 0))
        self.assertIsNone(self.replies.wait("print", "pause", "20010", 0))
        self.assertIsNone(self.replies.wait("print", "gcode_line", "20011", 0))

    def test_acknowledged_is_not_renamed_executed(self):
        for fields in ({"result": "SUCCESS"}, {"err_code": 0}, {"result": "succeed"}, {"result": 0}):
            self.replies.observe(self.reply(**fields))
            reply = self.replies.wait("print", "gcode_line", "20010", 0)
            self.assertEqual(reply["status"], "acknowledged")
            self.assertNotIn("executed", reply.values())

    def test_new_session_clears_replies_and_wakes_waiters(self):
        self.replies.observe(self.reply(err_code=0))
        self.replies.reset()
        self.assertIsNone(self.replies.latest())
        self.assertIsNone(self.replies.wait("print", "gcode_line", "20010", 0))
        output = []
        ready = threading.Event()
        def waiting():
            ready.set()
            output.append(self.replies.wait("print", "gcode_line", "20011", 0.2))
        thread = threading.Thread(target=waiting)
        thread.start()
        ready.wait(1)
        self.replies.reset()
        thread.join(1)
        self.assertEqual(output, [None])

    def test_bound_and_invalid_inputs(self):
        for i in range(200):
            self.replies.observe(self.reply(sequence_id=str(20000 + i), err_code=0))
        self.assertEqual(len(self.replies._replies), 64)
        self.assertIsNone(self.replies.wait("print", "gcode_line", "20000", 0))
        for invalid in ([], None, {"print": "bad"}, self.reply(sequence_id=True, err_code=0),
                        self.reply(sequence_id="secret", err_code=0)):
            self.replies.observe(invalid)


class ControllerReplyTests(unittest.TestCase):
    def setUp(self):
        from test_machine import fixture
        self.manager, self.client = fixture()
        self.client.command_replies = module.CommandReplies()

    def test_firmware_rejection_is_error_even_when_native_publish_succeeds(self):
        from test_machine import machine
        self.client.command_replies.observe({"print": {
            "command": "gcode_line", "sequence_id": "20001", "err_code": 84033544}})
        with self.assertRaisesRegex(machine.MachineError, "Printer rejected.*84033544"):
            self.manager.execute("ONE", "home", {})
        self.client.publish.assert_called_once()

    def test_explicit_firmware_acknowledgement_is_returned(self):
        self.client.command_replies.observe({"print": {
            "command": "gcode_line", "sequence_id": "20001", "result": "success"}})
        result = self.manager.execute("ONE", "temperature", {"heater": "bed", "value": 60})
        self.assertEqual(result["status"], "acknowledged")
        self.assertEqual(result["sequence_id"], "20001")
        self.assertIn("physical execution is not confirmed", result["message"])
