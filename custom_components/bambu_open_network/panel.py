"""Authenticated HA panel and automation service for machine control."""
from __future__ import annotations

from pathlib import Path
try:
    import probatio as vol  # HA 2026.10+
except ImportError:
    import voluptuous as vol  # HA 2025.1+

from homeassistant.components import frontend, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.panel_custom import async_register_panel
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.service import async_register_admin_service

from .cloud_entries import entry_settings
from .const import DOMAIN, UPSTREAM_DOMAIN, VERSION
from .machine import MachineController, MachineError

PANEL_PATH = "bambu-control"
STATIC_KEY = DOMAIN + "_panel_static"
URL = f"/{DOMAIN}/machine-panel-{VERSION}.js"


def controller(hass):
    patch = hass.data.get(DOMAIN)
    if patch is None or not patch.active or not hasattr(patch, "machine_controller"):
        raise MachineError("Bambu Open Network is not loaded")
    return patch.machine_controller


def printers(hass):
    devices = device_registry.async_get(hass)
    entities = entity_registry.async_get(hass)
    result = []
    for entry in hass.config_entries.async_entries(UPSTREAM_DOMAIN):
        serial = entry.data.get("serial")
        if not serial:
            continue
        settings = entry_settings(entry)
        device = devices.async_get_device(identifiers={(UPSTREAM_DOMAIN, serial)})
        name = ((device.name_by_user or device.name) if device else None)
        result.append({
            "serial": serial, "name": name or settings.get("name") or entry.title,
            "camera": entities.async_get_entity_id(
                "camera", DOMAIN, f"{serial}_open_bamboo_cloud_camera"),
        })
    return result


def require_printer(hass, serial):
    if serial not in {item["serial"] for item in printers(hass)}:
        raise MachineError("Unknown Bambu printer")


@websocket_api.websocket_command({"type": DOMAIN + "/machines"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_machines(hass, connection, msg):
    try:
        manager = controller(hass)
        items = printers(hass)
        for item in items:
            item.update(manager.status(item["serial"]))
        connection.send_result(msg["id"], {"printers": items})
    except MachineError as err:
        connection.send_error(msg["id"], "machine_unavailable", str(err))


@websocket_api.websocket_command({
    "type": DOMAIN + "/machine_command",
    vol.Required("serial"): str, vol.Required("action"): str,
    vol.Optional("params", default={}): dict,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_command(hass, connection, msg):
    try:
        require_printer(hass, msg["serial"])
        result = await hass.async_add_executor_job(
            controller(hass).execute, msg["serial"], msg["action"], msg["params"])
        connection.send_result(msg["id"], result)
    except MachineError as err:
        connection.send_error(msg["id"], "machine_command_failed", str(err))


async def async_setup_panel(hass, patch):
    patch.machine_controller = MachineController(patch)
    # Static routes cannot be unregistered; reuse on config entry reload.
    if not hass.data.get(STATIC_KEY):
        await hass.http.async_register_static_paths([
            StaticPathConfig(URL, str(Path(__file__).parent / "frontend/machine-panel.js"), False)
        ])
        hass.data[STATIC_KEY] = True
    websocket_api.async_register_command(hass, ws_machines)
    websocket_api.async_register_command(hass, ws_command)

    async def send_gcode(call):
        devices = device_registry.async_get(hass)
        device = devices.async_get(call.data["device_id"])
        serials = [value for domain, value in device.identifiers
                   if domain == UPSTREAM_DOMAIN] if device else []
        if len(serials) != 1:
            raise HomeAssistantError("Select a Bambu Lab printer device")
        try:
            require_printer(hass, serials[0])
            await hass.async_add_executor_job(
                controller(hass).execute, serials[0], "gcode",
                {"gcode": call.data["gcode"],
                 "allow_during_print": call.data["allow_during_print"]})
        except MachineError as err:
            raise HomeAssistantError(str(err)) from None

    async_register_admin_service(hass, DOMAIN, "send_gcode", send_gcode, vol.Schema({
        vol.Required("device_id"): str,
        vol.Required("gcode"): str,
        vol.Optional("allow_during_print", default=False): bool,
    }))
    await async_register_panel(
        hass, frontend_url_path=PANEL_PATH,
        webcomponent_name="bambu-machine-panel", sidebar_title="Bambu Control",
        sidebar_icon="mdi:printer-3d", module_url=URL, require_admin=True)


def async_unload_panel(hass):
    frontend.async_remove_panel(hass, PANEL_PATH)
    hass.services.async_remove(DOMAIN, "send_gcode")
    # WS handlers remain registered and look up the current adapter for every
    # request. They reject requests while unloaded and never retain old workers.
