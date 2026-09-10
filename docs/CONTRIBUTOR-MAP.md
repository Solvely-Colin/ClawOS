# Find your way around ClawOS

The `m0`–`m4` names come from milestones, not separate operating systems.
Most current runtime code is under `m1`, `m2` and `m3`. Start by behavior:

| Work on | Source | Verification |
| --- | --- | --- |
| ISO assembly and build tooling | `m1/bin/`, `m1/config/`, `m1/profile-overlay/` | `m1/bin/preflight-iso`; build/validate ISO inside Linux |
| Installer and disk guards | `m1/profile-overlay/airootfs/usr/local/bin/clawos-install-dev`, `usr/lib/clawos/clawos_install_targets.py` under the same airootfs | `m1/tests/test_install_*.py`; disposable-disk proof for behavior changes |
| Desktop, panel and onboarding | `m1/profile-overlay/airootfs/etc/clawos/`, `usr/lib/clawos/`, `usr/share/clawos/` under that airootfs | focused `m1/tests/`; visual and keyboard checks in a VM |
| OpenClaw integration | `m2/openclaw-plugin/` | `npm --prefix m2/openclaw-plugin test` |
| Privileged system broker | `m3/clawosd/`, `m3/dbus/`, `m3/polkit/` | `m3/tests/`; real-UID D-Bus proof in CI |
| Standalone/remote-node roles | `clawos-role` and node helpers under the airootfs; plugin routing under `m2` | `m4/tests/role-switch.sh`, plugin tests; separate-controller VM proof remains |
| Windows VM management | `tools/windows/` | host tests plus SSH/ACPI lifecycle verification; never hard-stop QEMU |

New to the project? Start with [Contributing](../CONTRIBUTING.md), then
[Getting started](GETTING-STARTED.md). All runtime proof is VM-only. A green
source check is not proof of installation, inference or full-system recovery.

## What is historical?

`m0` is a guarded host-side experiment, not image content. Its static checks
still run in preflight. `shell-prototype` is a frozen browser mockup with its
own CI regression check, not the shipped desktop. Design rationale in `m2`
can include earlier approaches; current code and dated evidence take priority.
Retired plans, milestone diaries and private demo notes stay local. The public
[architecture](ARCHITECTURE.md) describes component ownership and remaining gaps.

## Planned component migration

Tracked in [#92](https://github.com/Solvely-Colin/ClawOS/issues/92); not part of
the documentation-only launch cleanup.

The intended direction is `image/` for image assembly, `runtime/` for installed
shell/installer/deployment components, `integrations/openclaw/` for the plugin,
`services/clawosd/` for the broker, and `tests/integration/roles/` for role tests.
Historical executable experiments can move under `experiments/` after their
checks and relative paths are updated. These names are a migration plan, not
paths contributors can use today.

Migrate in dedicated, behavior-preserving PRs. ISO materialization and live
deployment each map source files to installed destinations; update both,
along with CI, Dependabot, fixtures, docs and agent instructions. Preserve
installed `/usr/lib/clawos` paths and compare payload destinations/hashes.
Before landing runtime moves, run source checks, Linux ISO assembly and a
checkpointed VM live-deployment smoke test. Keep a compatibility entry point
for documented developer commands during the transition.
