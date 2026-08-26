#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
profile="${1:-$repo_root/m1/profile-overlay}"

source "$repo_root/m1/config/versions.env"

grep -Fqx 'SigLevel = Required DatabaseOptional' "$repo_root/m1/profile-overlay/pacman.conf"
if grep -RniE 'SigLevel[[:space:]]*=[[:space:]]*(Never|Optional)' \
  "$repo_root/m1/profile-overlay" "$repo_root/m1/config"; then
  echo "Weak package signature policy detected." >&2
  exit 1
fi

if grep -RniE 'omarchy|omacom|basecamp/omarchy' \
  "$repo_root/m1/profile-overlay" "$repo_root/m1/config"; then
  echo "Omarchy contamination detected in build inputs." >&2
  exit 1
fi

grep -Fqx "Server = https://archive.archlinux.org/repos/${ARCH_SNAPSHOT}/\$repo/os/\$arch" \
  "$repo_root/m1/config/mirrorlist"

for package in base linux linux-firmware networkmanager openssh; do
  grep -Fqx "$package" "$repo_root/m1/profile-overlay/packages.x86_64"
done

if [[ -d "$profile/airootfs" ]]; then
  "$repo_root/m1/tests/no-omarchy.sh" "$profile/airootfs"
fi

echo "Milestone 1 profile validation passed."
