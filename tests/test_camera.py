"""Cloud video codec, resource limits, disconnection and native pipe tests."""
import support
import base64
from fractions import Fraction
from io import BytesIO
import importlib
import importlib.util
import sys
import threading
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
pkg = ModuleType("custom_components.bambu_open_network")
pkg.__path__ = [str(ROOT / "custom_components/bambu_open_network")]
sys.modules.setdefault("custom_components", ModuleType("custom_components"))
sys.modules.setdefault("custom_components.bambu_open_network", pkg)
video = importlib.import_module("custom_components.bambu_open_network.cloud_camera")


def jpeg():
    output = BytesIO()
    Image.new("RGB", (64, 48), (30, 80, 150)).save(output, "JPEG")
    return output.getvalue()


class CloudCameraTests(unittest.TestCase):
    def setUp(self):
        self.frames = video.CloudFrames()
    def tearDown(self):
        self.frames.close()
    def feed(self, data, codec="mjpeg"):
        self.frames.feed({"codec": codec, "data": base64.b64encode(data).decode()})

    def test_real_mjpeg_frame_is_displayable(self):
        expected = jpeg()
        self.feed(expected)
        result = self.frames.image(3)
        self.assertEqual(result, expected)
        with Image.open(BytesIO(result)) as image:
            self.assertEqual(image.size, (64, 48))
        self.assertEqual(self.frames.state, "streaming")

    def test_disconnect_clears_image_and_wakes_waiter(self):
        self.feed(jpeg())
        self.assertIsNotNone(self.frames.image(3))
        self.frames.set_state("disconnected")
        self.assertIsNone(self.frames.image())
        output = []
        self.frames.set_state("connecting")
        waiting = threading.Thread(target=lambda: output.append(self.frames.image(10)))
        waiting.start()
        self.frames.close()
        waiting.join(1)
        self.assertFalse(waiting.is_alive())
        self.assertEqual(output, [None])

    def test_stale_and_failed_sessions_never_return_old_frame(self):
        self.feed(jpeg())
        self.assertIsNotNone(self.frames.image(3))
        self.frames._updated = time.monotonic() - 20
        self.assertIsNone(self.frames.image())
        self.frames.set_state("missing_signing_credentials")
        self.assertIsNone(self.frames.image(1))

    def test_malformed_and_oversized_frames_do_not_break_decoder(self):
        for value in ("%%%", "a" * (4 * video.MAX_FRAME), None):
            self.frames.feed({"codec": "mjpeg", "data": value})
        self.feed(b"\xff\xd8not-a-jpeg\xff\xd9")
        self.feed(jpeg())
        self.assertIsNotNone(self.frames.image(3))

    def test_queue_has_byte_and_frame_limits(self):
        # Freeze the consumer to model a much slower decoder.
        self.frames._thread = SimpleNamespace(is_alive=lambda: True)
        for _ in range(20):
            self.feed(b"x" * (1024 * 1024), "h264")
        self.assertLessEqual(self.frames._bytes, video.MAX_BUFFER)
        self.assertLessEqual(len(self.frames._queue), 60)
        self.assertGreater(self.frames._generation, 0)
        self.frames._thread = None

    def test_unknown_status_cannot_leak_native_text(self):
        self.frames.set_state("secret token=abc")
        self.assertEqual(self.frames.state, "camera_failed")

    @unittest.skipUnless(importlib.util.find_spec("av"), "PyAV required for real H.264 test")
    def test_real_h264_access_units_decode_to_jpeg(self):
        import av
        encoder = av.CodecContext.create("libx264", "w")
        encoder.width, encoder.height = 64, 48
        encoder.pix_fmt = "yuv420p"
        encoder.time_base = Fraction(1, 10)
        encoder.options = {"preset": "ultrafast", "tune": "zerolatency",
                           "x264-params": "keyint=1:repeat-headers=1"}
        frame = av.VideoFrame.from_image(Image.new("RGB", (64, 48), "green"))
        for packet in list(encoder.encode(frame)) + list(encoder.encode(None)):
            self.feed(bytes(packet), "h264")
        result = self.frames.image(3)
        self.assertIsNotNone(result)
        with Image.open(BytesIO(result)) as decoded:
            self.assertEqual(decoded.size, (64, 48))

    def test_decoder_absence_is_reported_without_stopping_mqtt(self):
        with patch.dict(sys.modules, {"av": None}):
            self.feed(b"\x00\x00\x00\x01\x65test", "h264")
            self.assertIsNone(self.frames.image(3))
            self.assertEqual(self.frames.state, "decoder_unavailable")
