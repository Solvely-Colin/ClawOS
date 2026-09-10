# Third-party notices and provenance

ClawOS source code in this repository is licensed under the MIT License (see
[LICENSE](LICENSE)), except for the files listed under "Files under other
licenses" below, which the MIT grant does not cover. Third-party projects keep
their own licenses and copyright; nothing here relicenses them. This file
records what is copied into the repository, what the built ISO and installed
systems redistribute, and where provenance is unknown.

## Files under other licenses (not MIT)

### Derived from archiso (GPL-3.0-or-later)

`m1/bin/materialize-profile` copies the `releng` profile from the installed
`archiso` package (pinned in `m1/config/versions.env`) at build time and
overlays `m1/profile-overlay/`. The following overlay files were copied from
archiso's `configs/releng` and modified by ClawOS, first on 2026-08-26. They
remain under GPL-3.0-or-later and each carries a header saying so:

- `m1/profile-overlay/profiledef.sh`
- `m1/profile-overlay/pacman.conf` (archiso's copy of pacman's stock
  `pacman.conf`; pacman is GPL-2.0-or-later)
- `m1/profile-overlay/packages.x86_64` (ClawOS's own package selection in
  archiso's file format, scaffolded from the releng list)
- `m1/profile-overlay/efiboot/loader/entries/01-archiso-linux.conf`
- `m1/profile-overlay/efiboot/loader/entries/02-archiso-speech-linux.conf`

archiso: https://gitlab.archlinux.org/archlinux/archiso, copyright the Arch
Linux archiso contributors. The license text is in
`LICENSES/GPL-3.0-or-later.txt`.

### Plymouth theme script (GPL-2.0-or-later)

`m1/profile-overlay/airootfs/usr/share/plymouth/themes/clawos/clawos.script`
contains a password-bullet loop adapted from Plymouth's example theme
`themes/script/script.script` (Plymouth, GPL-2.0-or-later,
https://www.freedesktop.org/wiki/Software/Plymouth/). The file carries an
SPDX header and stays under GPL-2.0-or-later; the license text is in
`LICENSES/GPL-2.0-or-later.txt`.

### Radix Icons (MIT, Copyright (c) 2022 WorkOS)

The following files are Radix Icons (https://github.com/radix-ui/icons, from
`@radix-ui/react-icons` 1.3.x) with the fill color changed:

- `m1/profile-overlay/airootfs/usr/share/clawos/icons/arrow-left.svg` (Radix `arrow-left`)
- `m1/profile-overlay/airootfs/usr/share/clawos/icons/reload.svg` (Radix `reload`)
- `m1/profile-overlay/airootfs/usr/share/clawos/theme/clawos-pin.svg` (Radix `sewing-pin-filled`)
- `m1/profile-overlay/airootfs/usr/share/clawos/theme/clawos-pin.png` (raster of the file above)

The license text ships at
`m1/profile-overlay/airootfs/usr/share/licenses/clawos-radix-icons/LICENSE`
and is installed at `/usr/share/licenses/clawos-radix-icons/LICENSE`. No
separately drawn ClawOS logo exists; the "ClawOS" wordmark is rendered text.
The installer explicitly copies this license alongside the custom icon tree;
profile validation and the installed-system test check its presence.

## Artwork and images

Origins recorded below come from embedded C2PA manifests, retained generation
and design records, and Git history. Working prompts and screenshot QA diaries
are kept locally; the public provenance conclusions remain here. Where no
record exists, this file says so.

- `m1/profile-overlay/airootfs/usr/share/clawos/theme/background.png`,
  `m1/profile-overlay/airootfs/usr/share/plymouth/themes/clawos/background.png`
  and `shell-prototype/public/assets/clawos-background.png` are one identical
  1487x1058 image (halftone "claw" texture on graphite). Its embedded C2PA
  manifest records generation on 2026-08-26 by OpenAI's image model
  (softwareAgent "gpt-image" 2.0, "trainedAlgorithmicMedia", watermarked),
  signed by "OpenAI Media Service API". The prompt is unrecorded, and whether
  the file was cropped or edited after generation is unverified. It is the
  desktop wallpaper, lock-screen and boot-splash background, the live-welcome
  raster and the prototype background.
- `docs/assets/clawos-header.png` (2172x724) was generated on 2026-09-06 with
  the same OpenAI image model (C2PA manifest present); the prompt is recorded
  in a retained local generation record. It is branding artwork, not a screenshot.
- `docs/assets/hardware-installer-preview.png` (1440x900) is a screenshot of
  the ClawOS GTK installer preview with synthetic disk data, added 2026-09-06.
  The capture tool is unrecorded. The source-publication review on 2026-09-10
  retained this explicit unknown: the visible content is the project's installer
  with a disk labelled "Synthetic NVMe disk", not evidence of a physical install.
  No third-party photograph or desktop application content is visible. The
  background and Radix-derived mark are covered above; the missing capture-tool
  name does not establish an additional artwork source.
- Design mock-ups referenced in retained local design QA as
  "source visual truth" were AI-generated
  images stored outside this repository; they are not included.

Copyright in AI-generated images is uncertain in many jurisdictions. ClawOS
claims no rights in these images beyond those the generation service's terms
grant to the user, and to the extent it holds any, releases them under the
same MIT License as the rest of the repository. They are not trademarks and
are not endorsed by OpenAI.

## Design language

Carapace (https://carapace.design, https://github.com/openclaw/carapace; MIT,
Copyright (c) 2026 openclaw) is the OpenClaw project's design system, not a
ClawOS project. `m1/profile-overlay/airootfs/etc/clawos/design-system.css`
adapts its color roles for GTK; no Carapace source files are copied. Other
ClawOS token values (`m2/DESIGN-SYSTEM.md`, `shell-prototype/src/styles.css`)
are ClawOS's own.

## Fonts

No font files are stored in this repository. The image installs, from Arch
Linux repositories: Inter (`inter-font`, SIL OFL 1.1 with Reserved Font Name),
Noto Sans / Noto Sans Mono (`noto-fonts`, SIL OFL 1.1), and Geist Mono
(`otf-geist-mono-nerd`, Vercel's Geist Mono under SIL OFL 1.1, patched with
Nerd Fonts glyph sets that carry their own licenses; see the package's license
files). `shell-prototype` loads Inter and Geist Mono from Google Fonts at run
time and does not redistribute them.

## OpenClaw

OpenClaw (https://github.com/openclaw/openclaw; MIT, Copyright (c) 2026
OpenClaw Foundation) is not vendored in this repository. `m1/bin/build-iso`
installs the version pinned in `m1/config/versions.env` into the ISO with
`npm install --global`, and the installer copies that tree from the live ISO
to the target. Every ClawOS ISO and installed system therefore contains
OpenClaw and its complete npm dependency closure under
`/usr/lib/node_modules/openclaw` (including, among many others,
`@anthropic-ai/sdk`, `@google/genai`, `openai`, `express`, `playwright-core`,
`tree-sitter-bash`, `typescript`, `ws`, `zod`). Each package's license file is
kept inside its own directory in that tree; a generated license manifest for
that tree is not yet produced at build time.

`m2/openclaw-plugin` (`@clawos/openclaw-system`) is ClawOS code under MIT; it
declares an optional peer dependency on OpenClaw and installs no third-party
packages.

## Arch Linux packages in the built image

Every other component of the live ISO and the installed system is an
unmodified Arch Linux package fetched at build or install time from the Arch
Linux Archive snapshot pinned in `m1/config/versions.env` and
`m1/config/mirrorlist`, as listed in `m1/profile-overlay/packages.x86_64`
(live image) and
`m1/profile-overlay/airootfs/usr/lib/clawos/clawos-install-packages.sh`
(installed target). The ISO contains its package list at
`arch/pkglist.x86_64.txt`; release builds also record the build container's
package list in `BUILD-PACKAGES.txt`. License texts are installed under
`/usr/share/licenses/` on the image. The main components and their declared
licenses:

- archiso releng airootfs content copied into the live image at build time
  (for example `/root/.automated_script.sh`, `/root/.zlogin`,
  `/usr/local/bin/choose-mirror`, `/usr/local/bin/Installation_guide`,
  `/usr/local/bin/livecd-sound`, `/etc/motd`,
  `/etc/mkinitcpio.conf.d/archiso.conf`, the tty1 root autologin drop-in,
  networkd and reflector configuration, `efiboot/loader/loader.conf`):
  GPL-3.0-or-later
- mkinitcpio-archiso: GPL-3.0-or-later; mkinitcpio: GPL-2.0-only
- Linux kernel: GPL-2.0-only WITH Linux-syscall-note; linux-firmware,
  intel-ucode, amd-ucode: redistributable firmware licenses recorded in each
  package
- systemd: LGPL-2.1-or-later; pacman: GPL-2.0-or-later; glibc: LGPL-2.1-or-later
- Plymouth: GPL-2.0-or-later
- Sway, swaybg, swayidle, Waybar, foot, fuzzel, Mesa: MIT
- gtklock and gtklock-userinfo-module: GPL-3.0-only; gtk-layer-shell:
  LGPL-3.0-or-later; GTK 3, python-gobject, polkit, lxqt-policykit, Orca: LGPL
- Chromium: BSD-3-Clause plus the licenses of its bundled third-party code
- Node.js: MIT (plus bundled dependencies); npm: Artistic-2.0
- NetworkManager, iwd, openssh, cryptsetup, btrfs-progs, tmux, zsh, tailscale
  (installed target only): see the package license fields

Arch Linux publishes the corresponding source for its packages at
https://gitlab.archlinux.org/archlinux/packaging/packages/, and the pinned
snapshot identifies the exact package versions used. ClawOS relies on that
public source for the GPL components it redistributes in ISO images and
records the snapshot in every build's `BUILD-METADATA.txt`.

## Build and host tools (not redistributed)

QEMU, edk2-ovmf (OVMF), Docker's `archlinux:base-devel` image, GitHub Actions,
ShellCheck, and the Windows QEMU helper scripts in `tools/windows/` are used
on build or host machines only. Nothing from them is copied into this
repository or the image. `m0/` is a retained historical experiment that ran
on a host machine; it ships nothing.

## shell-prototype

`shell-prototype/` is a separate visual prototype. Its dependencies (React,
react-dom, Vite, @vitejs/plugin-react, @radix-ui/react-icons, all MIT) are
installed with npm and not vendored. `src/App.jsx` and `src/styles.css`
hotlink Google's Gmail logo and favicon from ssl.gstatic.com for a mock Gmail
surface; those assets are Google's and are not redistributed here. Mock
message content uses fictional text and mentions third-party product names
only as placeholder content.

The development/test dependency `@playwright/test` and its `playwright` and
`playwright-core` dependencies are Apache-2.0 (Microsoft;
https://github.com/microsoft/playwright/blob/main/LICENSE). Downloaded Chromium
test binaries are not tracked or shipped in the ClawOS source repository.

The pinned prototype lockfile also records these non-MIT transitive packages:
`detect-libc` (Apache-2.0), `lightningcss` and its platform binaries (MPL-2.0),
`picocolors` (ISC), and `source-map-js` (BSD-3-Clause). These are installed with
npm, not copied into this source tree. Vite's MIT license does not relicense
its dependencies. Preserve the installed package license/notice files when
redistributing a dependency tree; a prototype bundle or ISO distribution needs
its own artifact-level review.

## Source-publication review boundary (2026-09-10)

The tracked source inventory was checked against the copied-file headers,
shipped license texts, nine tracked image/icon files, and the prototype
lockfile. No font binaries or vendored npm tree are tracked. The three wallpaper
paths have the same Git blob; source/header records for the generated artwork
and the explicitly unknown screenshot capture tool are retained above. This
records the source inventory and known provenance, not a legal certification
or a claim to have verified every package inside an ISO. The OpenClaw license
manifest/SBOM and artifact-level distribution review remain release follow-ups.

## Trademarks

Arch Linux, OpenClaw, Carapace, Chromium, Gmail and Google, Outlook and
Microsoft, Tailscale, and other names used here are trademarks of their
respective owners. ClawOS is an independent project and is not affiliated
with or endorsed by any of them, including the OpenClaw project whose runtime
it builds on. The Gmail and Outlook web-app launchers in
`m1/profile-overlay/airootfs/usr/share/applications/` use those names to
identify the sites they open and use generic system icons.
