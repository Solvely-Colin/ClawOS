# Shell prototype

`shell-prototype/` is a frozen Vite/React visual prototype of the ClawOS
desktop: a top system bar with a system menu, a full-canvas mock Gmail
surface, the centered bottom command shelf with an agent status strip, and an
on-demand OpenClaw conversation panel. Its last design QA was
dated 2026-08-28; operator screenshots and QA notes remain local. It has not been
developed since beyond dependency maintenance. It is not the installed OS
runtime. The `prototype` CI job now installs its locked dependencies, builds,
runs the retained Sites tests, and checks development/production rendering,
conversation controls and React Fast Refresh in Chromium. This is dependency
regression coverage, not renewed product development or installed-OS proof.

The installed shell that grew out of these ideas lives under
`image/profile-overlay/airootfs/`:

| Prototype idea | Installed implementation |
| --- | --- |
| Top system bar and system menu | `etc/clawos/waybar/config.jsonc`, `etc/clawos/waybar/style.css`, `usr/lib/clawos/clawos-system-menu`, `etc/clawos/system-menu.css` |
| Bottom command shelf and status strip | `usr/lib/clawos/clawos-agent-shelf`, `etc/clawos/agent-shelf.css` |
| On-demand OpenClaw conversation | `usr/lib/clawos/clawos-agent-window` |
| Full-canvas application surfaces (the Gmail mock) | `usr/share/applications/clawos-gmail.desktop` and the other launchers there; `usr/lib/clawos/clawos-browse`, `clawos-command`, `clawos-build`; see [architecture](../docs/ARCHITECTURE.md) |
| Graphite and coral tokens | `etc/clawos/design-system.css`; rationale in [`docs/DESIGN-SYSTEM.md`](../docs/DESIGN-SYSTEM.md) |
| Workspaces and window management | `etc/clawos/sway.conf` |

## Running it

Needs Node 24 or newer. Dependencies are installed with npm, not vendored:

```sh
cd shell-prototype
npm ci
npm run dev
```

Vite prints the local URL. `vite.config.mjs` sets `server.host` to `0.0.0.0`,
so the dev server listens on every interface of the machine, not only
localhost.

To run the dependency gate locally after `npm ci`:

```sh
npm run build
npm run test:sites
npx playwright install chromium
npm run test:browser
```

The browser tests start loopback-only dev and preview servers. The Fast Refresh
test temporarily edits `src/App.jsx` and restores it in `finally`; use a clean,
dedicated checkout and do not edit that file concurrently. CI checks for drift.
React/React DOM and Vite/React-plugin updates are grouped in Dependabot so each
compatible pair can be reviewed and landed atomically.

## External assets

The mock Gmail surface hotlinks Google's Gmail logo and favicon from
`ssl.gstatic.com`, and `src/styles.css` loads Inter and Geist Mono from Google
Fonts at run time. Those assets are Google's and are not redistributed here;
see [NOTICE.md](../NOTICE.md). Running the prototype therefore makes requests
to Google.

## "Sites" handoff files (owner decision pending)

`.openai/hosting.json`, `worker/index.js`, `scripts/prepare-sites-build.mjs`
and `tests/sites-worker.test.mjs` are not part of the prototype's UI. "Sites"
is the app-hosting handoff of OpenAI's Codex agent environment, in which the
prototype was written; that is why its manifest lives under `.openai/`. The
worker uses the Cloudflare Workers static-assets binding (`env.ASSETS.fetch`),
and the manifest's `d1` and `r2` entries, Cloudflare's database and
object-storage bindings, are `null` because the prototype needs neither.

`prepare-sites-build.mjs` copies the worker and manifest into `dist/` after
`vite build`, `worker/index.js` serves `index.html` for unknown HTML routes,
and `test:sites` unit-tests that worker and then checks that the built files
exist, so it fails until `npm run build` has run. The `build` and `test:sites`
scripts in `package.json` reference them.

They are a deployment artifact, not ClawOS. Whether to keep them or delete
them together with those two `package.json` script references is an owner
decision that has not been made (issue #50). Until it is, they stay as they
are and are not to be extended; `AGENTS.md` says the same.

## Agent instructions

`AGENTS.md` in this directory holds instructions for coding agents that edit
the prototype. As the repository's root `AGENTS.md` says, subdirectory
guidance is not the installed runtime contract.
