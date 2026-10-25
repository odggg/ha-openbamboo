"""Panel lifecycle and authorization using real HA websocket decorators.

Registry/executor objects are fixtures; schemas use actual voluptuous/probatio.
"""
import support
import asyncio
import functools
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
import voluptuous
import probatio

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "bambu_open_network"


class Unauthorized(Exception):
    pass


def load_panel(modern=True):
    schema = probatio if modern else voluptuous
    namespace = {
        "vol": schema, "probatio": schema, "wraps": functools.wraps,
        "callback": lambda fn: fn, "Unauthorized": Unauthorized, "TYPE_CHECKING": False,
        "messages": NS(BASE_COMMAND_MESSAGE_SCHEMA=schema.Schema({
            schema.Required("id"): int, schema.Required("type"): str})),
    }
    source = (ROOT / "tests/fixtures/ha_websocket_decorators.py.txt").read_text(encoding="utf-8")
    exec(compile(source, "ha_websocket_decorators_fixture", "exec"), namespace)
    ws = ModuleType("homeassistant.components.websocket_api")
    for name in ("websocket_command", "async_response", "require_admin"):
        setattr(ws, name, namespace[name])
    ws.async_register_command = Mock()
    frontend = NS(async_remove_panel=Mock())
    components = ModuleType("homeassistant.components")
    components.frontend = frontend
    components.websocket_api = ws
    http = ModuleType("homeassistant.components.http")
    http.StaticPathConfig = lambda *args: args
    custom = ModuleType("homeassistant.components.panel_custom")
    async def register(*args, **kwargs):
        custom.registrations.append(kwargs)
    custom.registrations = []
    custom.async_register_panel = register
    errors = ModuleType("homeassistant.exceptions")
    errors.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
    helpers = ModuleType("homeassistant.helpers")
    helpers.device_registry = NS(async_get=lambda hass: hass.devices)
    helpers.entity_registry = NS(async_get=lambda hass: hass.entities)
    service = ModuleType("homeassistant.helpers.service")
    service.async_register_admin_service = Mock()
    modules = {
        "homeassistant.components": components, "homeassistant.components.websocket_api": ws,
        "homeassistant.components.http": http, "homeassistant.components.panel_custom": custom,
        "homeassistant.exceptions": errors, "homeassistant.helpers": helpers,
        "homeassistant.helpers.service": service, "probatio": probatio if modern else None,
    }
    spec = importlib.util.spec_from_file_location(
        "custom_components.bambu_open_network.panel_under_test",
        ROOT / "custom_components/bambu_open_network/panel.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module, custom, service


class PanelTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.module, self.custom, self.service = load_panel()
        self.tasks = []
        async def executor(fn, *args):
            return fn(*args)
        async def static(configs):
            self.routes.append(configs)
        self.routes = []
        self.entry = NS(data={"serial": "ONE"}, options={"name": "Cloud name"}, title="Entry")
        self.manager = NS(status=Mock(return_value={"ready": True}), execute=Mock(return_value={"status": "accepted"}))
        self.adapter = NS(active=True, machine_controller=self.manager)
        self.hass = NS(
            data={DOMAIN: self.adapter},
            async_add_executor_job=executor,
            async_create_background_task=lambda coro, *args, **kwargs: self.tasks.append(asyncio.create_task(coro)),
            config_entries=NS(async_entries=lambda domain: [self.entry]),
            devices=NS(
                async_get_device=lambda **kwargs: NS(name_by_user="Mein Drucker", name="Cloud name"),
                async_get=lambda key: NS(identifiers={("bambu_lab", "ONE")}) if key == "DEVICE" else None),
            entities=NS(async_get_entity_id=lambda *args: "camera.one_cloud"),
            http=NS(async_register_static_paths=static),
            services=NS(async_remove=Mock()))
        self.connection = NS(user=NS(is_admin=True), send_result=Mock(), send_error=Mock(),
                             async_handle_exception=Mock())

    async def dispatch(self, fn, message):
        fn(self.hass, self.connection, fn._ws_schema(message) if fn._ws_schema else message)
        await asyncio.gather(*self.tasks)
        self.tasks.clear()

    async def test_admin_list_preserves_user_name_and_camera(self):
        await self.dispatch(self.module.ws_machines, {"type": DOMAIN + "/machines", "id": 1})
        item = self.connection.send_result.call_args.args[1]["printers"][0]
        self.assertEqual(item["name"], "Mein Drucker")
        self.assertEqual(item["camera"], "camera.one_cloud")

    async def test_non_admin_and_missing_user_cannot_list_or_send(self):
        for user in (None, NS(is_admin=False)):
            self.connection.user = user
            for handler, msg in (
                (self.module.ws_machines, {"type": DOMAIN + "/machines", "id": 1}),
                (self.module.ws_command, {"type": DOMAIN + "/machine_command", "id": 2,
                                         "serial": "ONE", "action": "home"})):
                with self.assertRaises(Unauthorized):
                    await self.dispatch(handler, msg)
        self.manager.execute.assert_not_called()
        self.manager.status.assert_not_called()

    async def test_command_validates_printer_then_uses_current_adapter(self):
        msg = {"type": DOMAIN + "/machine_command", "id": 3, "serial": "ONE",
               "action": "gcode", "params": {"gcode": "M105\nM114"}}
        await self.dispatch(self.module.ws_command, msg)
        self.manager.execute.assert_called_once_with("ONE", "gcode", {"gcode": "M105\nM114"})
        msg["serial"] = "OTHER"
        await self.dispatch(self.module.ws_command, msg)
        self.assertEqual(self.manager.execute.call_count, 1)
        self.connection.send_error.assert_called_once()

    async def test_unload_rejects_existing_websocket_handlers(self):
        self.hass.data.pop(DOMAIN)
        await self.dispatch(self.module.ws_command, {"type": DOMAIN + "/machine_command",
            "id": 4, "serial": "ONE", "action": "home"})
        self.manager.execute.assert_not_called()
        self.connection.send_error.assert_called_once()

    async def test_schema_compatibility_old_and_new_ha(self):
        for modern in (False, True):
            module, _, _ = load_panel(modern)
            valid = module.ws_command._ws_schema({"type": DOMAIN + "/machine_command",
                "id": 5, "serial": "ONE", "action": "home"})
            self.assertEqual(valid["params"], {})
            with self.assertRaises(Exception):
                module.ws_command._ws_schema({"type": DOMAIN + "/machine_command",
                    "id": 5, "serial": 123, "action": "home"})

    async def test_static_route_reused_admin_panel_and_admin_automation_service(self):
        # Setup replaces the current controller; command delivery tested separately.
        await self.module.async_setup_panel(self.hass, self.adapter)
        await self.module.async_setup_panel(self.hass, self.adapter)
        self.assertEqual(len(self.routes), 1)
        self.assertTrue(self.custom.registrations[-1]["require_admin"])
        registration = self.service.async_register_admin_service.call_args
        self.assertEqual(registration.args[1:3], (DOMAIN, "send_gcode"))
        schema = registration.args[4]
        self.assertFalse(schema({"device_id": "DEVICE", "gcode": "M105"})["allow_during_print"])
        self.module.async_unload_panel(self.hass)
        self.hass.services.async_remove.assert_called_once_with(DOMAIN, "send_gcode")
