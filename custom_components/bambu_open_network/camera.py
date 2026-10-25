"""Cloud liveview camera attached to the existing Bambu Lab printer device."""
from __future__ import annotations

import asyncio
from datetime import timedelta

from homeassistant.components.camera import Camera
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.exceptions import HomeAssistantError

from .cloud_entries import entry_settings
from .const import DOMAIN, UPSTREAM_DOMAIN
from .cloud_camera import ERRORS

SCAN_INTERVAL = timedelta(seconds=10)


async def async_setup_entry(hass, entry, async_add_entities):
    printers = [upstream for upstream in hass.config_entries.async_entries(UPSTREAM_DOMAIN)
                if not entry_settings(upstream).get("local_mqtt", True)]
    async_add_entities([OpenBambooCloudCamera(hass, printer) for printer in printers])


class OpenBambooCloudCamera(Camera):
    _attr_has_entity_name = True
    _attr_name = "Cloud camera"
    _attr_brand = "Bambu Lab"
    _attr_should_poll = True
    _attr_icon = "mdi:cloud"
    _attr_frame_interval = 0.25

    def __init__(self, hass, printer):
        super().__init__()
        self.hass = hass
        self._serial = printer.data["serial"]
        self._attr_unique_id = f"{self._serial}_open_bamboo_cloud_camera"
        self._printer_entry_id = printer.entry_id
        self._linked = False
        self._image_lock = asyncio.Lock()

    def _client(self):
        patch = self.hass.data.get(DOMAIN)
        if not patch or not patch.active:
            return None
        return next((client for client in patch.snapshot_clients()
                     if client.owner._serial == self._serial
                     and not client.owner._local_mqtt
                     and client.is_connected()), None)

    @property
    def available(self):
        # Stay callable before first frame and after transient failures, so
        # opening the camera can start/retry an on-demand cloud connection.
        return self._client() is not None

    @property
    def extra_state_attributes(self):
        client = self._client()
        state = client.camera.state if client else "disconnected"
        return {"transport": "cloud_tutk", "camera_status": state,
                "last_error": state if state in ERRORS else None}

    async def async_camera_image(self, width=None, height=None):
        async with self._image_lock:
            client = self._client()
            if client is None:
                return None
            await self.hass.async_add_executor_job(client.request_camera)
            image = await self.hass.async_add_executor_job(client.camera.image, 8)
            if image is None and client.camera.state in ERRORS:
                errors = {
                    "missing_signing_credentials":
                        "Cloud camera requires matching slicer_key.pem, slicer_cert.pem "
                        "and slicer_crl.pem in the configured credentials folder. "
                        "Reload Bambu Open Network after adding them.",
                    "cloud_camera_rejected":
                        "Bambu Cloud refused the TUTK camera session. Check the cloud "
                        "login, signing credentials and printer camera support.",
                    "decoder_unavailable": "Home Assistant's PyAV video decoder is unavailable.",
                }
                raise HomeAssistantError(errors.get(client.camera.state,
                    "Cloud camera session did not deliver a usable image."))
            return image

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._link_printer()

    def _link_printer(self):
        if self._linked:
            return
        devices = device_registry.async_get(self.hass)
        for device in device_registry.async_entries_for_config_entry(
                devices, self._printer_entry_id):
            if (UPSTREAM_DOMAIN, self._serial) in device.identifiers:
                entities = entity_registry.async_get(self.hass)
                if entities.async_get(self.entity_id):
                    entities.async_update_entity(self.entity_id, device_id=device.id)
                    self._linked = True
                return

    async def async_update(self):
        # Also link new cloud imports once their upstream device exists.
        self._link_printer()
