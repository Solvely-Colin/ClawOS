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

archive_host=archive.archlinux.org
# Space the download area needs beyond the summed package sizes: the sync
# databases, detached signatures, pacman's log, and headroom so filling the
# RAM-backed /tmp cannot push the live system into memory exhaustion.
download_margin_bytes=$((256 * 1024 * 1024))

archive_url() {
  # $1: repository name. Prints the pinned snapshot URL of its database file.
  printf 'https://%s/repos/%s/%s/os/x86_64/%s.db\n' "$archive_host" "$ARCH_SNAPSHOT" "$1" "$1"
}

to_mib() {
  echo $(( ($1 + 1048575) / 1048576 ))
}

fail_preparation() {
  # The one line a person or the GTK log should read last. Every preparation
  # failure passes through here, after any raw diagnostic has been replayed.
  echo "Package preparation failed: $1 The target disk has not been changed." >&2
}

# --- Pure classification and arithmetic (unit-tested; no network, no disk) ---

classify_probe_result() {
  # $1: curl exit status of the HEAD probe; $2: HTTP status it saw ("000"
  # when no response). Prints ok, dns, refused, tls, timeout, reset, unknown,
  # or "http <code>" for an answered-but-wrong status.
  local status=$1 code=${2:-000}
  case "$status" in
    0|22) if [[ "$code" == 200 ]]; then echo ok; else echo "http $code"; fi ;;
    5|6) echo dns ;;
    7) echo refused ;;
    28) echo timeout ;;
    35|51|53|54|58|59|60|66|77|80|82|83|90|91) echo tls ;;
    16|18|52|55|56|92) echo reset ;;
    *) echo unknown ;;
  esac
}

classify_transfer_failure() {
  # $1: exit status of a pacman transfer run under coreutils timeout; $2: its
  # captured stderr. Same vocabulary as classify_probe_result plus storage and
  # signature. Name resolution is checked before generic timeouts so a
  # resolver that never answers is reported as DNS, not as a slow archive.
  local status=$1 text=${2:-} code
  case "$status" in 124|137) echo timeout; return ;; esac
  if grep -qiE 'could not resolve|couldn.t resolve|resolving timed out|name or service not known|failure in name resolution' <<<"$text"; then
    echo dns
  elif grep -qiE 'connection refused|failed to connect|couldn.t connect|no route to host|network is unreachable' <<<"$text"; then
    echo refused
  elif code=$(grep -oiE 'returned error: [0-9]{3}' <<<"$text" | head -n1 | grep -oE '[0-9]{3}$'); then
    echo "http $code"
  elif grep -qiE 'connection reset|stream [0-9]+ was not closed cleanly|http/?2 (stream|framing)|recv failure|send failure|failure when (receiving|sending) data|transfer closed with|empty reply|partial file|connection died|closed connection unexpectedly|unexpected eof' <<<"$text"; then
    echo reset
  elif grep -qiE 'timed out|timeout was reached|operation too slow' <<<"$text"; then
    echo timeout
  elif grep -qiE 'ssl|tls|certificate' <<<"$text"; then
    echo tls
  elif grep -qiE 'no space left|too full|not enough free disk space|disk quota exceeded|failed writing' <<<"$text"; then
    echo storage
  elif grep -qiE 'signature|pgp|keyring|invalid or corrupted package' <<<"$text"; then
    echo signature
  else
    echo unknown
  fi
}

download_failure_retryable() {
  # Only a deadline or a dropped stream can succeed on a second try. DNS,
  # connection, TLS, HTTP, storage and signature failures need a fix first.
  [[ "$1" == timeout || "$1" == reset ]]
}

describe_http_status() {
  local code=$1
  case "$code" in
    3[0-9][0-9]) echo "$archive_host answered HTTP $code (redirect): a captive portal or proxy is intercepting HTTPS. Sign in to the network in a browser, then retry." ;;
    404|410) echo "$archive_host answered HTTP $code for snapshot $ARCH_SNAPSHOT: that archive path does not exist. Check ARCH_SNAPSHOT in versions.env and rebuild the ISO." ;;
    4[0-9][0-9]) echo "$archive_host answered HTTP $code: the request was refused. Check for an intercepting proxy or a wrong system clock, then retry." ;;
    5[0-9][0-9]) echo "$archive_host answered HTTP $code: the archive is temporarily unavailable. Try again later." ;;
    *) echo "$archive_host answered an unexpected HTTP status ($code)." ;;
  esac
}

describe_download_failure() {
  # $1: class; $2: detail (the HTTP status for class http). One sentence
  # naming the cause and one naming the fix.
  local class=$1 detail=${2:-}
  case "$class" in
    dns) echo "$archive_host could not be resolved (DNS). Check the network's DNS settings or sign in to its captive portal, then retry." ;;
    refused) echo "A connection to $archive_host was refused or the host is unreachable. Check the network connection and any firewall, then retry." ;;
    tls) echo "The TLS connection to $archive_host failed. A captive portal, an intercepting proxy or a wrong system clock breaks HTTPS; fix that, then retry." ;;
    http) describe_http_status "$detail" ;;
    timeout) echo "$archive_host did not answer within the deadline (timeout). Check the connection speed, then retry." ;;
    reset) echo "The connection to $archive_host was reset mid-transfer. Retry on a stable connection; the whole download must complete in one session." ;;
    storage) echo "The live system ran out of temporary storage during the download. /tmp is RAM-backed on the live ISO; increase VM memory to at least 4 GiB, then retry." ;;
    signature) echo "Package signature verification failed; the downloaded files or the live keyring cannot be trusted. Re-download or rebuild the ISO, then retry." ;;
    *) echo "The package transfer failed for a reason the installer does not classify; see the lines above." ;;
  esac
}

sum_download_bytes() {
  # stdin: one decimal byte count per resolved package (pacman -Sp %s).
  # Refuse anything else so a stray message can never pass as a size.
  local line total=0 count=0
  while IFS= read -r line; do
    [[ "$line" =~ ^[0-9]+$ ]] || return 1
    total=$((total + line))
    count=$((count + 1))
  done
  (( count > 0 )) || return 1
  echo "$total"
}

check_download_capacity() {
  # $1: summed package bytes; $2: free bytes where the download lands;
  # $3: MemAvailable bytes when that location is RAM-backed, empty otherwise.
  # Prints the reason and fails when either budget is short of size + margin.
  local size=$1 free=$2 memory=${3:-} required
  required=$((size + download_margin_bytes))
  if (( free < required )); then
    echo "the package download needs $(to_mib "$required") MiB of temporary storage ($(to_mib "$size") MiB of packages plus a $(to_mib "$download_margin_bytes") MiB margin) but /tmp has $(to_mib "$free") MiB free. /tmp is RAM-backed on the live ISO: increase VM memory to at least 4 GiB (a physical machine needs 4 GiB of RAM), then retry."
    return 1
  fi
  if [[ -n "$memory" ]] && (( memory < required )); then
    echo "the package download needs $(to_mib "$required") MiB of memory for the RAM-backed /tmp but only $(to_mib "$memory") MiB is available; increase VM memory to at least 4 GiB (a physical machine needs 4 GiB of RAM), then retry."
    return 1
  fi
}

# --- Live-system probes (overridden by the unit tests) ---

tmp_available_bytes() {
  # $1: a path inside the download area.
  df --output=avail --block-size=1 -- "$1" | tail -n1 | tr -d ' '
}

memory_available_bytes() {
  # $1: a path inside the download area. Prints nothing when that area is not
  # RAM-backed, so a disk-backed /tmp is never held to a memory budget.
  [[ "$(findmnt -nro FSTYPE --target "$1")" == tmpfs ]] || return 0
  awk '/^MemAvailable:/ { printf "%d\n", $2 * 1024 }' /proc/meminfo
}

probe_archive() {
  # $1: stage directory. One HEAD request with a ten-second deadline to the
  # pinned core database; fails fast and classified, no retry. This is what
  # turns a captive portal or broken DNS into a message instead of a
  # fifteen-minute wait.
  local stage=$1 url http status=0 class detail
  url=$(archive_url core)
  http=$(curl --head --silent --show-error --max-time 10 --output /dev/null \
    --write-out '%{http_code}' -- "$url" 2>"$stage/probe.err") || status=$?
  read -r class detail <<<"$(classify_probe_result "$status" "$http")"
  if [[ "$class" == ok ]]; then
    echo "Package archive reachable: HTTP $http from $archive_host for snapshot $ARCH_SNAPSHOT."
    return 0
  fi
  cat "$stage/probe.err" >&2
  fail_preparation "$(describe_download_failure "$class" "$detail")"
  return 1
}

transfer_with_retries() {
  # $1: stage directory; $2: deadline for one attempt; $3: label; then the
  # pacman arguments. Slow archive responses must not trip libalpm's 10-second
  # low-speed limit, so the caller disables it and this hard deadline bounds
  # each attempt instead. Retries happen only after a timeout or a reset
  # stream; every other failure stops at once with one line naming the cause.
  # Only this download-only process may be timed out, never a disk writer or
  # a target package installation.
  local stage=$1 deadline=$2 label=$3 attempt status class detail
  shift 3
  for attempt in 1 2 3; do
    echo "$label (attempt $attempt/3); disk unchanged."
    status=0
    timeout --kill-after=10s "$deadline" pacman "$@" 2>"$stage/transfer.err" || status=$?
    if (( status == 0 )); then return 0; fi
    cat "$stage/transfer.err" >&2
    read -r class detail <<<"$(classify_transfer_failure "$status" "$(<"$stage/transfer.err")")"
    if (( attempt == 3 )) || ! download_failure_retryable "$class"; then
      fail_preparation "$(describe_download_failure "$class" "$detail")"
      return 1
    fi
    sleep 3
  done
}

prepare_install_packages() {
  local stage=$1 file size free memory reason
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
  local transfer_args=("${pacman_args[@]}" --disable-sandbox --disable-download-timeout)

  # Everything up to the package download is a check: reachability, then the
  # small database refresh, then the size of the resolved set against the
  # free space of the RAM-backed /tmp and the available memory. A machine
  # that cannot hold the download fails here in seconds, before any package
  # byte is fetched and long before the caller's first disk write.
  probe_archive "$stage" || return 1
  transfer_with_retries "$stage" 5m 'Refreshing the pinned package databases' \
    "${transfer_args[@]}" -Sy || return 1
  pacman "${pacman_args[@]}" -Sp --print-format '%s' "${install_packages[@]}" \
    >"$stage/sizes.list" 2>"$stage/resolve.err" || {
    cat "$stage/resolve.err" >&2
    fail_preparation "the package set could not be resolved against snapshot $ARCH_SNAPSHOT; see the lines above."
    return 1
  }
  size=$(sum_download_bytes <"$stage/sizes.list") || {
    fail_preparation 'pacman did not report a download size for every resolved package.'
    return 1
  }
  free=$(tmp_available_bytes "$stage") && [[ "$free" =~ ^[0-9]+$ ]] || {
    fail_preparation 'the free space of the live /tmp could not be determined.'
    return 1
  }
  memory=$(memory_available_bytes "$stage") || memory=
  [[ "$memory" =~ ^[0-9]*$ ]] || memory=
  reason=$(check_download_capacity "$size" "$free" "$memory") || {
    fail_preparation "$reason"
    return 1
  }
  echo "Download size $(to_mib "$size") MiB; free temporary storage $(to_mib "$free") MiB${memory:+; available memory $(to_mib "$memory") MiB}."

  transfer_with_retries "$stage" 15m 'Downloading and verifying installation packages' \
    "${transfer_args[@]}" -Syw --noconfirm "${install_packages[@]}" || return 1
  # Download-only verifies package integrity/signatures. Record the exact
  # resolved files and require detached signatures again during local install.
  pacman "${pacman_args[@]}" -Sp --print-format '%f' "${install_packages[@]}" >"$stage/packages.list" || {
    fail_preparation 'the downloaded package set could not be listed.'
    return 1
  }
  install_files=()
  while IFS= read -r file; do
    [[ -n "$file" && "$file" != */* && "$file" == *.pkg.tar.* && "$file" != *.sig ]] || {
      fail_preparation "pacman named '$file', which is not a plain package file."
      return 1
    }
    [[ -s "$stage/cache/$file" && -s "$stage/cache/$file.sig" ]] || {
      fail_preparation "$file or its detached signature is missing from the download area."
      return 1
    }
    install_files+=("$stage/cache/$file")
  done <"$stage/packages.list"
  (( ${#install_files[@]} > 0 )) || {
    fail_preparation 'no packages were resolved for the target.'
    return 1
  }
  sha256sum -- "${install_files[@]}" >"$stage/packages.sha256"
  cat >"$stage/local.conf" <<'EOF'
[options]
Architecture = x86_64
SigLevel = Required DatabaseOptional
LocalFileSigLevel = Required
EOF
}
