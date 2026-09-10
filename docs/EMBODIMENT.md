> **Historical record.** Describes design or state at that time, not current release acceptance. `artifacts/...` paths cited below were local, git-ignored build outputs and are not in this repository.

# ClawOS Embodiment

## Problem

Installing OS tools is insufficient if OpenClaw still reasons as though it were
a headless server. A forced test that names `clawos_app` proves only tool
execution, not an agent-native operating system. ClawOS needs a stable machine
identity and capability-routing contract on every agent turn.

## Runtime contract

The external `clawos-system` plugin uses OpenClaw's supported
`before_prompt_build` hook. It appends static system context that establishes:

- the agent inhabits the visible ClawOS graphical machine;
- OpenClaw owns activities and applications are supporting surfaces;
- explicit open/show/launch requests use `clawos_app`, never raw GUI commands;
- unattended work prefers connectors, APIs, CLI, or headless automation;
- visible applications are for sign-in, review, judgment, and takeover.
- visible web applications report an exact `browserProfile` when OpenClaw can
  inspect and interact with that same window through its browser tool;
- terminal and build work remain typed exec/tmux control, while arbitrary
  native Linux pixel control is explicitly not claimed.

The hook runs for new and existing sessions. It does not persist or log prompts.
For an explicit presentation verb, it asks the same-user broker for the sanitized
application registry and resolves a conservatively matched application name to
one validated id. Only that id is added as per-turn context; arbitrary desktop
metadata is never injected into the prompt.

## Shell command guard

The plugin's `before_tool_call` hook blocks direct graphical launches through
`exec`, including Chromium, Firefox, `xdg-open`, and `gio launch`. This preserves
activity ownership, window lifecycle, and auditability. Diagnostics such as
`which chromium` remain allowed, and non-graphical shell work is unaffected.

## Human contract

The primary palette asks **What do you want to do?** It offers activity actions,
not an app grid. “Open another installed application…” is deliberately last and
opens the registry-backed application search as a secondary escape hatch.

The top panel shows current work and lifecycle, for example `Main · Ready` or
`Release · Working`. While a supporting surface is visible it becomes a spatial
breadcrumb such as `← Main / Gmail`; clicking it returns to the activity. The
surface is always subordinate to, and never replaces, the activity's identity.

The same Control UI conversation can also be opened temporarily over a
supporting surface. The user can continue directing the agent while keeping the
app spatially present, then dismiss the panel and resume direct control. This
does not create a parallel ClawOS chat implementation.

## Acceptance proof

The installed VM's `agent:main:main` route received only `open gmail`. Ollama
Cloud MiniMax made one `clawos_app` call with zero failures, presented the
registered Gmail surface, and replied that Gmail was visible locally. It did not
use `exec`, claim the system was headless, ask for an app id, or redirect the
user to another device.
