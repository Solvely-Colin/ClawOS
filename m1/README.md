# Milestone 1: clean ArchISO

This milestone produces a clean, generic x86_64 ClawOS development ISO from
Arch's official `releng` profile plus a small reviewed overlay. It is the first
environment allowed to count toward ClawOS release gates.

The initial ISO proves provenance, UEFI boot, networking, recovery TTY, and the
absence of Omarchy. T2 packages, OpenClaw offline packaging, the graphical shell,
and installation are added only after this base boots in QEMU.

## Host preparation

```bash
./m1/bin/install-build-deps
```

## Validate and build

```bash
./m1/tests/validate-profile.sh
sudo ./m1/bin/build-iso
./m1/tests/boot-smoke-qemu
./m1/bin/run-qemu
```

Build products live under `artifacts/m1/` and are ignored by Git.

`boot-smoke-qemu` is the release gate for the live base. It boots the ISO
headlessly, controls ClawOS over its serial console, verifies OS identity,
systemd health, networking, and the live overlay root, then powers the VM off.
Each run preserves its serial log and transcript in `artifacts/m1/smoke.*`.

## Writable development disk

Installer work is restricted to a generated qcow2 disk under
`artifacts/m1/disks/`. The runner rejects physical devices, raw images, symlinks
that resolve outside that directory, and images whose detected format is not
qcow2.

```bash
./m1/bin/create-dev-disk          # creates a new 32G clawos-dev.qcow2
./m1/bin/run-installer-qemu       # ISO plus that isolated writable disk
```

Disk creation refuses to overwrite an existing image. The current M1 image is
only the live/recovery base; the destructive in-guest installer is not enabled
until its target guard and recovery tests exist.
