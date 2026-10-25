"""Extend existing ha-bambulab entries with the Open Bamboo MQTT backend."""
from __future__ import annotations

import importlib
import logging
from pathlib import Path

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .const import CONF_CREDENTIALS, DEFAULT_CREDENTIALS, DOMAIN, UPSTREAM_DOMAIN
from .cloud_entries import CloudImportHook, entry_settings, sync_cloud_printers
from .patch import IncompatibleUpstream, TransportPatch
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
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async def reload_printers(event=None):
        # This task may have been queued before the extension was unloaded.
        if hass.data.get(DOMAIN) is patch:
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
    patch = hass.data.pop(DOMAIN, None)
    if patch:
        patch.restore()
        patch.cloud_import_hook.restore()
        await hass.async_add_executor_job(patch.stop)
        await _reload_upstream(hass)
    return True

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    await hass.config_entries.async_reload(entry.entry_id)
