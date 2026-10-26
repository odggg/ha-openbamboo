Bambu Open Network v0.5.2 corrects command IDs and reports firmware acknowledgements/rejections.

The machine panel previously generated arbitrary random sequence IDs up to two billion.
The native worker now assigns print commands using Open Bamboo's own shared, randomly
seeded Studio counter in the 20000–29999 range, before encryption and signing.
This also covers print commands sent by the upstream integration.

- Native protocol v4 returns the actual wire sequence ID to Home Assistant.
- Protocol v3 runtimes are rejected instead of silently mixing old/new sending behavior.
- Printer replies are correlated by printer connection, section, command and wire ID.
- Immediate firmware rejections raise an error with the numeric firmware code.
- Late matching acknowledgements/rejections appear in the panel history.
- Native acceptance without a matching firmware reply stays explicitly unconfirmed.
- Redacted last-command feedback is available in diagnostics. G-code, account tokens,
  access codes and raw firmware reason strings are not included.
- Commands are not automatically retried.

Update in HACS, restart Home Assistant fully and reload Bambu Control with Ctrl+F5.

Validation: 112 Python tests and both browser suites pass locally. Added coverage for
native acceptance followed by an early firmware rejection over real subprocess pipes,
correlation/redaction/session reset, explicit acknowledgements and late UI feedback.
The compiled worker self-test checks the Studio ID range, 10,000-value wrap,
normalization of homing/nozzle/bed commands and preservation of their G-code.
Both native architecture builds and package checks run before publication.

The reported A1 hardware failure has not been physically retested during development.
This fixes a concrete protocol mismatch and makes any remaining firmware rejection visible;
it does not claim that every A1 firmware combination is confirmed working.
