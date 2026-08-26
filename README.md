# ClawOS

ClawOS is an Arch-based, OpenClaw-native operating-system project. OpenClaw's
Control UI is the primary desktop and agent control plane.

The current implementation is **Milestone 1**: a clean ArchISO, guarded QEMU
installer, encrypted standalone development disk, and first-boot OpenClaw
onboarding path. The real upstream Control UI is the graphical OS surface;
ClawOS does not maintain a second dashboard.

Milestone 0 remains available as a reversible host-only compositor experiment.

## Milestone 0

Review [PLAN.md](PLAN.md), then run:

```bash
./m0/tests/static-check.sh
sudo ./m0/bin/install-m0 colin
sudo systemctl start clawos-session@colin.service
```

The session expects OpenClaw at `http://127.0.0.1:18789/`. Override it in
`/etc/clawos/session.env` before starting the service. Switch to the session with
`Ctrl+Alt+F2`; `Ctrl+Alt+F3` remains the recovery TTY.

Stop and remove the experiment without touching the existing desktop:

```bash
sudo systemctl stop clawos-session@colin.service
sudo ./m0/bin/uninstall-m0
```

The installer deliberately does not enable the service at boot.

Current implementation and machine state are tracked in
[m0/STATUS.md](m0/STATUS.md).

## Milestone 1

Build, install, and boot the isolated QEMU proof by following
[m1/README.md](m1/README.md). On first graphical boot, ClawOS asks whether the
Gateway should run on this machine or on an existing host, then delegates setup
to the pinned upstream `openclaw onboard` wizard. `Ctrl+Alt+F3` remains the
independent recovery console.
