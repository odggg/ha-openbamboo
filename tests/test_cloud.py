"""Cloud login challenges and normal ha-bambulab entry migration."""
import support
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
if "custom_components.bambu_open_network" not in sys.modules:
    pkg = ModuleType("custom_components.bambu_open_network")
    pkg.__path__ = [str(ROOT / "custom_components/bambu_open_network")]
    sys.modules.setdefault("custom_components", ModuleType("custom_components"))
    sys.modules["custom_components.bambu_open_network"] = pkg
cloud = importlib.import_module("custom_components.bambu_open_network.cloud")
entries_mod = importlib.import_module("custom_components.bambu_open_network.cloud_entries")

def complete(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as done:
            return done.value

def fake_api(mode="direct"):
    api = SimpleNamespace(mode=mode)
    for name in ("CodeRequiredError", "CodeIncorrectError", "CodeExpiredError",
                 "TfaCodeRequiredError", "CloudflareError", "CsrfError", "CsrfObtainError"):
        setattr(api, name, type(name, (Exception,), {}))
    class BambuCloud:
        def __init__(self, *args):
            self.auth_token = self.username = ""
            self._password = ""
            self.code_requests = 0
        def login(self, region, email, password):
            self._password = password
            if api.mode == "email":
                raise api.CodeRequiredError()
            if api.mode in ("tfa", "csrf"):
                raise api.TfaCodeRequiredError()
            if api.mode == "denied":
                raise PermissionError("secret-response")
            if api.mode == "blocked":
                raise api.CloudflareError()
            if api.mode == "invalid_token":
                self.auth_token = ValueError("bad upstream response")
                return
            self.auth_token, self.username = "session-token", "u_12345"
        def login_with_verification_code(self, code):
            if code == "expired":
                raise api.CodeExpiredError()
            if code != "012345":
                raise api.CodeIncorrectError()
            self.auth_token, self.username = "session-token", "u_12345"
        def login_with_2fa_code(self, code):
            if api.mode == "csrf":
                raise api.CsrfObtainError()
            self.login_with_verification_code(code)
        def request_new_code(self):
            self.code_requests += 1
        def get_device_list(self):
            if api.mode == "offline":
                return None
            return [
                {"dev_id": "P2S123", "dev_product_name": "P2S", "name": "Farm P2S",
                 "dev_access_code": "account-code"},
                {"dev_id": "P2S123", "dev_product_name": "P2S"},
                {"dev_id": "../invalid", "dev_product_name": "P2S"},
            ]
        def get_device_type_from_device_product_name(self, name):
            return name.replace(" ", "").upper()
    api.BambuCloud = BambuCloud
    return api

class CloudLoginTests(unittest.TestCase):
    def test_direct_login_drops_password_and_exposes_only_session_fields(self):
        login = cloud.CloudLogin(fake_api())
        self.assertEqual(login.login("Europe", " user@example.test ", "private-password"), "ready")
        self.assertEqual(login.client._password, "")
        self.assertEqual(set(login.session()), {"region", "email", "username", "auth_token"})
        self.assertEqual(login.session()["email"], "user@example.test")
        self.assertNotIn("private-password", repr(login.session()))

    def test_email_code_login(self):
        login = cloud.CloudLogin(fake_api("email"))
        self.assertEqual(login.login("Europe", "user@example.test", "private"), "email_code")
        self.assertEqual(login.client._password, "")
        self.assertEqual(login.verify("012345"), "ready")

    def test_two_factor_login(self):
        login = cloud.CloudLogin(fake_api("tfa"))
        self.assertEqual(login.login("Europe", "user@example.test", "private"), "two_factor")
        self.assertEqual(login.verify("012345"), "ready")

    def test_csrf_failure_falls_back_to_email_code(self):
        login = cloud.CloudLogin(fake_api("csrf"))
        login.login("Europe", "user@example.test", "private")
        self.assertEqual(login.verify("012345"), "email_code")
        self.assertEqual(login.client.code_requests, 1)
        self.assertEqual(login.verify("012345"), "ready")

    def test_wrong_or_expired_code_is_retryable(self):
        login = cloud.CloudLogin(fake_api("email"))
        login.login("Europe", "user@example.test", "private")
        for code, expected in (("wrong", "code_incorrect"), ("expired", "code_expired"),
                               ("", "code_needed")):
            with self.assertRaisesRegex(cloud.CloudLoginError, expected):
                login.verify(code)
            self.assertEqual(login.stage, "email_code")
        self.assertEqual(login.verify("012345"), "ready")

    def test_auth_errors_do_not_expose_server_responses(self):
        login = cloud.CloudLogin(fake_api("denied"))
        with self.assertRaises(cloud.CloudLoginError) as result:
            login.login("Europe", "user@example.test", "private")
        self.assertEqual(str(result.exception), "invalid_auth")
        self.assertEqual(login.client._password, "")

    def test_cloudflare_has_a_distinct_error(self):
        with self.assertRaisesRegex(cloud.CloudLoginError, "cloud_blocked"):
            cloud.CloudLogin(fake_api("blocked")).login("Europe", "user@example.test", "private")

    def test_invalid_upstream_token_is_not_saved(self):
        login = cloud.CloudLogin(fake_api("invalid_token"))
        with self.assertRaisesRegex(cloud.CloudLoginError, "invalid_auth"):
            login.login("Europe", "user@example.test", "private")

    def test_printer_list_is_sanitized_and_deduplicated(self):
        login = cloud.CloudLogin(fake_api())
        login.login("Europe", "user@example.test", "private")
        printers = login.printers()
        self.assertEqual(len(printers), 1)
        self.assertEqual(printers[0]["serial"], "P2S123")
        self.assertEqual(printers[0]["access_code"], "account-code")

    def test_connection_failure_is_not_an_empty_printer_list(self):
        api = fake_api()
        login = cloud.CloudLogin(api)
        login.login("Europe", "user@example.test", "private")
        api.mode = "offline"
        with self.assertRaisesRegex(cloud.CloudLoginError, "cannot_connect"):
            login.printers()

    def test_resend_requests_email_code(self):
        login = cloud.CloudLogin(fake_api("tfa"))
        login.login("China", "user@example.test", "private")
        self.assertEqual(login.resend(), "email_code")
        self.assertEqual(login.client.code_requests, 1)

SESSION = {"region": "Europe", "email": "user@example.test",
           "username": "u_12345", "auth_token": "session-token"}
PRINTER = {"serial": "P2S123", "device_type": "P2S", "name": "Farm P2S", "access_code": ""}

class Entries:
    def __init__(self, initial=(), fail_create=False):
        self.entries = list(initial)
        self.flow = SimpleNamespace(async_init=self.create)
        self.fail_create = fail_create
        self.removed = []
        self.payloads = []
    def async_entries(self, domain):
        return self.entries[:]
    def async_update_entry(self, entry, **values):
        for key, value in values.items():
            setattr(entry, key, value)
    async def create(self, domain, context, data):
        self.payloads.append(data)
        if self.fail_create:
            return {"type": "abort"}
        entry = SimpleNamespace(entry_id="created", data=data["data"], options=data["options"])
        self.entries.append(entry)
        return {"type": "create_entry", "result": entry}
    async def async_remove(self, entry_id):
        self.removed.append(entry_id)
        self.entries = [entry for entry in self.entries if entry.entry_id != entry_id]

class CloudEntriesTests(unittest.TestCase):
    def test_existing_printer_is_updated_without_recreating_it(self):
        entry = SimpleNamespace(entry_id="original-id", data={"serial": "P2S123"},
                                options={"local_mqtt": True, "host": "192.0.2.1",
                                         "access_code": "old-code", "enable_camera": True})
        entries = Entries([entry])
        complete(entries_mod.sync_cloud_printers(SimpleNamespace(config_entries=entries),
            {"cloud_session": SESSION, "cloud_printers": [PRINTER]}))
        self.assertEqual(entry.entry_id, "original-id")
        self.assertFalse(entry.options["local_mqtt"])
        self.assertEqual(entry.options["host"], "192.0.2.1")
        self.assertEqual(entry.options["access_code"], "old-code")
        self.assertEqual(entry.options["auth_token"], "session-token")
        self.assertTrue(entry.options["enable_camera"])
        self.assertEqual(entries.payloads, [])
        self.assertEqual(entries.removed, [])

    def test_new_printer_needs_neither_ip_nor_access_code(self):
        entries = Entries()
        complete(entries_mod.sync_cloud_printers(SimpleNamespace(config_entries=entries),
            {"cloud_session": SESSION, "cloud_printers": [PRINTER]}))
        options = entries.entries[0].options
        self.assertFalse(options["local_mqtt"])
        self.assertEqual(options["host"], "")
        self.assertEqual(options["access_code"], "")
        self.assertNotIn("password", options)

    def test_failed_add_rolls_back_previous_updates(self):
        old = {"local_mqtt": True, "auth_token": "old"}
        entry = SimpleNamespace(entry_id="original-id", data={"serial": "P2S123"},
                                options=dict(old))
        entries = Entries([entry], fail_create=True)
        with self.assertRaises(ValueError):
            complete(entries_mod.sync_cloud_printers(SimpleNamespace(config_entries=entries),
                {"cloud_session": SESSION, "cloud_printers": [
                    PRINTER, {**PRINTER, "serial": "NEW"}]}))
        self.assertEqual(entry.options, old)
        self.assertEqual(entries.removed, [])

    def test_duplicate_existing_serial_is_not_silently_replaced(self):
        entries = Entries([SimpleNamespace(data={"serial": "P2S123"}) for _ in range(2)])
        with self.assertRaises(ValueError):
            complete(entries_mod.sync_cloud_printers(SimpleNamespace(config_entries=entries),
                {"cloud_session": SESSION, "cloud_printers": [PRINTER]}))
        self.assertEqual(entries.removed, [])

    def test_account_access_code_is_optional_and_can_be_updated_automatically(self):
        payload = entries_mod.printer_payload(
            SESSION, {**PRINTER, "access_code": "from-account"})
        self.assertEqual(payload["options"]["access_code"], "from-account")
        self.assertFalse(payload["options"]["local_mqtt"])

    def test_import_hook_is_reversible(self):
        class Flow:
            pass
        hook = entries_mod.CloudImportHook(Flow)
        hook.install()
        self.assertTrue(hasattr(Flow, "async_step_import"))
        hook.restore()
        self.assertFalse(hasattr(Flow, "async_step_import"))
