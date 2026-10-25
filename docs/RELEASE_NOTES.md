Bambu Open Network v0.5.0 adds a Pronterface-style machine-control panel to Home Assistant.

- New **Bambu Control** sidebar panel for HA administrators, with the existing printer names and a Cloud-camera shortcut.
- X/Y/Z jog controls, selectable steps/feed rate, all-axis homing, hot-nozzle extrusion/retraction.
- Active nozzle/bed temperature readout and targets, part cooling fan, print pause/resume/cancel.
- Multiline G-code console with session history and the **bambu_open_network.send_gcode** automation action.
- Existing cloud/LAN Open Bamboo transport and signing; no second printer connection or cloud LAN-access-code requirement.
- Server-side bounds, fresh-status checks, busy/paused motion locks, explicit busy-print override for raw G-code, expiring queued manual commands and no automatic retries.
- Native publish acceptance is displayed honestly: it does not confirm firmware execution and is not a serial Pronterface ok/response stream.
- English/German panel labels and a German usage guide.

Update in HACS to the latest regular version and restart Home Assistant. Open **Bambu Control** in the sidebar.

Validation: 101 Python regression tests; browser checks cover printer isolation, multiline submission, XSS handling, motion locks, stale status, no retry, camera navigation and desktop/mobile layout.
Native Linux amd64/aarch64 builds, cipher/RSA self-tests and HACS asset checks run before publication.
No physical motion or heating was triggered during development testing. Hardware/firmware validation of the new controls remains to be done.

Guide: https://github.com/odggg/ha-openbamboo/blob/main/docs/MACHINE_CONTROL_DE.md
