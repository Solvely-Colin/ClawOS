# Image tooling, installer and native shell

This component produces the x86_64 ClawOS live ISO from Arch's official
`releng` profile plus a reviewed overlay, and the experimental blank-disk
installer behind the live Try/Install surface. It is the first environment
allowed to count toward ClawOS release gates.

The image bundles the pinned OpenClaw runtime, the graphical live session, the
installer and the recovery TTY. Everything below has been verified only in
QEMU (Linux KVM and Windows WHPX); no physical machine has been installed.

## Host preparation

```bash
./image/bin/install-build-deps
```

## Validate and build

[docs/GETTING-STARTED.md](../docs/GETTING-STARTED.md) walks a first-time
contributor through this section and marks which steps have been verified.

For edits to the running ClawOS shell, broker, plugin, or UI assets, use the
in-guest runtime deployment loop before building another ISO:

```bash
./image/bin/deploy-runtime plan
./image/bin/deploy-runtime apply
./image/bin/deploy-runtime status
```

Apply runs preflight, stages a hash-versioned payload, and dispatches a root
system service. Follow the returned job ID until its receipt is `complete`.
It snapshots root and backs up changed files before applying, and automatically
restores them if runtime health checks fail. See [live development](../docs/SELF-DEVELOPMENT.md)
for scope, rollback, and recovery. ISO builds remain the fresh-install test path.

```bash
./image/bin/preflight-iso
sudo ./image/bin/build-iso
./image/tests/boot-smoke-qemu
./image/tests/m2-e2e-qemu
./image/bin/run-qemu
```

`boot-smoke-qemu`, `m2-e2e-qemu` and `run-installer-qemu` need Linux KVM with a
Q35 machine; a Linux guest without nested virtualization has none. `run-qemu --software`
runs the ISO under TCG (slow, no install gate), and Windows hosts drive QEMU
through `tools/windows/`. `build-iso --fast` writes a quicker-compressing image
to `artifacts/m1/out-fast/` for iteration; the Linux gates read `artifacts/m1/out/`.

`preflight-iso` is the required non-root source gate. It covers clean-Arch
provenance, first-boot resume behavior, Gateway/UI lifecycle, exact local-node
enrollment policy, the privileged broker, OpenClaw plugin, transactional role
switching, patch hygiene, tracked-tree hygiene and shell static analysis before
the slower image build begins. The last two are standalone scripts.
`tools/check-tree.sh` inspects the Git index and fails on any tracked file over
2 MiB, any path under `transfer/` or `artifacts/`, developer home paths
(`/home/<name>` other than the image accounts, and Windows user-profile paths)
and well-known credential prefixes; stage new work with `git add` before running
it. `tools/check-shell.sh` runs `shellcheck -S warning` over the scripts under
`experiments/host-session/bin`, `experiments/host-session/tests`, `image/bin`, `image/tests`, `tests/integration/roles` and `tools`, with the
agreed exclusions in `.shellcheckrc`; the scripts under `image/profile-overlay`
are only syntax-checked until their findings are triaged. `install-build-deps`
installs `shellcheck`.

The QEMU proof declares a 1440 x 900 virtual display at device creation time,
so the boot splash and encrypted unlock screen always initialize on the same
16:10 canvas even when the host tiles or resizes the GTK window.

Build products live under `artifacts/m1/` and are ignored by Git.
Every build rematerializes the ArchISO profile and recreates mkarchiso's work
tree so overlay changes cannot be hidden by stale build state. The previous
`out/` directory is moved under `artifacts/m1/archive/` before the new build.

`build-iso` ends by running `image/tests/validate-iso.sh` against the new image.
Besides the boot chain and the pinned OpenClaw runtime, it extracts
`etc/ssh/sshd_config`, `etc/ssh/sshd_config.d/` and `etc/issue` from
`airootfs.sfs` and asserts the shipped sshd posture: `sshd_config` includes the
drop-in directory, `00-clawos.conf` carries `PasswordAuthentication no`,
`KbdInteractiveAuthentication no` and `PermitRootLogin no` as exact lines, and
archiso's `10-archiso.conf` is present and sorts after it in C-locale order, so
the key-only values win. It also requires `etc/issue` to keep saying "Verified
only in virtual machines". Each failure names its reason. The checks are
functions over an extracted tree; `image/tests/test_iso_posture.py` runs them
against fixture trees (a drop-in renamed `20-clawos.conf`, a missing
`10-archiso.conf`) without an ISO, and the CI unit-test job runs that file.

`boot-smoke-qemu` is the release gate for the live base. It boots the ISO
headlessly, controls ClawOS over its serial console, verifies OS identity,
systemd health, networking, the live overlay root and the effective sshd
posture (`sshd -T` inside the guest must report `passwordauthentication no`,
`kbdinteractiveauthentication no` and `permitrootlogin no`; the marker loop
requires the resulting `SSHD_KEYONLY_OK`), then powers the VM off. Each run
preserves its serial log, transcript and QEMU log in `artifacts/m1/smoke.*`
and passes only after `image/tests/scan-log-secrets.sh` finds no secret-shaped
strings in them, so a CI upload step can publish them; the scanner names the
file, line and pattern but never prints the matched text.

`m2-e2e-qemu` is the stronger graphical-installation gate. It creates a fresh
throwaway qcow2 disk, proves the live graphical session and recovery TTY,
captures the Try/Install screen, executes the exact guarded installer behind
the UI, boots the encrypted result with the ISO detached, proves the native
agent session/top bar/shelf/onboarding/recovery files are image-built, captures
first boot, then exercises the native Milestone 3 approval broker with a real
allowlisted package install, pre-change Btrfs snapshot, audit check, and
single-use authorization check before shutting down cleanly. It runs the same
`sshd -T` posture check on the live medium (`SSHD_KEYONLY_OK`) and again on the
installed system (`INSTALLED_SSHD_KEYONLY_OK`), and both are required markers.
Evidence is retained under `artifacts/m1/m2-e2e.*` after the same secret-string
scan of its serial and QEMU logs.
If a local assertion fails after installation, set
`CLAWOS_M2_RESUME_RUNTIME=artifacts/m1/m2-e2e.<id>` to rerun only the
ISO-detached installed-system phase against that disposable disk.

## Writable development disk

Installer work is restricted to a generated qcow2 disk under
`artifacts/m1/disks/`. The runner rejects physical devices, raw images, symlinks
that resolve outside that directory, and images whose detected format is not
qcow2.

```bash
./image/bin/create-dev-disk          # creates a new 32G clawos-dev.qcow2
./image/bin/run-installer-qemu       # ISO plus that isolated writable disk
./image/bin/run-installed-qemu       # disk only; proves the ISO is no longer used
```

Disk creation refuses to overwrite an existing image. The live/recovery base
must boot independently before installer testing begins.

The live image boots a dedicated `clawos-live` Wayland session into a branded
**Try / Install ClawOS** surface. The guided path collects the disk-unlock
secret, displays installation progress, and offers a graphical restart; it
does not require terminal commands. The independent `Ctrl+Alt+F3` recovery
console remains visible throughout the flow.

The live surface follows the selected Carapace-aligned Agent Canvas rather
than a card launcher: a native machine bar, open installation hero,
real ClawOS halftone raster, measured Inter/Geist typography, coral action,
equal readiness/event panes, and a quiet recovery footer. Dynamic disk and
network copy reports the actual VM state. In the QEMU proof the compositor and
GTK client are both pinned to the 1440 x 900 virtual output (`Virtual-1` in
`live-sway.conf`/`sway.conf`); other outputs use their native mode and are
untested.

The UI delegates erasure to `clawos-install-dev`, a deliberately narrow,
network-backed experimental installer. Target discovery and every guard live in
`clawos_install_targets.py`: eligible blank SATA/NVMe/virtio/eMMC whole disks
of at least 32 GiB, never the boot media, never anything mounted, held,
partitioned or carrying a filesystem or partition-table signature. It requires
the exact `ERASE-/dev/<disk>` token bound to a kernel-generation-aware disk
identity, plus either a mode-0600 key file in the live user's runtime directory
or the explicit `--passwordless` flag. A Polkit rule authorizes the live user
for only this installer and an exact reboot helper; it grants neither a general
root shell nor arbitrary `systemctl`. See [docs/HARDWARE.md](../docs/HARDWARE.md)
for the hardware boundary; the QEMU harness passes `--vm-test` to keep serial
root autologin on the installed disk.

The installed proof uses a 1 GB EFI partition plus a LUKS2-encrypted Btrfs
system partition with `@`, `@home`, `@var_log`, `@pkg`, and `@snapshots`
subvolumes. It installs systemd-boot and can boot from qcow2 with the ISO
removed. Packages are downloaded and signature-verified into the live
environment before the first disk write, then installed from those local
files; the OpenClaw runtime is copied from the ISO. Before the download the
installer checks that the pinned archive answers, sizes the resolved package
set and refuses to continue when the RAM-backed `/tmp` or available memory
cannot hold it, so a 2 GiB VM fails in seconds rather than mid-download.
Internet access and at least 4 GiB of RAM are still required, and a complete
offline package repository remains an M1 release requirement.

The LUKS passphrase is also the proof's single startup credential boundary.
Plymouth presents a ClawOS-branded encrypted-root unlock screen, keeps routine
boot output out of the primary visual path, and then hands the same visual
identity to the graphical session. There is no second desktop password prompt.
Boot details remain available with `Esc`, and the independent recovery TTY
remains available on `Ctrl+Alt+F3` after the root filesystem is unlocked.
That passphrase is also the `root` and `clawos` account password (Polkit
prompts and session unlock use it); `clawos` never types it for sudo because
Full Root is passwordless sudo. Password, keyboard-interactive and root logins
over SSH are refused (`/etc/ssh/sshd_config.d/00-clawos.conf`); `sshd` and
`tailscaled` are enabled on the installed system, so add an authorized key
locally before relying on remote access.

The installer also lays down the first graphical ClawOS appliance proof. It
installs the exact OpenClaw version in `image/config/versions.env`, then a Sway
session starts for the dedicated, unprivileged `clawos` account on tty2 after
the boot splash exits.

On an unconfigured machine, graphical onboarding begins directly beneath the
native ClawOS panel; it does not add a second branded application header. The
panel exposes a clickable **Setup required** state that returns to first boot if
the user explores another workspace. Onboarding presents one ClawOS decision:
run the Gateway here or connect to an existing Gateway. It then delegates
configuration to the pinned upstream `openclaw onboard` flow.
Local mode installs the upstream user Gateway service with token auth; remote
mode collects the existing Gateway URL and auth through OpenClaw. Both modes
install this machine's upstream node host. A fullscreen terminal wizard remains
only as recovery when the graphical setup cannot start. After setup, Chromium
enters the real Control UI in borderless app mode beneath a root-owned Wayland
panel and receives token auth through a mode-0600, short-lived runtime bootstrap
file rather than a token on its process command line.

The graphical shell does not wait for network-online, Gateway health, or node
registration before becoming visible. It opens an OpenClaw-shaped Agent
connection state as soon as Sway starts, brings those services up in parallel,
and automatically transitions the same window into Control UI. This keeps slow
or unavailable networking visible as agent readiness instead of presenting an
empty desktop or terminal.

The panel exposes one **Main activity**, not permanent application tabs. The
upstream OpenClaw Control UI is the activity canvas. Command, Build, and Browse
are temporary inspection surfaces in a hidden layer, never splits or app tabs. Command
and Build attach to named tmux sessions so work survives after their visible
surface closes; Browse uses a persistent profile and a loopback-only debugging
endpoint so the local agent can attach without a second Control UI login. The
restrained 48-pixel panel shows the current activity and focused surface,
Gateway state, genuine attention state, time, and recovery context.

The bundled `clawos-system` OpenClaw plugin gives the agent a narrow typed API
to present, hide, and focus Terminal, Browser, or Build and to project activity
and attention state into the native shell. These tools are added to the active
OpenClaw tool profile during local onboarding. Automation remains non-visual by default;
a surface appears only for inspection or takeover. The same broker now owns a
validated freedesktop application registry and exposes it through the typed
`clawos_app` tool. The clickable intent palette presents work—continue, review,
inspect, browse, or take over—while full application search is one secondary
escape hatch. Standard Linux applications and registered web apps therefore
occupy the activity canvas without becoming the visible OS model. `Alt+Space`
opens the intent palette; Gmail and Outlook are the
first persistent-profile web-app proofs. Their interactive sign-in remains in
the app surface and does not silently grant the agent connector or mailbox data
access. `Alt+Enter`, `Alt+B`,
`Alt+Shift+B`, `Alt+A`, and `Alt+Q` remain optional direct-human controls, not
the normal workflow. Terminal, Build, and Browse do not start at boot or reopen
after an intentional close.

The same plugin observes OpenClaw's supported metadata lifecycle hooks. Model
start, agent completion, and delegated-agent events automatically update the
native activity state even when the model makes no ClawOS tool call. The handler
does not inspect or store prompts, replies, or transcript messages. The broker
persists only its small projection under the user's XDG state directory and
restores interrupted `running` work as `waiting` after a graphical restart.

Clicking the native **ClawOS** wordmark opens the graphical system surface with Lock,
Restart, Shut down, and Cancel actions. Lock uses GTK's secure Wayland session
lock protocol and preserves every workspace. Restart and shutdown require a
second graphical confirmation, then Plymouth owns the transition so the normal
path never falls through to a terminal. `Alt+L` locks immediately and
`Alt+Shift+E` opens the power surface. The proof installer uses the encrypted
disk secret for explicit session unlock, while boot still authenticates only
once before starting the dedicated ClawOS session.

The installer still needs the network to prepare packages before it erases the
disk; it is not yet an offline release installer. ClawOS ships no parallel launch
page, sessions dashboard, or competing desktop UI. Its native activity control
opens a transient searchable palette rather than a second desktop or permanent
application navigation. `Ctrl+Alt+F3`
remains the independent recovery path.
