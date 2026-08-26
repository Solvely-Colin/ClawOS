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
./m1/bin/run-qemu
```

Build products live under `artifacts/m1/` and are ignored by Git.
