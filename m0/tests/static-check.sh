#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/../.." && pwd)"

bash -n "$root/m0/bin/clawos-session"
bash -n "$root/m0/bin/clawos-browser"
bash -n "$root/m0/bin/install-m0"
bash -n "$root/m0/bin/uninstall-m0"
bash -n "$root/m0/bin/pair-browser-profile"

grep -Fq 'sway -c /etc/clawos/sway.conf' "$root/m0/bin/clawos-session"
grep -Fq 'exec /usr/lib/chromium/chromium' "$root/m0/bin/clawos-browser"
if grep -Fq '/usr/bin/chromium' "$root/m0/bin/clawos-browser"; then
  echo "ClawOS browser must bypass the Omarchy Chromium wrapper." >&2
  exit 1
fi
grep -Fq 'DeveloperToolsAvailability' "$root/m0/config/chromium-policy.json"
grep -Fq 'ExtensionInstallBlocklist' "$root/m0/config/chromium-policy.json"
grep -Fq 'User=%i' "$root/m0/systemd/clawos-session@.service"
grep -Fq 'TTYPath=/dev/tty2' "$root/m0/systemd/clawos-session@.service"
grep -Fq 'ExecStartPre=+/usr/bin/chvt 2' "$root/m0/systemd/clawos-session@.service"
grep -Fq 'ExecStopPost=+/usr/bin/chvt 1' "$root/m0/systemd/clawos-session@.service"

if grep -R -n -E '(^|/)home/colin|~/.config/(sway|hypr)' \
  "$root/m0/bin" "$root/m0/config" "$root/m0/systemd"; then
  echo "Milestone 0 contains a user-specific or user-overridable config path." >&2
  exit 1
fi

echo "Milestone 0 static checks passed."
