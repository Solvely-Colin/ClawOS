# Privileged system broker

`clawosd` is the root-owned typed system broker. In the default
Full Root mode, OpenClaw can prepare and commit exact actions without a human
authorization prompt. The typed route still creates recovery points and audit
receipts. Full User + Approvals retains short-lived single-use tokens and local
Polkit authorization; User Limited uses a separate runtime account.

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

## Status is not startup acceptance

`GetStatus` / `clawosctl status` reports `brokerState: "ready"` when the
broker answers, but machine `state: "unknown"`. Its `readiness` fields for
setup, desktop, lock, Gateway and model are explicitly `"unverified"`.
Supported capabilities and pending/grant counts are not evidence that those
components work. Status does not run inference or inspect provider credentials.
The shell's Gateway/controller tooltip separately says reachability leaves the
model unverified. Consumers must not promote either signal to machine readiness.

This is the first, conservative slice of #53, not the shared startup-state
implementation: setup/lock observation, unified consumers and five cold-boot
acceptance remain outstanding.

## Caller and approval boundary

Mutating calls and token-bearing pending lists require root, the OS-resolved
configured owner account, or (in User Limited) the configured agent account in
an exact Gateway/Node user-service cgroup. A similarly named unit or an unrelated
UID does not qualify. Gateway/Node preparation requires explicit agent metadata
and policy, even when it runs as the owner; direct owner/root CLI administration
and onboarding may omit metadata. The plugin binds metadata through the pinned
OpenClaw SDK's factory and per-call hooks, not the execute abort-signal argument.

Tokens bind to the requester's UID and current boot, not its short-lived CLI PID.
The owner/root approval UI may review and act on runtime requests; other callers
cannot take their tokens. Approval modes and high-impact actions still require
Polkit, and commit rechecks the original agent's current policy/grant. Upgrading
from an unbound-token version invalidates outstanding approvals; prepare again.

This is an OS-account boundary, not cryptographic per-agent isolation. Processes
sharing a trusted account/unit can still claim metadata belonging to that shared
runtime. Full Root continues to trust the owner account with passwordless sudo.

Run the source checks with:

```bash
python3 -m unittest discover -s services/clawosd/tests -v
npm --prefix integrations/openclaw test
./image/tests/validate-profile.sh
```

In a disposable ClawOS VM with `python-dbus`, GLib, `dbus-daemon`, `runuser`,
and the normal `clawos`/`nobody` accounts, also run:

```bash
sudo python3 services/clawosd/tests/verify_dbus_authorization.py "$PWD"
```

This creates a private D-Bus daemon and temporary broker state, uses real caller
UIDs, and substitutes a fake machine runner. It never changes real services.

CI runs the same proof on every push and pull request: the `arch-preflight` job
in `.github/workflows/ci.yml` installs `dbus`, `python-dbus` and `python-gobject`
from the pinned Arch snapshot, creates the configured owner account, and runs
the script as root after `preflight-iso`. The job fails if its `PASS` line is
missing.
