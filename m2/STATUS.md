> **Historical record.** Describes design or state at that time, not current release acceptance. `artifacts/...` paths cited below were local, git-ignored build outputs and are not in this repository.

# Milestone 2 delivery status

Last updated: 2026-09-02

## Active exit criterion

A fresh UEFI VM must boot into a branded **Try / Install ClawOS** experience,
complete the guarded encrypted installation without requiring terminal
commands, reboot through disk unlock directly into the agent workspace without
a second login, and retain independent recovery. The installed top bar, agent
shelf, OpenClaw Control UI, onboarding, and scaling must come from the image.
The complete path must retain automated logs and screenshots.

## Implemented in source

- The live image owns a dedicated unprivileged `clawos-live` PAM/Wayland
  session on tty2 and leaves tty3 as the visible recovery path.
- A native GTK surface provides Try, Install, disk selection, byte-exact
  passphrase collection, progress output, failure recovery, completion, and
  graphical restart states.
- The selected Carapace-aligned Agent Canvas is implemented in the native GTK
  surface with measured near-black/coral/sea-green tokens, Arch `inter-font`
  (`Inter Variable`), Geist Mono, the real ClawOS halftone raster, a 52-pixel
  top bar, open hero, equal readiness/event panes, and no generic cards.
- Same-viewport design QA passed after verifying the Sway rect and GTK client
  geometry are both exactly 1440 x 900. Keyboard-tested welcome, Try, guarded
  no-disk Install, and focused comparison evidence is retained under
  `artifacts/m2/design/`; the full report is in `design-qa.md`.
- The live Polkit policy authorizes only the already guarded Q35 `/dev/vda`
  proof installer and an exact reboot helper. It does not authorize a shell or
  general `systemctl` operation.
- The ArchISO source now includes the compositor, GTK, Chromium, Node.js,
  fonts, Mesa, Waybar, and other packages needed to enter the graphical live
  path rather than a terminal.
- The existing installer continues to build LUKS2/Btrfs, installs the pinned
  OpenClaw appliance, copies the top bar/shelf/onboarding/session from source,
  and enables direct post-unlock entry into the `clawos` session.
- `m1/tests/m2-e2e-qemu` creates a throwaway qcow2 disk, captures the graphical
  live welcome, runs the guarded installer contract, boots the encrypted disk
  with the ISO detached, validates the image-built shell and recovery path,
  captures installed first boot, and shuts down cleanly.
- Static profile, OpenClaw integration, application registry, surface broker,
  Python syntax, shell syntax, policy-scope, and no-Omarchy checks pass.
- The next-image release pass replaces the misleading Try action with a
  truthful system-inspection path, adds guarded inline passphrase validation
  and destructive-action disclosure, removes inert live top-bar controls,
  exposes Escape and accessible password-field navigation, reports the active
  display geometry, and makes the Agent shelf and System Center responsive.
  These changes passed the seven-stage source gate and live 1440 x 900,
  1360 x 768, and 1280 x 768 hot-load QA. Image-level acceptance also passes on
  the 2026-09-02 19:53 rebuild: the fresh ISO booted against a new blank qcow2
  target, contained both required font packages, reported zero failed units,
  and visually passed Welcome, Inspect System, and guarded Install at
  1440 x 900.
- A clean materialized profile also passes validation; the current source does
  not rely on the host's Omarchy repositories, paths, extensions, or theme.

## Completed verification

- Fresh ISO:
  `artifacts/m1/out/clawos-2026.09.01-x86_64.iso`
  (`1710792704` bytes, built 2026-09-01 15:03:39 -0500).
- SHA-256:
  `5b795ec11bcf0b9af52a522c283f9c7a3650b999de6942487a674276bd88ebf1`.
- The build's boot-chain validation passed, and the clean profile retained the
  no-Omarchy and static validation gates. An independent headless UEFI boot of
  the same ISO passed identity, systemd, DHCP, overlay-root, and clean-poweroff
  checks; evidence: `artifacts/m1/smoke.OdiWms/`.
- `m1/tests/m2-e2e-qemu` passed from a fresh live boot through a newly
  partitioned LUKS2/Btrfs installation and installed first boot with the ISO
  detached. Evidence: `artifacts/m1/m2-e2e.T5Npo7/`.
- Required live, install, systemd, agent-session, Agent Canvas, shelf, top-bar,
  onboarding, and recovery markers all passed. Both QEMU error logs are empty.
- `live-welcome.png`, `installed-unlock.png`, and
  `installed-first-boot.png` are each 1440 × 900 and were visually inspected.
  They show the native live canvas, branded unlock, and image-built first-boot
  agent workspace without terminal leakage, nested browser chrome, clipping,
  or scaling failure.
- The installed system reported zero failed systemd units and shut down
  cleanly after validation.

## Result

The M2 graphical installation exit criterion passed on 2026-09-01. Offline
release packaging and physical T2 MacBook validation remain later release
gates; they are not implied by this QEMU proof.

The next fresh-image regression additionally verifies that the installed image
contains the separate User Limited runtime identity and explicit share, and
uses upstream `openclaw agents` to create an isolated second agent, add an
explicit routing binding, and prove distinct workspace paths. M2 remains passed;
the expanded regression must pass before the combined M2-M4 candidate is
accepted.
