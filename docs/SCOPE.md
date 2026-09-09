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
network to the pinned Arch archive snapshot (`m1/config/versions.env`) and npm.

| Bucket | Capability | Evidence |
| --- | --- | --- |
| Supported in VM | Live ISO boots under UEFI/OVMF; installed system boots without the ISO through its systemd-boot entry; LUKS unlock with the typed passphrase | WHPX: [HARDWARE-INSTALLER-VALIDATION.md](HARDWARE-INSTALLER-VALIDATION.md) "2026-09-07: sshd policy and both install modes re-verified". KVM gates: `m1/tests/boot-smoke-qemu`, `m1/tests/m2-e2e-qemu` (not run in CI). ISO structure: `m1/tests/validate-iso.sh`, run by `build-iso` |
| Supported in VM | Blank-disk install, encrypted (LUKS2) and `--passwordless`, driven from the live `tty1`; complete package set downloaded and signature-verified before the first disk write | same 2026-09-07 section and "Download-failure regression checks (2026-09-07)"; `m1/tests/test_install_targets.py`, `m1/tests/test_install_packages.py` (`ci.yml` job `unit-tests`) |
| Supported in VM | Installed system: `sshd` refuses password, keyboard-interactive and root login; `tailscaled` enabled but not enrolled; `clawosd` and `clawos-session@clawos` active | same 2026-09-07 section (`sshd -T`, `tailscale status`) |
| Supported in VM | Source gate: Python and Node unit tests, `./m1/bin/preflight-iso` | `ci.yml` jobs `unit-tests` and `arch-preflight` on every push |
| Experimental | GTK installer (`clawos-live-welcome`); onboarding past its first screen; provider enrollment and model inference; the Control UI | synthetic GTK preview only; listed as not exercised on 2026-09-07 |
| Experimental | Runtime deployment and rollback, broker approvals, remote-node roles, Windows VM lifecycle scripts | development VM and isolated tests only ([FEATURES.md](../FEATURES.md)) |
| Experimental | CI-built ISO (`release.yml`); physical x86_64 UEFI hardware | the workflow went green twice on 2026-09-08 (first on `main`: run 34270708295); it validates but does not boot, and that image was booted live by hand, not installed from ([EVIDENCE.md](EVIDENCE.md)); no physical machine installed ([KNOWN-ISSUES.md](KNOWN-ISSUES.md)) |
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
