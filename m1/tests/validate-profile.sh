#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
profile="${1:-$repo_root/m1/profile-overlay}"

source "$repo_root/m1/config/versions.env"

grep -Fq 'materialize-profile" "$profile"' "$repo_root/m1/bin/build-iso"
grep -Fq 'find "$generated_dir" -depth -delete' "$repo_root/m1/bin/build-iso"

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

for package in base linux linux-firmware mkinitcpio-archiso networkmanager openssh syslinux zsh; do
  grep -Fqx "$package" "$repo_root/m1/profile-overlay/packages.x86_64"
done

# ArchISO's releng initramfs includes the memdisk hook even for a UEFI-only
# image. syslinux supplies memdiskfind, which that hook runs before archiso can
# discover and mount the live root filesystem.
archiso_mkinitcpio="$profile/airootfs/etc/mkinitcpio.conf.d/archiso.conf"
if [[ -f "$archiso_mkinitcpio" ]] && grep -Fq 'memdisk' "$archiso_mkinitcpio"; then
  grep -Fqx 'syslinux' "$repo_root/m1/profile-overlay/packages.x86_64"
fi

if [[ -f "$archiso_mkinitcpio" ]] && grep -Fq 'archiso' "$archiso_mkinitcpio"; then
  grep -Fqx 'mkinitcpio-archiso' "$repo_root/m1/profile-overlay/packages.x86_64"
fi

if [[ -f "$profile/airootfs/etc/passwd" ]] && \
   grep -Eq '^root:.*:/usr/bin/zsh$' "$profile/airootfs/etc/passwd"; then
  grep -Fqx 'zsh' "$repo_root/m1/profile-overlay/packages.x86_64"
fi

grep -Fq "bootmodes=('uefi.systemd-boot')" "$repo_root/m1/profile-overlay/profiledef.sh"
if grep -Fq 'bios.' "$repo_root/m1/profile-overlay/profiledef.sh"; then
  echo "Legacy BIOS boot mode is outside the ClawOS UEFI target." >&2
  exit 1
fi

if [[ -d "$profile/airootfs" ]]; then
  "$repo_root/m1/tests/no-omarchy.sh" "$profile/airootfs"
fi

installer="$profile/airootfs/usr/local/bin/clawos-install-dev"
if [[ -f "$installer" ]]; then
  grep -Fq 'target" != /dev/vda' "$installer"
  grep -Fq "ERASE-QEMU-/dev/vda" "$installer"
  grep -Fq 'systemd-detect-virt --vm' "$installer"
  grep -Fq 'Standard PC (Q35 + ICH9, 2009)' "$installer"
  grep -Fq 'clawos-session@clawos.service' "$installer"
  grep -Fq 'npm install --global' "$installer"
  grep -Fq '"openclaw@$OPENCLAW_VERSION"' "$installer"
  grep -Fq -- "--allow-scripts='openclaw,@google/genai,tree-sitter-bash,protobufjs'" "$installer"
fi

for launch_file in \
  usr/lib/clawos/clawos-session \
  usr/lib/clawos/clawos-browser \
  usr/lib/clawos/clawos-entry \
  usr/lib/clawos/clawos-onboard \
  usr/lib/clawos/clawos-install-node \
  etc/clawos/sway.conf \
  etc/systemd/system/clawos-session@.service; do
  test -f "$profile/airootfs/$launch_file"
done

grep -Fq 'openclaw onboard' "$profile/airootfs/usr/lib/clawos/clawos-onboard"
grep -Fq 'openclaw config get gateway.mode' "$profile/airootfs/usr/lib/clawos/clawos-entry"
grep -Fq '#token=${token}' "$profile/airootfs/usr/lib/clawos/clawos-browser"
grep -Fq 'exec --no-startup-id /usr/lib/clawos/clawos-entry' \
  "$profile/airootfs/etc/clawos/sway.conf"
if [[ -d "$profile/airootfs/usr/share/clawos-launch" ]]; then
  echo "A parallel ClawOS web shell is not allowed; use upstream OpenClaw Control UI." >&2
  exit 1
fi

if [[ "$profile" == "$repo_root/m1/profile-overlay" ]]; then
  "$repo_root/m1/tests/onboarding-static.sh"
fi

echo "Milestone 1 profile validation passed."
