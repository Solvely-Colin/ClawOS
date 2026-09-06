# Accessibility and in-context Agent proof

Date: 2026-08-28

## Outcome

ClawOS now has a working interaction proof for continuing to direct OpenClaw
without leaving the application currently on screen. A supporting surface stays
full-canvas while the same authenticated OpenClaw Control UI session can be
opened as a right-side Agent panel and dismissed back to the exact prior
surface. This is one activity and one conversation, not a second assistant.

The interaction direction is accepted. The current visual treatment is not.
The installed GTK action sheet and crowded top-bar controls are accessibility
scaffolding that prove reachability and focus behavior; they are not the final
Carapace-quality shell design.

The accepted follow-on direction is now implemented as an OS-owned command shelf centered at the
bottom of every supporting surface. It stays hidden on the OpenClaw Agent
canvas and during ClawOS setup, where those products already own their input,
and keeps the current supporting application full-canvas,
provides a visible context-aware `Ask Agent about …` entry, exposes no more than
three compact secondary actions, and raises work or approval state in a short
strip above the composer. The full upstream Control UI remains available on
demand.

Submitting from the shelf no longer binds work to the GTK window. The shelf
hands the request over standard input to a private queue, which stores it as a
mode-0600 message file and starts a transient user service. The runner uses the
pinned upstream `openclaw agent --message-file` interface, so prompt text does
not enter argv or the service journal. OpenClaw owns the task and transcript;
ClawOS deletes the message file and retains only a non-secret completion
receipt. This survives shelf and compositor restarts. Reboot reconciliation is
explicit rather than automatic: a leftover handoff becomes a native Center
decision with Resume and Discard actions, and Resume warns that effects may be
repeated. Active transient requests are excluded from the interrupted list.

## Human interaction contract

- A visible `Ask Agent` control is available on supporting surfaces.
- Opening it preserves the surface and focuses the existing OpenClaw composer.
- `Close Agent` restores focus to the prior surface without ending either app.
- The activity breadcrumb remains a visible route back to the full Agent canvas.
- A visual Actions surface exposes Agent, Terminal, Build, Browser, Gmail,
  Outlook, screen reader, and an explicit close action with keyboard mnemonics.
- `Alt+Space` is an optional accelerator for Actions; it is not required.
- Fresh images include Orca, set `NO_AT_BRIDGE=0`, and expose a visible
  screen-reader toggle. Spoken output was process-tested in the VM; quality of
  speech, Braille, switch input, and physical audio remain hardware QA.

## Agent computer-use contract

Registered web applications may declare a loopback-only OpenClaw browser
profile. Gmail uses `clawos-gmail` on CDP port 9223; Outlook uses
`clawos-outlook` on 9224; the general ClawOS browser remains on 9222. OpenClaw
can snapshot, click, type, and continue work in the same visible web window by
using the returned `browserProfile` exactly. Human sign-in, passkeys, CAPTCHA,
and two-factor confirmation remain human-controlled.

Terminal and Build are controlled through typed exec and durable tmux sessions.
ClawOS does not yet claim arbitrary pixel control of native Linux applications.
That requires a future accessibility/input broker with typed targets, explicit
authority, audit receipts, and recovery boundaries. OpenClaw's documented Codex
Computer Use integration is macOS-specific and is not treated as a Linux proof.

## Runtime evidence

- `04-topbar-fixed.png`: visible Back, Ask Agent, and Actions routes on Gmail.
- `07-agent-overlay-final.png`: the live OpenClaw Control UI over Gmail with the
  concise `Back to Main · Gmail` context and a usable composer.
- `08-actions-final.png`: complete keyboard-focusable Actions surface at
  1440×900 with no clipped action.
- OpenClaw `browser --browser-profile clawos-gmail tabs --json` returned the
  visible Gmail page at the loopback DevTools endpoint.
- OpenClaw `browser --browser-profile clawos-gmail snapshot --format ai`
  returned Gmail's live accessible DOM.
- Starting the visible screen-reader action produced a live Orca process; the
  second invocation stopped it.
- `agent-shelf-gmail.png`: the native shelf resolves the registered Gmail
  activity and updates its prompt context without replacing the app.
- `agent-shelf-typed.png`: text entered into the real GTK shelf over Gmail.
- `agent-shelf-working.png`: the visual Send action submitted to
  `agent:main:main` and moved both shelf and top-bar activity to Working.
- The completed request was found in the durable OpenClaw main-session
  transcript; the shelf returned to Ready with no process log errors.
- `background-queue-live.png`: the hot-loaded shelf after its process was
  restarted independently of a queued request.
- `center-queue-live.png`: the completed CLI task in the native Center with no
  false attention from skipped heartbeat jobs.
- `center-recovery-live.png`: one simulated interrupted private request with
  explicit Resume and Discard actions in the live installed VM.

Evidence directory: `artifacts/m2/a11y-audit-2026-08-28/`
Command-shelf evidence: `artifacts/m1/runtime/agent-shelf-*.png`
Background-handoff evidence: `artifacts/m1/runtime/*queue-live.png`

## Visual findings for the next pass

1. The center bar has too many equal-weight pills and reads as app chrome.
2. The Actions sheet gives every capability equal weight, is visually heavy,
   and uses legacy Adwaita imagery rather than the prototype's restrained
   control hierarchy.
3. The Agent panel behaves correctly but arrives as a hard Chromium slab. It
   needs a ClawOS-native relationship to the current activity without forking
   or theming upstream Control UI internals.
4. The prototype's compact Agent tray is the stronger visual anchor: a small
   persistent status/prompt affordance can expand into the real Control UI only
   when needed.

The installed M3 audit found that “persistent” cannot mean “always visible”:
the shelf duplicated and covered OpenClaw's native composer on the Agent canvas.
The image source now recognizes `OpenClaw Control` and `ClawOS Setup` as owning
surfaces and hides the shelf there. It remains available over Gmail, Outlook,
browser, terminal, build, and registered applications. The approval client also
uses a runtime singleton lock so repeated Review actions focus one guarded
surface instead of tiling duplicates.

That reduction is now present in the image profile: one calm activity control
remains in the bar, in-context prompting lives in the compact native shelf, and
secondary Agent/machine actions are hierarchical popovers. The earlier side
panel, focus restoration, screen-reader, and browser-profile paths remain
available underneath it.
