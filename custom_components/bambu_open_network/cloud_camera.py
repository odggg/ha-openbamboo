"""Bounded native video decoding, shared by all viewers of one printer.

Frames and TUTK session credentials never enter entity attributes/diagnostics.
The HA stream dependency supplies PyAV. No network IO is performed here.
"""
from __future__ import annotations

import base64
import binascii
from collections import deque
from io import BytesIO
import threading
import time

MAX_FRAME = 2 * 1024 * 1024
MAX_BUFFER = 8 * 1024 * 1024
MAX_AGE = 15
STATES = frozenset({
    "idle", "connecting", "streaming", "missing_signing_credentials",
    "cloud_camera_rejected", "invalid_camera_session", "camera_timeout",
    "camera_failed", "decoder_unavailable", "decode_failed", "disconnected",
})
ERRORS = STATES - {"idle", "connecting", "streaming", "disconnected"}


class CloudFrames:
    def __init__(self):
        self.state = "idle"
        self._condition = threading.Condition()
        self._queue = deque()
        self._bytes = 0
        self._jpeg = None
        self._updated = 0.0
        self._closed = False
        self._thread = None
        self._generation = 0

    def set_state(self, state):
        if state not in STATES:
            state = "camera_failed"
        with self._condition:
            self.state = state
            if state != "streaming":
                self._jpeg = None
                self._updated = 0.0
                self._queue.clear()
                self._bytes = 0
                self._generation += 1
            self._condition.notify_all()

    def feed(self, event):
        codec = event.get("codec")
        encoded = event.get("data")
        if codec not in ("mjpeg", "h264") or not isinstance(encoded, str):
            return
        if len(encoded) > 4 * ((MAX_FRAME + 2) // 3):
            return
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            return
        if not data or len(data) > MAX_FRAME:
            return
        if codec == "mjpeg" and not (data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9")):
            return
        with self._condition:
            if self._closed:
                return
            if self._bytes + len(data) > MAX_BUFFER or len(self._queue) >= 60:
                # After dropping H.264 references, reset the decoder and wait
                # for parameter sets/IDR rather than showing corrupt frames.
                self._queue.clear()
                self._bytes = 0
                self._generation += 1
            self._queue.append((self._generation, codec, data))
            self._bytes += len(data)
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._decode,
                                                name="OBN-Camera", daemon=True)
                self._thread.start()
            self._condition.notify_all()

    @property
    def frame_age(self):
        """Age of the last decoded frame; no image or credentials in telemetry."""
        with self._condition:
            if self._closed or self._jpeg is None or not self._updated:
                return None
            return max(0.0, time.monotonic() - self._updated)

    def image(self, timeout=0):
        deadline = time.monotonic() + timeout
        with self._condition:
            while not self._closed:
                if self._jpeg and time.monotonic() - self._updated < MAX_AGE:
                    return self._jpeg
                if self.state in ERRORS or self.state == "disconnected":
                    return None
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(remaining)
        return None

    def _store(self, jpeg, generation):
        if len(jpeg) > MAX_FRAME:
            return
        with self._condition:
            if self._closed or generation != self._generation:
                return
            self._jpeg = jpeg
            self._updated = time.monotonic()
            self.state = "streaming"
            self._condition.notify_all()

    def _decode(self):
        decoder = None
        generation = -1
        last_output = 0.0
        while True:
            with self._condition:
                # One decoder thread per viewed printer; no executor backlog.
                if not self._queue and not self._closed:
                    self._condition.wait(10)
                if self._closed:
                    return
                if not self._queue:
                    continue
                item_generation, codec, data = self._queue.popleft()
                self._bytes -= len(data)
            if item_generation != generation:
                generation, decoder = item_generation, None
            if codec == "mjpeg":
                # Verify JPEG dimensions and integrity off the RPC thread.
                try:
                    from PIL import Image
                    with Image.open(BytesIO(data)) as image:
                        if image.width > 4096 or image.height > 4096:
                            continue
                        image.verify()
                    self._store(data, generation)
                except (OSError, ValueError):
                    continue
                continue
            try:
                import av
            except ImportError:
                self.set_state("decoder_unavailable")
                return
            try:
                if decoder is None:
                    decoder = av.CodecContext.create("h264", "r")
                    decoder.thread_count = 1
                # TUTK supplies complete Annex-B access units.
                for frame in decoder.decode(av.Packet(data)):
                    now = time.monotonic()
                    if now - last_output < 0.25:
                        continue
                    if frame.width > 4096 or frame.height > 4096:
                        continue
                    output = BytesIO()
                    frame.to_image().save(output, "JPEG", quality=80)
                    self._store(output.getvalue(), generation)
                    last_output = now
            except Exception:
                # Decoder errors are common until the next H.264 IDR. Never
                # leak packet content in exception messages or kill MQTT.
                decoder = None

    def close(self, wait=True):
        with self._condition:
            self._closed = True
            self._jpeg = None
            self._queue.clear()
            self._bytes = 0
            self.state = "disconnected"
            self._condition.notify_all()
        if wait and self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=3)
