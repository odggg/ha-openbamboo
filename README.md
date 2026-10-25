# Bambu Open Network v0.2.0

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=odggg&repository=ha-openbamboo&category=integration)

Enable prereleases/beta versions in HACS to install v0.2.0.

Experimental HACS companion for [ha-bambulab](https://github.com/greghesp/ha-bambulab).
Uses the real [Open Bamboo Networking](https://github.com/ClusterM/open-bamboo-networking)
library as its MQTT backend.

**[v0.2.0 is available as an experimental HACS prerelease](https://github.com/odggg/ha-openbamboo/releases/tag/v0.2.0).**
48 offline Python tests and the native amd64/aarch64 build and protocol smoke
tests pass. Live Home Assistant, cloud account and printer validation remains
pending.

Use the release asset `bambu_open_network.zip` or HACS. GitHub's automatic
source-code download does not contain the built runtimes.

## Cloud login without entering an access code

1. After installing a built release, add **Bambu Open Network** in HA.
2. Choose **Bambu Cloud login**.
3. Enter account region, email and password.
4. Complete email/SMS verification or 2FA if requested.
5. Select one or more printers from the account and confirm.

No manual LAN access code or printer IP is needed. Account login and HTTP use
ha-bambulab's existing authentication implementation. Cloud MQTT uses Open
Bamboo with the account username and session token.

Existing selected ha-bambulab entries are updated in place: config-entry and
entity IDs remain unchanged. New selected printers are created as standard
ha-bambulab entries. An account-provided device code can be obtained
automatically for existing local features; cloud MQTT never authenticates
with that code.

Passwords and verification codes are not saved to configuration entries.
The transient upstream password is cleared after each login attempt.
Account tokens are stored in HA's normal configuration storage for reconnects.
Sign in again under **Configure > Bambu Cloud login** if the token expires or
you change accounts. Automatic token renewal is not implemented.

If website 2FA fails because of a CSRF requirement, the flow requests an
email/SMS code, following the upstream implementation.

## Scope and prerequisites

- Keep ha-bambulab installed. Reviewed version: **v2.2.26**.
- Native Linux targets: **amd64 and aarch64** (HA OS/Container).
- Install a **built release**, containing the native runtimes.
- Cameras, RTSP/TCP6000, FTP, uploads and cloud REST stay with ha-bambulab.
- New cloud-only entries have no local IP, so local cameras/FTP are initially
  unavailable. Existing local IP and camera settings are preserved.
- Switching account transport to cloud intentionally uses Bambu Cloud.
  An open-source client does not make the cloud service open-source.

Firmware authorization is separate from account login. Firmware that requires
signed commands still needs your own matching slicer key, certificate chain
and CRL, or a supported Developer Mode. Account login alone does not remove
the printer's command verification. Signing material is not included.

Optional signing files, relative to the HA configuration directory:

```text
bambu_open_network/credentials/slicer_key.pem
bambu_open_network/credentials/slicer_cert.pem
bambu_open_network/credentials/slicer_crl.pem
```

The folder can be changed in setup. Reload the integration after changing
these files. Keys stay outside the repository and release archives.

## Install via HACS

1. Add the published new repository as an Integration in HACS custom repositories.
2. Enable prereleases and download the experimental release.
3. Restart HA and add **Bambu Open Network**.
4. Choose Cloud login, or **Use existing printer connections** to keep the
   original LAN/cloud settings.

HACS installation alone does not activate an integration. A one-time UI setup
is required; no YAML is needed. Source repository: https://github.com/odggg/ha-openbamboo.
Native release availability is shown on its Releases page. See [PUBLISH_DE.md](PUBLISH_DE.md).

## Transport and failure behavior

The adapter makes reversible, scoped in-memory hooks; it does not modify
ha-bambulab files. Each printer gets an isolated OBN process. Incoming MQTT
still uses ha-bambulab's models and entities.

The existing control guard is relaxed only for a live native connection with
parsed matching signing material and an acknowledged app certificate.
Disconnects and signature errors revoke readiness; raw printer flags remain
unchanged.

Commands are queued without blocking HA. A publish return code of zero means
accepted for delivery, not printer execution confirmation. Native rejections
are recorded/logged. Commands with unknown outcomes are not retried by this
adapter, and buffered actions are discarded on disconnect.

An incompatible upstream interface or missing native runtime prevents setup.
Failed multi-printer cloud configuration restores previous options and removes
only entries created by that failed operation. Disabling the companion
restores original transport methods and reloads ha-bambulab. Cloud account
settings remain standard ha-bambulab settings after disabling the companion.

## Development

```sh
python -m unittest discover -s tests -v
python -m compileall -q custom_components scripts tests
```

The GitHub workflow builds OBN and the worker under Alpine for amd64/aarch64,
bundles musl and transitive libraries, and publishes the corresponding source.
There are no compiler/package-manager requirements on the HA host.

Open Bamboo is pinned to 7822614fc7d24b4e41b2f394ae067aa88ef4b05a, ABI 02.08.04.
ha-bambulab v2.2.26 is cd67ed90e08561175a831f35b45773fe427996d7. Reviewed transport
methods also match main commit 0e027ff135a6d9265cb756d3e246747954c76722.

See [architecture](docs/ARCHITECTURE.md) and [validation](docs/VALIDATION.md).
GPL-3.0-or-later; preserve [third-party notices](NOTICE.md).
