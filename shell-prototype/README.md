# Shell prototype

`shell-prototype/` is a frozen Vite/React visual prototype of the ClawOS
desktop: a top system bar with a system menu, a full-canvas mock Gmail
surface, the centered bottom command shelf with an agent status strip, and an
on-demand OpenClaw conversation panel. Its last design QA is
[`design-qa.md`](design-qa.md), dated 2026-08-28, and it has not been
developed since. It is not the installed OS runtime, and nothing in CI
installs, builds or tests it. Treat it as unmaintained: `npm run build` and
`npm run test:sites` may no longer work.

The installed shell that grew out of these ideas lives under
`m1/profile-overlay/airootfs/`:

| Prototype idea | Installed implementation |
| --- | --- |
| Top system bar and system menu | `etc/clawos/waybar/config.jsonc`, `etc/clawos/waybar/style.css`, `usr/lib/clawos/clawos-system-menu`, `etc/clawos/system-menu.css` |
| Bottom command shelf and status strip | `usr/lib/clawos/clawos-agent-shelf`, `etc/clawos/agent-shelf.css` |
| On-demand OpenClaw conversation | `usr/lib/clawos/clawos-agent-window` |
| Full-canvas application surfaces (the Gmail mock) | `usr/share/applications/clawos-gmail.desktop` and the other launchers there; `usr/lib/clawos/clawos-browse`, `clawos-command`, `clawos-build`; see [`m2/APPLICATION-SURFACES.md`](../m2/APPLICATION-SURFACES.md) |
| Graphite and coral tokens | `etc/clawos/design-system.css`; rationale in [`m2/DESIGN-SYSTEM.md`](../m2/DESIGN-SYSTEM.md) |
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
