# Milestone 0 status

This VT2 implementation is a disposable hardware spike on the existing host,
not a ClawOS release environment. The Omarchy Chromium wrapper demonstrated
that host-userspace inheritance violates the product boundary. The service is
disabled and stopped; product work now moves to a clean ClawOS Arch root.

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
- Sway, swaylock, and swayidle are installed. The first physical launch proved
  the session must activate VT2 before acquiring DRM; the corrected unit still
  needs to be copied into the root-owned system location.
- OpenClaw 2026.7.1-2 is installed from the current published npm release.
- The Codex plugin is pinned at 2026.7.1-1 and passed an end-to-end agent turn.
- The loopback-only, token-authenticated Gateway is installed as an enabled
  systemd user service and passes `openclaw health`.
- Insecure Control UI authentication is disabled. The security audit has no
  critical findings; its sole warning is intentionally empty `trustedProxies`
  while the Gateway remains loopback-only.
- The experimental ClawOS service is installed but disabled and stopped.

## Next proof

Run the package and session install from a visible terminal:

```bash
cd /home/colin/Work/ClawOS
./m0/bin/complete-host-install
```

Do not enable the unit. OpenClaw is already listening on the configured URL;
after verifying the installed files, start the experiment manually:

```bash
sudo systemctl start clawos-session@colin.service
```

Validate VT switching, lock, idle, suspend, lid close, Chromium policy, HiDPI,
GPU behavior, browser recovery, and tmux persistence before advancing M0.
