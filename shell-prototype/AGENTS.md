> **Prototype-only instructions.** The visual prototype is not the OS runtime; the installed shell lives under `image/profile-overlay`.

# Prototype Instructions

The prototype is frozen; [README.md](README.md) records its status, how to run it and which `image/` paths implement its ideas. To check a change, start the dev server with `npm run dev` and open the URL Vite prints in a browser.

When the user gives durable prototype-specific design feedback, preferences, or decisions, record them in `AGENTS.md`.

When implementing from a selected generated mock, treat that image as the source of truth for layout, component anatomy, density, spacing, color, typography, visible content, and hierarchy.

Build app UI in `src/`. The Sites handoff files (`.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`, `tests/sites-worker.test.mjs`) and the `build` and `test:sites` scripts that reference them are retained pending the owner decision recorded in README.md. Do not extend them. Dependency maintenance is covered by the `prototype` CI job: clean install, build, retained Sites tests, and Chromium rendering/Fast Refresh smoke tests. This does not make the prototype the installed OS runtime. Run browser tests in a dedicated checkout because the HMR test temporarily edits and restores `src/App.jsx`.

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
