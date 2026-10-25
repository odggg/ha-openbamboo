# Bambu Open Network v0.5.1

## Reclaim your printer's freedom

## ⚠️ Required: ha-bambulab must be installed

> [!IMPORTANT]
> **Install [Bambu Lab (ha-bambulab)](https://github.com/greghesp/ha-bambulab) through HACS first. This extension requires ha-bambulab v2.2.26.**
>
> Keep your existing Bambu Lab installation and printers. Bambu Open Network adds the features below to it.

[Deutsche Anleitung](PUBLISH_DE.md)

## What you get

Control and monitor your Bambu printer from Home Assistant through Bambu Cloud:

- **Camera beside the controls:** watch the selected printer directly in Bambu Control while moving axes or sending G-code. Cloud access needs no printer IP or LAN access code.
- **Machine control:** move X/Y/Z, home the printer, set nozzle/bed temperatures and the part cooling fan.
- **Extruder controls:** extrude or retract through the active, heated nozzle.
- **Print controls:** pause, resume or cancel a print.
- **G-code console:** send one or more lines of custom G-code, with a session history. Also available as an automation action.
- **One control page:** open **Bambu Control** from the HA sidebar; the camera follows your printer selection automatically.
- **Your printer names:** imported printers use their Bambu names; custom Home Assistant names and existing entity IDs are preserved.
- **Automatic setup:** sign in with your Bambu account and select printers. Signing certificates are set up automatically.

## Installation

**There are two parts: download the files in HACS, then add Bambu Open Network as an integration in Home Assistant.**

### 1. Before you start

You need Home Assistant with HACS, an administrator account, and **[ha-bambulab v2.2.26](https://github.com/greghesp/ha-bambulab)** downloaded through HACS.
For cloud access, the printer must be online and already linked to the Bambu account you use in Bambu Handy.

Keep any existing Bambu Lab printer entries. You do not need to remove or recreate them.

### 2. Download Bambu Open Network in HACS

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=odggg&repository=ha-openbamboo&category=integration)

1. Select **Open in HACS** above. If prompted, enter your Home Assistant address.
2. Open/add the repository, then select **Download**.
3. Keep the latest regular version selected. No beta or manual version selection is needed.
4. Wait for the download to finish.

If the button does not work, open **HACS → ⋮ → Custom repositories**, add
**https://github.com/odggg/ha-openbamboo**, choose **Integration** as the type and
select **Add**. Then search HACS for **Bambu Open Network** and download it.

### 3. Restart Home Assistant

Restart **Home Assistant itself** and wait until it is available again.
Refreshing the browser alone does not load the downloaded integration.

### 4. Add the integration in Home Assistant

**The HACS download is not the final step. Add the integration now:**

1. Open **Settings → Devices & services**.
2. Select **Add integration** in the bottom-right corner.
3. Search for **Bambu Open Network** and select it.
4. Choose **Bambu Cloud login**.
5. Choose your account region, then enter your Bambu account email and password.
6. If asked, enter the email/SMS or authenticator verification code.
7. Select the printers you want to use.
8. Leave the certificate-directory field at its default value.
9. Submit the form and finish setup.

**Using Google sign-in?** Set up an email/password login for your **existing Bambu account** first:
[English guide](docs/GOOGLE_LOGIN.md) · [Deutsche Anleitung](docs/GOOGLE_LOGIN_DE.md).

The selected printers are imported or their existing Bambu Lab entries are updated.
Allow a little time for the first connection and automatic certificate setup.

### 5. Open the controls and camera

1. As an HA administrator, open **Bambu Control** in the sidebar.
2. Select your printer by name and wait for a connected status.
3. Use the axis, temperature, fan, extruder and print controls.
4. The selected printer's **Cloud camera** appears directly beside the controls. Select **Open camera** for a larger view.
5. Use the G-code console for your own commands.

For a dashboard, add the printer's **Cloud camera** entity to a camera card.
The older **Camera** entity belongs to ha-bambulab's local camera; use **Cloud camera**
for this extension's cloud feed.

[Machine-control guide and automation example (German)](docs/MACHINE_CONTROL_DE.md)

### Updating an existing installation

Update **Bambu Open Network** in HACS, then restart Home Assistant.
An already configured integration does not need to be added again.
Keep existing printer entries; the **Bambu Control** page appears after the restart.

### If something is missing

- **Bambu Open Network is not in Add integration:** check that the HACS download finished, restart HA fully, then refresh your browser.
- **Bambu Control is missing:** finish step 4 and use an HA administrator account.
- **No printers are listed:** check the Bambu account and region; the printers must be linked to that account.
- **The camera is unavailable:** select **Cloud camera**, allow the first connection to finish and reopen it after an initial thumbnail timeout.
- **Google sign-in only:** follow the linked email/password guide before attempting the cloud login.

## Technical details

The sections below cover compatibility, transport, limitations and development.

### Compatibility and installation files

- Home Assistant 2025.1 or newer on **Linux amd64 or aarch64**.
- Required upstream integration: **ha-bambulab v2.2.26**.
- For manual installation, use the built release asset **bambu_open_network.zip**.
  GitHub's automatic source archives do not include the native runtimes.
- This is a custom integration installed through HACS and HA's integration screen;
  it is not installed through the Home Assistant add-on store.

### Machine control and G-code behavior

From v0.5.1, Bambu Control embeds the selected printer's authenticated HA MJPEG
camera feed. The old image is cleared on printer changes, disconnected/unavailable
states and stale decoder timestamps. Failed requests reconnect with backoff;
**Reconnect** restarts the feed manually. Switching away from the page stops its
image request; it resumes on return. No extra camera connection or credentials
need to be configured. The backend shares its existing per-printer camera session.


Commands use the existing signed Open Bamboo connection. Motion buttons require
an idle printer; extrusion/retraction additionally requires a reported active
nozzle temperature of at least 170 °C. Raw G-code during a print requires an
explicit override. Server-side limits, fresh-status checks, expiring queued manual
commands and no automatic retries apply.

Native acceptance does **not** confirm firmware execution. The console does not
provide Pronterface's serial ok/response protocol or streamed G-code-file printing.
The automation action is **bambu_open_network.send_gcode**.
[Limits and usage](docs/MACHINE_CONTROL_DE.md).

### Imported printer names

New printer entries and HA devices use their assigned Bambu Cloud names.
Existing serial-number titles are corrected when loading/importing the selected
cloud printers. Custom Home Assistant names and existing entity IDs are preserved.

### Automatic slicer certificates

The integration uses the [persano Open Bamboo fork](https://github.com/persano/open-bamboo-networking),
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

### Cloud camera

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

### Printer controls

Use the normal **Bambu Lab** device page for pause/resume/stop, chamber light and
other functions supported by ha-bambulab and the printer model. Commands use OBN's
actual MQTT signing/send implementation.

Firmware verification remains active. The automatically provisioned credentials
must be accepted by the printer's app-certificate exchange before signed controls
are unlocked. Once acknowledged, previously omitted control entities are recreated.

Queue acceptance is not an execution acknowledgement. Firmware rejection revokes
readiness. Unknown command outcomes and buffered actions are never replayed by the adapter.

### Account and local features

Login/HTTP use ha-bambulab's maintained BambuCloud implementation in an executor.
Passwords and verification codes are transient. Account tokens are stored in HA.
Use Configure > Bambu Cloud login again if the account session expires;
automatic account-token renewal is not implemented.

Local cameras, FTP and uploads remain upstream and require their local settings.
Cloud camera is the separate companion entity above.
Disabling this companion restores the original MQTT methods; ordinary account
settings remain in ha-bambulab.

### Validation

Offline tests include real H.264 encode/decode, MJPEG validation, bounded video
buffering, stale-frame removal, cloud worker IPC, credential provisioning with
generated test-only keys, failure rollback, freshness checks and login/control regressions.

GitHub Actions builds both native architectures and runs the fork's actual
app-certificate cipher/RSA known-answer tests before release packaging.
Runtime protocol v3, source pin and full SHA256 checks prevent mixing older runtimes.

The owner reported successful operation of **v0.4.0** on 25 October 2026.
Model and firmware coverage remains limited. See [validation](docs/VALIDATION.md).

### Development and source

    python -m pip install av==19.0.0 Pillow cryptography voluptuous==0.16.0 probatio==0.13.0
    python -m unittest discover -s tests -v
    python -m compileall -q custom_components scripts tests

Native source: persano/open-bamboo-networking @ 85c2b52445721bccc49534e82f52650037189d4f, ABI 02.08.04.
A reproducible build patch disables detached per-printer credential fetches;
HA owns persistent provisioning and renewal. Reviewed ha-bambulab:
v2.2.26 @ cd67ed90e08561175a831f35b45773fe427996d7.

AGPL-3.0-or-later. Corresponding source accompanies binary releases.
[Architecture](docs/ARCHITECTURE.md) · [German setup](PUBLISH_DE.md) · [Notices](NOTICE.md).
