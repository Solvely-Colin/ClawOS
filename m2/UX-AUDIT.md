> **Historical record.** Describes design or state at that time, not current release acceptance. `artifacts/...` paths cited below were local, git-ignored build outputs and are not in this repository.

# ClawOS activity navigation audit

Date: 2026-08-28

## Scope

Combined UX and screenshot-level accessibility audit of the primary journey:
state intent in OpenClaw, enter a supporting machine surface, inspect or take
over, and return to the durable activity.

## User goal

Move around ClawOS without having to remember which layer owns navigation or
losing the active OpenClaw activity.

## Captured journey

1. **Agent canvas — usable, but navigation ownership is split.** OpenClaw has
   its own sidebar while the ClawOS bar independently represents the machine.
   The product does not yet explain which one changes sessions and which one
   changes machine surfaces.

   Evidence: `artifacts/m2/ux-audit-2026-08-28/02-return-agent.png`

2. **Intent palette — understandable choices, weak location awareness.** The
   palette is keyboard accessible and has a clear prompt, but “Continue with
   ClawOS” does not say whether it returns, opens, resumes, or creates work.
   Static app destinations compete with activity actions.

   Evidence: `artifacts/m2/ux-audit-2026-08-28/03-intent-palette.png`

3. **Gmail surface — task is visible, return path is invisible.** ClawOS keeps
   its native bar, but the bar still says only `Main · Ready`; it does not tell
   the user that Gmail is an attached surface or expose a visible way back.
   The user must know `Alt+A`.

   Evidence: `artifacts/m2/ux-audit-2026-08-28/04-gmail-surface.png`

4. **Return to agent — state is preserved.** Returning does not destroy the
   Gmail window or the OpenClaw session. This is the strongest part of the
   current stack model.

   Evidence: `artifacts/m2/ux-audit-2026-08-28/05-return-from-gmail.png`

5. **Terminal surface — spatial continuity is visibly broken.** Percentage
   sizing leaves part of the underlying Agent canvas visible at the bottom.
   It reads as a floating app placed on a web page rather than a machine mode.

   Evidence: `artifacts/m2/ux-audit-2026-08-28/06-terminal-surface.png`

## Highest-impact findings

1. There is no visible, consistent Back-to-activity action on supporting
   surfaces.
2. Surface location is omitted from the central activity control.
3. Human navigation and agent navigation use different pathways and state can
   lag when a hotkey is used directly.
4. Percentage-based floating geometry produces seams and exposed underlay.
5. The intent palette uses explanatory sentences where short action labels
   would scan more quickly.

## Accessibility risks

- Returning from a surface depends on memorizing an undisclosed shortcut.
- Focus changes are visually apparent, but the bar does not announce the
  location change in text.
- The palette supports keyboard operation, though screen-reader semantics,
  focus announcement, contrast ratios, zoom behavior, and reduced-motion
  behavior require runtime assistive-technology testing and cannot be proven
  from screenshots.

## Implemented response

- The activity pill becomes `← Main / Surface` while a supporting surface is
  visible and clicking it returns to the Agent canvas.
- Right-clicking the pill and `Alt+Space` always open the intent palette.
- `Alt+Escape` is a second explicit Back-to-activity shortcut; `Alt+A` remains
  compatible.
- Terminal, build, browser, and registered app surfaces are fitted to the
  exact current Sway workspace rectangle rather than `100 ppt`.
- Palette labels are shortened to direct actions: Talk, Open, Inspect, Browse,
  Review, and More applications.

## Evidence limits

This audit covers the installed proof VM at 1440×900. Physical display scaling,
touch, multiple monitors, screen-reader output, switch control, and long-lived
session restoration still need dedicated validation.

## Installed proof after changes

- Simplified intent palette:
  `artifacts/m2/ux-audit-2026-08-28/10-after-palette.png`
- Exact full-canvas terminal with visible `← Main / Terminal` breadcrumb:
  `artifacts/m2/ux-audit-2026-08-28/12-terminal-breadcrumb.png`
- Exact Gmail surface with visible `← Main / Gmail` breadcrumb:
  `artifacts/m2/ux-audit-2026-08-28/13-gmail-breadcrumb.png`
- Preserved OpenClaw state after invoking the activity return action:
  `artifacts/m2/ux-audit-2026-08-28/14-return-via-activity-action.png`

## Follow-on accessibility and copilot audit

The later in-context Agent proof fixed the functional gap: the same OpenClaw
conversation can open over Gmail and close back to Gmail, while a visual Actions
surface and Orca toggle remove mandatory shortcut knowledge. Dedicated browser
profiles also let OpenClaw interact with the same visible Gmail/Outlook page.

That proof is directionally correct but visually not accepted. The center bar
became crowded, the full-height Actions list is too heavy, and the Agent panel
reads as a hard browser slab. Preserve the behavior and replace the chrome with
the compact Agent tray and restrained hierarchy recorded in
`m2/ACCESSIBILITY-AND-COPILOT.md`.
