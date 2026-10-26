"""Bounded, redacted MQTT command replies, correlated by section/name/wire ID."""
from __future__ import annotations

from collections import OrderedDict
import threading
import time

MAX_REPLIES = 64
MAX_REPLY_AGE = 60


class CommandReplies:
    def __init__(self):
        self._condition = threading.Condition()
        self._replies = OrderedDict()
        self._latest = None
        self._generation = 0

    def reset(self):
        with self._condition:
            self._generation += 1
            self._replies.clear()
            self._latest = None
            self._condition.notify_all()

    @staticmethod
    def _integer(value):
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and len(value) <= 12:
            try:
                return int(value)
            except ValueError:
                pass
        return None

    def observe(self, body):
        if not isinstance(body, dict):
            return
        for section in ("print", "system"):
            item = body.get(section)
            if not isinstance(item, dict):
                continue
            command = item.get("command")
            raw_sequence = item.get("sequence_id")
            if (not isinstance(command, str) or not command.isidentifier()
                    or len(command) > 64 or command == "push_status"
                    or isinstance(raw_sequence, bool)
                    or not isinstance(raw_sequence, (str, int))):
                continue
            sequence = str(raw_sequence)
            if not sequence.isascii() or not sequence.isdecimal() or len(sequence) > 10:
                continue
            error = self._integer(item.get("err_code", item.get("errno")))
            result = item.get("result")
            token = result.lower() if isinstance(result, str) else None
            numeric_result = result if isinstance(result, int) and not isinstance(result, bool) else None
            rejected = (numeric_result is not None and numeric_result != 0) or (error is not None and error != 0) or token in ("fail", "failed", "error", "failure")
            acknowledged = numeric_result == 0 or error == 0 or token in ("success", "succeed", "ok")
            # An echoed request or unsolicited telemetry is not an acknowledgement.
            if not rejected and not acknowledged:
                continue
            reply = {"section": section, "command": command,
                     "sequence_id": sequence,
                     "status": "rejected" if rejected else "acknowledged",
                     "error_code": error}
            with self._condition:
                key = (section, command, sequence)
                self._replies[key] = (time.monotonic(), reply)
                self._replies.move_to_end(key)
                while len(self._replies) > MAX_REPLIES:
                    self._replies.popitem(last=False)
                self._latest = (time.monotonic(), reply)
                self._condition.notify_all()

    def wait(self, section, command, sequence, timeout=2):
        deadline = time.monotonic() + timeout
        key = (section, command, str(sequence))
        with self._condition:
            generation = self._generation
            while generation == self._generation:
                found = self._replies.get(key)
                if found and time.monotonic() - found[0] <= MAX_REPLY_AGE:
                    return dict(found[1])
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(remaining)
        return None

    def latest(self):
        with self._condition:
            if self._latest and time.monotonic() - self._latest[0] <= MAX_REPLY_AGE:
                return dict(self._latest[1])
        return None
