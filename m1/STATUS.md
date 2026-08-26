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

## Not yet proven

- Partitioning, LUKS2, Btrfs subvolumes, or installation to the qcow2 disk.
- Booting an installed system without the live ISO.
- Offline package installation and recovery/rollback entries.
- T2 hardware packages or booting on the reference MacBook.
- The graphical setup application and OpenClaw appliance.

The live/recovery ISO is valid; it is not yet an installer or a graphical
ClawOS release.
