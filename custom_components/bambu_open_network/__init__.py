"""Extend existing ha-bambulab entries with the Open Bamboo MQTT backend."""
from __future__ import annotations

from datetime import timedelta
import importlib
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_CREDENTIALS, DEFAULT_CREDENTIALS, DOMAIN, UPSTREAM_DOMAIN
from .cloud_entries import CloudImportHook, entry_settings, sync_cloud_printers
from .patch import IncompatibleUpstream, TransportPatch
from .credentials import CredentialManager
from .runtime import RuntimeUnavailable, validate_runtime

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    return True

async def _reload_upstream(hass: HomeAssistant):
    for upstream in hass.config_entries.async_entries(UPSTREAM_DOMAIN):
        if upstream.state is ConfigEntryState.LOADED:
            await hass.config_entries.async_reload(upstream.entry_id)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if DOMAIN in hass.data:
        raise ConfigEntryError("Only one Open Bamboo adapter can be active")
    settings = entry_settings(entry)
    credentials = Path(hass.config.path(
        settings.get(CONF_CREDENTIALS, DEFAULT_CREDENTIALS))).resolve()
    patch = None
    import_hook = None
    state_root = Path(hass.config.path(DOMAIN, "state"))
    try:
        command = await hass.async_add_executor_job(validate_runtime)
        client_module = await hass.async_add_executor_job(
            importlib.import_module, "custom_components.bambu_lab.pybambu.bambu_client")
        model_module = await hass.async_add_executor_job(
            importlib.import_module, "custom_components.bambu_lab.pybambu.models")
        patch = TransportPatch(client_module, model_module, command, state_root, credentials)
        await hass.async_add_executor_job(patch.install)
        flow_module = await hass.async_add_executor_job(
            importlib.import_module, "custom_components.bambu_lab.config_flow")
        import_hook = CloudImportHook(flow_module.BambuLabFlowHandler)
        import_hook.install()
        patch.cloud_import_hook = import_hook
        patch.credentials_manager = CredentialManager(command, credentials, hass.config.config_dir)
        if settings.get("connection_mode") == "cloud":
            await sync_cloud_printers(hass, settings)
    except Exception as err:
        if import_hook:
            import_hook.restore()
        if patch:
            patch.restore()
            await hass.async_add_executor_job(patch.stop)
        if isinstance(err, (RuntimeUnavailable, IncompatibleUpstream)):
            raise ConfigEntryError(str(err)) from None
        # Upstream network exceptions can contain account tokens. Do not echo.
        raise ConfigEntryError("Unable to activate the Open Bamboo cloud/transport configuration") from None
    hass.data[DOMAIN] = patch
    try:
        await hass.config_entries.async_forward_entry_setups(entry, [Platform.CAMERA])
    except Exception:
        hass.data.pop(DOMAIN, None)
        patch.restore()
        import_hook.restore()
        await hass.async_add_executor_job(patch.stop)
        raise ConfigEntryError("Unable to set up the Open Bamboo cloud camera") from None
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    def cloud_enabled():
        return any(not entry_settings(upstream).get("local_mqtt", True)
                   for upstream in hass.config_entries.async_entries(UPSTREAM_DOMAIN))

    async def refresh_credentials(event=None):
        if hass.data.get(DOMAIN) is not patch or not patch.active or not cloud_enabled():
            return
        changed = await hass.async_add_executor_job(patch.credentials_manager.ensure)
        if changed and hass.data.get(DOMAIN) is patch and patch.active:
            await _reload_upstream(hass)

    entry.async_on_unload(async_track_time_interval(
        hass, refresh_credentials, timedelta(minutes=15)))

    async def reload_printers(event=None):
        # This task may have been queued before the extension was unloaded.
        if hass.data.get(DOMAIN) is patch:
            if cloud_enabled():
                await hass.async_add_executor_job(patch.credentials_manager.ensure)
            if hass.data.get(DOMAIN) is patch and patch.active:
                await _reload_upstream(hass)

    async def shutdown(event):
        patch.restore()
        patch.cloud_import_hook.restore()
        await hass.async_add_executor_job(patch.stop)

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, shutdown))
    if hass.is_running:
        # Do not await a reload of our dependency while our own setup is locked.
        hass.async_create_task(reload_printers())
    else:
        entry.async_on_unload(hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, reload_printers))
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if not await hass.config_entries.async_unload_platforms(entry, [Platform.CAMERA]):
        return False
    patch = hass.data.pop(DOMAIN, None)
    if patch:
        patch.restore()
        patch.cloud_import_hook.restore()
        await hass.async_add_executor_job(patch.stop)
        await _reload_upstream(hass)
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)
