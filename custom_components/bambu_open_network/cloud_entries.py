"""Create normal ha-bambulab config entries and update existing printers in place."""
from __future__ import annotations

from .const import DOMAIN, UPSTREAM_DOMAIN

def entry_settings(entry):
    return {**entry.data, **entry.options}

def printer_payload(session, printer, old_options=None):
    if not all(isinstance(session.get(key), str) and session[key]
               for key in ("region", "email", "username", "auth_token")):
        raise ValueError("Incomplete cloud session")
    options = dict(old_options or {})
    defaults = {
        "host": "", "access_code": "", "print_cache_count": 1,
        "timelapse_cache_count": 0, "usage_hours": 0.0, "disable_ssl_verify": False,
        "enable_firmware_update": False, "force_ip": False,
    }
    for key, value in defaults.items():
        options.setdefault(key, value)
    options.update({key: session[key]
                    for key in ("region", "email", "username", "auth_token")})
    options.update({"local_mqtt": False, "name": printer["name"]})
    if printer.get("access_code"):
        options["access_code"] = printer["access_code"]
    return {"adapter": DOMAIN,
            "data": {"serial": printer["serial"], "device_type": printer["device_type"]},
            "options": options}

class CloudImportHook:
    """Supply a missing upstream import step while the companion is active."""

    def __init__(self, flow_class):
        self.flow_class = flow_class
        self.original = getattr(flow_class, "async_step_import", None)
        self.installed = False

    def install(self):
        if self.installed:
            return
        original = self.original

        async def async_step_import(flow, user_input=None):
            if not isinstance(user_input, dict) or user_input.get("adapter") != DOMAIN:
                if original:
                    return await original(flow, user_input)
                return flow.async_abort(reason="unknown")
            serial = user_input["data"]["serial"]
            # ha-bambulab's existing entries may have no unique_id. Check data
            # first to avoid duplicate devices and preserve existing entities.
            for entry in flow.hass.config_entries.async_entries(UPSTREAM_DOMAIN):
                if entry.data.get("serial") == serial:
                    return flow.async_abort(reason="already_configured")
            await flow.async_set_unique_id(serial)
            flow._abort_if_unique_id_configured()
            return flow.async_create_entry(
                title=serial, data=dict(user_input["data"]),
                options=dict(user_input["options"]))

        self.flow_class.async_step_import = async_step_import
        self.installed = True

    def restore(self):
        if not self.installed:
            return
        if self.original is None:
            delattr(self.flow_class, "async_step_import")
        else:
            self.flow_class.async_step_import = self.original
        self.installed = False

async def sync_cloud_printers(hass, settings):
    """Apply a login to the explicitly selected printers, rolling back on errors."""
    session = settings["cloud_session"]
    printers = settings["cloud_printers"]
    if not isinstance(printers, list) or not printers:
        raise ValueError("No cloud printers selected")
    entries = hass.config_entries
    modified, created = [], []
    try:
        serials = set()
        for printer in printers:
            serial = printer["serial"]
            if serial in serials:
                raise ValueError("Duplicate printer selection")
            serials.add(serial)
            existing = [entry for entry in entries.async_entries(UPSTREAM_DOMAIN)
                        if entry.data.get("serial") == serial]
            if len(existing) > 1:
                raise ValueError("Multiple ha-bambulab entries have the same serial")
            if existing:
                entry = existing[0]
                payload = printer_payload(session, printer, entry.options)
                modified.append((entry, dict(entry.options)))
                entries.async_update_entry(entry, options=payload["options"])
            else:
                result = await entries.flow.async_init(
                    UPSTREAM_DOMAIN, context={"source": "import"},
                    data=printer_payload(session, printer))
                if result["type"] != "create_entry":
                    raise ValueError("Unable to create cloud printer entry")
                created.append(result["result"].entry_id)
    except Exception:
        for entry_id in reversed(created):
            await entries.async_remove(entry_id)
        for entry, old_options in reversed(modified):
            entries.async_update_entry(entry, options=old_options)
        raise
