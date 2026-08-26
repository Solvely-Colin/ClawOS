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

## Not yet proven

- Automated install-to-disk and installed-boot regression gates.
- Offline package installation and previous-kernel/recovery/rollback entries.
- T2 hardware packages or booting on the reference MacBook.
- Graphical installed-boot proof in QEMU, first-boot setup, and the complete
  OpenClaw appliance.

The live/recovery ISO and network-backed QEMU proof installer are valid. This
is not yet the offline production installer or a graphical ClawOS release.
