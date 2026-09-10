# ClawOS interface system

ClawOS uses one visual language for native shell chrome, onboarding, recovery, and OpenClaw-adjacent surfaces. The interface is intentionally quiet: the current task stays dominant, while OS controls appear as compact overlays instead of permanent app-like sidebars.

## Principles

- The OpenClaw canvas is the primary work surface. Native OS UI frames it without duplicating its navigation.
- The `ClawOS` wordmark owns one compact system menu. It does not open a second sidebar.
- Agent actions begin with intent. The Actions control opens the centered intent palette; the shelf remains available above every app.
- Work, approvals, and recovery live in one centered System Center overlay with a dismissible scrim.
- Destructive actions are explicit, confirmed, and paired with a recovery path where one exists.

## Tokens

| Role | Value |
| --- | --- |
| Canvas | `#090b0b` |
| Panel | `#0b0d0d` |
| Surface | `#101312` |
| Raised | `#202121` |
| Line | `#292d2b` |
| Strong line | `#414643` |
| Primary text | `#f3f1ee` |
| Muted text | `#a5a19f` |
| Quiet text | `#747876` |
| Agent coral | `#ff684f` |
| Healthy green | `#35ce78` |
| Danger | `#ff5c5c` |

The canonical native GTK definitions live in `/etc/clawos/design-system.css`.

## Type and geometry

- UI: Inter Variable, Noto Sans fallback.
- Technical labels and state: GeistMono Nerd Font, Noto Sans Mono fallback.
- Boot-only surfaces may use Noto because they render before the full userspace font stack.
- System bar: 48 px (installed Waybar); the live installer top bar is 51 px. Controls: 38–44 px. Radius: 7 px controls, 9–10 px cards, 12–14 px overlays.
- System menu: 264 px, aligned 14 px from the left and 6 px below the bar.
- Agent shelf: up to 880 px wide, with a 24 px minimum side gutter on narrower outputs.
- System Center: up to 1040 × 740 px, responsively inset and centered over a full-screen scrim.

## Interaction rules

- Every core action must be reachable visually; hotkeys are accelerators, not the only path.
- Escape closes menus, palettes, and overlays. Clicking outside a transient menu dismisses it.
- Focus is indicated with coral, never by color removal alone.
- Use GTK symbolic icons or the licensed Radix assets already packaged by ClawOS. Do not use emoji, text glyphs, or approximate hand-drawn icons as controls.
- A surface may introduce its own product design—such as Gmail—but ClawOS chrome around it must use these tokens and behaviors.
