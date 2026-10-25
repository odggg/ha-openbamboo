Bambu Open Network v0.5.1 embeds the selected printer's camera directly in Bambu Control.

- Watch the Cloud camera beside the axis, extruder and temperature controls.
- The camera follows the selected printer automatically; the previous image is removed immediately.
- Existing authenticated Home Assistant MJPEG camera proxy; no camera URL, extra card or credentials to configure.
- Reconnect button and automatic retry with backoff for failed camera requests.
- Stale-frame detection uses the backend decoder timestamp, so a static scene is not mistaken for a frozen feed.
- Disconnected/unavailable cameras show a status instead of retaining the previous printer image.
- Image requests stop on panel close or when the page is hidden and resume on return.
- Responsive desktop/mobile layout; the larger camera dialog remains available.

Update Bambu Open Network in HACS, restart Home Assistant, then refresh Bambu Control.
The camera appears automatically when selecting a connected printer with a Cloud camera entity.

Validation: 103 Python regression tests, existing machine-panel browser tests and a real multipart MJPEG browser fixture passed locally. Browser coverage includes simultaneous controls, printer switching, scoped-token rotation, stale/error recovery, stream reuse, page visibility and connection cleanup.
The release workflow also builds/tests native Linux amd64 and aarch64 runtimes and validates the regular HACS release assets.
No physical printer motion or heating was triggered during development tests.

Guide: https://github.com/odggg/ha-openbamboo/blob/main/docs/MACHINE_CONTROL_DE.md
