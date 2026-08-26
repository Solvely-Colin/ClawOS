# ClawOS: An OpenClaw-Native “Jellyware” Operating System

## Summary

Build a real bootable OS whose primary interface and runtime are OpenClaw—not a conventional desktop with OpenClaw installed.

The first release targets the 2019 Intel MacBook Pro `MacBookPro15,1`. It will:

- Boot from a custom, pinned Arch Linux image with the required T2 kernel and firmware.
- Present OpenClaw’s Control UI as the desktop.
- Run in either:
  - **Standalone mode:** local Gateway, agent runtime, tools, terminal, and local node.
  - **Node mode:** connect the whole machine to another Gateway and display that controller’s UI.
- Support OpenClaw-native multi-agent operation, with logically isolated agent
  identities, workspaces, credentials, sessions, skills, and runtimes.
- Allow authorized agents full access as the normal OS user, bounded by the
  machine security level and any narrower per-agent policy.
- Require typed, visible approval for privileged OS changes.
- Follow tested OpenClaw releases without maintaining a permanent hard fork.
- Retain a native recovery surface even if OpenClaw, networking, or the WebUI fails.
- Install from a complete offline image; networking is only required after the
  first successful boot.

ClawOS does not invent a second agent roster, session store, routing layer, or
orchestration service. Visual agent graphs, automatic worktree orchestration,
and general PC support are not part of v1; OpenClaw's existing multi-agent and
subagent capabilities are.

## Architecture

### 1. Distribution and hardware layer

Create a separate `clawos` repository containing the ArchISO profile, installer, OS packages, release tooling, integration tests, and any temporary OpenClaw patches.

Use Arch because the reference machine already runs the working `linux-t2` stack. T2 support must be treated as a hardware platform layer, since the special kernel is required for the keyboard, trackpad, Touch Bar, audio, fan, and Wi-Fi. [T2Linux documents these requirements](https://wiki.t2linux.org/guides/postinstall/), and its current Arch installer uses `linux-t2`, Apple firmware/audio packages, and `t2fanrd`. [T2 Arch installation guide](https://wiki.t2linux.org/distributions/arch/installation/)

The image includes:

- `linux-t2` and headers.
- `apple-bcm-firmware`, `apple-t2-audio-config`, `t2fanrd`, and `tiny-dfr`.
- NetworkManager using iwd and the kernel `brcmfmac` driver.
- PipeWire and WirePlumber.
- Intel and AMD Mesa support with Intel as the default GPU and Radeon offload available.
- systemd, LUKS2, Btrfs, systemd-boot, Plymouth, Polkit.
- Sway as a minimal Wayland compositor, Chromium, swaylock/swayidle, tmux,
  Git, SSH, BlueZ, and optional Tailscale and 1Password CLI integrations.
- Node.js versions supported by the pinned OpenClaw release.

Sway uses a root-owned, minimal kiosk configuration with no bar, launcher,
workspace workflow, theme layer, or user-writable startup commands. It is chosen
because it supports the session-lock and idle protocols required by swaylock and
swayidle. ClawOS deliberately does not inherit Omarchy's Hyprland desktop model,
Super-key bindings, shell, themes, or application workflow. Arch supplies the
base; OpenClaw supplies the user interface.

Build the ISO with an ArchISO profile rather than an installation script. ArchISO officially supports custom packages, alternative kernels, UEFI media, and QEMU testing. [ArchISO documentation](https://wiki.archlinux.org/title/Archiso)

Every ClawOS release pins:

- Arch repository snapshot.
- T2 kernel and firmware versions.
- OpenClaw version and commit.
- ClawOS packages and integration patches.
- Node.js and browser versions.
- Bun version, immutable Carapace release tag, and Sway version. Sway must be
  version 1.8 or newer for the required session-lock and idle protocols.

Release artifacts include a complete offline bootable ISO, signed package
repository, lock manifest, checksums, SBOM, and recovery image. T2 packages are
mirrored, pinned, and re-signed by ClawOS rather than consumed at install time
from an unsigned repository.

### 2. Installation, boot, and recovery

The production installer is designed for full replacement of the internal disk:

- Verify the detected model is `MacBookPro15,1`.
- Refuse a destructive installation unless the selected target is the internal
  NVMe device resolved through its stable device path.
- Show the exact disk model, serial, size, and partitions.
- Require an explicit typed erase confirmation.
- Create a 2 GB EFI partition and LUKS2-encrypted Btrfs system partition.
- Create separate Btrfs subvolumes for system, home, logs, package cache, and snapshots.
- Install systemd-boot with current, previous-kernel, and recovery entries.
- Apply the required T2 kernel parameters, including `intel_iommu=on`,
  `iommu=pt`, `pm_async=off`, and `mem_sleep_default=deep`.
- Preserve the live ISO as the supported out-of-band recovery method.

During development, the installer also has an explicitly experimental
**coexist mode** for the reference machine. It never edits the partition table
or formats a filesystem. It snapshots the current `@` root, creates separate
`@clawos` and `@clawos-home` Btrfs subvolumes, shares only
`/home/colin/Work`, installs separately named kernel/initramfs files on the
existing EFI partition, and adds a Limine entry. This mode proves real installed
boot behavior without becoming a supported production layout.

Coexist mode owns an independently named kernel and initramfs through a
ClawOS-specific pacman hook, and its Limine entry is installed through the
host's preserved configuration mechanism so a host kernel update cannot erase
it. Host and ClawOS snapshots never roll back one another. The shared `Work`
path must be verified as a dedicated subvolume or explicit bind mount before
installation. Hibernation is disabled in ClawOS MVP so the host's resume
configuration and swap state are never shared across installations.

One root-owned, loopback-only setup application has two modes: live installation
and first-boot onboarding. Its UI uses Carapace from an immutable, pinned GitHub
release tag and is built with Bun into the offline image; Carapace is not fetched
from npm or resolved during installation. Chromium connects only to the local
setup service. Secrets are accepted only on the exact setup steps that require
them, are never logged, and are handed directly to their owning system service.

Live-install mode collects only hardware, disk, encryption, locale, and local
account information. First-boot mode collects:

- Timezone and network.
- Standalone or Node role.
- OpenClaw identity and provider credentials for Standalone mode.
- Gateway join URL/code for Node mode.
- Optional guided Tailscale and 1Password enrollment. Node mode accepts any
  supported secure Gateway connection; Tailscale is recommended, not required.
- Device name and remote-access preference.
- Agent security level: Full User + Approvals or User Limited.

Standalone onboarding creates the first owner agent using OpenClaw's normal
agent setup and initially designates it as the OS agent. A fresh installation
can remain a simple one-agent system, but users can add isolated agents
immediately through OpenClaw without reinstalling or enabling a separate ClawOS
orchestrator.

The default security level is **Full User + Approvals**. User Limited runs all
OpenClaw agents under one separate `claw` UID with explicitly shared resources;
per-agent Unix accounts are deferred. Full Root is intentionally absent from
onboarding and can be enabled only after installation from System → Security,
with a prominent warning and authentication. The level can be changed later,
and raising privilege always requires authentication.

After disk unlock, the primary user is automatically logged into the ClawOS
session without a second boot-time login. The account password remains required
for privilege approvals and screen unlock. Default idle policy locks after 10
minutes, turns off the display after 15 minutes, suspends after 30 minutes on
battery, uses a longer plugged-in timeout, and locks before lid-close suspend;
all values are configurable.

Recovery remains available independently of OpenClaw:

- Standard Linux virtual terminals remain available, including
  `Ctrl+Alt+F3`; ClawOS defines no custom Super-key escape workflow.
- The recovery boot entry starts networking, diagnostics, rollback, and repair tools without starting the graphical OpenClaw shell.
- Three consecutive shell startup failures automatically select the recovery UI.

### 3. OpenClaw as the operating-system shell

OpenClaw’s upstream Control UI is the desktop. ClawOS does not build a competing dashboard.

The visible boot sequence is:

```text
Firmware → LUKS unlock → systemd → Sway
         → Chromium kiosk → OpenClaw Control UI
```

For MVP, the ClawOS shell is launched by a system-level
`clawos-session@.service` (or an equivalently locked-down greetd configuration),
not an overridable systemd user unit. It runs Sway as the selected owner with an
explicit `sway -c /etc/clawos/sway.conf`, so user configuration cannot replace
the root-owned kiosk policy. A small root-owned launcher script:

- Waits for network and the selected OpenClaw endpoint.
- Starts Chromium in Wayland kiosk mode without browser chrome, with validated
  HiDPI and hardware-acceleration settings for the reference display. The
  launcher owns and tests the exact Wayland flags, including
  `--ozone-platform=wayland` and any version-required Ozone feature flag.
- Restarts the UI after crashes.
- Shows an offline/reconnecting view when the selected Gateway is unavailable.

Chromium receives root-owned managed policy from
`/etc/chromium/policies/managed/`. The policy blocks extensions, Developer
Tools, browser sign-in, Incognito, and navigation outside the configured local
Gateway or explicitly enrolled controller origins. Updating a Node controller
origin is a typed `clawosd` operation; a user-writable Chromium profile cannot
relax managed policy.

It does not implement a desktop bar, application launcher, window-manager
shortcuts, native file manager, or parallel desktop UX. A richer native shell is
written only if living in the MVP proves that OpenClaw cannot own a required
workflow.

A bundled `clawos-system` OpenClaw plugin contributes a first-class **System** tab using OpenClaw’s existing Control UI plugin descriptors. External plugins can already supply sidebar tabs through this supported interface. [OpenClaw Plugin SDK](https://docs.openclaw.ai/plugins/sdk-overview)

`clawosd` is the single local device API behind this tab. In Standalone mode,
the plugin calls the local broker backend. In Node mode, the controlling Gateway
must have a compatible `clawos-system` plugin, which selects the paired ClawOS
device and routes the same typed operations through OpenClaw's node invocation
path. The ClawOS node advertises its broker API version and supported operations;
the controller disables incompatible controls rather than guessing. Plugin and
node compatibility are tested and released with the corresponding ClawOS API.

The System tab is a compact ClawOS control surface built from Carapace
components. It is not a conventional desktop settings application. MVP contains
only these sections:

- **Overview:** Standalone/Node role, Gateway connection, OpenClaw and ClawOS
  versions, update state, machine model, kernel, uptime, temperature, fan,
  battery, memory, and storage pressure.
- **Connections:** Wi-Fi network selection, Bluetooth enable/pair/disconnect,
  Tailscale state and guided setup, remote Gateway address, device pairing, and
  node capability status.
- **Device:** display brightness and scaling, audio input/output and volume,
  microphone mute, battery/power profile, idle-lock timing, suspend, and lid
  behavior. MVP supports the reference laptop display; broader multi-monitor
  configuration is deferred.
- **Security:** active agent security level, pending privileged approvals,
  approval history, screen lock, Gateway authentication status, and the
  authenticated flow for changing security level.
- **Software:** signed update status, release notes, download/apply/reboot,
  automatic security-update policy, current/previous boot versions, and
  rollback. There is no general pacman or AUR interface.
- **Recovery:** OpenClaw, node-host, browser, and ClawOS service health; bounded
  recent logs; restart/repair actions; snapshot status; recovery-boot selection;
  and export of a redacted diagnostic bundle.
- **Power:** lock, suspend, restart, and shut down.

Every privileged or destructive control shows its exact effect, requires the
security-level-appropriate authentication or approval, reports progress, and
ends in a clear success, failure, or rollback state. The UI never accepts raw
root commands.

Explicitly excluded from the MVP System tab are a file manager, application
launcher, theme manager, window/workspace settings, package browser, process
manager, generic systemd editor, arbitrary kernel controls, and shell-command
input. OpenClaw chat, terminal, Browser, Files/Review, and the standard recovery
TTY own those workflows.

The existing OpenClaw terminal remains the primary terminal UI. Configure `gateway.terminal.shell` to launch a ClawOS terminal wrapper that attaches to named tmux sessions. This lets shell processes survive browser and Gateway restarts even though OpenClaw’s current PTY registry is process-local.

OpenClaw's Browser panel and Files/Review surfaces are the primary browser and
workspace-file experiences. They are not treated as a general personal browser
or filesystem manager in MVP. Emergency local access is through a standard TTY
or the recovery boot entry, not Omarchy-style hotkeys.

### 4. Standalone and Node roles

Keep role management outside OpenClaw so switching roles remains possible when OpenClaw is unhealthy.

#### Standalone mode

Run:

- OpenClaw Gateway as a systemd user service.
- Bundled Control UI on loopback.
- Local agent/model-provider runtime.
- Local node host paired to the loopback Gateway for device and machine capabilities.
- `clawos-system` plugin.
- Browser pointed at the local Gateway.

First boot generates a durable `gateway.auth.token` and completes the normal
Control UI device-pairing flow. Loopback does not disable OpenClaw authentication.

This makes one machine the complete OpenClaw system.

#### OpenClaw-native multi-agent operation

ClawOS treats OpenClaw as the sole agent control plane. One Gateway can host
multiple logically isolated agents, each retaining OpenClaw's own workspace, `agentDir`,
SQLite session store, identity files, credentials, model configuration, skills,
memory, and runtime settings. ClawOS does not mirror this state in an OS-specific
agent database.

The first owner agent is the initial `agents.defaults.systemAgent.agentId` and
therefore owns ambient OpenClaw and ClawOS work. The owner can later designate a
different configured agent as the OS agent through an authenticated operation.
When more than one agent exists, ClawOS uses `agents.ownership: "explicit"` and
requires explicit bindings or `agentId` targets so unattended or ambient work
cannot silently run as the wrong agent.

OpenClaw's existing agent switcher, All Agents view, agent settings, sessions,
tasks, automations, subagents, and typed `agents.create` operation remain the
user interface and API. Agent creation retains OpenClaw's creator provenance and
approval flow. Cross-agent delegation uses `sessions_spawn`, explicit target
allowlists, concurrency and nesting limits, and sandbox-inheritance protections;
ClawOS does not add a separate herder protocol. Under Full User + Approvals,
these boundaries are OpenClaw routing and state boundaries, not Unix isolation:
agents execute as the same UID and could access another agent's files if given
unrestricted host tools. User Limited separates OpenClaw from the desktop owner,
but its MVP uses one `claw` UID for the whole fleet rather than one UID per agent.

The selected ClawOS security level is a machine-wide authority ceiling.
OpenClaw's `audit.run.inspect` can verify an exact execution, but existence of an
execution does not prove that a same-UID D-Bus caller owns it. Therefore
per-agent broker policy is advisory in Full User + Approvals, and the one-UID
User Limited MVP creates a human-versus-agent boundary rather than an
agent-versus-agent boundary. Enforced per-agent OS policy requires a future
Gateway component that attests each action with identity unavailable to agents,
or separate per-agent OS principals. `clawosd` never treats a plugin-supplied or
same-UID self-reported agent ID as authorization. Audit records correlate the
requesting agent, session, execution, task/delegation, exact typed action,
decision, result, and recovery point when authoritative upstream evidence is
available, and explicitly mark unavailable attribution rather than inventing it.

Standalone MVP may query `audit.run.inspect` using a root-provisioned,
read-scoped Gateway credential for attribution. Node mode records the remote
controller identity and its node-invocation approval; it does not claim locally
verified per-agent attribution.

Durable task authority is a ClawOS capability built across Milestones 3–5, not
an assumed OpenClaw feature. Its signed, narrowly scoped grant binds an approved
task, action classes, targets, expiry, delegation constraints, and recovery
policy. Subagents can inherit only the narrowed grant. Restart and reboot
recovery can resume the authorized task without turning its grant into ambient
authority for unrelated work.

The System tab shows the designated OS agent, active and background agents,
their current work and machine-access level, pending approvals, and blocked
states. Detailed agent configuration remains in upstream OpenClaw surfaces.

#### Node mode

Run:

- OpenClaw node-host service.
- No externally active local Gateway.
- Browser pointed at the controlling Gateway.
- Local recovery supplied by the standard TTY and boot recovery entry.
- Node-hosted skills, MCP tools, execution capabilities, and ClawOS system commands advertised to the controller.

Node enrollment obtains Gateway authentication, completes per-device pairing on
the controller, and validates the configured HTTPS/WSS, private-LAN, SSH-tunnel,
or Tailscale route. The ordinary Control UI terminal belongs to the Gateway;
Node mode does not claim to provide a general local shell inside that terminal.

OpenClaw already persists node identity, pairing tokens, Gateway metadata, node-hosted skills, and per-node execution approvals. Nodes are intentionally peripherals rather than Gateways, which matches this role division. [OpenClaw node documentation](https://docs.openclaw.ai/nodes)

Role switching performs a transactional sequence:

1. Validate the target role’s configuration and credentials.
2. Stop the currently active OpenClaw service.
3. Switch the active ClawOS role atomically.
4. Start and health-check the target service.
5. Redirect the shell to the correct UI.
6. Revert automatically if the new role fails its health check.

Standalone and Node configurations use separate `OPENCLAW_STATE_DIR` and
`OPENCLAW_CONFIG_PATH` values so switching roles never overwrites local Gateway
identity with remote-node identity. A target role has 60 seconds to pass its
health checks; failure reverts to the prior role, and recovery remains available
if neither role is healthy.

### 5. Privileged system broker

OpenClaw's operating identity follows the selected security level:

- **Full Root:** unrestricted root capability; intentionally unsafe and never
  the default. Enabling it gives the OpenClaw service account passwordless sudo
  and therefore bypasses `clawosd` approvals; the UI and audit remain advisory
  in this mode. It is available only as an authenticated post-install change.
- **Full User + Approvals:** full desktop-user access, with privileged actions
  gated through `clawosd`; this is the default developer experience.
- **User Limited:** separate `claw` UID with explicitly shared files and brokered
  capabilities.

Except in Full Root mode, root operations go through a Rust system service named
`clawosd`. It is also the single API for brokered device controls. Its typed
D-Bus surface includes:

```text
GetStatus()
GetCapabilities()
PrepareAction(action, parameters) → approval token + exact summary
CommitAction(approval token)
CancelAction(approval token)

SetRole(standalone | node)
SetNetwork(network ID, credentials reference)
SetBluetooth(enabled)
PairBluetooth(device ID)
SetDisplay(settings)
SetAudio(settings)
SetPowerPolicy(settings)
SetSecurityLevel(level)
CheckForUpdates()
ApplyRelease(release ID)
Rollback(snapshot ID)
RestartService(service ID)
Reboot()
PowerOff()
```

Rules:

- The broker never accepts arbitrary shell text.
- Every action has a typed schema and validated target.
- Destructive or privileged actions require Polkit approval.
- Approval binds the exact normalized action and expires quickly.
- The broker records requester, action, result, and rollback information.
- OpenClaw can propose and prepare changes, but the UI displays the exact root operation before committing it.
- An emergency developer setting may relax individual action classes, but unrestricted passwordless sudo is not part of the default image.

In Full User + Approvals mode, the approval boundary protects against accidental
or unapproved root changes; it is not a security boundary against a malicious
agent already running as the same user. User credentials and same-UID session
state are therefore in scope for that trust decision. User Limited is the mode
for a real isolation boundary.

NetworkManager remains responsible for network state; systemd remains responsible for services; `clawosd` coordinates them instead of replacing them.

## OpenClaw Upstream and Release Strategy

Package unmodified upstream OpenClaw whenever possible. ClawOS additions live in:

- The external/bundled `clawos-system` plugin.
- The ClawOS shell and privileged broker.
- OS configuration and service units.
- A small, auditable downstream patch queue only when no supported extension point exists.

The OpenClaw update pipeline:

1. Detect a new upstream stable release.
2. Open an automated version-bump branch.
3. Build the matching Gateway and Control UI together.
4. Run API, UI, plugin, terminal, Standalone, Node, and role-switch tests.
5. Boot the candidate ISO in QEMU.
6. Install it on the reference MacBook canary.
7. Promote it into a signed ClawOS release only after approval.

Gateway updates are promoted before node updates because OpenClaw supports a limited N-1 node protocol window and documents Gateway-first fleet upgrades.

Generic missing seams—particularly durable terminal backends or Linux-native shell integration—should be proposed upstream. ClawOS carries a temporary patch only until the equivalent upstream release is accepted and validated.

ClawOS adds no telemetry, analytics, or crash-report upload. Upstream OpenClaw's
own explicit opt-in remains visible and unchanged.

## Updates and Rollback

ClawOS does not expose unrestricted Arch rolling updates through the desktop.

Critical browser, certificate, revocation, and security fixes use an automatic
fast lane backed by a separate signed emergency manifest channel. It contains
only explicitly allowlisted packages, uses the same pinned repository snapshots,
pre-update snapshot, health validation, and rollback machinery, and never opens
unrestricted rolling updates. Normal ClawOS, OpenClaw, kernel, and T2 releases
download in the background but require approval before installation or reboot.

An OS update:

1. Downloads a signed ClawOS release manifest.
2. Verifies package hashes and signatures.
3. Confirms the release supports `MacBookPro15,1`.
4. Creates a read-only Btrfs pre-update snapshot.
5. Preserves the prior kernel, initramfs, and boot entry.
6. Applies only packages approved by that release manifest.
7. Runs offline validation and reboots.
8. Marks the release healthy only after hardware, OpenClaw, and UI checks pass.

If health validation fails, the system selects the previous boot entry and offers Btrfs rollback. User data remains outside the rolled-back system subvolume.

OpenClaw configuration and conversation state are backed up before migrations and restored only through version-aware OpenClaw tooling.

## Implementation Sequence

### Milestone 0: Prove the OpenClaw desktop bet

- Run the pinned OpenClaw Gateway and Control UI on the reference Arch system.
- Launch Chromium through a root-owned minimal Sway session as the complete
  visible UI.
- Launch Sway with `-c /etc/clawos/sway.conf` from a system service, and verify
  user Sway files and user-unit masks cannot replace the session definition.
- Apply Chromium managed policy and verify a writable browser profile cannot
  enable extensions, Developer Tools, sign-in, Incognito, or unapproved origins.
- Configure standard TTY and boot recovery without custom Super-key bindings.
- Prove swaylock/swayidle, lock-before-suspend, lid close, HiDPI, both GPU paths,
  Chromium's exact Wayland flags, and `Ctrl+Alt+F3` VT switching on the reference
  MacBook.
- Use this setup as the daily environment for one week and record every workflow
  that requires leaving the Control UI.

Exit criterion: the upstream WebUI is viable as the primary interface, and the
actual missing OS surfaces are known before a custom shell is written.

### Milestone 1: Pinned and hash-verified bootable base

- Establish the ClawOS repository, Arch Linux Archive snapshot, and pinned
  dependency manifest.
- Build the custom T2 ArchISO and signed local repository.
- Mirror and re-sign all required T2 packages.
- Build a complete offline image.
- Build the pinned Carapace/Bun setup application into the offline image and run
  its live-install mode from a root-owned loopback-only service.
- Boot in UEFI QEMU.
- Exercise coexist installation into `@clawos` on the reference machine before
  allowing clean-disk installation.
- Boot the live image on the reference MacBook.
- Validate keyboard, trackpad, display, Wi-Fi, audio, Touch Bar, fan, battery, suspend, resume, and both GPUs.

Exit criterion: the ISO can install a minimal encrypted system and reliably return to the live recovery environment.

### Milestone 2: Standalone OpenClaw appliance

- Package the pinned OpenClaw Gateway and Control UI.
- Build OpenClaw from its pinned source commit and `pnpm-lock.yaml` using a
  pre-fetched offline pnpm store; the installer never resolves npm dependencies.
- Implement first-boot onboarding.
- Create the first owner/OS agent through OpenClaw onboarding and verify that
  additional logically isolated agents can be created, selected, routed, and removed
  through upstream OpenClaw surfaces.
- Enable explicit ownership for multi-agent fleets and preserve OpenClaw's
  agent provenance, workspace, credential, and session boundaries.
- Start the local Gateway, local node, Sway, Chromium kiosk, and launcher unit.
- Implement the System plugin and read-only status surfaces.
- Configure the OpenClaw terminal and tmux wrapper.

Exit criterion: booting the Mac reaches a fullscreen OpenClaw desktop; the owner
agent can work locally; a second logically isolated agent can be created and explicitly
routed without state collision; terminal sessions function; and native recovery
remains accessible.

### Milestone 3: Privileged OS control

- Implement `clawosd`, D-Bus schemas, Polkit rules, approval UI, and audit log.
- Add package update, service control, power, rollback, and role operations.
- Implement User Limited with one fleet-wide `claw` UID and explicit sharing.
- Implement authenticated post-install Full Root enablement and make its
  approval-bypass semantics unmistakable.
- Add per-agent broker action policies and a trusted Gateway execution-identity
  binding; mark missing attribution as unavailable.
- Introduce task-scoped capability grants with expiry and narrowed subagent
  delegation, initially without reboot resumption.
- Verify agents cannot bypass approval through the plugin or broker.

Exit criterion: an agent can propose a real OS change, the user can approve the exact typed action, and the system can recover from a failed change.

### Milestone 4: Full Node role

- Implement remote Gateway enrollment.
- Start the node-host with persistent identity and capabilities.
- Display the controller’s Control UI locally.
- Require a compatible controller-side `clawos-system` plugin and route typed
  System operations to the selected ClawOS node through node invocation.
- Keep local recovery available when the controller is unreachable.
- Implement transactional Standalone ↔ Node switching.

Exit criterion: the same installation can alternate between a complete local OpenClaw system and a remotely controlled full-machine node without reinstalling or losing either identity.

### Milestone 5: Tested releases and self-update

- Build the upstream OpenClaw intake pipeline.
- Produce signed release manifests and repositories.
- Add pre-update snapshots, previous-kernel boot, validation, and rollback.
- Persist and recover task-scoped grants across controlled Gateway restart and
  reboot, bound to the original task and recovery policy.
- Document disaster recovery and state backup.

Exit criterion: a pinned OpenClaw and OS update can be promoted, installed, validated, deliberately failed, and rolled back on the reference MacBook.

## Test Plan

- Pinned and hash-verified ISO build from a clean Arch builder; bit-for-bit
  reproducibility is not claimed for MVP.
- Signature, checksum, lockfile, and SBOM verification.
- UEFI live boot and full blank-disk installation in QEMU.
- Installer refusal on an unapproved disk or unsupported hardware.
- Coexist installer refusal to resize, repartition, or format any filesystem.
- LUKS unlock, Btrfs layout, current/previous/recovery boot entries.
- Cold boot, restart, suspend/resume, lid close, battery, Wi-Fi, Bluetooth, audio, microphone, Touch Bar, fan, Intel GPU, and Radeon offload tests.
- Offline boot with usable recovery and terminal.
- Standard TTY access without custom compositor shortcuts.
- Sway session locking, idle notification, lock-before-suspend, lid policy,
  Chromium Wayland/HiDPI launch, and VT switching on the reference hardware.
- Gateway crash, browser crash, malformed configuration, and missing-network recovery.
- Standalone agent execution, tool use, terminal, and approved root action.
- Multi-agent creation provenance, explicit ownership/routing, workspace and
  session logical isolation, targeted subagent spawning, sandbox inheritance,
  and concurrent background work.
- Per-agent broker-policy enforcement and authoritative Gateway-to-`clawosd`
  attribution, including explicit unavailable-attribution cases.
- Task-scoped grant narrowing across agent handoff, plus persistence and recovery
  across controlled Gateway restart, crash recovery, and reboot.
- Node enrollment, reconnect, token persistence, command approval, controller outage, and unpairing.
- Transactional role-switch success and forced-failure rollback.
- OpenClaw upstream version-bump compatibility.
- ClawOS update success, interrupted update, failed health check, previous-kernel boot, and Btrfs rollback.
- Security tests confirming the WebUI cannot call arbitrary root commands or reuse expired approval tokens.

## Assumptions

- Working name: **ClawOS**.
- The first supported device is only `MacBookPro15,1`.
- The internal disk may be erased once the release gates pass.
- Arch is pinned per ClawOS release rather than continuously rolling.
- OpenClaw’s Control UI is the desktop and remains visually recognizable as upstream OpenClaw.
- One installation can switch between Standalone and Node roles.
- Node mode displays the controlling Gateway's UI; independent local recovery is
  provided by standard TTYs and the recovery boot entry.
- Authorized agents receive normal-user host access within the machine-wide
  security ceiling; root actions follow the configured approval policy.
- The default security level is Full User + Approvals; Full Root and User Limited
  remain explicit alternatives.
- ClawOS uses no Omarchy shell, Hyprland workflow, Super-key command model,
  launcher, bar, or theme layer.
- The production installer is complete and offline; development coexist mode is
  not a supported production configuration.
- Provider choice remains OpenClaw configuration rather than an OS-level model lock-in.
- OpenClaw-native multi-agent operation ships in MVP. Visual orchestration
  graphs and automatic worktree management are deferred.
- Broad hardware support, an app store, and a fully immutable A/B root
  filesystem are deferred until the reference implementation is stable.
