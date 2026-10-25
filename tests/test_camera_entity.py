"""Exercise the actual HA camera entity with small registry/executor stubs."""
import support
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from test_camera import video

ROOT = Path(__file__).resolve().parents[1]


def run_immediate(coro):
    try:
        coro.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError("Unexpected pending await in fixture")


def load_camera():
    base = ModuleType("homeassistant.components.camera")
    class Camera:
        def __init__(self):
            pass
        async def async_added_to_hass(self):
            pass
    base.Camera = Camera
    helpers = ModuleType("homeassistant.helpers")
    helpers.device_registry = SimpleNamespace()
    helpers.entity_registry = SimpleNamespace()
    errors = ModuleType("homeassistant.exceptions")
    errors.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
    spec = importlib.util.spec_from_file_location(
        "custom_components.bambu_open_network.camera_under_test",
        ROOT / "custom_components/bambu_open_network/camera.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "homeassistant.components.camera": base,
        "homeassistant.helpers": helpers,
        "homeassistant.exceptions": errors,
    }):
        spec.loader.exec_module(module)
    return module


class CameraEntityTests(unittest.TestCase):
    def setUp(self):
        self.module = load_camera()
        self.client = SimpleNamespace(
            owner=SimpleNamespace(_serial="ONE", _local_mqtt=False),
            is_connected=lambda: True, camera=video.CloudFrames())
        adapter = SimpleNamespace(active=True, snapshot_clients=lambda: [self.client])
        self.hass = SimpleNamespace(data={"bambu_open_network": adapter})
        self.printer = SimpleNamespace(data={"serial": "ONE"}, entry_id="upstream-one")
        self.entity = self.module.OpenBambooCloudCamera(self.hass, self.printer)
    def tearDown(self):
        self.client.camera.close()

    def test_matches_cloud_worker_and_not_another_printer(self):
        self.assertTrue(self.entity.available)
        self.client.owner._serial = "TWO"
        self.assertFalse(self.entity.available)
        self.client.owner._serial = "ONE"
        self.client.owner._local_mqtt = True
        self.assertFalse(self.entity.available)

    def test_missing_credentials_are_actionable_and_attributes_are_redacted(self):
        self.client.camera.set_state("missing_signing_credentials")
        self.client.request_camera = lambda: None
        async def executor(fn, *args):
            return fn(*args)
        self.hass.async_add_executor_job = executor
        with self.assertRaisesRegex(Exception, "slicer_key.pem"):
            run_immediate(self.entity.async_camera_image())
        self.assertEqual(self.entity.extra_state_attributes, {
            "transport": "cloud_tutk",
            "camera_status": "missing_signing_credentials",
            "last_error": "missing_signing_credentials"})

    def test_links_existing_upstream_device_by_config_entry_without_duplicate(self):
        calls = []
        registry = SimpleNamespace(
            async_get=lambda entity_id: object(),
            async_update_entity=lambda *args, **kwargs: calls.append((args, kwargs)))
        dr = self.module.device_registry
        dr.async_get = lambda hass: object()
        dr.async_entries_for_config_entry = lambda registry, entry_id: [
            SimpleNamespace(id="existing-printer-device",
                            identifiers={("bambu_lab", "ONE")})]
        self.module.entity_registry.async_get = lambda hass: registry
        self.entity.entity_id = "camera.one_cloud_camera"
        self.entity._link_printer()
        self.assertEqual(calls, [
            (("camera.one_cloud_camera",), {"device_id": "existing-printer-device"})])
        self.assertTrue(self.entity._linked)

    def test_platform_only_creates_cameras_for_cloud_entries(self):
        local = SimpleNamespace(data={"serial": "LAN"}, options={"local_mqtt": True},
                                entry_id="local")
        self.printer.options = {"local_mqtt": False}
        self.hass.config_entries = SimpleNamespace(
            async_entries=lambda domain: [local, self.printer])
        added = []
        run_immediate(self.module.async_setup_entry(self.hass, None, added.extend))
        self.assertEqual([entity._serial for entity in added], ["ONE"])
