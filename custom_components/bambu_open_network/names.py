"""Use imported printer names while preserving all upstream device metadata."""
from __future__ import annotations

class PrinterNamePatch:
    def __init__(self, coordinator_class):
        self.coordinator_class = coordinator_class
        self.original = None

    def install(self):
        if self.original is not None:
            return
        self.original = self.coordinator_class.get_printer_device
        original = self.original

        def get_printer_device(coordinator, *args, **kwargs):
            info = original(coordinator, *args, **kwargs)
            options = coordinator.config_entry.options
            name = options.get("name")
            if (isinstance(info, dict) and "_open_bamboo_cloud_name" in options
                    and isinstance(name, str) and name.strip()):
                info = dict(info)
                info["name"] = name.strip()
            # HA's name_by_user continues to override this integration name.
            return info

        self.coordinator_class.get_printer_device = get_printer_device

    def restore(self):
        if self.original is not None:
            self.coordinator_class.get_printer_device = self.original
            self.original = None
