# Milestone 1 status

Last validated: 2026-09-02

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
- The installed session now has a native Waybar panel from root-owned config with fixed
  Agent, Command, Build, and Browse workspaces. Chromium uses borderless app
  mode instead of kiosk mode, while named tmux sessions keep Command and Build
  work alive across UI restarts.
- The development installer pins and installs OpenClaw `2026.8.2`, Node.js,
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
- The selected native-shell implementation has now been hot-loaded into the
  installed development VM and visually verified at 1440 x 900: authentic dark
  upstream Control UI in Agent, a clean ClawOS Zsh/tmux Command workspace, a
  split Build workspace with live Gateway activity, and the branded Browse
  start surface.
- The installed native panel now follows the selected 52-pixel prototype rather
  than a dense Linux telemetry bar. It uses Inter Variable plus the packaged
  `GeistMono Nerd Font`, centered numbered workspace pills, a live Gateway
  state, a working Command workspace affordance, and stacked time. Fresh-install
  QA removed the standalone image module after Arch's `glycin` loader looped on
  both PNG and SVG inputs; the remaining panel is visually faithful and idle.
- A compositor-restart test found and fixed orphaned workspace launchers. The
  installed VM now returns to exactly one Waybar and one launcher for each
  ClawOS workspace after restarting the root-owned Sway session.
- A reversible clone of the installed VM completed the new graphical first-boot
  flow at 1440 x 900: local Gateway, provider-later, Full User + Approvals,
  progress, ready, launch, authenticated upstream Control UI, and tty3 recovery.
  The access screen was tightened to fit beneath the native panel without a
  scrollbar, and its default keyboard focus now matches its selected policy.
- Gateway and Ollama Cloud onboarding now use upstream environment SecretRefs.
  The setup service stores values only in OpenClaw's mode-0600 `.env` and keeps
  them out of process arguments, URLs, logs, and the ClawOS access-policy file.
  An isolated pinned-upstream test proved the Gateway token is persisted as an
  environment-source object.
- A rebuilt ISO installed to a new 32 GB encrypted qcow2 disk, booted with the
  ISO detached, reported zero failed system units, and completed the graphical
  local-Gateway/provider-later/Full User + Approvals path. The authenticated
  upstream Control UI and Agent, Command, Build, and Browse workspaces were
  captured directly from Sway at 1440 x 900. `Ctrl+Alt+F3` reached active tty3
  recovery and `Ctrl+Alt+F2` returned to the live session.
- The onboarding chrome audit is implemented in the source profile and proof
  VM. Waybar is now the sole OS header, setup begins with the progress rail,
  network readiness is scoped to the active setup step, and the final action
  enters the Agent workspace instead of “launching” ClawOS. Unfinished setup is
  represented by a clickable native **Setup required** state with a recovery
  path back to the setup surface.
- The next native-shell checkpoint adds a GTK session lock, a centered graphical
  Lock/Restart/Shut down surface, guarded power confirmations, and a 15-minute
  idle lock. Fresh installs reuse the disk-unlock secret for explicit session
  unlock without adding a second boot login. Plymouth now distinguishes normal
  startup, restart, shutdown, and update transitions, and the installer no
  longer creates a tty1 root autologin path.
- A normal encrypted-disk reboot now hands off directly from Plymouth to the
  native shell without waiting for `network-online.target`. Agent opens an
  upstream-shaped graphical connection state immediately while Gateway startup
  and node registration continue in parallel, then automatically replaces it
  with the authenticated Control UI. The proof VM was hot-updated, rebooted,
  and framebuffer-verified through both states with no terminal or empty-black
  interval.
- Chromium background mode is disabled for the persistent Agent and Browse
  surfaces. Closing Browse's last window now terminates the old profile process,
  allowing the ClawOS supervisor to create a fresh window automatically. The
  proof VM verified a zero-window state followed by a new Chromium PID and
  visible Browse workspace within four seconds.
- The ClawOS wordmark is now the single system-menu affordance in the native
  panel; the redundant right-side System button has been removed. A real Waybar
  pointer click in the proof VM opened the graphical Lock, Restart, Shut down,
  and Cancel surface successfully.
- The fixed Agent, Command, Build, and Browse navigation has been replaced by a
  single `Main` activity canvas. Terminal, Build, and Browse no longer boot as
  permanent destinations; typed shell launchers reveal them on demand from a
  hidden surface layer. The activity indicator follows the focused surface without changing
  the identity of the work.
- The running installed proof was hot-updated and framebuffer-verified in both
  states: OpenClaw alone and a terminal temporarily covering the activity canvas. `Alt+Q`
  then removed the terminal surface and returned the canvas to full width
  without the old supervisor reopening it. Zero system units are failed.
- The installed proof now runs a same-user typed surface broker and the bundled
  `clawos-system` OpenClaw plugin. With the normal `coding` profile intact,
  onboarding additively enables `clawos_surface` and `clawos_activity`. An
  Ollama Cloud `minimax-m2.7` agent completed both calls with no failures,
  projected `Agent shell proof` into the native panel, presented Terminal, and
  returned to the OpenClaw canvas on a second turn. Both states were captured
  from the framebuffer without a compositor hotkey or injected VM input.
- Automatic projection is now proven independently of model compliance. The
  plugin consumes OpenClaw's typed `model_call_started`, `agent_end`,
  `subagent_spawned`, and `subagent_ended` hooks, using only run/session metadata.
  A normal Ollama Cloud `minimax-m2.7` turn made no ClawOS tool calls while the
  panel automatically moved from `Agent main is working` to
  `Agent run complete in 25s`. The running state was framebuffer-captured.
  Concurrent runs are reference-counted, failed delegated work raises native
  attention, and the broker safely restores its minimal projection after restart.
- The installed proof now has a validated capability registry backed by the
  standard freedesktop application directories plus root-owned ClawOS web-app
  manifests. Its searchable application picker is secondary infrastructure. It
  discovers normal Linux applications without accepting raw executable input
  and routes every launch through the same-user typed broker using validated
  application or desktop identifiers.
- Gmail and Outlook are proven as persistent-profile activity surfaces. Gmail
  was launched through the human palette; Outlook was opened by an Ollama Cloud
  `minimax-m2.7` OpenClaw turn using only `clawos_app` (two calls, zero tool
  failures). Both cover the full activity canvas beneath the native panel,
  carry their names in the activity indicator, and can be hidden back to Agent
  without terminating their browser processes.
- Application-window validation caught and fixed three live integration defects:
  long broker requests closing on socket half-close, Sway treating command
  fragments as CLI flags, and floating containers being omitted from lifecycle
  lookup. Restarted brokers can re-adopt registered web apps through their
  standard `StartupWMClass` metadata.
- The app-first palette has been demoted to a secondary escape hatch. Clicking
  the activity on the Agent canvas or pressing `Alt+Space` now opens an
  intent-first menu headed **What do you want to do?** with direct Talk, Open,
  Inspect, Browse, and Review actions. When a supporting surface is visible the
  same central control becomes a breadcrumb such as `← Main / Gmail`; clicking
  it returns to Agent. `Alt+Escape` provides the same visible-stack Back action
  while `Alt+A` remains compatible. Exact workspace geometry removes exposed
  strips of the Agent canvas beneath Terminal and web-app surfaces.
- The `clawos-system` plugin now establishes machine embodiment through the
  supported `before_prompt_build` hook on every run. It tells OpenClaw that it
  inhabits a graphical ClawOS activity, resolves explicit presentation intent
  against the live validated registry, and blocks raw graphical launches through
  `exec`. A natural `open gmail` turn on `agent:main:main` used exactly one
  `clawos_app` call with zero failures and opened Gmail locally; the prompt did
  not name a tool or application id.
- A visual-accessibility and in-context Agent proof now keeps Gmail full-canvas
  while opening the same authenticated OpenClaw Control UI as a dismissible
  side panel. Focus returns to Gmail on close. Visible Back, Agent, Actions, and
  Orca controls remove hotkey dependence; the VM started and stopped Orca.
  Gmail and Outlook expose loopback-only browser profiles, and the Gmail proof
  returned both live tabs and an accessible snapshot through OpenClaw. The
  interaction direction is accepted, but the first large GTK action sheet and
  crowded multi-pill bar are explicitly not visual release candidates; the
  accepted replacement is a centered OS-owned command shelf. The image profile
  now includes that native GTK layer-shell surface: it follows focus across
  Gmail, Outlook, terminal, build, browser, and other registered applications;
  submits prompts to the durable `agent:main:main` OpenClaw session; reflects
  activity state in the top bar; and keeps the full Control UI on demand.
- The accepted command shelf has now been hot-loaded and exercised in the
  installed proof VM. It resolved the focused registered Gmail surface from the
  typed activity registry, accepted text through the real GTK entry, submitted
  through `openclaw agent --session-key agent:main:main`, visibly transitioned
  from Ready to Working, and completed with the response recorded in the
  durable OpenClaw transcript. State writes preserve the broker-owned activity
  identity, summary, visible surface, and registered applications. A qcow2
  snapshot named `before-agent-shelf` preserves the pre-test machine state.
- The accepted shelf is now in the freshly built
  `clawos-2026.09.01-x86_64.iso`. Its checksum and boot chain validate; an
  independent UEFI QEMU smoke boot proved ClawOS identity, zero failed systemd
  units, DHCP, overlay live root, and clean shutdown. Direct SquashFS inspection
  matched the shelf byte-for-byte to the source profile and confirmed the
  selected 52-pixel top bar. Runtime evidence is in
  `artifacts/m1/smoke.yKN9Ol/`.
- The automated `m2-e2e-qemu` release gate now passes from a fresh branded live
  boot through a new guarded LUKS2/Btrfs install, ISO-detached graphical
  unlock, direct agent-session entry, image-built Agent Canvas/shelf/top
  bar/onboarding, tty3 recovery, and clean shutdown. The validated ISO SHA-256
  is `5b795ec11bcf0b9af52a522c283f9c7a3650b999de6942487a674276bd88ebf1`;
  logs and three inspected 1440 x 900 captures are retained in
  `artifacts/m1/m2-e2e.T5Npo7/`.
- A final independent headless UEFI boot of that same ISO passed ClawOS
  identity, zero failed systemd units, DHCP, live overlay root, and clean
  poweroff. Evidence: `artifacts/m1/smoke.OdiWms/`.
- The first Milestone 3 privileged-action slice now passes the same uninterrupted
  fresh-live-to-installed gate. On the ISO-detached encrypted system,
  `clawosd` rendered the native exact-action approval, created a read-only
  Btrfs recovery snapshot, installed allowlisted package `tree`, emitted a
  root-owned token-free audit event, and rejected approval-token reuse. The
  validated ISO SHA-256 is
  `9a2a14e498c225ab76f7096c1ed06fd51cbf7bf10a9cdbf9bbc8794b43fb70da`;
  evidence is retained in `artifacts/m1/m2-e2e.NwKOfe/`.
- Onboarding now records a mode/access-scoped, non-secret stage checkpoint and
  reports readiness only after the upstream base setup, reviewed plugin, tool
  policy, role profile, and machine security policy have all committed. A
  restart after a partial failure returns to a resumable attention state instead
  of treating `gateway.mode` alone as proof of completion.
- Full Root now enrolls the same-machine node through both upstream OpenClaw
  approval layers using an exact cryptographic device identity and an exact
  `clawos.system` capability request. Ambiguous requests fail closed. Full User
  + Approvals and User Limited preserve explicit approval.
- The Agent surface now watches local Gateway lifecycle. Two consecutive health
  failures recycle only the Control UI process through its health-gated
  bootstrap, preventing a Gateway restart from leaving OpenClaw's persistent
  style-failure banner. A live VM reload proved that the existing banner clears
  against the healthy Gateway.
- The same-user surface broker now has an atomic PID/cmdline-verified singleton
  lock. A second broker exits without unlinking or stealing the live desktop
  socket; restart persistence remains covered by the Node test.
- QEMU can run the real ClawOS framebuffer headlessly on a loopback-only VNC
  listener, with guarded qcow2 paths and an explicit TCG fallback. The private
  VPS demo contract keeps VNC behind SSH or the provider recovery console and
  refuses to introduce an unauthenticated public browser bridge.
- The native attention surface is now a unified **ClawOS Center** rather than a
  machine-only approval dialog. It reads upstream durable tasks and OpenClaw
  approvals, combines them with typed `clawosd` requests, supports exact
  decisions and guarded task cancellation, and keeps terminal results visible
  as recent work. The top bar reports concrete `working` and `Needs you` counts,
  tracks viewed results in a mode-0600 projection file, and clears stale broker
  attention after a handled decision. The complete seven-stage pre-ISO source
  gate passes. The current source was hot-loaded into the installed proof VM:
  Sway reported one focused floating 1040 × 740 Center at the center of the
  1440 × 900 activity canvas, the framebuffer showed its live task history over
  the authenticated Control UI, and a GTK CSS parser gate now prevents the
  invalid style value found during that run. Fresh-image regression remains
  required.
- Back and return actions now use the same licensed Radix arrow asset selected
  in the prototype instead of a text arrow or host-theme icon. The compact
  ClawOS button treatment is shared by the activity breadcrumb, onboarding,
  live installer, and Center. Live Terminal and Center captures verified both
  controls at 1440 × 900. This run also found and fixed a socket-path mismatch
  in `clawos-appctl`; the typed app client now follows the installed broker at
  `/run/clawos-control/surface.sock`.
- Native shelf prompts now cross a private background boundary instead of
  keeping the OpenClaw CLI inside the GTK process. `clawos-agent-submit` writes
  a same-user mode-0600 message file and starts a collected transient user
  service; `clawos-agent-run` invokes the pinned upstream CLI with
  `--message-file`, removes the prompt, and records only a non-secret result.
  Automated checks cover success, failure attention, private permissions, and
  unsafe-file rejection. In the installed VM, request
  `f8f99dafa9bb9d0e51c52d438f0ba3b3` ran as a separate service, survived a
  shelf restart, completed as upstream task
  `6480b204-ac46-45f9-a4ac-5425f1d7787e`, and appeared in the Center as recent
  work. The same pass stopped skipped no-route heartbeat jobs from falsely
  reporting that the user was needed. Evidence:
  `artifacts/m1/runtime/center-queue-live.png`.
- Interrupted-handoff recovery is now implemented without unsafe automatic
  replay. Session startup detects only private request files whose transient
  service is no longer active. ClawOS Center shows the local prompt summary and
  requires an explicit Resume or Discard decision; Resume warns that external
  or machine effects may repeat, while Discard removes the prompt and writes a
  non-secret receipt. A simulated interrupted request was hot-loaded into the
  installed VM, surfaced as exactly one attention item, visually verified, and
  discarded cleanly. Evidence: `artifacts/m1/runtime/center-recovery-live.png`.
- The native shell now has a single Carapace-derived interface contract in
  `m2/DESIGN-SYSTEM.md` and `/etc/clawos/design-system.css`. The full-height
  Actions sidebar and legacy tile power sheet have been removed from both the
  package set and image profile. Actions now opens a compact centered intent
  palette; clicking the ClawOS wordmark opens a dismissible 264-pixel native
  system menu; and the Center is a centered OS overlay instead of a competing
  application sidebar. Inter owns UI copy, Geist Mono owns technical state,
  and the same graphite, warm-white, coral, green, borders, radii, and focus
  rules now cover Waybar, the Agent shelf, Fuzzel, onboarding, the live
  installer, lock screen, browser handoff, and System Center. The installed VM
  passed GTK CSS parsing and 1440 x 900 visual checks for Center, shelf, intent
  palette, system menu, and lock screen. Evidence is retained in
  `artifacts/m2/ui-audit-2026-09-02/`.
- Fresh-ISO inspection additionally caught that Geist Mono was present in the
  target installer package set but absent from the live image. The live profile
  now packages `otf-geist-mono-nerd` so setup and recovery-time technical state
  use the same type system before and after installation.
- The next-image UX batch is complete in source and was hot-loaded into a fresh
  live boot with a disposable guarded disk. The welcome action now says
  **Inspect system** instead of promising an unavailable live Agent workspace;
  that screen keeps its system facts at their intended height. The install
  screen now explains LUKS2, the Full Root default, recovery, and the irreversible
  erase boundary; validates both passphrase fields live; disables the erase
  action until the values are valid and equal; exposes accessible field names;
  and supports Escape back-navigation. The live surface reports the active
  output dimensions, its top bar no longer contains inert power/audio icons,
  and the Agent shelf and System Center derive their width/height from the
  output rather than requiring 1440 x 900. Visual evidence is retained under
  `artifacts/m2/release-ui-2026-09-02/`. Welcome and guarded Install were also
  exercised at 1360 x 768 and 1280 x 768; both retain the top bar, all content,
  Back, and the disabled destructive action without clipping. The complete
  source gate passes.
- Fresh-image acceptance completed against
  `artifacts/m1/out/clawos-2026.09.02-x86_64.iso` after the rebuild at
  2026-09-02 19:53:02 -0500. The image is 1,796,542,464 bytes with SHA-256
  `e2f1c7329286b10bb63fffe8d132bd177daac828d1e365c3544d363ad04a0f5a`.
  It booted on a new blank 32 GB qcow2 disk, reached the native welcome with no
  failed systemd units, packaged `inter-font 4.1-1` and
  `otf-geist-mono-nerd 3.5.1-2`, reported the guarded target, and visually
  passed Welcome, Inspect System, and guarded Install at 1440 x 900. Evidence:
  `artifacts/m2/release-ui-2026-09-02/23-fresh-rebuild-welcome.png`,
  `24-fresh-rebuild-inspect.png`, and `25-fresh-rebuild-install.png`.

## Not yet proven

- Offline package installation and previous-kernel/recovery/rollback entries.
- T2 hardware packages or booting on the reference MacBook.
- Fresh-image proof of automatic Full Root local node enrollment. The exact
  selection and policy behavior pass isolated tests; the running VM was paired
  manually because its ISO predates this source change.
- Fresh-image reboot proof of interrupted-request reconciliation. Source,
  isolated tests, and a live simulated orphan are proven; an actual reboot with
  an in-flight request remains intentionally separate destructive-effects QA.
- Successful privileged machine-action execution through a separately hosted
  remote Gateway, including controller outage and reconnect.
- Authenticated Gmail/Outlook account use and headless mail connector actions;
  this milestone proves human/agent surface ownership, not mailbox authorization.
- The complete offline OpenClaw appliance and production installer.

The live/recovery ISO and network-backed QEMU proof installer are valid. This
is not yet the offline production installer or a graphical ClawOS release.
