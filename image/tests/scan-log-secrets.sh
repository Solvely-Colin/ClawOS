#!/usr/bin/env bash
# Refuse to hand QEMU evidence (serial.log, transcript.log, qemu.log) to an
# artifact upload while it carries a secret-shaped string. boot-smoke-qemu and
# m2-e2e-qemu run this over their logs before reporting success; a CI upload
# step should run it again over whatever it is about to publish, including the
# logs of a failed run.
#
# Findings name the file, line numbers and pattern only. The matched text is
# never printed: copying it into a CI log would defeat the scan.
#
# Usage: scan-log-secrets.sh FILE...
set -euo pipefail

# name<TAB>extended regex. Every pattern is matched case-insensitively. The
# prefixes follow tools/check-tree.sh's list (issue #46); the sk- rule is
# word-anchored so names such as disk-safety pass.
secret_patterns=(
  $'private-key-block\t-----BEGIN [A-Z ]*PRIVATE KEY-----'
  $'github-token\tgh[pousr]_[A-Za-z0-9]{36}'
  $'github-fine-grained-token\tgithub_pat_[A-Za-z0-9_]{22,}'
  $'aws-access-key\tAKIA[0-9A-Z]{16}'
  $'tailscale-key\ttskey-[A-Za-z0-9-]{8,}'
  $'slack-token\txox[abpr]-[A-Za-z0-9-]{10,}'
  $'google-api-key\tAIza[0-9A-Za-z_-]{35}'
  $'sk-prefixed-api-key\t(^|[^A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}'
  $'jwt\teyJ[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]{8,}\\.[A-Za-z0-9_-]{8,}'
  $'credential-assignment\t(password|passwd|passphrase|secret|token|api[_-]?key)["\']?[[:space:]]*[=:][[:space:]]*["\']?[^[:space:]"\']{8,}'
)

# scan_log_secrets FILE...
# Returns 0 when no file matches any pattern, 1 when at least one does, 2 when
# an argument is not a readable file.
scan_log_secrets() {
  local status=0 file entry name regex lines
  for file in "$@"; do
    if [[ ! -f "$file" || ! -r "$file" ]]; then
      echo "scan-log-secrets: not a readable file: $file" >&2
      return 2
    fi
    for entry in "${secret_patterns[@]}"; do
      name="${entry%%$'\t'*}"
      regex="${entry#*$'\t'}"
      # -a: serial logs carry NUL bytes from the UART; treat them as text so
      # grep reports line numbers instead of "binary file matches".
      lines="$(grep -aniE -- "$regex" "$file" | cut -d: -f1 | paste -sd, -)" || true
      if [[ -n "$lines" ]]; then
        echo "scan-log-secrets: $file: $name pattern at line(s) $lines" >&2
        status=1
      fi
    done
  done
  return "$status"
}

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  return 0
fi

if (( $# == 0 )); then
  echo "usage: scan-log-secrets.sh FILE..." >&2
  exit 2
fi
if scan_log_secrets "$@"; then
  echo "scan-log-secrets: no secret-shaped strings in $# file(s)."
else
  status=$?
  if (( status == 1 )); then
    echo "scan-log-secrets: refusing to publish; inspect the named lines locally and redact or fix the leak." >&2
  fi
  exit "$status"
fi
