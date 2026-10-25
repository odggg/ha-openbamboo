# Architecture

This is a HACS custom integration, not a Supervisor app.

## MQTT transport

The companion validates its bundled native worker and hashes of the reviewed
ha-bambulab transport methods. ContextVar-scoped wrappers select a Paho-shaped
adapter only within ha-bambulab's BambuClient connect/test paths. Global Paho
imports elsewhere in HA are untouched.

Every printer uses an isolated OBN subprocess because OBN configuration and
signer caches are process-global. A bounded publish queue, RPC reader and
separate callback dispatcher avoid blocking HA or deadlocking callback-triggered
publishes. Credentials go over stdin, never command-line arguments.

The C++ worker calls actual OBN ABI functions. A small extension compiled into
the OBN DSO reports signing readiness after key/certificate parsing, matching
and printer app-certificate acknowledgement. Python never passes C++ std::string
or std::function objects through ctypes.

Incoming data is handed to existing ha-bambulab models. Cameras and file
transfer remain upstream. Raw firmware authorization flags are preserved;
the control guard is relaxed only for our live acknowledged native client.

## Cloud login and entry synchronization

The setup/options UI calls the maintained upstream BambuCloud authentication
implementation in HA's executor. Email-code login, 2FA, resend and CSRF fallback
are supported. Passwords are transient and cleared after the request.

Only session fields and sanitized selected printer specs enter configuration
storage. The selected printers authenticate to cloud MQTT with account
username/token, without a user-supplied LAN access code.

A reversible upstream import-step hook creates standard ha-bambulab entries
through HA's config-flow manager. Existing entries are updated in place.
A failed synchronization restores old options and removes only newly created
entries from that failed operation. No existing printer is removed/recreated.

New cloud-only entries use an empty local host. Existing local settings remain
available. Options allow a fresh account login; automatic token renewal is not
implemented. A config reauthentication route is provided.

## Lifecycle and limits

Unloading restores original MQTT methods and the prior import-step handler,
stops workers, and reloads existing entries. Account settings are normal
ha-bambulab settings and remain valid after disabling the companion.

Unknown upstream interfaces, missing runtimes and unsupported architectures
prevent activation. There is no silent fallback for failed commands.

The native worker and Alpine packaging still require Linux execution.
Offline tests do not establish real HA startup/reload or live login behavior.
Native TLS is implemented by OBN: the upstream Python SSLContext's TLS-version
cap is not passed through with the extracted CA bundle. P2S firmware
compatibility must be checked physically. An upstream encryption repair
notification can remain visible after signing becomes ready.
