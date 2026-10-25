"""Scoped, reversible hook into ha-bambulab; never modifies its files."""
from __future__ import annotations

from contextvars import ContextVar
import hashlib
import inspect
import json
from pathlib import Path
import textwrap
import weakref

from .transport import OpenBambooClient

_CURRENT_OWNER: ContextVar = ContextVar("open_bamboo_owner", default=None)

class IncompatibleUpstream(RuntimeError):
    """The private interface changed and needs review."""

def source_hash(value):
    return hashlib.sha256(textwrap.dedent(inspect.getsource(value)).encode()).hexdigest()

def check_contract(client_module, model_module):
    expected = json.loads((Path(__file__).with_name("upstream_contract.json")).read_text())
    actual = {
        "BambuClient.connect": source_hash(client_module.BambuClient.connect),
        "BambuClient.try_connection": source_hash(client_module.BambuClient.try_connection),
        "PrintFun.mqtt_signature_required": source_hash(
            model_module.PrintFun.mqtt_signature_required.fget),
    }
    if actual != expected:
        raise IncompatibleUpstream(
            "ha-bambulab transport interface changed. Update Bambu Open Network "
            "or disable this extension to use the original transport."
        )

class ScopedMqtt:
    def __init__(self, original, patch):
        self._original, self._patch = original, patch

    def __getattr__(self, name):
        return getattr(self._original, name)

    def Client(self, *args, **kwargs):
        owner = _CURRENT_OWNER.get()
        if owner is None or not self._patch.active or owner._mock:
            return self._original.Client(*args, **kwargs)
        client = OpenBambooClient(owner, self._patch.command, self._patch.state_root,
                                 self._patch.credentials)
        self._patch.clients.add(client)
        return client

class TransportPatch:
    def __init__(self, client_module, model_module, command, state_root, credentials):
        self.client_module, self.model_module = client_module, model_module
        self.command, self.state_root, self.credentials = command, state_root, credentials
        self.clients = weakref.WeakSet()
        self.active = False
        self._originals = None

    def install(self):
        if self.active:
            return
        check_contract(self.client_module, self.model_module)
        cls = self.client_module.BambuClient
        self._originals = (self.client_module.mqtt, cls.connect, cls.try_connection,
                           self.model_module.PrintFun.mqtt_signature_required)
        original_mqtt, original_connect, original_try, original_required = self._originals

        async def connect(owner, *args, **kwargs):
            token = _CURRENT_OWNER.set(owner)
            try:
                return await original_connect(owner, *args, **kwargs)
            finally:
                _CURRENT_OWNER.reset(token)

        async def try_connection(owner, *args, **kwargs):
            token = _CURRENT_OWNER.set(owner)
            try:
                return await original_try(owner, *args, **kwargs)
            finally:
                _CURRENT_OWNER.reset(token)

        def required(print_fun):
            raw = original_required.fget(print_fun)
            client = getattr(print_fun._client, "client", None)
            if (raw and isinstance(client, OpenBambooClient)
                    and client in self.clients and client.is_connected() and client.signed_ready):
                return False
            return raw

        self.active = True
        self.client_module.mqtt = ScopedMqtt(original_mqtt, self)
        cls.connect, cls.try_connection = connect, try_connection
        self.model_module.PrintFun.mqtt_signature_required = property(
            required, original_required.fset, original_required.fdel, original_required.__doc__)

    def restore(self):
        if not self.active:
            return
        self.active = False
        mqtt, connect, try_connection, required = self._originals
        self.client_module.mqtt = mqtt
        self.client_module.BambuClient.connect = connect
        self.client_module.BambuClient.try_connection = try_connection
        self.model_module.PrintFun.mqtt_signature_required = required

    def stop(self):
        for client in list(self.clients):
            client.disconnect()
        for client in list(self.clients):
            client.loop_stop()
