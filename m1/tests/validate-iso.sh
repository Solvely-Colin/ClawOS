#!/usr/bin/env bash
set -euo pipefail

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

echo "ClawOS ISO boot-chain and pinned runtime validation passed."
