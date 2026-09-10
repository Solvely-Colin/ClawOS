#!/usr/bin/env bash
# ShellCheck gate for the host-side shell scripts.
#
# Every bash or sh script (by shebang or .sh suffix) under the roots below is
# checked at warning severity. Project-wide exclusions live in .shellcheckrc at
# the repository root; keep any inline "# shellcheck disable=" directive on one
# line with the reason next to it.
#
# Deferred: the scripts under image/profile-overlay (usr/lib/clawos/*,
# usr/local/bin/clawos-install-dev, profiledef.sh). They are syntax-checked by
# validate-profile.sh and onboarding-static.sh, and their ShellCheck findings
# have not been triaged. Add the directory to roots once they are.
#
# Runs as a preflight-iso stage and on its own: ./tools/check-shell.sh
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

roots=(experiments/host-session/bin experiments/host-session/tests image/bin image/tests tests/integration/roles tools)

if ! command -v shellcheck >/dev/null 2>&1; then
  echo 'check-shell: shellcheck not found. On Arch run ./image/bin/install-build-deps; elsewhere install shellcheck.' >&2
  exit 1
fi

scripts=()
while IFS= read -r -d '' file; do
  first_line=
  IFS= read -r first_line <"$file" 2>/dev/null || true
  if [[ "$file" == *.sh || "$first_line" =~ ^#!.*/(env[[:space:]]+)?(ba)?sh([[:space:]]|$) ]]; then
    scripts+=("$file")
  fi
done < <(find "${roots[@]}" -type f -print0 | sort -z)

if (( ${#scripts[@]} == 0 )); then
  echo 'check-shell: no shell scripts found under the configured roots.' >&2
  exit 1
fi

shellcheck -S warning -x "${scripts[@]}"
echo "Shell static analysis passed (${#scripts[@]} scripts under ${roots[*]})."
