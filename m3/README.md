# Milestone 3: privileged OS control

M3 introduces `clawosd`, the root-owned typed system broker. In the default
Full Root mode, OpenClaw can prepare and commit exact actions without a human
authorization prompt. The typed route still creates recovery points and audit
receipts. Full User + Approvals retains short-lived single-use tokens and local
Polkit authorization; User Limited remains the isolated option.

The current vertical slice supports coherent read-only machine inspection,
allowlisted and verified system-service management, durable token-free action
receipt lookup, an allowlisted signed Arch package install, an exact
ClawOS-promoted OpenClaw update, system time preferences, and recovery rollback. Updates install
the pinned upstream package, run upstream post-update migration and plugin
convergence under the OpenClaw owner, restart the Gateway from the root system
scope, and verify it is active before recording success.

No API accepts shell text, arbitrary package names, arbitrary service names,
paths, or executables. Plugin-supplied agent metadata is recorded only as
self-reported correlation; D-Bus peer UID and PID are authoritative.

Run the source checks with:

```bash
python3 -m unittest discover -s m3/tests -v
npm --prefix m2/openclaw-plugin test
./m1/tests/validate-profile.sh
```
