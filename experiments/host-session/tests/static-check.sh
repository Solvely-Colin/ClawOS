#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/../../.." && pwd)"

bash -n "$root/experiments/host-session/bin/clawos-session"
bash -n "$root/experiments/host-session/bin/clawos-browser"
bash -n "$root/experiments/host-session/bin/install-m0"
bash -n "$root/experiments/host-session/bin/uninstall-m0"
bash -n "$root/experiments/host-session/bin/pair-browser-profile"

grep -Fq 'sway -c /etc/clawos/sway.conf' "$root/experiments/host-session/bin/clawos-session"
grep -Fq 'exec /usr/lib/chromium/chromium' "$root/experiments/host-session/bin/clawos-browser"
if grep -Fq '/usr/bin/chromium' "$root/experiments/host-session/bin/clawos-browser"; then
  echo "ClawOS browser must invoke the packaged Chromium binary directly." >&2
  exit 1
fi
grep -Fq 'DeveloperToolsAvailability' "$root/experiments/host-session/config/chromium-policy.json"
grep -Fq 'ExtensionInstallBlocklist' "$root/experiments/host-session/config/chromium-policy.json"
grep -Fq 'ExtensionInstallAllowlist' "$root/experiments/host-session/config/chromium-policy.json"
grep -Fq 'User=%i' "$root/experiments/host-session/systemd/clawos-session@.service"
grep -Fq 'TTYPath=/dev/tty2' "$root/experiments/host-session/systemd/clawos-session@.service"
grep -Fq 'ExecStartPre=+/usr/bin/chvt 2' "$root/experiments/host-session/systemd/clawos-session@.service"
grep -Fq 'ExecStopPost=+/usr/bin/chvt 1' "$root/experiments/host-session/systemd/clawos-session@.service"

if grep -R -n -E '(^|/)home/colin|~/.config/(sway|hypr)' \
  "$root/experiments/host-session/bin" "$root/experiments/host-session/config" "$root/experiments/host-session/systemd"; then
  echo "Milestone 0 contains a user-specific or user-overridable config path." >&2
  exit 1
fi

echo "Milestone 0 static checks passed."
