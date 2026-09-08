> **Historical record.** Describes design or state at that time, not current release acceptance. `artifacts/...` paths cited below were local, git-ignored build outputs and are not in this repository.

# ClawOS Activity Shell

## Decision

ClawOS is organized around work, not applications. OpenClaw owns the agent,
sessions, tasks, delegation, and conversation state. ClawOS owns the machine
surfaces, approvals, recovery points, and window placement needed to complete
that work.

The four fixed `Agent`, `Command`, `Build`, and `Browse` destinations were a
useful compositor proof. They are not the product information architecture.

## User model

An **activity** is a durable piece of work such as “ship the Solvely release” or
“repair the OpenClaw node.” It has:

- one owning OpenClaw session and agent;
- optional delegated runs and remote nodes;
- attached surfaces such as terminal, browser, files, review, logs, or preview;
- pending approvals and attention requests;
- machine actions, audit receipts, and recovery points;
- a lifecycle: running, waiting, needs approval, needs attention, complete,
  failed, or rolled back.

A **surface** is only a view or control used by an activity. It is not a top-level
OS destination. Agent tools run in the background by default. When the user
chooses to inspect or take over one, that surface temporarily covers the activity
canvas; returning to the agent moves it back to a hidden surface layer and
restores OpenClaw at full size. Surfaces never force a split or compositor tab.
They can be closed without ending the activity, and
terminal processes survive through tmux even when their visible surface closes.

## Shell contract

The persistent shell contains:

1. The ClawOS wordmark, which opens machine and power controls.
2. The current activity, owning agent, and lifecycle state.
3. A global approval/attention indicator.
4. Gateway and node health.
5. Time and physical-machine state.

OpenClaw fills the activity canvas. Sway is an implementation detail that places
and focuses surfaces. There is no permanent Terminal, Browser, Build, System,
or application navigation in the native panel. On the Agent canvas, clicking
the activity control opens an intent palette for talking, review, inspection,
browsing, and human takeover. On an attached surface, the same control becomes
the Radix-arrow **Back to Activity · Surface** button and clicking it returns
to the Agent canvas. Standard
Linux applications and registered web apps live behind the typed capability
registry; full application search is a secondary action.

While a supporting surface is visible, the user can open the existing
OpenClaw Control UI as an in-context Agent panel, continue prompting the same
session, and dismiss it back to the exact prior surface. This is a transient
view of the activity, not a split workspace or second assistant. Web surfaces
may report a dedicated browser profile so OpenClaw can inspect and interact
with the same visible window after presenting it.

The initial implementation has one `Main` activity. OpenClaw can project its
state and present or hide Terminal, Browser, and Build through the typed
`clawos_activity` and `clawos_surface` tools. Direct-human shortcuts remain as
optional takeover controls: `Alt+Enter` reveals Terminal, `Alt+B` Browser,
`Alt+Shift+B` Build, `Alt+A` and `Alt+Escape` return to the agent, and `Alt+Q`
closes the visible surface without ending its durable process. They are not the
primary workflow.

## OpenClaw boundary

ClawOS must not duplicate OpenClaw session or task state. An adapter reads the
active OpenClaw session/run and projects the minimum shell state:

```text
activity id
title
owning agent
run/delegation state
attention state
attached ClawOS surface ids
target node ids
```

The adapter stores only projection and correlation data. OpenClaw remains the
source of truth. If the Gateway is unavailable, the last projection is shown as
offline and recovery remains usable.

ClawOS-specific machine actions go through `clawosd`. Each action receipt is
correlated to the OpenClaw execution when authoritative identity is available,
but an activity id is never treated as authorization.

## Implementation stages

### A. Single-activity shell — implemented proof

- Replace fixed app workspaces with one `Main` activity canvas.
- Stop pre-launching terminal, build, and browser windows.
- Launch and focus them on demand as attached full-canvas surfaces.
- Show activity/surface context in the native panel.
- Preserve the upstream Control UI and existing recovery path.

### B. Gateway activity projection

- The supported OpenClaw plugin seam now exposes narrow activity and surface
  tools; a same-user broker maintains the shell projection over a mode-0600 Unix
  socket and state file.
- Typed OpenClaw lifecycle hooks automatically drive running/completion state,
  owning-agent metadata, delegated-run counts, failures, and attention without
  requiring a model-authored tool call. The plugin deliberately discards all
  conversation content supplied alongside the completion event.
- Explicit agent tools add richer human-readable activity context and surface
  requests without becoming required for lifecycle correctness.
- Persist the minimal projection and restore interrupted work as waiting after
  shell restart; the Agent canvas remains the authoritative restored surface.

### C. Activity and surface lifecycle

- Create/switch/finish activities through supported OpenClaw operations.
- Associate Sway containers, tmux sessions, browser contexts, previews, and
  remote-node views with an activity id.
- Extend the implemented typed local API from the single activity to multiple
  durable activities and richer surface metadata.
- Discover freedesktop applications and ClawOS web-app definitions through one
  validated registry shared by the human palette and OpenClaw tools.
- Launch, focus, hide, and close application windows as activity-owned surfaces;
  application identifiers never become arbitrary executable input.
- Give the user take-over and return-to-agent controls without changing task
  ownership.
- Read upstream `openclaw tasks` as the durable-work source of truth and expose
  active, failed, and recently completed work through the native Center without
  creating a parallel ClawOS task store.
- Hand native shelf prompts to a collected user service through private
  mode-0600 message files. The shelf can restart without cancelling work;
  OpenClaw remains the lifecycle authority and ClawOS keeps only a non-secret
  handoff receipt.
- Reconcile an orphaned handoff after session restart as an explicit Center
  decision. Never auto-replay ambiguous work: Resume warns about duplicate
  effects, Discard records the decision, and currently active services never
  appear as interrupted.

### D. Approvals and recovery

- Show one global native ClawOS Center in the shell. It combines OpenClaw's
  pending approvals and durable task history with `clawosd` machine approvals,
  while each decision remains owned and recorded by its source subsystem.
- Derive the top-bar attention and working states from concrete upstream tasks,
  OpenClaw approvals, and broker requests; acknowledging terminal results is
  stored as private shell projection only.
- Bind privileged action preparation, approval, execution, and recovery receipt
  to the activity timeline.
- Create a Btrfs recovery point before destructive system transactions.
- Make resume, retry, rollback, and abandon explicit lifecycle transitions.

### E. Visual and assistive interaction — directional proof

- Large visible Back, Agent, Actions, and screen-reader routes are runtime
  proven without requiring hotkey knowledge.
- The same Control UI session is proven as a dismissible panel over Gmail with
  focus restoration.
- Gmail's dedicated browser profile is proven through live tabs and accessible
  snapshot output.
- The current large action sheet and multi-pill bar are not visually accepted;
  replace them with the prototype-aligned compact Agent tray and hierarchical
  control surface while preserving the proven semantics.

## Acceptance criteria

- A fresh boot lands in work, not an application launcher or browser kiosk.
- The user can ask the agent to perform work without manually opening tools.
- Agent-opened terminal and browser tools can run without occupying the screen;
  their surfaces can be inspected, controlled, or closed on demand.
- Closing a visible surface does not lose its durable process or activity state.
- A blocked activity tells the user what needs approval or attention.
- Gateway failure does not remove machine controls, rollback, or tty recovery.
