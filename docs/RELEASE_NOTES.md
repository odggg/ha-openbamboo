Cloud MQTT printer control and cloud TUTK camera liveview for ha-bambulab.

- Sign in with your Bambu Cloud account and select printers.
- Slicer signing certificates are fetched and renewed automatically using the Open Bamboo fork shipped by the linked Orca plugin.
- Cloud camera provides JPEG/MJPEG monitoring without a printer LAN IP or manual access code.
- Imported printers use their assigned Bambu names; existing custom HA names and entity IDs are preserved.
- A Google/OAuth email-and-password setup guide is linked from the README and German installation guide.

Install through the HACS button in the README, then restart Home Assistant.
This regular release is selected by default; no beta-version selection is needed.

Validation: 80 offline regression tests, real H.264/MJPEG decoding, certificate cipher/RSA tests and native amd64/aarch64 builds passed.
The owner reported successful operation of v0.4.0 on 25 October 2026. Model and firmware coverage remains limited.

Documentation: https://github.com/odggg/ha-openbamboo/blob/main/PUBLISH_DE.md
