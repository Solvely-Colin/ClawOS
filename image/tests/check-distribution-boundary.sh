#!/usr/bin/env bash
# Validate the declared ClawOS identity and pinned Arch package sources.
set -euo pipefail
repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$repo_root/image/tests/check_arch_base.py" "$@"
