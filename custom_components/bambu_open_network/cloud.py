"""Cloud account login via ha-bambulab's maintained authentication implementation."""
from __future__ import annotations

import importlib
import re

REGIONS = ("AsiaPacific", "China", "Europe", "NorthAmerica", "Other")

class CloudLoginError(Exception):
    """A UI translation key; never carry upstream responses or credentials."""

def _is(error, module, *names):
    return any(isinstance(error, getattr(module, name, ())) for name in names)

class CloudLogin:
    """Synchronous; every method doing I/O must run in HA's executor."""

    def __init__(self, api_module=None):
        self.api = api_module or importlib.import_module(
            "custom_components.bambu_lab.pybambu.bambu_cloud")
        self.client = None
        self.region = self.email = ""
        self.stage = None

    def _error(self, error):
        if _is(error, self.api, "CloudflareError", "CurlUnavailableError"):
            return CloudLoginError("cloud_blocked")
        if _is(error, self.api, "CodeExpiredError"):
            return CloudLoginError("code_expired")
        if _is(error, self.api, "CodeIncorrectError"):
            return CloudLoginError("code_incorrect")
        if isinstance(error, PermissionError):
            return CloudLoginError("invalid_auth")
        return CloudLoginError("cannot_connect")

    def _ready(self):
        if (not isinstance(self.client.auth_token, str) or not self.client.auth_token
                or not isinstance(self.client.username, str) or not self.client.username):
            raise CloudLoginError("invalid_auth")
        self.stage = "ready"
        return self.stage

    def login(self, region, email, password):
        if region not in REGIONS or not isinstance(email, str) or not email.strip() or not password:
            raise CloudLoginError("invalid_auth")
        self.region, self.email = region, email.strip()
        self.stage = None
        self.client = self.api.BambuCloud("", "", "", "")
        try:
            self.client.login(region, self.email, password)
            return self._ready()
        except CloudLoginError:
            raise
        except Exception as error:
            if _is(error, self.api, "CodeRequiredError"):
                self.stage = "email_code"
                return self.stage
            if _is(error, self.api, "TfaCodeRequiredError"):
                self.stage = "two_factor"
                return self.stage
            raise self._error(error) from None
        finally:
            # Upstream retains the password on its transient client; subsequent
            # verification/resend calls do not need it.
            if self.client is not None:
                self.client._password = ""

    def verify(self, code):
        if self.stage not in ("email_code", "two_factor") or not isinstance(code, str) or not code.strip():
            raise CloudLoginError("code_needed")
        try:
            if self.stage == "two_factor":
                self.client.login_with_2fa_code(code.strip())
            else:
                self.client.login_with_verification_code(code.strip())
            return self._ready()
        except CloudLoginError:
            raise
        except Exception as error:
            if _is(error, self.api, "CsrfError", "CsrfObtainError"):
                # Same fallback as ha-bambulab: website 2FA can be blocked
                # while API email-code login is still usable.
                return self.resend()
            raise self._error(error) from None

    def resend(self):
        if self.stage not in ("email_code", "two_factor"):
            raise CloudLoginError("code_needed")
        try:
            self.client.request_new_code()
        except Exception as error:
            raise self._error(error) from None
        self.stage = "email_code"
        return self.stage

    def session(self):
        self._ready()
        return {"region": self.region, "email": self.email,
                "username": self.client.username, "auth_token": self.client.auth_token}

    def printers(self):
        self._ready()
        try:
            devices = self.client.get_device_list()
            if not isinstance(devices, list):
                raise CloudLoginError("cannot_connect")
            result = []
            seen = set()
            for device in devices:
                if not isinstance(device, dict):
                    continue
                serial = device.get("dev_id")
                product = device.get("dev_product_name")
                if (not isinstance(serial, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", serial)
                        or serial in seen or not isinstance(product, str) or not product):
                    continue
                seen.add(serial)
                model = self.client.get_device_type_from_device_product_name(product)
                result.append({
                    "serial": serial, "device_type": str(model),
                    "name": str(device.get("name") or product),
                    # Account-provided code is optional and only supports local
                    # features. Cloud MQTT never authenticates with this value.
                    "access_code": device.get("dev_access_code", "")
                        if isinstance(device.get("dev_access_code", ""), str) else "",
                })
            return result
        except CloudLoginError:
            raise
        except Exception as error:
            raise self._error(error) from None
