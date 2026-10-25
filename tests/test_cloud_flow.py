"""Exercise the actual flow methods using small HA/UI stubs (no live login)."""
import support
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from test_cloud import cloud, complete, fake_api

ROOT = Path(__file__).resolve().parents[1]

class FlowBase:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
    async def async_set_unique_id(self, value):
        self.unique_id = value
    def _abort_if_unique_id_configured(self):
        pass
    def async_show_form(self, **values):
        return {"type": "form", **values}
    def async_show_menu(self, **values):
        return {"type": "menu", **values}
    def async_abort(self, **values):
        return {"type": "abort", **values}
    def async_create_entry(self, **values):
        return {"type": "create_entry", **values}

def load_flow():
    vol = ModuleType("voluptuous")
    vol.Schema = lambda values: values
    vol.Optional = vol.Required = lambda key, **kwargs: key
    vol.In = lambda choices: choices
    ha = ModuleType("homeassistant")
    ha.__path__ = []
    ha.config_entries = SimpleNamespace(ConfigFlow=FlowBase, OptionsFlow=FlowBase)
    core = ModuleType("homeassistant.core")
    core.callback = lambda fn: fn
    helpers = ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    selectors = ModuleType("homeassistant.helpers.selector")
    for name in ("SelectSelector", "SelectSelectorConfig", "TextSelector", "TextSelectorConfig"):
        setattr(selectors, name, lambda *args, **kwargs: (args, kwargs))
    selectors.SelectSelectorMode = SimpleNamespace(LIST="list")
    selectors.TextSelectorType = SimpleNamespace(EMAIL="email", PASSWORD="password")
    name = "custom_components.bambu_open_network.cloud_flow_under_test"
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "custom_components/bambu_open_network/config_flow.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {
        "voluptuous": vol, "homeassistant": ha, "homeassistant.core": core,
        "homeassistant.helpers": helpers, "homeassistant.helpers.selector": selectors,
    }):
        spec.loader.exec_module(module)
    return module

class CloudFlowTests(unittest.TestCase):
    def setUp(self):
        self.module = load_flow()
        self.api = fake_api()
        self.module.CloudLogin = lambda: cloud.CloudLogin(self.api)
        self.module.validate_runtime = lambda: ["native-worker"]
        async def executor(fn, *args):
            return fn(*args)
        self.hass = SimpleNamespace(
            config=SimpleNamespace(config_dir=str(ROOT)),
            async_add_executor_job=executor)

    def flow(self):
        flow = self.module.ConfigFlow()
        flow.hass = self.hass
        return flow

    def login(self, flow):
        return complete(flow.async_step_cloud({
            "region": "Europe", "email": "user@example.test", "password": "private-password"}))

    def test_initial_menu_offers_cloud_and_existing_entries(self):
        result = complete(self.flow().async_step_user())
        self.assertEqual(result["menu_options"], ["cloud", "existing"])

    def test_password_is_masked_and_not_reused_on_failure(self):
        self.api.mode = "denied"
        result = self.login(self.flow())
        self.assertEqual(result["errors"], {"base": "invalid_auth"})
        self.assertNotIn("private-password", repr(result))
        self.assertNotIn("access_code", result["data_schema"])

    def test_full_login_selects_cloud_printer_without_access_code_input(self):
        flow = self.flow()
        result = self.login(flow)
        self.assertEqual(result["step_id"], "printers")
        self.assertNotIn("access_code", result["data_schema"])
        result = complete(flow.async_step_printers({"printers": ["P2S123"]}))
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["data"]["connection_mode"], "cloud")
        self.assertEqual(result["data"]["cloud_session"]["username"], "u_12345")
        self.assertNotIn("private-password", repr(result))
        self.assertIsNone(flow._login)

    def test_email_challenge_then_device_selection(self):
        self.api.mode = "email"
        flow = self.flow()
        result = self.login(flow)
        self.assertEqual(result["step_id"], "verify")
        result = complete(flow.async_step_verify({"code": "wrong"}))
        self.assertEqual(result["errors"]["base"], "code_incorrect")
        result = complete(flow.async_step_verify({"code": "012345"}))
        self.assertEqual(result["step_id"], "printers")

    def test_unlisted_printer_cannot_be_added(self):
        flow = self.flow()
        self.login(flow)
        result = complete(flow.async_step_printers({"printers": ["OTHER_ACCOUNT_PRINTER"]}))
        self.assertEqual(result["type"], "form")
        self.assertEqual(result["errors"]["printers"], "select_printer")

    def test_credential_folder_cannot_escape_ha_config(self):
        flow = self.flow()
        self.login(flow)
        result = complete(flow.async_step_printers({
            "printers": ["P2S123"], "credentials_directory": "../../outside"}))
        self.assertEqual(result["errors"]["credentials_directory"], "outside_config")

    def test_options_login_reuses_the_existing_adapter_entry(self):
        entry = SimpleNamespace(entry_id="adapter-id", data={}, options={})
        flow = self.module.OptionsFlow(entry)
        flow.hass = self.hass
        self.login(flow)
        result = complete(flow.async_step_printers({"printers": ["P2S123"]}))
        self.assertEqual(result["title"], "")
        self.assertEqual(flow._entry.entry_id, "adapter-id")
        self.assertEqual(result["data"]["connection_mode"], "cloud")

    def test_switching_to_existing_mode_drops_account_from_new_options(self):
        flow = self.module.OptionsFlow(SimpleNamespace(data={}, options={}))
        flow.hass = self.hass
        result = complete(flow.async_step_existing({}))
        self.assertEqual(result["data"]["connection_mode"], "existing")
        self.assertIsNone(result["data"]["cloud_session"])
