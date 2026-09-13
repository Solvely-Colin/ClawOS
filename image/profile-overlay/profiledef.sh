#!/usr/bin/env bash
# Derived from archiso v89 configs/releng/profiledef.sh (Arch Linux archiso, GPL-3.0-or-later);
# modified by ClawOS from 2026-08-26. This file stays GPL-3.0-or-later, not MIT.
# SPDX-License-Identifier: GPL-3.0-or-later
# shellcheck disable=SC2034

iso_name="clawos"
iso_label="CLAWOS_LIVE"
iso_publisher="ClawOS <https://github.com/Solvely-Colin/ClawOS>"
iso_application="ClawOS experimental live image and installer"
iso_version="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d)"
install_dir="arch"
buildmodes=('iso')
bootmodes=('uefi.systemd-boot')
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
bootstrap_tarball_compression=('zstd' '-c' '-T0' '--auto-threads=logical' '--long' '-19')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/root"]="0:0:750"
  ["/root/.automated_script.sh"]="0:0:755"
  ["/root/.gnupg"]="0:0:700"
  ["/usr/local/bin/choose-mirror"]="0:0:755"
  ["/usr/local/bin/Installation_guide"]="0:0:755"
  ["/usr/local/bin/livecd-sound"]="0:0:755"
  ["/usr/local/bin/clawos-install-dev"]="0:0:755"
  ["/usr/lib/clawos/clawos-deploy"]="0:0:755"
  ["/usr/lib/clawos/clawos-provider-setup"]="0:0:755"
  ["/usr/lib/clawos/clawos-agent-window"]="0:0:755"
  ["/usr/lib/clawos/clawos-live-session"]="0:0:755"
  ["/usr/lib/clawos/clawos-live-welcome"]="0:0:755"
  ["/usr/lib/clawos/clawos-live-reboot"]="0:0:755"
  ["/usr/lib/clawos/clawos-live-serial-getty"]="0:0:755"
)
