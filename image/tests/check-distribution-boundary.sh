#!/usr/bin/env bash
set -euo pipefail

# These names are forbidden-input test data, never runtime dependencies.

root="${1:-}"
if [[ -z "$root" || ! -d "$root" ]]; then
  echo "Usage: $0 <mounted-clawos-root>" >&2
  exit 2
fi

for forbidden in \
  usr/share/omarchy \
  etc/omarchy \
  etc/pacman.d/omarchy \
  etc/chromium/policies/managed/omarchy.json; do
  if [[ -e "$root/$forbidden" || -L "$root/$forbidden" ]]; then
    echo "Foreign-distribution path detected: /$forbidden" >&2
    exit 1
  fi
done

matches="$(find "$root" -xdev -type f \
  \( -path '*/systemd/system/*' -o -path '*/systemd/user/*' -o \
     -path '*/chromium/policies/*' -o -path '*/pacman.d/*' \) \
  -print0 2>/dev/null | xargs -0 -r grep -IilE \
  'omarchy|omacom|basecamp/omarchy' || true)"
if [[ -n "$matches" ]]; then
  printf '%s\n' "$matches" >&2
  echo "Foreign-distribution reference found in an OS policy, service, or package source." >&2
  exit 1
fi

echo "Distribution boundary check passed."
