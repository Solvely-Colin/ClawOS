# Getting started

This walkthrough goes from a ClawOS ISO to the first OpenClaw screen inside a
disposable virtual machine. Read [SCOPE.md](SCOPE.md) first: it says what is
supported (one VM configuration) and what is not. Use a throwaway VM and a
blank virtual disk. Every install so far has been inside QEMU; no physical
machine has been installed.

## Markers

Every step below ends with one of two markers.

- `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`:
  the step is backed by the "2026-09-07: sshd policy and both install modes
  re-verified" section of
  [HARDWARE-INSTALLER-VALIDATION.md](HARDWARE-INSTALLER-VALIDATION.md). That
  run built a fast ISO from `ee2f4f1` in the builder VM, booted it on Windows
  QEMU (WHPX, OVMF) with a fresh 32 GiB virtio disk and fresh firmware
  variables, drove the installer from the live `tty1` root shell in both the
  encrypted and the passwordless mode, and checked first boot, LUKS unlock and
  key-only `sshd` on the installed systems.
- `NOT YET VERIFIED`: the step is described from the source at HEAD and was
  not exercised in that run. The GTK installer, onboarding past its first
  screen, the Polkit prompt and the Control UI are all in this state. Read
  those steps as a description of the code, not of an observed run.

## Requirements

Build host (path B only):

- Arch Linux in a disposable VM. `install-build-deps` calls `sudo pacman`, and
  `build-iso` runs `mkarchiso` as root.
- Roughly 20 GB free. The CI build refuses to start with less; a local build
  keeps its profile, work tree and ISO output under `artifacts/m1/` and
  `/var/tmp/`.
- Network access to `archive.archlinux.org` at the pinned snapshot
  (`ARCH_SNAPSHOT` in [m1/config/versions.env](../m1/config/versions.env)) and
  to `registry.npmjs.org`, from which `build-iso` installs
  `openclaw@$OPENCLAW_VERSION` into the image.

Guest (both paths):

- x86_64 with UEFI firmware (OVMF) and Secure Boot off. Legacy BIOS is not
  supported.
- 4 GiB RAM. `run-qemu` passes `-m 4096 -smp 4`.
- One blank disk of at least 32 GiB. The installer refuses the boot media,
  mounted or held disks, and anything carrying a partition table or filesystem
  signature; no disk is selected by default.
- Network access from the guest. The installer downloads and signature-verifies
  the complete package set before its first disk write and stops if that
  fails.

Accelerators:

- **KVM** (Linux host with `/dev/kvm`): the default in `m1/bin/run-qemu`,
  which passes `-enable-kvm -machine q35,accel=kvm -cpu host`.
- **TCG**: `m1/bin/run-qemu --software` switches to
  `-machine q35,accel=tcg -cpu max`. It needs no KVM, so it works inside a VM
  without nested virtualization, but boot and install are much slower. No
  install has been recorded on TCG.
- **Windows/WHPX**: the 2026-09-07 installs ran on Windows-managed QEMU with
  WHPX. The scripts in [tools/windows](../tools/windows/README.md) manage an
  existing builder VM through Scheduled Tasks; they are not a turnkey
  installer, and this repository does not ship the test guest's QEMU command
  line.

## Get an ISO

### A. Download a CI-built ISO

There are no releases and no tags. The **Experimental ISO build** workflow
([release.yml](../.github/workflows/release.yml)) runs on manual dispatch,
only in the `Solvely-Colin/ClawOS` repository, and uploads an Actions artifact
named `clawos-iso-<commit sha>` that expires after 14 days.

1. Open the repository's Actions tab, select **Experimental ISO build** and a
   green run, and download its `clawos-iso-<sha>` artifact. It holds
   `clawos-*.iso`, `SHA256SUMS`, `clawos-*.iso.sha256`, `BUILD-METADATA.txt`,
   `BUILD-PACKAGES.txt` and `BUILD-CONTAINER.txt`. `NOT YET VERIFIED` as a
   walkthrough step; the workflow has completed once (run 34270708295 on
   `00f81c5`) and that artifact was booted live, not installed from, on
   2026-09-08 ([KNOWN-ISSUES.md](KNOWN-ISSUES.md)).
2. Verify the checksum in the unpacked directory, then read
   `BUILD-METADATA.txt`; it records the source commit and states that boot,
   install and hardware acceptance were not run by the workflow.
   `verified 2026-09-08 against the run 34270708295 artifact` (ledger row in
   [EVIDENCE.md](EVIDENCE.md)).

   ```sh
   sha256sum -c SHA256SUMS
   ```

### B. Build on Arch

1. Install the build tooling. The script says what it is about to do, then
   runs `sudo pacman -S` for `base-devel`, `git`, `inetutils`, `archiso`,
   `mkinitcpio`, `qemu-desktop`, `edk2-ovmf`, Node.js, npm, Python, `jq`,
   `socat`, `shellcheck` and `rsync`:

   ```sh
   ./m1/bin/install-build-deps
   ```

   `NOT YET VERIFIED` in the 2026-09-07 run (the CI build installs the same
   packages in [tools/ci/build-release.sh](../tools/ci/build-release.sh)).
2. Run the non-root source gate. It requires Node 24+ and Python 3.12+, runs
   the M1 unit tests, profile and Omarchy checks, onboarding statics, broker
   tests, plugin tests, the role-switch test and `git diff --check`:

   ```sh
   ./m1/bin/preflight-iso
   ```

   `NOT YET VERIFIED` in the 2026-09-07 run (the `arch-preflight` job in
   [ci.yml](../.github/workflows/ci.yml) runs it on every push).
3. Build the fast ISO. `--fast` compresses with zstd, writes
   `clawos-fast-<date>-x86_64.iso` and its `.sha256` to
   `artifacts/m1/out-fast/`, and deletes the previous fast output. It
   rematerializes the profile from source, installs the pinned OpenClaw from
   npm into the image and runs `m1/tests/validate-iso.sh` on the result.

   ```sh
   sudo ./m1/bin/build-iso --fast
   ```

   `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`.
4. Or build the release image. Without a flag (or with `--release`) the xz
   image lands in `artifacts/m1/out/` and the previous output is moved under
   `artifacts/m1/archive/`:

   ```sh
   sudo ./m1/bin/build-iso
   ```

   `NOT YET VERIFIED` (release mode has only run in the CI helper, run
   34270708295).
5. Create the disposable installer disk. The runner only accepts qcow2 images
   under `artifacts/m1/disks/` and refuses to overwrite an existing one:

   ```sh
   ./m1/bin/create-dev-disk                 # artifacts/m1/disks/clawos-dev.qcow2, 32G
   ./m1/bin/create-dev-disk other.qcow2 40G # a second disk
   ```

   `NOT YET VERIFIED` (the 2026-09-07 disks were created on the Windows host).
6. Boot the ISO with that disk attached as virtio:

   ```sh
   ./m1/bin/run-installer-qemu              # default disk
   ./m1/bin/run-installer-qemu artifacts/m1/disks/other.qcow2
   ```

   `run-installer-qemu` calls `run-qemu --disk <image>`, and `run-qemu` looks
   for the ISO only in `artifacts/m1/out/`. After a `--fast` build, copy the
   image from `artifacts/m1/out-fast/` into `artifacts/m1/out/` first.
   `run-qemu` needs `/usr/share/edk2/x64/OVMF_CODE.4m.fd` (or `OVMF_CODE.fd`)
   from `edk2-ovmf`, opens a GTK window on a 1440 x 900 virtio-vga output and
   prints the serial log path; `m1/bin/qemu-console` and `m1/bin/qemu-monitor`
   attach to the guest. `--software` (TCG) and `--headless-vnc` are `run-qemu`
   flags, so call it directly for those:
   `./m1/bin/run-qemu --disk artifacts/m1/disks/clawos-dev.qcow2 --software`.
   `NOT YET VERIFIED`.
7. After installing, boot the disk alone to prove the ISO is no longer needed:

   ```sh
   ./m1/bin/run-installed-qemu              # run-qemu --installed --disk <image>
   ```

   `NOT YET VERIFIED` through this script; the same first boot without media
   is verified below on WHPX.

## Install

Boot the ISO. Systemd-boot shows the ClawOS entry and starts the live system.
The live image autologs `root` on `tty1` (archiso behaviour), runs the
`clawos-live` graphical session on `tty2`, and keeps `tty3` as an independent
recovery console (`Ctrl+Alt+F3`).
`verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX` for the `tty1` root shell (the installs were driven from it); the
`tty2` session and `tty3` console are `NOT YET VERIFIED` by that record.

### Graphical installer

None of these screens were used on 2026-09-07; every step in this section is
`NOT YET VERIFIED`. The copy is read from
`m1/profile-overlay/airootfs/usr/lib/clawos/clawos-live-welcome`.

1. **Welcome screen.** A window titled "ClawOS Setup" opens with the headline
   "Your machine, ready to work with you." and two buttons, **Install ClawOS**
   and **Inspect system**. Inspect system shows live-system facts (network,
   target disk, recovery) and writes nothing. `NOT YET VERIFIED`.
2. **Install.** Install ClawOS opens "Create the agent system.", which says the
   install is for a blank disk on an experimental x86_64 UEFI system and is
   encrypted with LUKS2 by default. `NOT YET VERIFIED`.
3. **Disk selection.** The selector starts at "Select a blank disk — no default
   target" and lists eligible blank whole disks of at least 32 GiB with path,
   capacity, model and an identity hint. In a `run-qemu` guest the disk is
   `/dev/vda`. If nothing qualifies the screen says "No eligible blank disk of
   at least 32 GiB found." `NOT YET VERIFIED` (the eligibility rules are the
   ones unit-tested in `m1/tests/test_install_targets.py` and the ones the
   `tty1` installs went through).
4. **Passphrase, or the passwordless checkbox.** "Disk unlock and session-lock
   passphrase": at least 10 characters, typed twice. The screen says one
   passphrase unlocks the encrypted disk and is also the `root` and `clawos`
   account password, and that approval prompts on the machine ask for it.
   Alternatively tick the passwordless checkbox (no disk encryption, no screen
   lock, empty account passwords; there is no password to establish approver
   identity, while local decisions, UID/token checks and typed controls remain).
   Empty-password Polkit behavior is not yet verified. That maps to
   `clawos-install-dev --passwordless`: plain Btrfs with no LUKS layer, empty
   `root` and `clawos` passwords, and `/etc/clawos-passwordless-entry`, which
   disables the screen lock. There is no in-place switch between the two
   modes; reinstall to change. `NOT YET VERIFIED`.
5. **Confirmation.** Type `ERASE-` followed by the exact selected disk path,
   for example `ERASE-/dev/vda`, into the confirmation field. **Erase disk and
   install** enables only when that token matches, a disk is selected and the
   passphrases are valid (or passwordless is ticked). `NOT YET VERIFIED`.
6. **Progress.** "Building the encrypted agent system…" (or "…passwordless…")
   with a scrolling installer log. The installer first downloads and verifies
   every package after archive-reachability and temporary-storage checks.
   Only timeouts or reset transfers are retried (up to three attempts of at
   most 15 minutes each); other classified preparation failures stop immediately.
   It then prints
   `CLAWOS_INSTALL_DISK_WRITE_STARTED` and partitions the disk. A failure
   before that line ends with "The target disk was not changed."; a failure
   after it with "The target may be partially installed." `NOT YET VERIFIED`.
7. **Restart into ClawOS.** "Installation complete." with the button **Restart
   into ClawOS**, which runs `/usr/lib/clawos/clawos-live-reboot` through
   `pkexec`. Detach the ISO before the guest comes back up. `NOT YET VERIFIED`.

### From the live tty1 shell

This is the path the 2026-09-07 record used. The installer is
`/usr/local/bin/clawos-install-dev`; every guard lives in
`/usr/lib/clawos/clawos_install_targets.py`. Do not pass `--vm-test`: it is
the integration harness's flag (serial root autologin on the installed disk,
Q35 KVM and `/dev/vda` only) and the 2026-09-07 runs omitted it.

1. List candidate disks and note the `diskId` of the one you mean:

   ```sh
   python3 /usr/lib/clawos/clawos_install_targets.py list
   ```

   `NOT YET VERIFIED` as the exact command; the record names the `diskId` it
   used but not how it was obtained.
2. Optionally validate the target without writing anything:

   ```sh
   clawos-install-dev --target /dev/vda --disk-id '<diskId>' \
     --confirm 'ERASE-/dev/vda' --dry-run
   ```

   `NOT YET VERIFIED` (the record does not mention a dry run).
3. Encrypted install. The passphrase must come from a regular file at
   `/run/user/<uid>/clawos-install.key`, owned by that uid, mode 0600 or 0400,
   containing one line of 10 to 512 bytes with no trailing newline; the
   installer refuses any other path. Then:

   ```sh
   clawos-install-dev --target /dev/vda --disk-id '<diskId>' \
     --confirm 'ERASE-/dev/vda' --key-file "/run/user/$(id -u)/clawos-install.key"
   ```

   `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`
   (exit 0; `Linux Boot Manager` and fallback entries created).
4. Passwordless install. Replace `--key-file` with `--passwordless`:

   ```sh
   clawos-install-dev --target /dev/vda --disk-id '<diskId>' \
     --confirm 'ERASE-/dev/vda' --passwordless
   ```

   `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`
   (exit 0, same boot entries).
5. Reboot with `systemctl reboot` and detach the ISO. `NOT YET VERIFIED` as
   the exact command (the record does not say how the guest was restarted);
   the first boot that followed is verified below.

### First boot

1. **Reboot without media.** The firmware boots the `Linux Boot Manager` entry
   that the installer registered with `bootctl --graceful install`; a fallback
   removable-media entry is written as well, so a firmware that refuses NVRAM
   writes still boots.
   `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`
   (first boot through `Boot0004`).
2. **LUKS unlock.** Encrypted installs stop at the boot-time unlock prompt
   (the image installs a ClawOS Plymouth theme for it, from code); type the disk
   passphrase. Passwordless installs boot straight through with no prompt.
   `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`
   (LUKS unlocked with the typed passphrase; the passwordless system reached
   its login prompt with no passphrase).
3. **Installed services.** `clawos-session@clawos` (Sway on `tty2` as the
   `clawos` account), `clawosd`, `sshd`, `NetworkManager` and `tailscaled` are
   active with zero failed units, and `clawosctl status` reports `full-root`.
   `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`.
4. **Console login.** On `tty3` (`Ctrl+Alt+F3`), `root` and `clawos` log in
   with the disk passphrase on an encrypted system and with no password on a
   passwordless one.
   `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX` for `root` in both modes; the `clawos` login and the exact tty are
   `NOT YET VERIFIED`.

### OpenClaw onboarding

On an unconfigured machine `clawos-entry` (run by the `clawos` session) starts
`clawos-onboard-ui`, which serves `/usr/share/clawos/onboarding/` from a
loopback Node service on port 19401 and opens it in Chromium as an app window
titled "ClawOS Setup". If Chromium or that service cannot start, the fullscreen
terminal wizard `clawos-onboard` is the fallback. The progress rail reads
**1 Start · 2 Gateway · 3 Agent · 4 Access · 5 Ready**.

1. **Start.** "FIRST BOOT / Make this machine an agent workspace." with a
   network indicator and the button **Set up ClawOS**.
   `verified 2026-09-07 on the 8826f15d fast ISO, WHPX` (the "Download-failure
   regression checks" record confirms the onboarding entry screen); the
   `ee2f4f1` record lists only "onboarding past the first screen" as not
   exercised.
2. **Gateway.** "Where should OpenClaw run?" Choose **This machine** (local,
   recommended) or **Existing Gateway** (connect this machine as a node to a
   Gateway over a private network; a `ws://` or `wss://` URL and an optional
   Gateway token). `NOT YET VERIFIED`.
3. **Agent.** For a local Gateway, "Set up OpenClaw." explains that provider,
   sign-in and model are chosen later in OpenClaw's own wizard and that ClawOS
   does not choose a model for you; the checkbox "Prepare the machine now;
   choose a model later" lets you defer that. For a remote Gateway, "Connect
   the Gateway." takes the WebSocket URL and token. `NOT YET VERIFIED`.
4. **Access.** "How independently can the agent work?" Choose **Full root**
   (default: the agent user gets passwordless sudo; rollback, power, role and
   policy changes still ask), **Full user + approvals** or **User limited**,
   then press **Install configuration**. `NOT YET VERIFIED`.
5. **Configuring.** The page shows "Bringing the system online." and cycles
   through "Securing Gateway credentials…", "Installing the OpenClaw
   service…", "Preparing the Agent workspace…" and "Checking the machine
   connection…". Behind it the setup service runs
   `openclaw onboard --non-interactive --flow quickstart` in the chosen mode,
   links the bundled plugin, enables the ClawOS tools, saves the role profile
   and records the checkpoints `start`, `base`, `plugin`, `tools`, `profile`,
   `machine-policy` and `complete` in `~/.local/state/clawos/onboarding.json`;
   a retry resumes from the first incomplete stage. Local mode generates a
   Gateway token into `~/.openclaw/.env`. `NOT YET VERIFIED`.
6. **Polkit prompt.** The `machine-policy` stage applies the chosen access
   level through `clawosctl` and `security.level.configure`, a high-impact
   action gated by Polkit (`org.clawos.system.commit`, `auth_admin`; the
   dialog text is "Authentication is required to apply this ClawOS system
   action"). The default choice, Full root, matches the shipped level, so that
   call is skipped and no prompt appears; choosing another level does prompt.
   The credential is the account password: the disk passphrase on an
   encrypted system, empty on a passwordless one ([HARDWARE.md](HARDWARE.md),
   [SECURITY.md](../SECURITY.md)). SECURITY.md records that which identity
   actually satisfies the `auth_admin` prompt has not been observed.
   `NOT YET VERIFIED`.
7. **Ready.** "MACHINE CONFIGURED / Continue with OpenClaw." **Choose provider
   and model** opens `openclaw configure --section model` in a fullscreen
   terminal; ClawOS has no provider catalog and collects no credentials on
   this page. **Choose a model later** ticks the defer checkbox instead.
   **Enter Agent workspace** enables once a model is selected or you chose to
   configure later, and closes the setup window. `NOT YET VERIFIED`.

### Afterwards

- **Control UI.** With a local Gateway, `clawos-entry` runs
  `openclaw gateway start`, installs and enrolls this machine's node host in
  the background, and then keeps `clawos-browser` running: Chromium in app
  mode on the Gateway's Control UI, receiving its token through a mode-0600
  bootstrap file in `$XDG_RUNTIME_DIR` rather than on the command line.
  `NOT YET VERIFIED`.
- **SSH.** `sshd` is enabled but refuses password, keyboard-interactive and
  root login (`/etc/ssh/sshd_config.d/00-clawos.conf`), and nothing installs
  an authorized key. Add one for the `clawos` account from the console before
  relying on remote access.
  `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`
  for the policy (`sshd -T` on both installed systems).
- **Tailscale.** `tailscaled` is enabled and running; nothing in the
  repository runs `tailscale up` or supplies an auth key.
  `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`
  (`tailscale status` logged out).
- **Full Root.** The `clawos` account has passwordless sudo
  (`/etc/sudoers.d/90-clawos-full-root`) until the level is changed. This is
  a trusted-agent mode, not containment; see [SECURITY.md](../SECURITY.md).
  `verified 2026-09-07 at ee2f4f1 (fast ISO built in the builder VM), WHPX`
  (`clawosctl status` at `full-root`).

## Known gaps in this walkthrough

- The live ISO in the `ee2f4f1` image still accepted `PasswordAuthentication
  yes` on its own `sshd`. The drop-in rename that fixes the live side
  (`7244a54`) is in the 2026-09-08 CI image, whose live side was observed
  key-only ([EVIDENCE.md](EVIDENCE.md)); the `ee2f4f1` fast ISO predates it.
- A passwordless WHPX guest once showed a blank frame and stalled SSH until it
  received keyboard input; the cause is unconfirmed.
- Nothing here has been done on physical hardware, and provider enrollment
  plus real model inference after a fresh install remain open items in
  [HARDWARE-INSTALLER-VALIDATION.md](HARDWARE-INSTALLER-VALIDATION.md).

See also [SCOPE.md](SCOPE.md), [HARDWARE.md](HARDWARE.md),
[KNOWN-ISSUES.md](KNOWN-ISSUES.md), [SECURITY.md](../SECURITY.md) and
[m1/README.md](../m1/README.md) for the build and QEMU gates in detail.
