# Milestone 0: historical host-side experiment

Milestone 0 was a 2026-08 spike that ran a reversible Sway/Chromium kiosk on
VT2 of the developer's existing Arch host. It showed that inheriting host
userspace violates the product boundary and was superseded by the clean
ArchISO, installer and native shell under [`image/`](../../image/README.md). Nothing
here ships in the image. Operator-specific milestone notes are kept locally.

The directory stays because `tests/static-check.sh` is a live negative test:
`image/bin/preflight-iso` runs it as stage 2/9 against `bin/`, `config/` and
`systemd/`, so those files cannot be removed without weakening the gate.

Do not run `bin/*` on a machine you use. `complete-host-install` installs
packages with `pacman`, then `install-m0` writes to `/etc/clawos`,
`/etc/chromium` and `/usr/lib/clawos` and registers a systemd unit. Both refuse
to run unless `CLAWOS_M0_EXPERIMENT=1` is set; use a disposable VM if you want
to reproduce the experiment:

    CLAWOS_M0_EXPERIMENT=1 ./experiments/host-session/bin/complete-host-install <owner-user>
