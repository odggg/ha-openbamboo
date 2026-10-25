"""Scoped factory and signing guard tests without network/event-loop dependencies."""
import contextvars
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace, coroutine
import unittest
from unittest.mock import patch as mock_patch

ROOT = Path(__file__).resolve().parents[1]
pkg = sys.modules.get("custom_components.bambu_open_network")
if pkg is None:
    pkg = ModuleType("custom_components.bambu_open_network")
    pkg.__path__ = [str(ROOT / "custom_components/bambu_open_network")]
    sys.modules.setdefault("custom_components", ModuleType("custom_components"))
    sys.modules["custom_components.bambu_open_network"] = pkg
mod = importlib.import_module("custom_components.bambu_open_network.patch")
OpenBambooClient = mod.OpenBambooClient

@coroutine
def suspend_once():
    yield

def complete(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as done:
            return done.value

class PatchTests(unittest.TestCase):
    def setUp(self):
        self.original_mqtt = SimpleNamespace(Client=lambda *a, **kw: "original", sentinel=42)
        self.client_module = SimpleNamespace(mqtt=self.original_mqtt)
        module = self.client_module
        class BambuClient:
            _mock = False
            async def connect(self, callback=None):
                await suspend_once()
                return module.mqtt.Client()
            async def try_connection(self):
                return module.mqtt.Client()
        class PrintFun:
            @property
            def mqtt_signature_required(self):
                return self._encryption_enabled
        self.client_module.BambuClient = BambuClient
        self.models = SimpleNamespace(PrintFun=PrintFun)
        self.original_connect = BambuClient.connect
        self.original_required = PrintFun.mqtt_signature_required
        self.patch = mod.TransportPatch(
            self.client_module, self.models, ["worker"], Path("state"), Path("credentials"))
        self.contract = mock_patch.object(mod, "check_contract")
        self.contract.start()
        self.patch.install()

    def tearDown(self):
        self.patch.restore()
        self.contract.stop()

    def owner(self):
        owner = self.client_module.BambuClient()
        owner._local_mqtt = True
        return owner

    def test_existing_class_references_use_new_transport(self):
        owner = self.owner()
        client = complete(owner.connect())
        self.assertIsInstance(client, OpenBambooClient)
        self.assertIs(client.owner, owner)

    def test_no_global_paho_patch(self):
        self.assertEqual(self.original_mqtt.Client(), "original")
        self.assertEqual(self.client_module.mqtt.Client(), "original")
        self.assertEqual(self.client_module.mqtt.sentinel, 42)

    def test_mock_printers_keep_original_transport(self):
        owner = self.owner()
        owner._mock = True
        self.assertEqual(complete(owner.connect()), "original")

    def test_interleaved_config_flows_keep_owner_context(self):
        one, two = self.owner(), self.owner()
        first, second = one.connect(), two.connect()
        ctx_one, ctx_two = contextvars.copy_context(), contextvars.copy_context()
        ctx_one.run(first.send, None)
        ctx_two.run(second.send, None)
        client_one = ctx_one.run(complete, first)
        client_two = ctx_two.run(complete, second)
        self.assertIs(client_one.owner, one)
        self.assertIs(client_two.owner, two)
        self.assertIsNone(mod._CURRENT_OWNER.get())

    def test_guard_only_relaxes_for_our_live_acknowledged_backend(self):
        owner = self.owner()
        owner.client = complete(owner.connect())
        value = self.models.PrintFun()
        value._client, value._encryption_enabled = owner, True
        self.assertTrue(value.mqtt_signature_required)
        owner.client._connected = owner.client.signed_ready = True
        self.assertFalse(value.mqtt_signature_required)
        self.assertTrue(value._encryption_enabled)
        owner.client.disconnect()
        self.assertTrue(value.mqtt_signature_required)

    def test_restore_preserves_original_objects(self):
        self.patch.restore()
        self.assertIs(self.client_module.mqtt, self.original_mqtt)
        self.assertIs(self.client_module.BambuClient.connect, self.original_connect)
        self.assertIs(self.models.PrintFun.mqtt_signature_required, self.original_required)

    def test_unknown_contract_leaves_upstream_untouched(self):
        self.patch.restore()
        with mock_patch.object(mod, "check_contract", side_effect=mod.IncompatibleUpstream("changed")):
            with self.assertRaises(mod.IncompatibleUpstream):
                self.patch.install()
        self.assertIs(self.client_module.mqtt, self.original_mqtt)
