# Milestone 0 status

## Implemented

- Root-owned Sway kiosk configuration, explicitly selected with `sway -c`.
- System-level VT2 session unit; it is never enabled automatically.
- Chromium Wayland kiosk launcher with bounded Gateway readiness wait.
- Root-owned Chromium managed policy blocking extensions, Developer Tools,
  browser sign-in, Incognito, and unapproved origins.
- Reversible installer and uninstaller that do not modify Omarchy files.
- Static validation for shell syntax and the critical policy invariants.

## Machine state

- Chromium and tmux are installed.
- Sway, swaylock, and swayidle still require an interactive privileged install.
- The OpenClaw CLI/Gateway is not currently installed or running on the host.
- No ClawOS service has been installed, enabled, or started.

## Next proof

Run the package and session install from a visible terminal:

```bash
sudo pacman -S --needed sway swaylock swayidle
cd /home/colin/Work/ClawOS
sudo ./m0/bin/install-m0 colin
```

Do not enable the unit. Once OpenClaw is listening on the configured URL, start
the experiment manually:

```bash
sudo systemctl start clawos-session@colin.service
```

Validate VT switching, lock, idle, suspend, lid close, Chromium policy, HiDPI,
GPU behavior, browser recovery, and tmux persistence before advancing M0.
