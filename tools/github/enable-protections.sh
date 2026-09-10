#!/usr/bin/env bash
# Enable the GitHub-side protections for the ClawOS repository (issue #16).
#
# Prepare, do not execute. The default mode is --dry-run: every step prints the
# exact `gh api` call it would make and reads the current setting without
# changing anything. --apply performs the calls in the order issue #16 mandates
# and re-reads each setting afterwards; a mismatch is reported as FAIL and the
# script exits nonzero. Every write is idempotent (PUT/PATCH, or update-by-name
# for rulesets), so re-running --apply is safe.
#
# Requirements: gh authenticated as a repository admin. Nothing else; jq
# expressions run through gh's built-in --jq. On the private repository most
# reads fail by design (private-vulnerability-reporting 404, vulnerability-alerts
# 404, rulesets 403, code-scanning 403, fork-pr approval 422, selected-actions
# 409); record that dry-run output as the "before" state. --apply refuses to run
# while the repository is private.
#
# The script never prints tokens or response headers, only status codes and
# response bodies, so its output can be filed in the evidence archive as is.
# See docs/FLIP-DAY.md for the order of operations around this script.
set -euo pipefail

REPO=${GH_REPO:-Solvely-Colin/ClawOS}
MODE=dry-run
MERGE_METHOD=merge
CODEQL_LANGUAGES=javascript-typescript,python
STEPS_ALL=(visibility pvr secret-scanning secret-alerts dependabot rulesets codeql fork-pr-approval actions workflow-permissions)
ONLY=
FAILURES=0

usage() {
  cat <<EOF
Usage: tools/github/enable-protections.sh [--dry-run | --apply] [options]

  --dry-run                 Print each API call and the current setting (default).
  --apply                   Perform the calls and verify each resulting setting.
  --repo OWNER/REPO         Repository (default: \$GH_REPO or $REPO).
  --merge-method METHOD     merge | squash | rebase; the main ruleset allows only
                            this method. squash or rebase also add the
                            required_linear_history rule (default: merge, the
                            method PRs #1-#3 landed with).
  --codeql-languages LIST   Comma-separated CodeQL default-setup languages
                            (default: $CODEQL_LANGUAGES).
  --only STEP[,STEP...]     Run a subset. Steps, in the order they run:
                            ${STEPS_ALL[*]}
  -h, --help                This text.

Exit status: 0 when every step passed (or in --dry-run), 1 when a write or a
verification failed, 2 for usage errors or a private repository in --apply.
EOF
}

while (($#)); do
  case $1 in
    --dry-run) MODE=dry-run ;;
    --apply) MODE=apply ;;
    --repo) REPO=$2; shift ;;
    --merge-method) MERGE_METHOD=$2; shift ;;
    --codeql-languages) CODEQL_LANGUAGES=$2; shift ;;
    --only) ONLY=$2; shift ;;
    -h | --help) usage; exit 0 ;;
    *) printf 'Unknown argument: %s\n\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

case $MERGE_METHOD in
  merge | squash | rebase) ;;
  *) printf -- '--merge-method must be merge, squash or rebase, not %s\n' "$MERGE_METHOD" >&2; exit 2 ;;
esac
[[ $REPO == */* ]] || { printf -- '--repo must be OWNER/REPO, not %s\n' "$REPO" >&2; exit 2; }

# ---------------------------------------------------------------- helpers ----

note() { printf '   %s\n' "$*"; }
step() { printf '\n== %s ==\n' "$*"; }
fail() { printf '   FAIL: %s\n' "$*"; FAILURES=$((FAILURES + 1)); }

repo_path() { printf 'repos/%s%s' "$REPO" "${1:+/$1}"; }

# show_call METHOD PATH [BODY]: print the exact gh invocation for the record.
show_call() {
  local method=$1 path=$2 body=${3:-}
  if [[ -n $body ]]; then
    printf "   gh api --method %s %s --input - <<'JSON'\n" "$method" "$(repo_path "$path")"
    printf '%s\n' "$body" | sed 's/^/   /'
    printf '   JSON\n'
  else
    printf '   gh api --method %s %s\n' "$method" "$(repo_path "$path")"
  fi
}

# api METHOD PATH [BODY]: run the call. Sets API_STATUS (three digits, or 000
# when gh produced no HTTP status line) and API_BODY (response body only).
api() {
  local method=$1 path=$2 body=${3:-} raw
  if [[ -n $body ]]; then
    raw=$(printf '%s' "$body" | gh api -i --method "$method" "$(repo_path "$path")" --input - 2>/dev/null) || true
  else
    raw=$(gh api -i --method "$method" "$(repo_path "$path")" 2>/dev/null) || true
  fi
  API_STATUS=$(printf '%s\n' "$raw" | sed -n '1s/^HTTP\/[0-9.]* \([0-9][0-9][0-9]\).*$/\1/p')
  [[ -n $API_STATUS ]] || API_STATUS=000
  API_BODY=$(printf '%s\n' "$raw" | sed '1,/^\r\{0,1\}$/d')
}

# read_jq PATH JQ: GET and print the jq projection; prints nothing on any error.
read_jq() {
  local out
  if out=$(gh api "$(repo_path "$1")" --jq "$2" 2>/dev/null); then
    printf '%s' "$out"
  fi
}

# current PATH JQ: the jq projection of a GET ("<empty>" when it is null or
# blank), or "HTTP <code>" when the call fails.
current() {
  local out
  if out=$(gh api "$(repo_path "$1")" --jq "$2" 2>/dev/null); then
    if [[ $out =~ ^[[:space:]]*$ ]]; then out='<empty>'; fi
    printf '%s' "$out"
  else
    api GET "$1"
    printf 'HTTP %s' "$API_STATUS"
  fi
}

# write METHOD PATH BODY OK_STATUSES: show the call; in --apply also run it and
# require one of the listed statuses. Returns 1 on failure so callers can stop.
write() {
  local method=$1 path=$2 body=$3 ok=$4
  show_call "$method" "$path" "$body"
  [[ $MODE == apply ]] || return 0
  api "$method" "$path" "$body"
  if [[ " $ok " == *" $API_STATUS "* ]]; then
    note "-> HTTP $API_STATUS"
  else
    fail "$method $(repo_path "$path") returned HTTP $API_STATUS: $(printf '%s' "$API_BODY" | tr -d '\r\n' | head -c 300)"
    return 1
  fi
}

# check LABEL PATH JQ [WANTED]: print the current value. In --apply with WANTED
# given, count a FAIL when they differ. In --dry-run only report.
check() {
  local label=$1 path=$2 jq=$3 cur
  cur=$(current "$path" "$jq")
  if [[ $MODE == apply && $# -ge 4 ]]; then
    if [[ $cur == "$4" ]]; then
      note "verified: $label = $cur"
    else
      fail "$label is '$cur', wanted '$4'"
    fi
  else
    note "current: $label = $cur"
  fi
}

# ------------------------------------------------------------------ steps ----

step_visibility() {
  step "Repository visibility and metadata (precondition)"
  show_call GET ""
  local vis
  vis=$(current "" '.visibility')
  note "current: visibility = $vis"
  note "current: description = $(current "" '.description')"
  note "current: homepage = $(current "" '.homepage')"
  note "current: topics = $(current "" '.topics | join(", ")')"
  note "current: merge methods allowed = $(current "" '[(if .allow_merge_commit then "merge" else empty end), (if .allow_squash_merge then "squash" else empty end), (if .allow_rebase_merge then "rebase" else empty end)] | join(", ")')"
  if [[ $MODE == apply && $vis != public ]]; then
    printf '\nRefusing --apply: %s is %s, not public. Flip the visibility first (docs/FLIP-DAY.md).\n' "$REPO" "$vis" >&2
    exit 2
  fi
  [[ $vis == public ]] || note "(private: expect 403/404/409/422 from the security endpoints below)"
}

step_pvr() {
  step "Private vulnerability reporting"
  local cur
  cur=$(current private-vulnerability-reporting '.enabled')
  note "current: enabled = $cur"
  if [[ $cur == true ]]; then
    note "already enabled; the call below is idempotent and skipped"
    show_call PUT private-vulnerability-reporting
  else
    write PUT private-vulnerability-reporting "" "204" || return 0
  fi
  check "private-vulnerability-reporting.enabled" private-vulnerability-reporting '.enabled' true
  note "manual: open https://github.com/$REPO/security/advisories/new in a logged-out browser and confirm 'Report a vulnerability'"
}

step_secret_scanning() {
  step "Secret scanning and push protection"
  local body cur
  body='{
  "security_and_analysis": {
    "secret_scanning": {"status": "enabled"},
    "secret_scanning_push_protection": {"status": "enabled"}
  }
}'
  cur=$(current "" '.security_and_analysis | [.secret_scanning.status, .secret_scanning_push_protection.status] | join(" ")')
  note "current: secret_scanning push_protection = $cur"
  if [[ $cur == "enabled enabled" ]]; then
    note "already enabled (the public-repository default); the call below is idempotent and skipped"
    show_call PATCH "" "$body"
  else
    write PATCH "" "$body" "200" || return 0
  fi
  check "security_and_analysis.secret_scanning.status" "" '.security_and_analysis.secret_scanning.status' enabled
  check "security_and_analysis.secret_scanning_push_protection.status" "" '.security_and_analysis.secret_scanning_push_protection.status' enabled
}

step_secret_alerts() {
  step "Secret scanning historical alerts (triage within the hour)"
  local path='secret-scanning/alerts?state=open&per_page=100' count
  show_call GET "$path"
  count=$(current "$path" 'length')
  note "current: open alerts = $count"
  if [[ $MODE == apply ]]; then
    if [[ $count == 0 ]]; then
      note "verified: 0 open secret-scanning alerts; record the count and the UTC time in the evidence archive"
    elif [[ $count =~ ^[0-9]+$ ]]; then
      fail "$count open secret-scanning alert(s): rotate or revoke first, then remove and re-scan; re-privatising is not a remedy"
      read_jq "$path" '.[] | "   - #\(.number) \(.secret_type_display_name) \(.html_url)"'
      printf '\n'
    else
      fail "could not list secret-scanning alerts ($count)"
    fi
  fi
}

step_dependabot() {
  step "Dependabot alerts and dependency graph"
  api GET vulnerability-alerts
  note "current: vulnerability-alerts = HTTP $API_STATUS (204 enabled, 404 disabled)"
  if [[ $API_STATUS == 204 ]]; then
    note "already enabled; the call below is idempotent and skipped"
    show_call PUT vulnerability-alerts
  else
    write PUT vulnerability-alerts "" "204" || return 0
  fi
  if [[ $MODE == apply ]]; then
    api GET vulnerability-alerts
    if [[ $API_STATUS == 204 ]]; then
      note "verified: vulnerability-alerts = HTTP 204"
    else
      fail "vulnerability-alerts is HTTP $API_STATUS, wanted 204"
    fi
  fi
  show_call GET dependency-graph/sbom
  local sbom
  sbom=$(current dependency-graph/sbom '.sbom.name')
  if [[ $MODE == apply ]]; then
    if [[ $sbom == HTTP* || $sbom == '<empty>' ]]; then
      fail "dependency graph is not answering (sbom: $sbom); enable it under Settings > Advanced Security"
    else
      note "verified: dependency graph answers (sbom name: $sbom)"
    fi
  else
    note "current: dependency graph sbom name = $sbom"
  fi
}

ruleset_main_body() {
  local linear=''
  case $MERGE_METHOD in
    squash | rebase) linear=',
    {"type": "required_linear_history"}' ;;
  esac
  cat <<EOF
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
  ],
  "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 0,
      "dismiss_stale_reviews_on_push": false,
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_review_thread_resolution": false,
      "allowed_merge_methods": ["$MERGE_METHOD"]
    }},
    {"type": "required_status_checks", "parameters": {
      "strict_required_status_checks_policy": false,
      "do_not_enforce_on_create": false,
      "required_status_checks": [
        {"context": "unit-tests"},
        {"context": "arch-preflight"},
        {"context": "container-wrapper"},
        {"context": "prototype"}
      ]
    }}$linear
  ]
}
EOF
}

ruleset_tags_body() {
  cat <<'EOF'
{
  "name": "release-tags",
  "target": "tag",
  "enforcement": "active",
  "bypass_actors": [
    {"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}
  ],
  "conditions": {"ref_name": {"include": ["refs/tags/v*"], "exclude": []}},
  "rules": [
    {"type": "creation"},
    {"type": "update"},
    {"type": "deletion"}
  ]
}
EOF
}

# upsert_ruleset NAME BODY EXPECTED_RULE_TYPES: create by POST or update by PUT
# on the ruleset with that name, then verify enforcement and the rule types.
upsert_ruleset() {
  local name=$1 body=$2 wanted_types=$3 id
  id=$(read_jq rulesets "[.[] | select(.name == \"$name\") | .id] | first // empty")
  if [[ -n $id ]]; then
    note "current: ruleset '$name' exists (id $id); updating in place"
    write PUT "rulesets/$id" "$body" "200" || return 0
  else
    note "current: no ruleset named '$name' ($(current rulesets 'length | tostring + " ruleset(s)"'))"
    write POST rulesets "$body" "201" || return 0
    [[ $MODE == apply ]] || return 0
    id=$(read_jq rulesets "[.[] | select(.name == \"$name\") | .id] | first // empty")
    [[ -n $id ]] || { fail "ruleset '$name' not found after creation"; return 0; }
  fi
  check "ruleset '$name' enforcement" "rulesets/$id" '.enforcement' active
  check "ruleset '$name' rule types" "rulesets/$id" '[.rules[].type] | sort | join(",")' "$wanted_types"
  check "ruleset '$name' bypass" "rulesets/$id" '[.bypass_actors[] | "\(.actor_type):\(.actor_id):\(.bypass_mode)"] | join(",")' "RepositoryRole:5:always"
}

step_rulesets() {
  step "Rulesets: main (PR + status checks, no force-push or deletion) and v* tags (owner only)"
  note "merge method: $MERGE_METHOD (change with --merge-method once CONTRIBUTING.md documents the choice)"
  local main_types="deletion,non_fast_forward,pull_request,required_status_checks"
  case $MERGE_METHOD in
    squash | rebase) main_types="deletion,non_fast_forward,pull_request,required_linear_history,required_status_checks" ;;
  esac
  upsert_ruleset main "$(ruleset_main_body)" "$main_types"
  if [[ $MODE == apply ]]; then
    local id
    id=$(read_jq rulesets '[.[] | select(.name == "main") | .id] | first // empty')
    [[ -z $id ]] || check "ruleset 'main' required checks" "rulesets/$id" '[.rules[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context] | sort | join(",")' "arch-preflight,container-wrapper,prototype,unit-tests"
    [[ -z $id ]] || check "ruleset 'main' merge methods" "rulesets/$id" '[.rules[] | select(.type == "pull_request") | .parameters.allowed_merge_methods[]] | join(",")' "$MERGE_METHOD"
  fi
  upsert_ruleset release-tags "$(ruleset_tags_body)" "creation,deletion,update"
  note "CODEOWNERS stays informational: require_code_owner_review is false and zero approvals are required"
}

step_codeql() {
  step "CodeQL default setup ($CODEQL_LANGUAGES)"
  local langs langs_json cur body jq_all lang
  IFS=, read -r -a langs <<<"$CODEQL_LANGUAGES"
  langs_json=$(printf '"%s", ' "${langs[@]}")
  body=$(printf '{"state": "configured", "query_suite": "default", "languages": [%s]}' "${langs_json%, }")
  cur=$(current code-scanning/default-setup '[.state, (.languages | join(","))] | join(" ")')
  note "current: state languages = $cur"
  jq_all='.state == "configured"'
  for lang in "${langs[@]}"; do
    jq_all="$jq_all and (.languages | index(\"$lang\") != null)"
  done
  if [[ $(current code-scanning/default-setup "$jq_all") == true ]]; then
    note "already configured with those languages; the call below is idempotent and skipped"
    show_call PATCH code-scanning/default-setup "$body"
  else
    write PATCH code-scanning/default-setup "$body" "200 202" || return 0
    [[ $MODE == apply && -n $API_BODY ]] && note "first analysis: $(printf '%s' "$API_BODY" | tr -d '\r\n' | head -c 200)"
  fi
  check "code-scanning default setup configured with $CODEQL_LANGUAGES" code-scanning/default-setup "$jq_all" true
}

step_fork_pr_approval() {
  step "Fork pull-request workflow approval for all outside collaborators"
  local body='{"approval_policy": "all_external_contributors"}' cur
  cur=$(current actions/permissions/fork-pr-contributor-approval '.approval_policy')
  note "current: approval_policy = $cur"
  if [[ $cur == all_external_contributors ]]; then
    note "already set; the call below is idempotent and skipped"
    show_call PUT actions/permissions/fork-pr-contributor-approval "$body"
  else
    write PUT actions/permissions/fork-pr-contributor-approval "$body" "204" || return 0
  fi
  check "fork-pr-contributor-approval.approval_policy" actions/permissions/fork-pr-contributor-approval '.approval_policy' all_external_contributors
}

step_actions() {
  step "Actions: SHA pinning required, only GitHub-owned and verified-creator actions"
  local perms='{"enabled": true, "allowed_actions": "selected", "sha_pinning_required": true}'
  local selected='{"github_owned_allowed": true, "verified_allowed": true, "patterns_allowed": []}'
  note "current: allowed_actions sha_pinning_required = $(current actions/permissions '[.allowed_actions, (.sha_pinning_required | tostring)] | join(" ")')"
  note "current: selected-actions = $(current actions/permissions/selected-actions '[.github_owned_allowed, .verified_allowed, (.patterns_allowed | length)] | map(tostring) | join(" ")') (409 while allowed_actions is 'all')"
  write PUT actions/permissions "$perms" "204" || return 0
  write PUT actions/permissions/selected-actions "$selected" "204" || return 0
  check "actions/permissions.allowed_actions" actions/permissions '.allowed_actions' selected
  check "actions/permissions.sha_pinning_required" actions/permissions '.sha_pinning_required | tostring' true
  check "selected-actions github_owned_allowed verified_allowed" actions/permissions/selected-actions '[.github_owned_allowed, .verified_allowed] | map(tostring) | join(" ")' "true true"
  note "consequence: every action reference, GitHub-owned included, must be pinned to a full-length commit SHA (reusable workflows may use a tag);"
  note "actions neither GitHub-owned nor from a verified creator are blocked regardless of pinning. Note this in CONTRIBUTING.md"
}

step_workflow_permissions() {
  step "Workflow token defaults (assert only; already read-only)"
  local body='{"default_workflow_permissions": "read", "can_approve_pull_request_reviews": false}' cur
  cur=$(current actions/permissions/workflow '[.default_workflow_permissions, (.can_approve_pull_request_reviews | tostring)] | join(" ")')
  note "current: default_workflow_permissions can_approve_pull_request_reviews = $cur"
  if [[ $cur == "read false" ]]; then
    note "already correct; the call below is what would restore it"
    show_call PUT actions/permissions/workflow "$body"
  else
    write PUT actions/permissions/workflow "$body" "204" || return 0
  fi
  check "actions/permissions/workflow" actions/permissions/workflow '[.default_workflow_permissions, (.can_approve_pull_request_reviews | tostring)] | join(" ")' "read false"
}

# ------------------------------------------------------------------- main ----

run_step() {
  case $1 in
    visibility) step_visibility ;;
    pvr) step_pvr ;;
    secret-scanning) step_secret_scanning ;;
    secret-alerts) step_secret_alerts ;;
    dependabot) step_dependabot ;;
    rulesets) step_rulesets ;;
    codeql) step_codeql ;;
    fork-pr-approval) step_fork_pr_approval ;;
    actions) step_actions ;;
    workflow-permissions) step_workflow_permissions ;;
    *) printf 'Unknown step: %s (see --help)\n' "$1" >&2; exit 2 ;;
  esac
}

command -v gh >/dev/null || { echo 'gh is required (https://cli.github.com)' >&2; exit 2; }

printf 'enable-protections.sh  %s  mode=%s  repo=%s  merge-method=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$MODE" "$REPO" "$MERGE_METHOD"
printf '%s  as %s\n' "$(gh --version | head -n 1)" "$(gh api user --jq .login 2>/dev/null || echo '<not authenticated>')"
[[ $MODE == apply ]] || printf 'Dry run: nothing below changes the repository.\n'

steps=("${STEPS_ALL[@]}")
if [[ -n $ONLY ]]; then
  IFS=, read -r -a steps <<<"$ONLY"
  for s in "${steps[@]}"; do
    [[ " ${STEPS_ALL[*]} " == *" $s "* ]] || { printf 'Unknown step: %s (see --help)\n' "$s" >&2; exit 2; }
  done
  # The public-visibility guard is not optional when writing.
  [[ $MODE != apply || " ${steps[*]} " == *" visibility "* ]] || steps=(visibility "${steps[@]}")
fi
for s in "${steps[@]}"; do
  run_step "$s"
done

printf '\n'
if [[ $MODE == apply ]]; then
  if ((FAILURES)); then
    printf 'FAILED: %d check(s) did not pass. Fix or re-run; every step is idempotent.\n' "$FAILURES"
    exit 1
  fi
  printf 'All steps applied and verified. File this output in the evidence archive.\n'
else
  printf 'Dry run complete. Re-run with --apply after the repository is public.\n'
fi
