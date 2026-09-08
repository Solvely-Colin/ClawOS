# Experimental hardware installation

The installer no longer requires a VM. It accepts eligible **blank SATA, NVMe,
virtio and eMMC whole disks** of at least 32 GiB on **x86_64 UEFI** systems.
This is code-level eligibility, not a tested-device compatibility guarantee.
Physical-hardware acceptance has not yet been completed.

## Safety boundary

- Run only from a ClawOS live ISO with identifiable boot media and Secure Boot off.
- Choose a disk explicitly; no disk is selected by default.
- Boot media, read-only disks, mounted disks, swap, device-mapper/RAID holders,
  existing partitions and filesystem signatures are refused.
- The UI shows path, capacity, model and a short identity hint. Type the exact
  `ERASE-/dev/...` confirmation for that disk in addition to the disk passphrase.
- The privileged installer rechecks disk identity and eligibility immediately
  before partitioning. Removing/swapping devices invalidates the selection.
  The identity includes the kernel disk generation, not only model/serial text,
  and is checked again before formatting the newly created partitions.
- The complete Arch package dependency set is downloaded and signature-verified
  into the live environment before erasure. Downloads use one connection, tolerate
  slow archive responses, and have three attempts of at most 15 minutes each.
  Download, signature or live-storage failures stop before disk writes.
  The target is installed from those local packages with required signatures;
  the pinned OpenClaw runtime is copied from the ISO, not fetched again.
  Internet access and sufficient temporary live storage are still needed for
  preparation. Hardware, power or installation-hook failures after formatting
  can still leave a partial installation; this is not an atomic OS installer.
- The installer does not repartition or migrate an existing OS. Use a blank spare
  disk and back up your machine; do not bypass guards to test on a daily driver.

## Inspect without installing

From the live ISO, list candidates:

```sh
python3 /usr/lib/clawos/clawos_install_targets.py list
```

After identifying your intended disk, validate it without partitioning,
formatting, changing credentials or installing packages:

```sh
sudo clawos-install-dev --target /dev/nvme0n1 \
  --disk-id '<diskId from the candidate list>' \
  --confirm 'ERASE-/dev/nvme0n1' --dry-run
```

The path above is an example, not a default. The graphical installer handles
selection, confirmation and passphrase storage without putting secrets in args.

## Passwordless setup (accepting the risk)

The install screen offers a **passwordless setup** checkbox for people who
explicitly accept that anyone with access to the machine can use it and read
its data. It maps to `clawos-install-dev --passwordless` and changes three
things: the system partition is plain Btrfs with no LUKS layer, the `root` and
`clawos` accounts get empty passwords, and `/etc/clawos-passwordless-entry`
(the same per-machine opt-in `clawos-lock` already honours) disables screen
locking. The exact `ERASE-/dev/...` confirmation is still required. In every
install mode `sshd` refuses password and root login (`/etc/ssh/sshd_config.d/00-clawos.conf`);
use SSH keys. Polkit approval prompts accept the empty password.
There is no in-place migration between the two modes; reinstall to switch.

## Installed system and remaining proof

The target uses GPT, an EFI system partition, LUKS2 (unless passwordless) and
Btrfs. SATA/virtio and NVMe/eMMC partition naming is handled separately. Both
common x86 microcode packages are included. The loader entry is written before
`bootctl --graceful install`, which runs from the live system rather than the
chroot (bootctl skips firmware variables inside a chroot). A firmware that
refuses NVRAM writes still gets a bootable ESP through the removable-media path.

Passwordless serial-root login is not installed by default. It is reserved for
the explicit `--vm-test` harness, which still requires Q35 KVM and `/dev/vda`.
On the live ISO itself, `ttyS0` only autologs in on that same Q35 KVM machine;
on any other hardware the serial console asks for credentials. The archiso
base still autologs root on the live `tty1`, as every Arch live image does.
The graphical session owns tty2; tty3 remains the normal recovery console.

Secure Boot, legacy BIOS, ARM, Apple Silicon, RAID/multipath installation,
existing-disk repartitioning and offline installation are outside this first
hardware-capable path. Intel T2 still needs its platform-specific work. GPU,
Wi-Fi, suspend and firmware compatibility require real hardware evidence.

Report ISO checksum, machine model, firmware mode, disk type and result. Omit
serial numbers, MAC addresses, credentials and identifying logs from public reports.
