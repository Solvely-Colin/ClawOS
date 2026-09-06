# Hardware-capable installer validation

The VM-only guard is replaced by a blank-disk safety policy. This change is
experimental and has not yet been used to install a physical machine.

## Checks performed

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
- No physical or virtual target was partitioned or formatted by these checks.

![Synthetic installer preview; no disk writes](assets/hardware-installer-preview.png)

## Required before broader release claims

- [ ] Build an ISO from the exact candidate revision and pass ISO validation.
- [ ] Run fresh QEMU SATA and NVMe installation tests, not only virtio.
- [ ] Verify boot media and mounted/signature-bearing disks are refused in that ISO.
- [ ] Verify UEFI boot, encryption unlock, desktop startup and OpenClaw setup.
- [ ] Repeat the QEMU install without `--vm-test` (NVRAM-writing bootctl path)
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
