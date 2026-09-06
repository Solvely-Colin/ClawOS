# Prototype Instructions

Run the local server yourself and open the preview in the browser available to this environment. Do not give the user server-start instructions when you can run it.

Before making substantial visual changes, use the Product Design plugin's `get-context` skill when the visual source is unclear or no longer matches the current goal. When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. Keep `.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, and `tests/sites-worker.test.mjs` intact so the same local prototype can be handed to Sites. Before a Sites handoff, run `npm run build` and `npm run test:sites`; the build must leave `dist/client/index.html`, `dist/server/index.js`, and `dist/.openai/hosting.json`.

## ClawOS visual contract

- Treat Carapace as the OpenClaw-facing design language: compact controls, dark pane layouts, coral actions, readable state colors, and monospace system labels.
- Preserve ClawOS identity tokens: graphite canvas, `#ff684f` coral, `#f3f1ee` warm white, `#a5a19f` muted text, and `#35ce78` readiness green.
- The product must read as a machine session, not a kiosk: persistent system bar, workspaces, managed windows, agent activity, approvals, and recovery state remain visible around the upstream OpenClaw workbench.
- OpenClaw remains upstream and recognizable; ClawOS owns session orchestration and guarded machine actions.
- The top system bar is the sole workspace navigator. Do not add a duplicate side rail.
- Agent, Command, Build, and Browse are full desktop surfaces, not rounded app windows nested inside an OS mock.
- Browser and terminal chrome must stay in the graphite ClawOS palette; a stock bright browser surface breaks the OS illusion.

## Selected in-context agent direction

- The accepted visual target is the centered bottom command shelf shown in ImageGen option 3 on 2026-08-28.
- Applications keep the full canvas. The persistent shelf carries current-app context, Agent readiness, a one-line prompt, compact actions, and send/voice affordances.
- Agent work or approval state rises as a short status strip above the shelf. The full upstream OpenClaw conversation opens only on demand.
- Do not replace the shelf with a right-side panel, fixed workspace tabs, an application dock, or a large action sheet.
- Back and return controls must use the selected Radix icon family and ClawOS button tokens. Do not use text arrows, emoji, or stock desktop-theme navigation icons.
