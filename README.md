# Bambu Open Network v0.3.0

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=odggg&repository=ha-openbamboo&category=integration)

Experimental HACS companion for [ha-bambulab](https://github.com/greghesp/ha-bambulab).
Uses the real [Open Bamboo Networking](https://github.com/ClusterM/open-bamboo-networking)
library for MQTT control and **cloud TUTK camera liveview**.

## Install and connect

1. Keep **ha-bambulab v2.2.26** installed. Linux amd64/aarch64 are supported.
2. Open this repository in HACS and choose **Download / Redownload > Need a different version? > Release > v0.3.0**. It is an experimental prerelease. Older HACS versions may require enabling beta versions.
3. Restart Home Assistant.
4. Add **Bambu Open Network** under Settings > Devices & services.
5. Choose **Bambu Cloud login**, enter region/email/password, complete verification and select your printers.

Existing selected printers are updated in place. New printers become normal Bambu Lab entries.
No manual printer IP or LAN access code is required for cloud MQTT or the new cloud camera.

Use the release asset `bambu_open_network.zip`. GitHub's automatic source archives lack the built native runtimes.

## Cloud camera

v0.3.0 adds a separate entity named **Cloud camera**, linked to the existing Bambu Lab printer device.
Select that entity for a dashboard camera card. The older **Camera** entity belongs to ha-bambulab's local-camera path and may remain unavailable without a LAN configuration.

Opening **Cloud camera** uses OBN to request a cloud camera session, send the liveview prepare command and receive video through its open TUTK implementation. It does not need a printer LAN IP or LAN access code. TUTK chooses a direct peer route or its relay where available.

**Cloud camera authentication requires your own matching slicer signing credentials**, even when telemetry works with only the account login. OBN's cloud camera endpoint uses certificate proof of possession. Developer Mode does not remove that cloud endpoint requirement.

Place these files in the HA configuration directory:

```text
/config/bambu_open_network/credentials/slicer_key.pem
/config/bambu_open_network/credentials/slicer_cert.pem
/config/bambu_open_network/credentials/slicer_crl.pem
```

Use the configured credentials folder if you changed it during setup, then reload **Bambu Open Network**.
Credentials are never included in repository/release files.
If you already configured Open Bamboo in a slicer, use your own corresponding credential files.

The camera's `camera_status` and `last_error` attributes distinguish missing signing material, a rejected cloud session, decoder absence and video timeouts. Session URLs, TUTK passwords and frame contents are not diagnostic attributes.

H.264 is decoded with HA's PyAV dependency; MJPEG is validated directly. The HA camera serves JPEG snapshots and MJPEG liveview, capped at four decoded images per second. This is a monitoring feed, not the full-frame-rate Slicer video player, and does not expose audio/HLS/RTSP recording.
One cloud session per printer is shared by viewers and idles out after 60 seconds without image requests. A first connection can take several seconds; reopen/refresh if the first thumbnail times out.

Only OBN's **TUTK** camera path is supported. Printers/accounts requiring Agora are not supported by this implementation.

## Printer controls

Use the ordinary **Bambu Lab** printer device page for pause/resume/stop, chamber light and the other controls supported by ha-bambulab and your model.
Commands pass through the real OBN MQTT send/signing implementation. This extension preserves ha-bambulab's existing entities, services and automation IDs.

Firmware requiring signed commands still needs valid matching signing material and a printer-acknowledged app certificate, or a supported Developer Mode for local commands.
Cloud login does not bypass firmware verification.
When signing becomes ready, the extension asks ha-bambulab to recreate controls that were previously omitted while locked.

A queued command is not an execution acknowledgement. Firmware rejections are logged, readiness is revoked on signature errors/disconnect, and uncertain commands are never automatically replayed.

## Account and local features

Account HTTP/login uses ha-bambulab's maintained BambuCloud implementation in an executor.
Passwords/verification codes are transient. Session tokens are stored in HA configuration storage.
Sign in again via **Configure > Bambu Cloud login** when the session expires; automatic token renewal is not implemented.

Local cameras, FTP and uploads remain with ha-bambulab and still require their local connection settings.
Cloud camera is provided by the companion entity described above.
Existing local IP/camera settings are preserved when cloud account settings are applied.

## Validation and limits

Offline tests include real H.264 encode/decode, MJPEG validation, bounded video buffering, stale-frame removal, cloud worker RPC, credential errors, signing readiness and existing login/transport regression tests.
GitHub Actions builds real OBN and the native worker on amd64/aarch64 before publishing release assets.

**No physical printer, actual cloud camera session or real Home Assistant lifecycle has been validated here.** This release is experimental.
See [validation](docs/VALIDATION.md) and the [release build](https://github.com/odggg/ha-openbamboo/actions).

The adapter uses reversible scoped in-memory hooks and does not edit ha-bambulab files.
It refuses unknown reviewed upstream interfaces and incomplete runtimes.
Disabling it restores the original transport; account settings remain normal upstream settings.

## Development

```sh
python -m pip install av==19.0.0 Pillow
python -m unittest discover -s tests -v
python -m compileall -q custom_components scripts tests
```

Open Bamboo is pinned to `7822614fc7d24b4e41b2f394ae067aa88ef4b05a`, ABI 02.08.04.
Reviewed ha-bambulab: v2.2.26, commit `cd67ed90e08561175a831f35b45773fe427996d7`.
Native protocol v2 prevents using a v0.2.0 MQTT-only runtime with this camera component.

[Architecture](docs/ARCHITECTURE.md) · [German installation notes](PUBLISH_DE.md) · [Third-party notices](NOTICE.md).
AGPL-3.0-or-later. Corresponding source accompanies binary releases.
