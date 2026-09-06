# Hardware support

ClawOS cannot currently be installed through its development installer on
arbitrary Arch-compatible hardware. This is an enforced safety boundary.

`m1/profile-overlay/airootfs/usr/local/bin/clawos-install-dev` requires:

- target `/dev/vda`, a blank whole disk with no mounted children;
- `systemd-detect-virt --vm` reporting `kvm`;
- machine model `Standard PC (Q35 + ICH9, 2009)`;
- explicit `ERASE-QEMU-/dev/vda` confirmation and an installer-owned LUKS key.

The existing Windows development VM is a managed runtime environment. That does
not establish that a fresh WHPX installation passes the installer's KVM guard.
Do not remove these guards to experiment on a daily-driver machine.

An ISO booting on physical UEFI x86_64 hardware is not installation or usability
proof. Graphics, firmware, network interfaces, storage, encryption, suspend,
Secure Boot and input must be validated separately. ARM and Apple Silicon are
not current targets; the long-term Intel T2 target also needs its own proof.

Hardware reports should include the ISO checksum, machine model, CPU/GPU,
firmware mode and observed result, but omit serial numbers, MAC addresses,
credentials and identifying logs unless shared privately and intentionally.
