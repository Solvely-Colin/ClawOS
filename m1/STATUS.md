# Milestone 1 status

Last validated: 2026-08-26

## Proven

- Clean Arch, UEFI-only ISO builds from the pinned Arch Linux Archive snapshot.
- ISO checksum, bootloader arguments, initramfs live-root hooks, and
  `memdiskfind` are validated before an artifact is accepted.
- No-Omarchy contamination checks pass on profile and live-root inputs.
- QEMU reaches an automatically logged-in ClawOS root shell on tty1 and ttyS0.
- The headless boot gate verifies ClawOS identity, zero failed systemd units,
  DHCP networking, the live overlay root, and clean guest poweroff.
- Agent operation works through a serial socket; QEMU lifecycle control works
  through a monitor socket while a GTK Machine View remains available.
- A guarded 32 GB qcow2 development disk is visible inside ClawOS as blank,
  unmounted `/dev/vda`. The runner rejects physical devices, raw images, and
  paths outside `artifacts/m1/disks/`.
- The development installer creates a 1 GB EFI partition and a LUKS2-encrypted
  Btrfs system with separate root, home, logs, package-cache, and snapshot
  subvolumes.
- The qcow2 boots through its own systemd-boot entry with the live ISO removed,
  accepts the LUKS passphrase over the recovery serial console, mounts the
  encrypted root, reaches `clawos-installed#`, obtains DHCP, and reports zero
  failed systemd units.
- The development installer now installs a dedicated `clawos` owner account,
  Sway/Chromium graphical shell, and system-level session service that opens
  the upstream OpenClaw Control UI after disk unlock without a second login.
- A validation gate rejects a parallel ClawOS web shell; the pinned OpenClaw
  bundle remains the sole graphical operating surface.
- The development installer pins and installs OpenClaw `2026.7.1-2`, Node.js,
  Chromium, Sway, Foot, NetworkManager, Polkit, and Tailscale into the target.
  Its npm 12 invocation explicitly permits only the install scripts required by
  OpenClaw and its three known scripted dependencies.
- The installer resets its filesystem-creation umask to `022` after validating
  the mode-0600 LUKS key, preventing the caller's secret-creation umask from
  making standard system directories inaccessible.
- First boot now selects local or existing-Gateway operation, delegates the
  actual setup to upstream `openclaw onboard`, installs an upstream node host,
  and enters the authentic Control UI without exposing its token in Chromium's
  process arguments.
- An installed QEMU boot reached the ClawOS role selector and successfully
  handed the local role to the authentic OpenClaw security/onboarding wizard.
  That run caught and repaired npm-script and inherited-umask defects; a fresh
  image/disk regression remains required for an unmodified end-to-end pass.
- The upstream local and remote onboarding entry points were exercised against
  isolated OpenClaw state without modifying the development host's config.

## Not yet proven

- Automated install-to-disk and installed-boot regression gates.
- Offline package installation and previous-kernel/recovery/rollback entries.
- T2 hardware packages or booting on the reference MacBook.
- Graphical installed-boot and end-to-end onboarding proof in QEMU.
- Successful first node pairing and agent-driven command execution in both
  local and remote-Gateway modes.
- The complete offline OpenClaw appliance and production installer.

The live/recovery ISO and network-backed QEMU proof installer are valid. This
is not yet the offline production installer or a graphical ClawOS release.
