#!/usr/bin/env bash
# Tracked-tree hygiene gate.
#
# Inspects the Git index (what a commit publishes; in CI that is the checkout)
# and exits 1 with a list of every finding:
#   - a tracked regular file over 2 MiB
#   - a tracked path under transfer/ or artifacts/ (build products and the
#     private transfer tree; .gitignore covers new files, this catches anything
#     force-added or added before the ignore rule)
#   - a developer home path: /home/<user> other than the image accounts
#     /home/clawos and /home/clawos-live, or a Windows \Users\ path
#   - well-known credential prefixes and private-key headers
#
# Push protection covers known secret formats on the hosting side; this runs
# before a push and also covers sizes and paths. Runs as a preflight-iso stage
# and on its own: ./tools/check-tree.sh
# Stage new work with git add first; unstaged edits are not inspected.
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

# This file holds the patterns below, so the text scans skip it.
self=tools/check-tree.sh
max_bytes=$((2 * 1024 * 1024))
forbidden_path_re='(^|/)(transfer|artifacts)/'
# The left boundary keeps prose such as "root/home/boot" out of the results.
host_path_re='(^|[^A-Za-z0-9_/])/home/[A-Za-z0-9._-]+'
# Image accounts: the installed clawos user and the live-session user.
allowed_home_re='/home/clawos(-live)?([^A-Za-z0-9._-]|$)'
windows_path='\Users\'
# sk- is anchored on a non-letter so words like disk-safety pass.
secret_re='ghp_|github_pat_|AKIA|tskey-|xox[abpr]-|AIza|sk-ant-|(^|[^A-Za-z])sk-[A-Za-z0-9]{8,}|-----BEGIN (RSA|DSA|EC|OPENSSH|PGP|ENCRYPTED|PRIVATE)'

failures=()
tracked=0
tab=$'\t'

# git grep exits 1 when nothing matches; anything above 1 is a real error and
# must not read as "clean", so callers capture the output with "$(...)" under
# set -e instead of piping it.
grep_index() {
  git grep --cached -I -n --no-color "$@" -- . ":!$self" || test $? -eq 1
}

# 1. Size cap on the index blobs. Reading the objects rather than the working
#    tree means a deleted or replaced file on disk cannot hide an oversized
#    tracked object.
while IFS=' ' read -r size path; do
  if [[ ! "$size" =~ ^[0-9]+$ ]]; then
    failures+=("size: index object unreadable: $size $path")
    continue
  fi
  tracked=$((tracked + 1))
  if (( size > max_bytes )); then
    failures+=("size: $path is $size bytes; the cap is $max_bytes")
  fi
done < <(
  git ls-files --stage -z |
    while IFS= read -r -d '' entry; do
      # entry: <mode> <object> <stage><TAB><path>; regular files only.
      [[ "$entry" == 100* ]] || continue
      object="${entry#* }"
      printf '%s %s\n' "${object%% *}" "${entry#*"$tab"}"
    done |
    git cat-file --batch-check='%(objectsize) %(rest)'
)

# 2. Paths that must never be tracked.
while IFS= read -r -d '' path; do
  if [[ "$path" =~ $forbidden_path_re ]]; then
    failures+=("path: $path is under transfer/ or artifacts/")
  fi
done < <(git ls-files -z)

# 3. Developer home paths. Allowlisted accounts are removed from each hit and
#    the line is tested again, so a line naming both an image account and a
#    developer home still fails.
hits="$(grep_index -E -e "$host_path_re")"
while IFS= read -r hit; do
  [[ -n "$hit" ]] || continue
  rest="$hit"
  while [[ "$rest" =~ $allowed_home_re ]]; do
    rest="${rest/"${BASH_REMATCH[0]}"/"${BASH_REMATCH[2]}"}"
  done
  if [[ "$rest" =~ $host_path_re ]]; then
    failures+=("home-path: $hit")
  fi
done <<<"$hits"

hits="$(grep_index -F -e "$windows_path")"
while IFS= read -r hit; do
  [[ -n "$hit" ]] || continue
  failures+=("windows-path: $hit")
done <<<"$hits"

# 4. Credential prefixes. Only the location is printed; the matched text stays
#    out of terminal scrollback and CI logs.
hits="$(grep_index -E -e "$secret_re")"
while IFS=: read -r path line _; do
  [[ -n "$path" ]] || continue
  failures+=("secret-prefix: $path:$line (content withheld)")
done <<<"$hits"

if (( ${#failures[@]} )); then
  printf 'check-tree: %d problem(s) in the tracked tree:\n' "${#failures[@]}" >&2
  printf '  %s\n' "${failures[@]}" >&2
  exit 1
fi

echo "Tracked tree checks passed ($tracked files under the $max_bytes byte cap)."
