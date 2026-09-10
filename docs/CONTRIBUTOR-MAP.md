# Find your way around ClawOS

The repository is organized by component rather than historical milestones.
Start by behavior:

| Work on | Source | Verification |
| --- | --- | --- |
| ISO assembly and build tooling | `image/bin/`, `image/config/`, `image/profile-overlay/` | `image/bin/preflight-iso`; build/validate ISO inside Linux |
| Installer and disk guards | `image/profile-overlay/airootfs/usr/local/bin/clawos-install-dev`, `usr/lib/clawos/clawos_install_targets.py` under the same airootfs | `image/tests/test_install_*.py`; disposable-disk proof for behavior changes |
| Desktop, panel and onboarding | `image/profile-overlay/airootfs/etc/clawos/`, `usr/lib/clawos/`, `usr/share/clawos/` under that airootfs | focused `image/tests/`; visual and keyboard checks in a VM |
| OpenClaw integration | `integrations/openclaw/` | `npm --prefix integrations/openclaw test` |
| Privileged system broker | `services/clawosd/src/`, `services/clawosd/dbus/`, `services/clawosd/polkit/` | `services/clawosd/tests/`; real-UID D-Bus proof in CI |
| Standalone/remote-node roles | `clawos-role` and node helpers under the airootfs; plugin routing under `integrations/openclaw` | `tests/integration/roles/role-switch.sh`, plugin tests; separate-controller VM proof remains |
| Windows VM management | `tools/windows/` | host tests plus SSH/ACPI lifecycle verification; never hard-stop QEMU |

New to the project? Start with [Contributing](../CONTRIBUTING.md), then
[Getting started](GETTING-STARTED.md). All runtime proof is VM-only. A green
source check is not proof of installation, inference or full-system recovery.

## What is historical?

`experiments/host-session` is a guarded host-side experiment, not image content. Its static checks
still run in preflight. `experiments/shell-prototype` is a frozen browser mockup with its
own CI regression check, not the shipped desktop. Design rationale in `docs/`
can include earlier approaches; current code and dated evidence take priority.
Retired plans, milestone diaries and private demo notes stay local. The public
[architecture](ARCHITECTURE.md) describes component ownership and remaining gaps.

## Updating an older checkout

Use `image/bin/` for the former image/build commands and
`integrations/openclaw/` for the plugin. Broker source lives in
`services/clawosd/src/`; reusable design and live-development guides live in
`docs/`. There are no milestone-named source directories or compatibility
directories to keep two layouts alive. Installed `/usr/lib/clawos` paths do
not change. Existing ignored `artifacts/m1/` output locations are retained so
the migration does not move or discard local VM disks and build evidence.

The filesystem overlay remains together under `image/profile-overlay/` so its
layout matches the installed filesystem. Separate image and runtime-deployment
mappings must continue to agree. Migration acceptance is tracked in
[#92](https://github.com/Solvely-Colin/ClawOS/issues/92).
