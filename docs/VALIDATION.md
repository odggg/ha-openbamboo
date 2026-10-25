# Validation record: 2026-10-25, v0.2.0

## Native release validation

[Build run 40231586850](https://github.com/odggg/ha-openbamboo/actions/runs/40231586850)
completed successfully for commit 559e82a1bfc6dbdcb0ce54cbab752211b0387cd1.

- Real OBN and worker compiled under Alpine for amd64 and aarch64.
- Each bundled worker passed its self-test inside the build container.
- Each bundled musl runtime passed the native JSON protocol/create/destroy
  smoke test on its Ubuntu host architecture.
- The loader and 16 shared libraries per architecture were collected from ELF metadata.
- Runtime checksums and corresponding-source packaging passed.
- Experimental v0.2.0 release assets were published.

## Completed offline checks

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

- Test actual Home Assistant setup/startup/reload/options/disable/remove.
- Test real account login, email verification/2FA and an expired token.
- Verify existing config-entry/entity IDs remain unchanged in real HA.
- Confirm LAN configuration makes no cloud connection.
- Test cloud subscription, printer offline/online, reconnect and worker failure.
- Test real signing material, app-cert acknowledgement and firmware rejection.
- Check P2S TLS behavior with installed firmware.
- Check existing local camera/FTP behavior after changing MQTT transport.
- Validate HACS metadata after configuring the real GitHub repository.

The native release is built and smoke-tested. It is experimental: no real
Home Assistant installation, cloud login or physical printer was tested.
