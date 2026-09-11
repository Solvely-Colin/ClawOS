# Scope

ClawOS is an experimental Arch-based operating system whose primary interface
is the OpenClaw agent: an archiso `releng` image plus a reviewed overlay, a
blank-disk installer that writes an encrypted (or, on explicit request,
passwordless) system, a root broker (`clawosd`) that exposes typed machine
actions, and the pinned upstream OpenClaw runtime, which owns models,
credentials and conversations. It is unreleased source with no tags.

**Who it is for:** developers with a disposable virtual machine who want to
build the ISO, install it on a throwaway disk and work on the OS itself. Not
for daily-driver machines. Steps are in [GETTING-STARTED.md](GETTING-STARTED.md).

**Supported target:** an x86_64 UEFI virtual machine (QEMU/KVM or Windows
QEMU/WHPX) with OVMF firmware, 4 GiB RAM, a blank disk of at least 32 GiB, and
network to the pinned Arch archive snapshot (`image/config/versions.env`) and npm.

The installer enforces a VM-only default. Its GUI cannot opt into physical
installation; the CLI requires `--experimental-hardware` for that unsupported
path, preserving all blank-disk/live-media safeguards. Unknown virtualization
is refused, not interpreted as a virtual machine. See [HARDWARE.md](HARDWARE.md).

| Bucket | Capability | Evidence |
| --- | --- | --- |
| Supported in VM | Live ISO boots under UEFI/OVMF; installed system boots without the ISO through its systemd-boot entry; LUKS unlock with the typed passphrase | WHPX: [HARDWARE-INSTALLER-VALIDATION.md](HARDWARE-INSTALLER-VALIDATION.md) "2026-09-07: sshd policy and both install modes re-verified". The ISO workflow requires `image/tests/boot-smoke-qemu` and passwordless `image/tests/install-smoke-qemu`; the legacy `image/tests/m2-e2e-qemu` remains separate. ISO structure: `image/tests/validate-iso.sh`, run by `build-iso` |
| Supported in VM | Blank-disk install, encrypted (LUKS2) and `--passwordless`, driven from the live `tty1`; complete package set downloaded and signature-verified before the first disk write | same 2026-09-07 section and "Download-failure regression checks (2026-09-07)"; `image/tests/test_install_targets.py`, `image/tests/test_install_packages.py` (`ci.yml` job `unit-tests`) |
| Supported in VM | Installed system: `sshd` refuses password, keyboard-interactive and root login; `tailscaled` enabled but not enrolled; `clawosd` and `clawos-session@clawos` active | same 2026-09-07 section (`sshd -T`, `tailscale status`) |
| Supported in VM | Source gate: Python and Node unit tests, `./image/bin/preflight-iso` | `ci.yml` jobs `unit-tests` and `arch-preflight` on every push |
| Experimental | GTK installer (`clawos-live-welcome`), default onboarding and the Control UI | Encrypted graphical install, disk-only boot, local Gateway, model deferred and Full Root verified on 2026-09-10 at `de19c1b`, CI run 34432248984, WHPX/8 GiB/40 GiB NVMe. Passwordless GTK, non-default policy, remote Gateway and provider inference remain unverified by that run ([record](HARDWARE-INSTALLER-VALIDATION.md#2026-09-10-graphical-encrypted-install-and-default-onboarding-on-the-ci-iso)) |
| Experimental | Runtime deployment and rollback, broker approvals, remote-node roles, Windows VM lifecycle scripts | Core agent loop passed on unmodified CI ISO run 34522981039 in a fresh passwordless WHPX guest: inference, update, lost-ack delivery retry and exact file rollback. Broader approval/role evidence remains development-VM and isolated-test scoped ([FEATURES.md](../FEATURES.md)) |
| Experimental | CI-built ISO (`release.yml`); physical x86_64 UEFI hardware | Workflow requires structural validation, live KVM boot and passwordless install/disk-only/updater-readiness checks. Run 34522981039 also passed the fresh WHPX core agent loop without runtime repair. No physical machine installed; manual ISO retention is opt-in and this temporary ISO artifact was removed ([EVIDENCE.md](EVIDENCE.md)) |
| Not implemented or by design | Secure Boot, legacy BIOS, ARM/Apple Silicon, RAID/multipath, existing-disk or dual-boot install, offline install | outside the first hardware path ([HARDWARE.md](HARDWARE.md)) |
| Not implemented or by design | Signed or supported releases; containment of an untrusted agent; multi-user hardening | Full Root is a trusted-agent mode ([SECURITY.md](../SECURITY.md)) |

**Non-goals:** not a hardened multi-user OS; not a sandbox for an untrusted
agent (Full Root gives the `clawos` account passwordless sudo); not a fork of
OpenClaw (the pinned upstream package is installed from npm unchanged); not an
installer for existing disks (blank whole disks only, nothing is migrated).

ClawOS is an independent project and is not affiliated with or endorsed by
OpenClaw or Arch Linux; see [NOTICE.md](../NOTICE.md).

See also [SECURITY.md](../SECURITY.md), [HARDWARE.md](HARDWARE.md),
[KNOWN-ISSUES.md](KNOWN-ISSUES.md) and [CONTRIBUTING.md](../CONTRIBUTING.md).
[FEATURES.md](../FEATURES.md) uses the same three buckets.
