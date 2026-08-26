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

echo "ClawOS ISO boot-chain validation passed."
