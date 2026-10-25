# Regular release: v0.4.1

[Build 40239397623](https://github.com/odggg/ha-openbamboo/actions/runs/40239397623)
passed for commit e72436903a2f5bf938c7e6568396259d4099ea2d:
80 offline tests, both native architecture builds/cipher tests, source packaging
and the real HACS ZIP / regular GitHub Latest checks all passed.
GitHub /releases/latest returns v0.4.1 with draft=false and prerelease=false.

Changes: default regular HACS publishing, imported Bambu printer entry/device
names, preserved custom HA names and Google/OAuth login documentation.
The real release ZIP and GitHub Latest endpoint are checked by the publishing
job so the regular version is the default HACS download.

80 offline tests pass locally. Name regression coverage includes actual import-hook titles, serial-number
upgrades, custom names, later cloud renames, Unicode/fallback names, rollback
and reversible device metadata. Existing IDs remain stable.

The owner reported v0.4.0 working on 25 October 2026. This report did not
itemize every model/firmware combination.

## Previous releases

# Validation: v0.4.0 automatic credentials

71 offline tests pass locally, including generated test-only RSA credentials,
matching key/leaf, freshness, reuse without network, failure rollback,
invalid response rejection and concurrent-request suppression.

[Release build 40236792384](https://github.com/odggg/ha-openbamboo/actions/runs/40236792384)
passed for commit 02064acfe4baf5d264dff4c7c782032362816b55.

- All 71 offline tests passed on GitHub Python 3.13 as well as locally.
- Native amd64/aarch64 builds passed, including the fork's actual app-cert
  cipher/RSA known-answer tests.
- Native protocol v3, rejected relative provisioning paths and worker
  lifecycle smoke tests passed on both architectures.
- Runtime/source packaging passed and v0.4.0 release assets were published.
No real Bambu credentials are used by these offline tests.

Still required: real Bambu certificate provisioning in HA, actual cloud
camera and signed commands, startup/reload and renewal at a physical printer.

## Previous releases

# Validation record: v0.3.0 cloud camera

## Completed release checks

[Build run 40234819461](https://github.com/odggg/ha-openbamboo/actions/runs/40234819461)
built commit 6a6c4f3488f81c2a738b09058a36d1d0e49f461a.

- All 63 offline tests passed locally and on GitHub under Python 3.13.
- Actual H.264 encode/decode and MJPEG validation passed with PyAV 19.
- Native amd64 and aarch64 builds, camera URL parsing self-test, and JSON
  protocol v2/create/destroy smoke tests passed on both architectures.
- Runtime checksum/corresponding-source packaging passed.
- Experimental v0.3.0 and both ZIP assets were published.

## Scope of verification

- Offline regression tests include actual PyAV H.264 encode/decode to JPEG,
  valid MJPEG images, malformed/oversized video, bounded buffering, stale
  image invalidation, missing signing credentials and cloud worker IPC.
- Camera entity tests exercise actual platform methods with small HA
  registry/executor stubs, printer identity isolation and actionable errors.
- Signing readiness tests verify that missing controls are recreated once.
- Native builds must compile the real OBN TUTK receiver and camera bridge
  on amd64/aarch64 and pass protocol v2 and camera URL parsing self-tests.
- Source/package checks preserve exact OBN provenance and runtime hashes.

There is no physical HA/printer or actual Bambu account/camera validation.
Offline frame decoding proves codec and pipe behavior, not end-to-end cloud
camera reachability or printer firmware authorization.

## Required live checks

- HACS install/update, restart, setup, reload and remove in actual HA.
- Account login with direct login and code/2FA.
- Cloud camera without local IP or LAN access code, using valid own slicer
  key/cert/CRL; both direct P2P and relayed TUTK network paths.
- Confirm same HA printer device linkage, stream rendering and reconnect.
- Missing/invalid signing files and rejected/expired cloud camera sessions.
- View multiple printers/viewers; close views and verify media session expiry.
- Pause/resume/light with firmware authorization accepted and rejected.
- Camera failure must not interrupt status or queued printer commands.
- H.264/MJPEG model coverage and explicit unsupported Agora behavior.

## Previous MQTT-only release validation

### v0.2.0 (2026-10-25)

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
