#!/usr/bin/env bash
# Sourced by the installer. Resolve against an EMPTY database, never the live
# system's installed packages: the target needs the complete dependency closure.
install_packages=(
  base linux linux-firmware intel-ucode amd-ucode btrfs-progs cryptsetup dosfstools
  networkmanager openssh sudo zsh tmux curl jq
  chromium foot fuzzel sway swaybg waybar swayidle mesa noto-fonts inter-font otf-geist-mono-nerd
  gtklock gtklock-userinfo-module gtk-layer-shell python-gobject orca
  nodejs npm polkit lxqt-policykit plymouth tailscale
)

prepare_install_packages() {
  local stage=$1 attempt file
  mkdir -p "$stage"/{root,db/local,cache}
  cat >"$stage/online.conf" <<EOF
[options]
Architecture = x86_64
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Required
ParallelDownloads = 1
[core]
Server = https://archive.archlinux.org/repos/$ARCH_SNAPSHOT/\$repo/os/\$arch
[extra]
Server = https://archive.archlinux.org/repos/$ARCH_SNAPSHOT/\$repo/os/\$arch
EOF
  local pacman_args=(--config "$stage/online.conf" --root "$stage/root"
    --dbpath "$stage/db" --cachedir "$stage/cache"
    --gpgdir /etc/pacman.d/gnupg --logfile "$stage/pacman.log")
  # Slow archive responses must not trip libalpm's 10-second low-speed limit.
  # Keep a hard deadline and finite retries; only this download-only process
  # may be timed out, never a disk writer or a target package installation.
  for attempt in 1 2 3; do
    echo "Downloading and verifying installation packages (attempt $attempt/3); disk unchanged."
    if timeout --kill-after=10s 15m pacman "${pacman_args[@]}" \
      --disable-sandbox --disable-download-timeout -Syw --noconfirm "${install_packages[@]}"; then
      break
    fi
    if (( attempt == 3 )); then
      echo 'Package preparation failed. The target disk has not been changed.' >&2
      return 1
    fi
    sleep 3
  done
  # Download-only verifies package integrity/signatures. Record the exact
  # resolved files and require detached signatures again during local install.
  pacman "${pacman_args[@]}" -Sp --print-format '%f' "${install_packages[@]}" >"$stage/packages.list" || return
  install_files=()
  while IFS= read -r file; do
    [[ -n "$file" && "$file" != */* && "$file" == *.pkg.tar.* && "$file" != *.sig ]] || return 1
    [[ -s "$stage/cache/$file" && -s "$stage/cache/$file.sig" ]] || return 1
    install_files+=("$stage/cache/$file")
  done <"$stage/packages.list"
  (( ${#install_files[@]} > 0 )) || return 1
  sha256sum -- "${install_files[@]}" >"$stage/packages.sha256"
  cat >"$stage/local.conf" <<'EOF'
[options]
Architecture = x86_64
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Required
EOF
}
