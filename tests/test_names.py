"""Printer import names, custom HA names and reversible device metadata."""
import support
from types import SimpleNamespace
import importlib
import unittest

from test_cloud import cloud, complete, entries_mod, Entries, PRINTER, SESSION, fake_api
names = importlib.import_module("custom_components.bambu_open_network.names")


class PrinterNameTests(unittest.TestCase):
    def sync(self, entry, printer=None, fail=False):
        entries = Entries([entry], fail_create=fail)
        printers = [printer or PRINTER]
        if fail:
            printers.append({**PRINTER, "serial": "NEW"})
        complete(entries_mod.sync_cloud_printers(SimpleNamespace(config_entries=entries),
            {"cloud_session": SESSION, "cloud_printers": printers}))
        return entries

    def test_new_import_uses_cloud_name_as_entry_title(self):
        class Flow:
            async def async_set_unique_id(self, value):
                self.unique_id = value
            def _abort_if_unique_id_configured(self):
                pass
            def async_create_entry(self, **kwargs):
                return kwargs
        hook = entries_mod.CloudImportHook(Flow)
        hook.install()
        try:
            flow = Flow()
            flow.hass = SimpleNamespace(config_entries=Entries())
            result = complete(flow.async_step_import(entries_mod.printer_payload(SESSION, PRINTER)))
            self.assertEqual(result["title"], "Farm P2S")
            self.assertEqual(result["options"]["name"], "Farm P2S")
            self.assertEqual(flow.unique_id, "P2S123")
        finally:
            hook.restore()

    def test_existing_serial_title_is_upgraded_without_changing_entry_id(self):
        entry = SimpleNamespace(entry_id="original", title="P2S123",
            data={"serial": "P2S123"}, options={"name": "P2S_P2S123"})
        self.sync(entry)
        self.assertEqual(entry.title, "Farm P2S")
        self.assertEqual(entry.options["name"], "Farm P2S")
        self.assertEqual(entry.entry_id, "original")

    def test_existing_custom_names_are_kept(self):
        entry = SimpleNamespace(entry_id="original", title="My workshop",
            data={"serial": "P2S123"}, options={"name": "Custom HA name"})
        self.sync(entry)
        self.assertEqual(entry.title, "My workshop")
        self.assertEqual(entry.options["name"], "Custom HA name")

    def test_legacy_name_in_entry_data_is_preserved(self):
        entry = SimpleNamespace(entry_id="original", title="P2S123",
            data={"serial": "P2S123", "name": "Legacy HA name"}, options={})
        self.sync(entry)
        self.assertEqual(entry.options["name"], "Legacy HA name")
        self.assertEqual(entry.title, "Legacy HA name")

    def test_previous_cloud_names_follow_a_later_import(self):
        entry = SimpleNamespace(entry_id="original", title="Old cloud name",
            data={"serial": "P2S123"}, options={
                "name": "Old cloud name", "_open_bamboo_cloud_name": "Old cloud name"})
        self.sync(entry)
        self.assertEqual(entry.title, "Farm P2S")
        self.assertEqual(entry.options["name"], "Farm P2S")

    def test_user_edit_after_import_is_not_overwritten(self):
        entry = SimpleNamespace(entry_id="original", title="User title",
            data={"serial": "P2S123"}, options={
                "name": "User name", "_open_bamboo_cloud_name": "Previous cloud name"})
        self.sync(entry)
        self.assertEqual(entry.title, "User title")
        self.assertEqual(entry.options["name"], "User name")

    def test_failed_multi_printer_import_restores_name_and_title(self):
        old = {"name": "P2S_P2S123"}
        entry = SimpleNamespace(entry_id="original", title="P2S123",
            data={"serial": "P2S123"}, options=dict(old))
        with self.assertRaises(ValueError):
            self.sync(entry, fail=True)
        self.assertEqual(entry.title, "P2S123")
        self.assertEqual(entry.options, old)

    def test_cloud_name_keeps_unicode_and_falls_back_for_invalid_name(self):
        login = cloud.CloudLogin(fake_api())
        login.login("Europe", "you@example.test", "test-password")
        login.client.get_device_list = lambda: [
            {"dev_id": "ONE", "dev_product_name": "P2S", "name": "  Werkstatt \u00e4 \U0001f5a8  "},
            {"dev_id": "TWO", "dev_product_name": "P1S", "name": 123},
            {"dev_id": "THREE", "dev_product_name": "A1", "name": "   "}]
        self.assertEqual([p["name"] for p in login.printers()],
                         ["Werkstatt \u00e4 \U0001f5a8", "P1S", "A1"])

    def test_device_name_patch_preserves_metadata_and_restores_original(self):
        original_info = {"name": "P2S_P2S123", "identifiers": {("bambu_lab", "P2S123")},
                         "model": "P2S", "sw_version": "firmware"}
        class Coordinator:
            def get_printer_device(self):
                return original_info
        original_method = Coordinator.get_printer_device
        patch = names.PrinterNamePatch(Coordinator)
        patch.install()
        try:
            coordinator = Coordinator()
            coordinator.config_entry = SimpleNamespace(options={
                "name": "Farm P2S", "_open_bamboo_cloud_name": "Farm P2S"})
            result = coordinator.get_printer_device()
            self.assertEqual(result["name"], "Farm P2S")
            self.assertEqual(result["identifiers"], original_info["identifiers"])
            self.assertEqual(result["sw_version"], "firmware")
            self.assertEqual(original_info["name"], "P2S_P2S123")
            self.assertNotIn("name_by_user", result)
            coordinator.config_entry.options = {"name": "Unmanaged printer"}
            self.assertIs(coordinator.get_printer_device(), original_info)
        finally:
            patch.restore()
        self.assertIs(Coordinator.get_printer_device, original_method)
