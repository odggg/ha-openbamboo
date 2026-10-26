"""Export only backend health; never tokens, payloads, serials or file paths."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, HA_BAMBULAB_COMMIT, OBN_COMMIT, OBN_REPOSITORY, VERSION

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    patch = hass.data.get(DOMAIN)
    clients = patch.snapshot_clients() if patch else []
    return {
        "version": VERSION,
        "obn_commit": OBN_COMMIT,
        "obn_repository": OBN_REPOSITORY,
        "reviewed_ha_bambulab_commit": HA_BAMBULAB_COMMIT,
        "active": bool(patch and patch.active),
        "mqtt_clients": [
            {"connected": client.is_connected(), "signed_commands_ready": client.signed_ready,
             "transport": "lan" if client.owner._local_mqtt else "cloud",
             "camera_status": client.camera.state,
             "last_command_reply": client.command_replies.latest()}
            for client in clients
        ],
        "scope": "mqtt_and_cloud_camera",
        "credential_provisioning": getattr(getattr(patch, "credentials_manager", None),
                                           "status", "not_checked"),
    }
