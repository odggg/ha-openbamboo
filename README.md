# Bambu Open Network v0.4.0

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=odggg&repository=ha-openbamboo&category=integration)

Experimental HACS companion for [ha-bambulab](https://github.com/greghesp/ha-bambulab):
cloud MQTT control and cloud TUTK camera liveview using real Open Bamboo Networking.

## Install

1. Keep ha-bambulab v2.2.26 installed. Linux amd64/aarch64 are supported.
2. HACS > Download / Redownload > Need a different version? > Release > **v0.4.0**.
3. Restart Home Assistant.
4. Add **Bambu Open Network**, choose **Bambu Cloud login**, sign in and select printers.

Existing selected Bambu Lab entries are updated in place, preserving IDs and local settings.
No manual printer IP or LAN access code is needed for cloud MQTT or Cloud camera.
Use the built release asset bambu_open_network.zip; automatic GitHub source archives lack runtimes.

## Automatic slicer certificates

v0.4.0 uses the [persano Open Bamboo fork](https://github.com/persano/open-bamboo-networking),
the same native revision shipped by [Open Bambu Networking v0.2.41 in Orca Plugin Hub](https://cloud.orcaslicer.com/app/plugins/plugin-hub/5d35283e-0378-474d-8d3a-6d8f718fddeb).

Its certificate-fetch implementation obtains the app certificate chain, CRL and
matching signing key from Bambu's certificate endpoint and stores them locally:

    /config/bambu_open_network/credentials/slicer_key.pem
    /config/bambu_open_network/credentials/slicer_cert.pem
    /config/bambu_open_network/credentials/slicer_crl.pem

**You do not need to extract or copy these files manually.**
The folder can be changed during setup. Existing valid files are reused.
Credentials persist across worker restarts and HACS updates; files are owner-readable/writable (0600).
Every 15 minutes HA checks local validity and renews when fewer than seven days remain.
Failed renewal restores previous files; successful renewal reloads printer workers.

Provisioning runs in an isolated native process. Diagnostics report credential_provisioning
as ready or provision_failed. Actual PEM signing credentials are never in the public repo/releases.
Bambu's certificate service must be reachable for provisioning. Pure LAN connections do not
run automatic provisioning.

The fork embeds a vendor app bootstrap value for this operation; see [third-party provenance](NOTICE.md).
No Bambu account token is needed by the certificate provisioner. Cloud MQTT/camera still use
the account session from your login.

## Cloud camera

Select the new **Cloud camera** entity for your dashboard. It is linked to the
existing Bambu Lab printer device. The older **Camera** entity is ha-bambulab's
local camera and may remain unavailable without a LAN connection.

Opening Cloud camera requests a cloud camera session, sends liveview.prepare and
receives video through the open TUTK implementation. TUTK selects a direct peer
or relay route. H.264 is decoded by HA's PyAV dependency; JPEG/MJPEG is validated
directly. HA serves snapshots and MJPEG, capped at four decoded images per second.

This is a monitoring feed, not the Slicer's full-frame-rate player. Audio, HLS/RTSP
recording and Agora are not implemented. One media session per printer is shared
by viewers and idles out after 60 seconds without image requests. The first
connection may take several seconds; refresh/reopen after an initial thumbnail timeout.

The camera_status and last_error attributes distinguish connection/session/decoder
errors. Session URLs, TUTK passwords, key material and image contents are not diagnostic attributes.

## Printer controls

Use the normal **Bambu Lab** device page for pause/resume/stop, chamber light and
other functions supported by ha-bambulab and the printer model. Commands use OBN's
actual MQTT signing/send implementation.

Firmware verification remains active. The automatically provisioned credentials
must be accepted by the printer's app-certificate exchange before signed controls
are unlocked. Once acknowledged, previously omitted control entities are recreated.

Queue acceptance is not an execution acknowledgement. Firmware rejection revokes
readiness. Unknown command outcomes and buffered actions are never replayed by the adapter.

## Account and local features

Login/HTTP use ha-bambulab's maintained BambuCloud implementation in an executor.
Passwords and verification codes are transient. Account tokens are stored in HA.
Use Configure > Bambu Cloud login again if the account session expires;
automatic account-token renewal is not implemented.

Local cameras, FTP and uploads remain upstream and require their local settings.
Cloud camera is the separate companion entity above.
Disabling this companion restores the original MQTT methods; ordinary account
settings remain in ha-bambulab.

## Validation

Offline tests include real H.264 encode/decode, MJPEG validation, bounded video
buffering, stale-frame removal, cloud worker IPC, credential provisioning with
generated test-only keys, failure rollback, freshness checks and login/control regressions.

GitHub Actions builds both native architectures and runs the fork's actual
app-certificate cipher/RSA known-answer tests before release packaging.
Runtime protocol v3, source pin and full SHA256 checks prevent mixing older runtimes.

**Actual Home Assistant/cloud-camera/printer operation has not been validated here.**
This is an experimental prerelease. See [validation](docs/VALIDATION.md).

## Development and source

    python -m pip install av==19.0.0 Pillow cryptography
    python -m unittest discover -s tests -v
    python -m compileall -q custom_components scripts tests

Native source: persano/open-bamboo-networking @ 85c2b52445721bccc49534e82f52650037189d4f, ABI 02.08.04.
A reproducible build patch disables detached per-printer credential fetches;
HA owns persistent provisioning and renewal. Reviewed ha-bambulab:
v2.2.26 @ cd67ed90e08561175a831f35b45773fe427996d7.

AGPL-3.0-or-later. Corresponding source accompanies binary releases.
[Architecture](docs/ARCHITECTURE.md) · [German setup](PUBLISH_DE.md) · [Notices](NOTICE.md).
