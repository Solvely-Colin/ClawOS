# ClawOS Control UI integration QA

- Source visual truth: the installed upstream OpenClaw bundle at
  `/home/colin/.local/share/mise/installs/node/26.7.0/lib/node_modules/openclaw/dist/control-ui/`
- Browser evidence: `artifacts/screenshots/openclaw-control-ui-current.jpg`
- Viewport: 1280 × 720 CSS pixels, desktop, device scale factor 1
- State: upstream Gateway connection/auth surface

## Architecture result

ClawOS no longer implements or styles a parallel WebUI. After a narrow
local-versus-remote first-boot choice, the root-owned session delegates setup to
the pinned upstream OpenClaw wizard and opens that Gateway's actual Control UI.
This makes the OpenClaw bundle itself the OS surface and preserves upstream UI
updates by version pin rather than visual reimplementation.

## Findings

- No ClawOS-created visual divergence remains in the shell path.
- The local installed OpenClaw auth surface renders successfully in the in-app
  browser.
- An authenticated connected session rendered successfully in the in-app
  browser, including the upstream navigation, session list, chat composer,
  settings, and documentation surfaces.
- The pinned OpenClaw package, local Gateway service flow, remote configuration
  flow, and token bootstrap are now included in the installed image inputs.
- Installed QEMU interaction QA remains pending until the image is rebuilt and
  the development disk is reinstalled.

## Required fidelity surfaces

- Fonts and typography: owned entirely by the upstream Control UI bundle.
- Spacing and layout rhythm: owned entirely by the upstream Control UI bundle.
- Colors and visual tokens: owned entirely by the upstream Control UI bundle.
- Image quality and asset fidelity: upstream favicons, provider icons, and
  compiled assets are served without replacement.
- Copy and content: owned by the pinned upstream version and live Gateway data.

## Comparison history

- Removed the centered ClawOS launch card after it was identified as an app
  launcher rather than an OS surface.
- Removed the Carapace Sessions imitation after comparison showed it diverged
  from the actual OpenClaw Control UI.
- Replaced both with a direct upstream Gateway route and added a validation gate
  that rejects a parallel `usr/share/clawos-launch` surface.

final result: source-complete; installed QEMU proof pending
