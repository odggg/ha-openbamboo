"""Activate the adapter or sign in to Bambu Cloud without entering a LAN code."""
from __future__ import annotations

from pathlib import Path
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector, SelectSelectorConfig, SelectSelectorMode,
    TextSelector, TextSelectorConfig, TextSelectorType,
)

from .cloud import CloudLogin, CloudLoginError, REGIONS
from .cloud_entries import entry_settings
from .const import CONF_CREDENTIALS, DEFAULT_CREDENTIALS, DOMAIN, NAME
from .runtime import RuntimeUnavailable, validate_runtime

class CloudSteps:
    _login = None
    _printers = None
    _entry = None

    def _defaults(self):
        return entry_settings(self._entry) if self._entry else {}

    async def _validate_settings(self, values):
        raw = values.get(CONF_CREDENTIALS, DEFAULT_CREDENTIALS).strip()
        root = Path(self.hass.config.config_dir).resolve()
        if not raw or not (root / raw).resolve().is_relative_to(root):
            return None, {CONF_CREDENTIALS: "outside_config"}
        try:
            await self.hass.async_add_executor_job(validate_runtime)
        except RuntimeUnavailable:
            return None, {"base": "runtime_unavailable"}
        return raw, {}

    async def async_step_existing(self, user_input=None):
        errors = {}
        if user_input is not None:
            raw, errors = await self._validate_settings(user_input)
            if not errors:
                return await self._finish({
                    CONF_CREDENTIALS: raw, "connection_mode": "existing",
                    "cloud_session": None, "cloud_printers": [],
                })
        return self.async_show_form(
            step_id="existing", errors=errors,
            data_schema=vol.Schema({vol.Optional(CONF_CREDENTIALS,
                default=self._defaults().get(CONF_CREDENTIALS, DEFAULT_CREDENTIALS)): str}))

    async def async_step_cloud(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                self._printers = None
                self._login = await self.hass.async_add_executor_job(CloudLogin)
                stage = await self.hass.async_add_executor_job(
                    self._login.login, user_input["region"], user_input["email"],
                    user_input["password"])
            except CloudLoginError as error:
                errors["base"] = str(error)
            except (ImportError, OSError):
                errors["base"] = "cannot_connect"
            else:
                if stage != "ready":
                    return await self.async_step_verify()
                return await self.async_step_printers()
        previous = self._defaults().get("cloud_session") or {}
        return self.async_show_form(
            step_id="cloud", errors=errors,
            data_schema=vol.Schema({
                vol.Required("region", default=previous.get("region", "Europe")): vol.In(REGIONS),
                vol.Required("email", default=previous.get("email", "")): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.EMAIL)),
                # Passwords are neither reused as defaults nor stored in entries.
                vol.Required("password"): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            }))

    async def async_step_verify(self, user_input=None):
        if self._login is None:
            return await self.async_step_cloud()
        errors = {}
        if user_input is not None:
            try:
                if user_input.get("resend", False):
                    await self.hass.async_add_executor_job(self._login.resend)
                else:
                    stage = await self.hass.async_add_executor_job(
                        self._login.verify, user_input.get("code", ""))
                    if stage == "ready":
                        return await self.async_step_printers()
            except CloudLoginError as error:
                errors["base"] = str(error)
        two_factor = self._login.stage == "two_factor"
        return self.async_show_form(
            step_id="verify", errors=errors,
            description_placeholders={
                "code_source": "Authenticator / 2FA" if two_factor else "E-Mail / SMS"},
            data_schema=vol.Schema({
                vol.Optional("code", default=""): str,
                vol.Optional("resend", default=False): bool,
            }))

    async def async_step_printers(self, user_input=None):
        if self._login is None:
            return await self.async_step_cloud()
        errors = {}
        if self._printers is None:
            try:
                self._printers = await self.hass.async_add_executor_job(self._login.printers)
            except CloudLoginError as error:
                return self.async_abort(reason=str(error))
        if not self._printers:
            return self.async_abort(reason="no_printers")
        available = {printer["serial"]: printer for printer in self._printers}
        if user_input is not None:
            selected = user_input.get("printers", [])
            if (not isinstance(selected, list) or not selected
                    or len(set(selected)) != len(selected)
                    or any(serial not in available for serial in selected)):
                errors["printers"] = "select_printer"
            else:
                raw, errors = await self._validate_settings(user_input)
                if not errors:
                    payload = {
                        CONF_CREDENTIALS: raw, "connection_mode": "cloud",
                        "cloud_session": self._login.session(),
                        "cloud_printers": [dict(available[serial]) for serial in selected],
                    }
                    self._login = None
                    return await self._finish(payload)
        default_selected = [p["serial"] for p in self._defaults().get("cloud_printers", [])
                            if p["serial"] in available]
        return self.async_show_form(
            step_id="printers", errors=errors,
            data_schema=vol.Schema({
                vol.Required("printers", default=default_selected): SelectSelector(
                    SelectSelectorConfig(options=[
                        {"value": serial, "label": f"{printer['name']} ({serial})"}
                        for serial, printer in available.items()],
                        multiple=True, mode=SelectSelectorMode.LIST)),
                vol.Optional(CONF_CREDENTIALS, default=self._defaults().get(
                    CONF_CREDENTIALS, DEFAULT_CREDENTIALS)): str,
            }))

class ConfigFlow(CloudSteps, config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow(config_entry)

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_show_menu(step_id="user", menu_options=["cloud", "existing"])

    async def async_step_reauth(self, entry_data):
        self._entry = self._get_reauth_entry()
        self._reauth = True
        return await self.async_step_cloud()

    async def _finish(self, data):
        if getattr(self, "_reauth", False):
            self.hass.config_entries.async_update_entry(self._entry, data=data, options={})
            await self.hass.config_entries.async_reload(self._entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return self.async_create_entry(title=NAME, data=data)

class OptionsFlow(CloudSteps, config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(step_id="init", menu_options=["cloud", "existing"])

    async def _finish(self, data):
        return self.async_create_entry(title="", data=data)
