# ClawOS Control UI integration QA

- Source visual truth: the installed upstream OpenClaw bundle at
  `/home/colin/.local/share/mise/installs/node/26.7.0/lib/node_modules/openclaw/dist/control-ui/`
- Browser evidence: `artifacts/screenshots/openclaw-control-ui-current.jpg`
- Viewport: 1280 × 720 CSS pixels, desktop, device scale factor 1
- State: upstream Gateway connection/auth surface

## Architecture result

ClawOS no longer implements or styles a parallel WebUI. The root-owned kiosk
launcher opens `CLAWOS_GATEWAY_URL`, defaulting to the upstream Gateway at
`http://127.0.0.1:18789/`. This makes the OpenClaw Control UI bundle itself the
OS surface and preserves upstream UI updates by version pin rather than visual
reimplementation.

## Findings

- No ClawOS-created visual divergence remains in the shell path.
- The local installed OpenClaw auth surface renders successfully in the in-app
  browser.
- Full connected-session visual and interaction QA is blocked because the
  current browser profile is not authenticated to the local Gateway.
- Installed QEMU proof is blocked until the pinned OpenClaw package and Gateway
  service are included in the image.

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

final result: blocked
