# Hardware-capable installer validation

The VM-only guard is replaced by a blank-disk safety policy. This change is
experimental and has not yet been used to install a physical machine.

## Initial source-only checks (historical)

- Eleven target-policy tests: SATA/NVMe/virtio/eMMC naming, partition naming,
  boot-media exclusion, unknown boot source, mounted/swap/read-only/holder
  rejection, existing partitions/filesystems, minimum capacity, stale identity,
  kernel disk-generation changes, exact confirmation and raw filesystem signatures.
- Full Arch preflight: 35 M1 tests, 21 broker tests, 26 plugin tests and existing
  profile/onboarding/role integration checks passed.
- Bash syntax and ShellCheck passed for the installer, excluding only SC1091
  for its installed `/etc/clawos/versions.env` include.
- The new discovery helper was run on the installed development workstation and
  correctly refused it because installation is restricted to the live ISO.
- A synthetic GTK preview confirmed no default disk, wrong-target rejection and
  enabling only after the exact selected path and matching passphrases. Its
  installer and reboot methods were replaced with no-op preview handlers.
- No physical or virtual target was partitioned or formatted by those initial checks.

![Synthetic installer preview; no disk writes](assets/hardware-installer-preview.png)

## Download-failure regression checks (2026-09-07)

The original `47b6e44` candidate failed fresh encrypted NVMe and passwordless
SATA installs when Arch archive transfers timed out after partitioning. The fix
prepares and verifies the complete package set before the first disk write,
uses bounded retries, and installs from local packages with required signatures.
OpenClaw is bundled during ISO construction with executable modes preserved.

- Full Linux preflight and four package-preparation regression tests passed.
- A clean ISO passed boot-chain, bundled-version and executable-entry validation.
- In a fresh QEMU guest, disabling networking for the actual installer exhausted
  all three attempts. The disk checksum, absent partition table and blank-disk
  eligibility remained unchanged.
- The encrypted NVMe installation recovered from an HTTP/2 stream reset during
  package preparation, completed, and booted without ISO media through its
  registered Linux Boot Manager entry. LUKS unlock, desktop/onboarding entry,
  pinned OpenClaw execution, broker and SSH services passed.
- Passwordless SATA installation completed on its first preparation attempt and
  booted without ISO media through its registered firmware entry. Plain Btrfs,
  empty account passwords, disabled locking, SSH's `PermitEmptyPasswords no`,
  pinned OpenClaw and onboarding entry were checked. An unprivileged `claw`
  account could not switch to root with an empty password.
- The passwordless Windows/WHPX guest initially showed a blank frame and stalled
  SSH, then recovered after keyboard input. Immediate unattended first-paint
  responsiveness is not established by this run; the cause remains unconfirmed.
- No installed serial-root autologin was enabled. Post-boot inspection used a
  test-only SSH public key; no provider account or production secret was used.
- Physical hardware and complete provider enrollment/model inference remain
  outside these QEMU checks.

Tested fast ISO SHA256:
`8826f15d050678130ba1700bc47d2222c7c82b61b0105df5d6cfd0fd7099a5fc`.
The image contains the download-fix working tree based on `47b6e44`; both tests
used Windows-managed QEMU/WHPX, 4 GiB RAM, fresh 40 GiB virtual disks and UEFI
variables, and omitted `--vm-test`. All VM shutdowns were guest/ACPI-driven.

## Required before broader release claims

- [x] Build an ISO from the candidate source and pass ISO validation.
- [x] Run fresh QEMU SATA and NVMe installation tests, not only virtio.
- [ ] Verify boot media and mounted/signature-bearing disks are refused in that ISO.
- [x] Verify UEFI boot, encryption unlock and the OpenClaw onboarding entry screen.
- [ ] Complete provider enrollment and verify real agent inference after installation.
- [x] Repeat the QEMU install without `--vm-test` (NVRAM-writing bootctl path)
  and once with `--passwordless`, confirming direct boot to the desktop with no
  passphrase prompt and no screen lock.
- [ ] Test at least one blank-disk physical x86_64 UEFI machine and publish its
  redacted model/firmware/storage results.
- [ ] Expand hardware coverage without weakening disk-protection checks.

The ordinary installer no longer configures serial-root autologin, and the live
ISO's own `ttyS0` autologin is now conditional on the Q35 KVM machine. The
explicit `--vm-test` path retains installed autologin solely for the existing
integration harness. A `--passwordless` mode (no encryption, empty account
passwords, no screen lock) exists for people who accept that risk explicitly.
Existing partitions, Secure Boot, legacy BIOS, RAID/multipath and non-x86_64
installation remain outside this first implementation.

## 2026-09-07: sshd policy and both install modes re-verified

ISO `clawos-fast-2026.09.07-x86_64.iso` (SHA-256
`dbc1f556389f618369ec6759ab59242f6f4d76e5a1e4a0f8781c6ebd2d8c4094` was the
09-06 image; the 09-07 image was built from `ee2f4f1` in the builder VM and
checksum-verified after transfer) on Windows QEMU (WHPX, OVMF), fresh 32 GiB
virtio disk and fresh firmware variables per run, installer driven from the
live `tty1` root shell. `systemd-detect-virt` reports `qemu`, so this is the
hardware branch, not `--vm-test`.

- Encrypted install: exit 0, `Linux Boot Manager` and fallback entries
  created, first boot through `Boot0004`, LUKS unlocked with the typed
  passphrase, root login with the same passphrase.
- Passwordless install: exit 0, same boot entries, first boot to the login
  prompt with no passphrase, root login with no password.
- On both installed systems: `sshd -T` reports `PasswordAuthentication no`,
  `KbdInteractiveAuthentication no`, `PermitRootLogin no`; the drop-in is
  `/etc/ssh/sshd_config.d/00-clawos.conf`; `clawos-session@clawos`, `clawosd`,
  `sshd`, `NetworkManager` and `tailscaled` active, zero failed units, Sway
  running, `clawosctl status` at `full-root`, `tailscale status` logged out.
- The live ISO in that image still reported `PasswordAuthentication yes`
  because archiso's `10-archiso.conf` sorted ahead of the drop-in; the drop-in
  was renamed to `00-clawos.conf` afterwards (`7244a54`) and that live-side
  fix has not been rebuilt into an ISO yet.
- Not exercised: the GTK installer path (driven from tty1), onboarding past the
  first screen, physical hardware.
