# Task-owned supporting windows

Ask the Agent in a conversation to open a terminal, build workspace, or browser.
The OpenClaw tool factory supplies that conversation's session key. The model
does not choose a destination session in its tool arguments.

Each task has its own window IDs, terminal/build tmux sessions, and Chromium
profile. Reopening a surface reuses that task's window. Keyboard shortcuts use
the focused window's task, or offer an explicit choice among registered tasks.
Before any tasks are registered, start by asking the Agent to open a surface.

The browser composer displays the destination task. Drafts are private files
per task and survive switching windows and restarting the desktop. A draft
clears only after its request is queued successfully. The queue records the
session key beside the private message file, so later execution and resume
use the original destination. Requests with missing or invalid ownership are
retained and refused; older unbound requests are never redirected to Main.
Failed requests remain available in Work and decisions for explicit retry or
discard. Retry can repeat an operation if the previous result was uncertain.

From a task window, **Open task conversation** opens OpenClaw's own terminal
conversation UI with `--session` set to its owner. It preserves the conversation
and draft currently displayed in the main graphical Agent view. The terminal
conversation also lives in a task-specific tmux session. Returning to Agent
focuses the existing main graphical view.

In a task terminal, `CLAWOS_SESSION_KEY` identifies the conversation. The native
submission helper reads a message on stdin and uses that key. Generic app
windows without task ownership cannot submit through the shelf composer.

Each task browser has a separate loopback debugging port. Its returned
`browserProfilePath` contains Chromium's `DevToolsActivePort`; the old shared
`clawos-browser` profile at port 9222 does not identify these task browsers.
Automatic registration of these dynamic profiles in OpenClaw's browser tool
is not implemented. The dedicated mail application profiles are unchanged.

Task identity routes work between conversations of the same trusted OS user;
it does not isolate mutually untrusted agents or user accounts.

## Verification

Linux regression tests queue two tasks concurrently and execute them in reverse
order, asserting the exact session key/message pair at the OpenClaw invocation.
They also cover missing ownership, retained failed messages, separate drafts,
late acknowledgements, saved task restoration, and stale compositor takeover.
The queue test uses a stand-in OpenClaw process and makes no inference claim.

The 2026-09-19 checkpointed WHPX runtime test opened terminal, build, browser,
and native conversation windows for two task keys. Eight distinct windows,
separate tmux environments, exact TUI session arguments and independent browser
debugging ports were checked. This is runtime evidence; no new ISO was built.
