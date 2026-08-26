# ClawOS

ClawOS is an Arch-based, OpenClaw-native operating-system project. OpenClaw's
Control UI is the primary desktop and agent control plane.

The current implementation is **Milestone 0**: a reversible Sway/Chromium kiosk
session for proving the desktop model on the existing T2 MacBook before building
an installer or ISO. It runs on VT2 and does not replace or modify Omarchy.

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
