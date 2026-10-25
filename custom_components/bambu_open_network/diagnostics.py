"""Export only backend health; never tokens, payloads, serials or file paths."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, HA_BAMBULAB_COMMIT, OBN_COMMIT, VERSION

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    patch = hass.data.get(DOMAIN)
    clients = list(patch.clients) if patch else []
    return {
        "version": VERSION,
        "obn_commit": OBN_COMMIT,
        "reviewed_ha_bambulab_commit": HA_BAMBULAB_COMMIT,
        "active": bool(patch and patch.active),
        "mqtt_clients": [
            {"connected": client.is_connected(), "signed_commands_ready": client.signed_ready,
             "transport": "lan" if client.owner._local_mqtt else "cloud"}
            for client in clients
        ],
        "scope": "mqtt_only",
    }
