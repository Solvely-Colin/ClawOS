#!/usr/bin/env bash
set -euo pipefail

# The lines 00-clawos.conf must carry, spelled as sshd_config(5) spells them.
# `sshd -T` reports the same settings lowercased; boot-smoke-qemu and
# m2-e2e-qemu grep that form inside the guest.
sshd_keyonly_directives=(
  'PasswordAuthentication no'
  'KbdInteractiveAuthentication no'
  'PermitRootLogin no'
)

# check_sshd_posture ROOT
# ROOT is an extracted airootfs tree (or a test fixture) holding etc/ssh.
# sshd applies an Include glob in C-locale order and keeps the first value it
# sees for each option, so the ClawOS drop-in only wins while it sorts ahead
# of archiso's 10-archiso.conf (PasswordAuthentication yes, PermitRootLogin
# yes). Every failure names its reason on stderr and returns 1.
check_sshd_posture() {
  local root="$1"
  local dropin_dir="$root/etc/ssh/sshd_config.d"
  local sshd_config="$root/etc/ssh/sshd_config"
  local archiso=10-archiso.conf
  local -a listing=() clawos_dropins=()
  local path name clawos directive archiso_present=false

  if [[ ! -f "$sshd_config" ]]; then
    echo "sshd posture: etc/ssh/sshd_config is missing" >&2
    return 1
  fi
  if ! grep -Eq '^[[:space:]]*Include[[:space:]]+/etc/ssh/sshd_config\.d/\*\.conf[[:space:]]*$' "$sshd_config"; then
    echo "sshd posture: etc/ssh/sshd_config does not Include /etc/ssh/sshd_config.d/*.conf, so no drop-in applies" >&2
    return 1
  fi
  if [[ ! -d "$dropin_dir" ]]; then
    echo "sshd posture: etc/ssh/sshd_config.d is missing" >&2
    return 1
  fi
  for path in "$dropin_dir"/*.conf; do
    [[ -e "$path" ]] || continue
    listing+=("${path##*/}")
  done
  if (( ${#listing[@]} == 0 )); then
    echo "sshd posture: etc/ssh/sshd_config.d holds no *.conf drop-in" >&2
    return 1
  fi
  # Bash sorts globs in the current locale; sshd's glob(3) runs in the C locale.
  mapfile -t listing < <(printf '%s\n' "${listing[@]}" | LC_ALL=C sort)

  for name in "${listing[@]}"; do
    if [[ "$name" == *-clawos.conf ]]; then
      clawos_dropins+=("$name")
    fi
    if [[ "$name" == "$archiso" ]]; then
      archiso_present=true
    fi
  done
  if (( ${#clawos_dropins[@]} != 1 )); then
    echo "sshd posture: expected exactly one *-clawos.conf in etc/ssh/sshd_config.d, found ${#clawos_dropins[@]} in: ${listing[*]}" >&2
    return 1
  fi
  clawos="${clawos_dropins[0]}"
  for directive in "${sshd_keyonly_directives[@]}"; do
    if ! grep -Fqx "$directive" "$dropin_dir/$clawos"; then
      echo "sshd posture: $clawos lacks the line '$directive'" >&2
      return 1
    fi
  done
  if [[ "$archiso_present" != true ]]; then
    echo "sshd posture: $archiso is missing from etc/ssh/sshd_config.d; archiso renamed its live drop-in, so the override order is unverified" >&2
    return 1
  fi
  for name in "${listing[@]}"; do
    if [[ "$name" == "$archiso" ]]; then
      echo "sshd posture: $clawos sorts after $archiso, so archiso's PasswordAuthentication yes and PermitRootLogin yes win on the live system" >&2
      return 1
    fi
    if [[ "$name" == "$clawos" ]]; then
      break
    fi
  done
  if [[ "$clawos" != 00-clawos.conf ]]; then
    echo "sshd posture: the ClawOS drop-in is $clawos, but clawos-install-dev copies 00-clawos.conf onto the installed system" >&2
    return 1
  fi
  echo "sshd posture: $clawos sorts ahead of $archiso in etc/ssh/sshd_config.d (${listing[*]})"
}

# check_live_banner ROOT
# The live login banner must keep stating the verification scope.
check_live_banner() {
  local root="$1"
  if [[ ! -f "$root/etc/issue" ]]; then
    echo "live banner: etc/issue is missing" >&2
    return 1
  fi
  if ! grep -Fq 'Verified only in virtual machines' "$root/etc/issue"; then
    echo "live banner: etc/issue no longer says 'Verified only in virtual machines'" >&2
    return 1
  fi
}

# m1/tests/test_iso_posture.py sources this file for the functions above; the
# ISO walk below runs only when the script is executed.
if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  return 0
fi

iso="${1:?usage: validate-iso.sh path/to/clawos.iso}"
tmpdir="$(mktemp -d /tmp/clawos-iso-validation.XXXXXX)"
trap 'rm -rf "$tmpdir"' EXIT

loader_entry="$tmpdir/loader.conf"
initramfs="$tmpdir/initramfs-linux.img"

bsdtar -xOf "$iso" loader/entries/01-archiso-linux.conf >"$loader_entry"
grep -Eq '^options +archisobasedir=arch +archisosearchuuid=[^ ]+ +console=tty0 +console=ttyS0,115200n8$' "$loader_entry"

bsdtar -xOf "$iso" arch/boot/x86_64/initramfs-linux.img >"$initramfs"
initramfs_files="$tmpdir/initramfs-files"
lsinitcpio -l "$initramfs" >"$initramfs_files"

for required in hooks/archiso hooks/archiso_loop_mnt usr/bin/memdiskfind; do
  grep -Fqx "$required" "$initramfs_files"
done

squashfs="$tmpdir/airootfs.sfs"
bsdtar -xOf "$iso" arch/x86_64/airootfs.sfs >"$squashfs"
unsquashfs -cat "$squashfs" usr/lib/node_modules/openclaw/openclaw.mjs >"$tmpdir/openclaw.mjs"
test -s "$tmpdir/openclaw.mjs"
unsquashfs -no-progress -d "$tmpdir/runtime-check" "$squashfs" \
  usr/bin/openclaw usr/lib/node_modules/openclaw/openclaw.mjs >/dev/null
test -x "$tmpdir/runtime-check/usr/bin/openclaw"
unsquashfs -cat "$squashfs" usr/lib/node_modules/openclaw/package.json >"$tmpdir/openclaw-package.json"
source "$(dirname "$0")/../config/versions.env"
python3 - "$tmpdir/openclaw-package.json" "$OPENCLAW_VERSION" <<'PY'
import json, sys
with open(sys.argv[1]) as package:
    assert json.load(package)['version'] == sys.argv[2], 'ISO OpenClaw version differs from the lock'
PY

# The sshd posture is otherwise asserted only at source level
# (validate-profile.sh). Extract what the live system will actually read and
# check the shipped files, including archiso's own drop-in and its order.
posture="$tmpdir/posture"
unsquashfs -no-progress -d "$posture" "$squashfs" \
  etc/ssh/sshd_config etc/ssh/sshd_config.d etc/issue >/dev/null
check_sshd_posture "$posture"
check_live_banner "$posture"

echo "ClawOS ISO boot-chain, pinned runtime and sshd posture validation passed."
