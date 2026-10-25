# Validation record: 2026-10-25, v0.2.0

## Completed

- 48 offline Python tests pass under Python 3.12.
- Syntax compilation passes for components, scripts and tests.
- Native transport tests use real subprocess fixtures, pipes and threads.
- Cloud tests use fake upstream account responses.
- Login/options flow tests execute the actual flow methods with small HA/UI stubs.
- No real account credentials were used and no physical printer was contacted.

Covered: scoped MQTT factories, reviewed upstream interface, reversible hooks,
multi-printer isolation, signing guard, queued publish behavior, command
rejection, timeouts, disconnect queue disposal, worker cleanup, cloud MQTT
username/token forwarding and preserved cloud TLS verification.

Cloud coverage: direct login, email code, 2FA, resend, CSRF fallback, incorrect
and expired codes, password clearing, invalid token responses, blocked login,
printer filtering, account-bound selection, in-place entry updates,
rollback, options login and credential-folder validation.

## Still required

- Compile OBN and worker for Alpine amd64 and aarch64.
- Run native self-tests and protocol smoke tests on each architecture.
- Verify packaged ELF dependencies, licenses and corresponding source.
- Test actual Home Assistant setup/startup/reload/options/disable/remove.
- Test real account login, email verification/2FA and an expired token.
- Verify existing config-entry/entity IDs remain unchanged in real HA.
- Confirm LAN configuration makes no cloud connection.
- Test cloud subscription, printer offline/online, reconnect and worker failure.
- Test real signing material, app-cert acknowledgement and firmware rejection.
- Check P2S TLS behavior with installed firmware.
- Check existing local camera/FTP behavior after changing MQTT transport.
- Validate HACS metadata after configuring the real GitHub repository.

The delivered ZIP is a source preview, not a tested installable HACS release.
