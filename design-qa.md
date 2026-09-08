> **Historical record.** Describes design or state at that time, not current release acceptance. `artifacts/...` paths cited below were local, git-ignored build outputs and are not in this repository.

# ClawOS boot identity design QA

- Source visual truth: `artifacts/screenshots/clawos-launch-reference.png`
- Implementation: `artifacts/screenshots/clawos-unlock-implementation-v5.png`
- Full-view comparison: `artifacts/screenshots/clawos-unlock-comparison.png`
- Focused comparison: `artifacts/screenshots/clawos-unlock-focus-comparison.png`
- Session handoff: `artifacts/screenshots/clawos-session-handoff.png`
- Ready workspace: `artifacts/screenshots/clawos-session-ready.png`
- State: encrypted-root unlock, followed by automatic local user session and the
  authenticated upstream OpenClaw Control UI

## Normalization

- Source pixels: 1487 x 1058.
- Implementation pixels: 1800 x 1095.
- Native OS surface; CSS size and browser device scale do not apply.
- Plymouth device scale: 1 for the QEMU proof profile.
- Full-view comparison normalizes both images to 1058 pixels high without
  changing either image's aspect ratio. The source is an earlier launch state
  with a narrower capture; the implementation is a 16:10-class machine unlock
  state. The comparison is therefore used for visual-language fidelity, not
  pixel-identical layout.
- Focused comparison uses centered 760 x 520 regions to make the wordmark,
  typography, palette, spacing, and state copy readable in one input.

## Full-view comparison evidence

- The exact graphite claw texture is reused as a source asset and covers the
  framebuffer without a blank region at the tested boot resolution.
- The coral, warm-white, muted-gray, and near-black tokens remain consistent.
- The implementation removes the launch card, readiness dashboard, and second
  launch action. This is intentional: encrypted-root unlock is now the single
  machine login, not an app-launch kiosk.
- `Esc  Boot details` provides a quiet recovery affordance without placing a
  terminal action in the primary flow.

## Focused comparison evidence

- The `OPENCLAW AGENT OS` eyebrow and split warm-white/coral `ClawOS` wordmark
  preserve the selected hierarchy and alignment.
- The state copy changes from `System ready`/`Launch ClawOS` to `Unlock ClawOS`
  because the implementation represents the earlier credential boundary.
- The implementation is deliberately calmer and less dense than the launch
  mock. No app controls appear before the machine is unlocked.

## Required fidelity surfaces

- Fonts and typography: Noto Sans and Noto Sans Mono provide an installed,
  initramfs-safe match for the reference's sans/monospace pairing. Hierarchy,
  optical weight, line spacing, and coral accent are preserved.
- Spacing and layout rhythm: the identity stack is centered in the framebuffer
  with the recovery hint pinned low. The earlier card is intentionally absent.
- Colors and visual tokens: coral `#ff684f`, warm white, muted gray, and the
  graphite canvas match the source design language.
- Image quality and asset fidelity: the original 1487 x 1058 claw texture is
  reused directly. Plymouth scales it to cover while preserving aspect ratio.
- Copy and content: startup copy is specific to encrypted-root unlock; the
  session then transitions to the unmodified upstream OpenClaw Control UI.

## Comparison history

1. P1: the first installed capture fell back to the text console because the
   serial recovery console caused Plymouth to suppress graphical output.
   Fix: add `plymouth.ignore-serial-consoles` while retaining ttyS0 recovery.
   Evidence: `clawos-unlock-implementation-v2.png` renders the graphical theme.
2. P1: automatic Plymouth HiDPI scaling and a half-width test window left the
   identity surface using only part of the framebuffer.
   Fix: set the QEMU proof to `DeviceScale=1`, declare a 1440 x 900 virtio-vga
   canvas at device creation, and reboot at the final host window size before
   capture.
   Evidence: `clawos-unlock-implementation-v5.png` fills and centers correctly.
3. P2: the initial password concealment glyph rendered as missing-glyph boxes.
   Fix: use the initramfs-safe asterisk concealment character.
   Evidence: the final empty unlock state contains no broken glyphs; typed input
   was accepted and unlocked the encrypted root.
4. Post-fix flow evidence: the passphrase unlocks the machine without a second
   login, the ClawOS texture remains visible during session startup, and the
   authenticated upstream OpenClaw workspace loads successfully.

## Findings

No actionable P0, P1, or P2 differences remain for the encrypted-unlock state.
The launch card and launch button are intentionally excluded because restoring
them would recreate the app-launch screen the OS direction rejected.

## Follow-up polish

- P3: replace the systemd-boot text menu with a branded loader treatment once
  the physical Mac boot path is being tested; it appears for only one second in
  the current QEMU proof.
- P3: derive hardware-specific Plymouth device scale during the physical-device
  installer instead of using the QEMU proof's fixed scale.

final result: passed

---

# Next-image live flow audit

- Fresh ISO baseline: `artifacts/m2/release-ui-2026-09-02/04-welcome-with-disk.png`
- Baseline installer: `artifacts/m2/release-ui-2026-09-02/05-install-before.png`
- Corrected welcome: `artifacts/m2/release-ui-2026-09-02/07-welcome-after-grid.png`
- Corrected inspection state: `artifacts/m2/release-ui-2026-09-02/08-inspect-after.png`
- Corrected guarded installer: `artifacts/m2/release-ui-2026-09-02/11-install-final.png`
- Inline validation state: `artifacts/m2/release-ui-2026-09-02/12-install-validation.png`
- Escape return proof: `artifacts/m2/release-ui-2026-09-02/15-escape-return.png`
- Responsive welcome: `artifacts/m2/release-ui-2026-09-02/19-welcome-1280x768.png`
- Responsive installer: `artifacts/m2/release-ui-2026-09-02/21-install-1280x768-final.png`
- Fresh-image welcome: `artifacts/m2/release-ui-2026-09-02/23-fresh-rebuild-welcome.png`
- Fresh-image inspection: `artifacts/m2/release-ui-2026-09-02/24-fresh-rebuild-inspect.png`
- Fresh-image installer: `artifacts/m2/release-ui-2026-09-02/25-fresh-rebuild-install.png`

## Findings and corrections

1. P1: **Try ClawOS** implied that the live environment provided an authenticated
   Agent workspace, while it only exposed pre-install machine diagnostics. It
   is now **Inspect system**, with copy that clearly places the Agent workspace
   after installation.
2. P1: the compact diagnostics grid expanded into a mostly empty full-height
   panel. It now keeps its measured 294-pixel height and leaves deliberate open
   canvas between the inspection data and actions.
3. P1: adding install guidance initially forced the persistent top bar and Back
   action outside the 900-pixel viewport. The guidance was reduced to a single
   scannable install-plan line and the full screen was recaptured with both OS
   chrome and actions visible.
4. P2: the live top bar showed audio and power glyphs that looked interactive
   but had no action. Those false affordances were removed; network state and
   time remain informational.
5. P2: the erase action could be invoked before the passphrase form was valid,
   relying on post-click errors. It is now disabled until a guarded target,
   ten-character passphrase, and exact confirmation are present. Short and
   mismatched values report inline errors without changing the disk.
6. P2: live setup, the Agent shelf, and System Center encoded proof-canvas
   dimensions. The live surface now reads its active output, the shelf keeps a
   24-pixel side gutter, and Center remains inset from the available screen.
7. P2 accessibility: password fields now expose distinct accessible names and
   password input purpose; the confirmation field submits on Enter; and Escape
   returns from Inspect or Install to the welcome screen. The destructive
   boundary remains explicit in visible copy.

## Validation

The changes were hot-loaded into the currently running fresh ISO on a disposable
32 GB qcow2 target. Welcome, Inspect, Install, invalid passphrase, and Escape
return were exercised at 1440 x 900 without clipping or terminal leakage. The
output was then changed to supported 1360 x 768 and 1280 x 768 modes and the
welcome and guarded installer were recaptured. Both retain the OS bar, full
content, Back action, inline warning, and disabled destructive action. No
install was started and the test disk was not changed. Python syntax validation
and the complete seven-stage pre-ISO source gate pass. The next required proof
is one clean build and fresh-image regression containing this batch and the
newly added Geist Mono live package.

next-image source result: passed

The rebuilt ISO subsequently passed fresh-image visual acceptance on a new
blank 32 GB qcow2 target. This confirmed that the corrected UI and both font
packages are in the image itself rather than only in the hot-loaded proof VM.
No destructive installation was started during this visual acceptance pass.

next-image image result: passed

## M2 clean-install release evidence

- Live canvas: `artifacts/m1/m2-e2e.T5Npo7/live-welcome.png`
- Graphical encrypted-root unlock:
  `artifacts/m1/m2-e2e.T5Npo7/installed-unlock.png`
- Installed first boot:
  `artifacts/m1/m2-e2e.T5Npo7/installed-first-boot.png`
- All three captures are 1440 x 900 and were taken by the automated clean
  live-to-installed gate, not from a hot-patched proof VM.
- The first-boot capture preserves the 52-pixel OS bar, open Carapace-aligned
  setup canvas, five-step onboarding rail, truthful machine readiness, and
  persistent in-context agent shelf. No terminal, browser frame, duplicate
  menu bar, clipped surface, or fallback kiosk UI is visible.

clean-install visual result: passed

---

# ClawOS onboarding and native shell design QA

- Selected Agent reference: `shell-prototype/artifacts/prototype-agent-desktop.png`
- Fresh-installed Agent implementation: `artifacts/m1/runtime/release-agent.png`
- Side-by-side comparison: `artifacts/m1/runtime/release-agent-reference-comparison.png`
- Command workspace: `artifacts/m1/runtime/release-command.png`
- Build workspace: `artifacts/m1/runtime/release-build.png`
- Browse workspace: `artifacts/m1/runtime/release-browse.png`
- Fresh-installed workspace contact sheet: `artifacts/m1/runtime/release-workspaces.png`
- Graphical onboarding implementation: served directly from
  `m1/profile-overlay/airootfs/usr/share/clawos/onboarding/` and exercised with
  the in-app browser through Gateway, Agent, Access, and failure states.
- Fresh-installed onboarding welcome: `artifacts/m1/runtime/release-onboard.png`
- Installed Gateway choice: `artifacts/m1/runtime/onboard-clone-gateway2.png`
- Installed Agent/provider state: `artifacts/m1/runtime/onboard-clone-agent.png`
- Installed safe access default: `artifacts/m1/runtime/onboard-clone-access-scaled2.png`
- Installed progress state: `artifacts/m1/runtime/onboard-clone-progress.png`
- Installed ready state: `artifacts/m1/runtime/onboard-clone-after30.png`
- Installed post-onboarding Agent: `artifacts/m1/runtime/onboard-clone-launched2.png`
- Native recovery console: `artifacts/m1/runtime/fresh-recovery.png`

## Agent comparison findings

- Both screenshots use a 1440-pixel-wide canvas. The 1440 x 1024 reference is
  cropped to the top 900 pixels for a like-for-like comparison with the final
  QEMU output.
- The implementation preserves the reference's graphite Control UI, coral
  active state, full-height OpenClaw navigation, edge-to-edge Agent surface,
  and persistent bottom composer.
- The prototype's simulated agent-activity tray is intentionally not injected
  into the upstream UI. The installed implementation uses the authentic
  OpenClaw Control UI and keeps ClawOS-owned state in the native top panel.
- The native panel now matches the mock's 52-pixel anatomy: split ClawOS
  wordmark, restrained OS eyebrow, centered numbered workspaces, Gateway state,
  working Command affordance, and stacked time.
- Permanent network and recovery diagnostics were removed from primary chrome.
  Gateway details remain in its tooltip, the Command control opens the real
  persistent workspace, and recovery remains discoverable on the ClawOS mark
  while `Ctrl+Alt+F3` continues to work.
- Inter Variable owns product labels while the packaged `GeistMono Nerd Font` face is
  explicitly selected for the OS eyebrow, workspace numbers, command hint, and
  time. Weight, tracking, pill height, spacing, and border radii were measured
  against the reference.
- The standalone Waybar image module was removed after fresh-install QA exposed
  an Arch `glycin` loader loop for both PNG and SVG inputs. The real source
  assets remain packaged for boot and onboarding; omitting the tiny panel pin
  preserves the prototype hierarchy while reducing steady panel CPU from one
  saturated core to roughly idle.

## Workspace findings

- Command opens directly to a clean ClawOS Zsh prompt in a persistent tmux
  session; the stock Zsh first-run wizard and stock tmux colors are absent.
- Build opens a persistent split workspace with the shell on the left and live
  OpenClaw Gateway activity on the right.
- Browse opens a real, agent-attachable Chromium workspace with a ClawOS start
  surface and standard browser controls. A stale crash-restore bubble observed
  after a forced development restart is suppressed by both supported Chromium
  flags in the release launchers.
- A session-restart regression initially left two generations of Waybar and
  workspace launchers. Each wrapper now exits when its originating Sway socket
  disappears. The installed VM reports exactly one panel, one Agent entry, and
  one launcher for each native workspace after an in-place Sway restart.

## Onboarding findings

- The installed setup surface fills the Agent workspace beneath the native
  panel; it does not show Chromium controls or look like a freestanding app.
- Welcome, local/remote Gateway, Ollama Cloud/provider-later, machine access,
  progress, ready, launch, failure, retry, and recovery affordances are present.
- At the 1440 x 900 proof resolution, all states fit the 858-pixel browser
  viewport without a page scrollbar. Full User + Approvals is both the visual
  selection and keyboard focus on the Access screen.
- A provider-later run completed upstream `openclaw onboard`, installed and
  started the Gateway, reached the ready screen, and launched the authentic
  dark Control UI. This used a reversible clone of the installed development
  disk so the already-configured model proof remained intact.
- `Ctrl+Alt+F3` switches from the completed Agent workspace to an independent
  tty3 login, and `Ctrl+Alt+F2` returns to the live graphical session.
- Provider and Gateway values now use upstream environment SecretRefs backed by
  OpenClaw's mode-0600 `.env`; an isolated pinned-upstream onboarding run proved
  that the Gateway config stores an object with `source: env`, not plaintext.

## Current result

The final same-input 1440 x 900 comparison has no remaining P0, P1, or P2
visual differences for the native top bar, onboarding, Agent, Command, Build,
Browse, or tty recovery. A clean encrypted disk completed installation from the
rebuilt ISO, booted without the ISO attached, completed provider-later local
onboarding, reached the authenticated upstream Control UI, exercised all four
workspaces, and switched to tty3 recovery and back to tty2. The final disk is
`artifacts/m1/disks/clawos-release-proof.qcow2`; the disposable QA-only `grim`
package was installed after the clean boot solely to capture compositor pixels.

full-goal result: passed

---

# Native shell design-system audit

- Canonical specification: `m2/DESIGN-SYSTEM.md`
- Shared native tokens: `m1/profile-overlay/airootfs/etc/clawos/design-system.css`
- Before—competing Actions sidebar: `artifacts/m2/ui-audit-2026-09-02/01-center-before.png`
- After—centered System Center: `artifacts/m2/ui-audit-2026-09-02/04-center-after.png`
- After—persistent Agent shelf: `artifacts/m2/ui-audit-2026-09-02/05-shelf-after.png`
- After—ClawOS system menu: `artifacts/m2/ui-audit-2026-09-02/06-system-menu-after.png`
- After—intent palette: `artifacts/m2/ui-audit-2026-09-02/07-intent-palette-after.png`
- After—lock screen: `artifacts/m2/ui-audit-2026-09-02/08-lock-after.png`

## Findings and corrections

1. P1: the former Actions sheet consumed the full right edge and visually
   became a second application sidebar. It was removed. The same action now
   opens a compact centered intent palette with no permanent navigation.
2. P1: the former power sheet used oversized legacy tiles and host-theme
   imagery. It was replaced by a 264-pixel GTK layer-shell menu under the
   ClawOS wordmark, with symbolic system icons, click-outside dismissal, Escape,
   keyboard focus, and guarded power actions.
3. P1: Center previously competed side-by-side with the active application.
   It now presents as a 1040 x 740 centered OS overlay with a scrim, explicit
   Back and Refresh controls, and a single decisions-and-work hierarchy.
4. P2: native surfaces had locally similar but drifting graphite, gray, font,
   radius, and focus values. They now consume one measured token set: Inter for
   interface copy, Geist Mono for technical state, coral `#ff684f`, green
   `#35ce78`, warm white `#f3f1ee`, and the shared canvas/surface/line scale.
5. P2: the shelf used a text plus sign as its action affordance. It now uses a
   real symbolic overflow icon and a real symbolic status mark with accessible
   names and tooltips.
6. P2: the Gateway handoff page reproduced a fake OpenClaw sidebar while the
   authentic UI was loading. It is now a calm, centered ClawOS state with the
   packaged identity asset and no duplicate navigation.

The live installed VM parsed every shared GTK stylesheet and visually passed
the five representative OS states at 1440 x 900. Source profile validation,
onboarding checks, agent queue checks, and whitespace validation also pass.

native-shell result: passed

---

# M2 live Agent Canvas design QA

- Source visual truth: an external generated mock (not tracked); see the normalized copy below.
- Normalized source: `artifacts/m2/design/agent-canvas-source-normalized.png`
- Rendered implementation: `artifacts/m2/design/implemented-agent-canvas-final-inter.png`
- Full-view comparison: `artifacts/m2/design/agent-canvas-comparison-final-inter.png`
- Focused comparison: `artifacts/m2/design/agent-canvas-focus-comparison-final-inter.png`
- Try state: `artifacts/m2/design/implemented-agent-canvas-try-final-inter.png`
- Install state: `artifacts/m2/design/implemented-agent-canvas-install-final-inter.png`
- State: graphical live welcome on the native Sway/Wayland output before installation

## Normalization

- Source pixels: 1586 x 992; normalized to 1440 x 900 to match the native proof output.
- Implementation pixels and compositor viewport: 1440 x 900 at device scale 1.
- Both artifacts use the same dark state, welcome content, and 16:10 frame after normalization.
- The implementation is a native GTK 3 surface, so browser CSS dimensions and browser device scale do not apply.

## Full-view comparison evidence

- The final render preserves the selected option's open canvas: a 52-pixel system bar, two-line hero, coral install action, quiet Try action, split readiness/event region, and low recovery hint. No launch card or freestanding app window remains.
- The hero title, line breaks, button width, section boundary, two-column split, top-bar anatomy, and footer placement align at the same viewport.
- Dynamic VM facts intentionally replace the mock's physical-machine values. The no-disk preview says `No guarded disk / Unavailable` and disables destructive installation rather than inventing a target.
- The real ClawOS halftone claw asset is positioned and clipped by a native drawing canvas. It is deliberately subtler than the generated source art but preserves the subject, crop, direction, and high-resolution raster treatment.

## Focused comparison evidence

- The focused hero comparison makes the Inter/Switzer-like typography, 58-pixel display scale, coral CTA, underline treatment, title wrapping, and artwork crop readable side by side.
- The focused lower-region comparison verifies the equal 720-pixel panes, thin Carapace dividers, four truthful machine rows, seven live events, small semantic status marks, and recovery placement.
- `Inter Variable` is loaded from Arch's `inter-font` package in the evidence VM. `GeistMono Nerd Font` remains the event-stream face.

## Required fidelity surfaces

- Fonts and typography: `Inter Variable` is the primary UI family with Noto Sans fallback; Geist Mono owns technical labels. Display size, weight, wrapping, tracking, and small-text hierarchy visibly match the selected direction.
- Spacing and layout rhythm: the surface is exactly 1440 x 900, with no oversized child geometry, clipped clock, off-screen action, generic card, or unintended scrollbar. Hero, readiness, event, and footer regions follow the source rhythm.
- Colors and visual tokens: the implementation uses the measured Carapace near-black surfaces, `#f5654a` coral, `#4fc8ae` sea green, warm white, muted gray, 1-pixel dividers, and 8-pixel control radii.
- Image quality and asset fidelity: the packaged 1487 x 1058 ClawOS claw raster is reused directly, scaled once with bilinear interpolation, painted at native compositor density, and clipped without a seam or stretched screenshot.
- Copy and content: welcome copy matches the selected concept. Live events and disk state are grounded in the current VM; installation explains LUKS2, the guarded Q35 `/dev/vda` boundary, single-unlock behavior, and tty recovery.
- Icons and accessibility: GTK symbolic icons replace text glyphs; visible controls are semantic GTK buttons and entries. Keyboard navigation exercised Install, Try, Back, password fields, disabled install, and the persistent recovery path.

## Comparison history

1. P1: the prior live installer used two large generic launch cards and read as an app launcher. Fix: replace it with the selected open Agent Canvas hierarchy and measured Carapace tokens. Evidence: `implemented-agent-canvas-pass1.png`.
2. P1: the first native render failed because GTK 3 rejected a nonstandard numeric font weight. Fix: use supported weights and validate the real process/window before capture. Evidence: `implemented-agent-canvas-pass1.png` after the runtime correction.
3. P2: the first comparison showed an oversized CTA, wide gutters, compressed machine rows, and an incorrectly placed/dim art field. Fix: tune the hero scale and action spacing, restore source-aligned gutters, distribute rows, and reposition the real claw asset. Evidence: `agent-canvas-comparison-pass3.png`.
4. P1: positioning the raster with `Gtk.Fixed` created an 1820-pixel minimum surface inside the 1440-pixel output, clipping the clock and right-side actions. Fix: paint the asset into a fixed 1440 x 900 drawing area and verify Sway `rect` and client `geometry` are both exactly 1440 x 900. Evidence: `implemented-agent-canvas-try-final.png`.
5. P1: the initial install state allowed long copy and fixed pane requests to overflow the right edge. Fix: constrain both panes, wrap explanatory copy, and keep Back as a compact secondary action. Evidence: `implemented-agent-canvas-install-final-inter.png`.
6. P2: the initial Try state hid its install action and showed simulated-ready event copy. Fix: use an equal native grid, keep Install visible at bottom right, and report staged/waiting facts truthfully. Evidence: `implemented-agent-canvas-try-final-inter.png`.
7. P2: the old test ISO lacked Inter, so the first evidence used Noto fallback. Fix: add Arch `inter-font`, select its actual `Inter Variable` family name, hot-load the exact package into the evidence VM, and recapture. Evidence: `agent-canvas-comparison-final-inter.png`.

## Findings

No actionable P0, P1, or P2 design differences remain for the M2 welcome, Try, guarded no-disk Install, keyboard navigation, or 1440 x 900 geometry. Hardware-specific disk values and the darker authentic ClawOS raster are intentional product-truth deviations from the generated mock.

## Follow-up polish

- P3: on physical hardware, derive the display row from the active output instead of the QEMU proof's fixed 1440 x 900 value.
- P3: add the same Carapace-aligned treatment to the later installer progress and completion evidence after the rebuilt ISO runs the full-disk path.

final result: passed
