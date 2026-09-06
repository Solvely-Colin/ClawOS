#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
subject="$repo_root/m1/profile-overlay/airootfs/usr/lib/clawos/clawos-attention-status"
temporary="$(mktemp -d)"
trap 'rm -rf -- "$temporary"' EXIT
mkdir -p "$temporary/runtime/clawos" "$temporary/state/clawos"
printf '%s\n' '{"activity":{"state":"waiting"},"attention":{"count":0}}' >"$temporary/runtime/clawos/activity.json"

cat >"$temporary/clawosctl" <<'EOF'
#!/usr/bin/env bash
if [[ "${CLAWOS_TEST_MODE:-full}" == full ]]; then
  printf '%s\n' '[{"id":"machine-1"}]'
else
  printf '%s\n' '[]'
fi
EOF

cat >"$temporary/openclaw" <<'EOF'
#!/usr/bin/env bash
if [[ "$1 $2" == 'approvals pending' ]]; then
  if [[ "${CLAWOS_TEST_MODE:-full}" == full ]]; then
    printf '%s\n' '[{"id":"approval-1"}]'
  else
    printf '%s\n' '[]'
  fi
elif [[ "$1 $2" == 'tasks list' ]]; then
  if [[ "${CLAWOS_TEST_MODE:-full}" == skipped ]]; then
    printf '%s\n' '{"tasks":[{"id":"skipped-1","runtime":"cron","taskKind":"automation_run","status":"failed","detail":{"status":"skipped"}}]}'
  else
    printf '%s\n' '{"tasks":[{"id":"active-1","status":"running"},{"id":"failed-1","status":"failed"},{"id":"skipped-1","runtime":"cron","taskKind":"automation_run","status":"failed","detail":{"status":"skipped"}}]}'
  fi
elif [[ "$1" == list ]]; then
  printf '%s\n' '[]'
else
  exit 64
fi
EOF
chmod 0755 "$temporary/clawosctl" "$temporary/openclaw"

run_status() {
  # Each fixture is a new source response, not the preceding five-second cache.
  rm -f -- "$temporary/runtime/clawos/work-snapshot.json"
  XDG_RUNTIME_DIR="$temporary/runtime" \
  XDG_STATE_HOME="$temporary/state" \
  CLAWOS_CTL="$temporary/clawosctl" \
  CLAWOS_OPENCLAW="$temporary/openclaw" \
  CLAWOS_AGENT_REQUEST="$temporary/openclaw" \
  CLAWOS_DEPLOY_RECEIPTS_DIR="$temporary/receipts" \
  CLAWOS_TEST_MODE="${1:-full}" \
    "$subject"
}

first="$(run_status full)"
printf '%s' "$first" | jq -e '.text == "Review 3" and .class == "attention"' >/dev/null

printf '%s\n' '{"version":1,"taskIds":["failed-1"]}' >"$temporary/state/clawos/center-seen.json"
second="$(run_status active)"
printf '%s' "$second" | jq -e '.text == "Working 1" and .class == "normal"' >/dev/null

printf '%s\n' '{"version":1,"taskIds":["failed-1"]}' >"$temporary/state/clawos/center-seen.json"
third="$(run_status skipped)"
printf '%s' "$third" | jq -e '.text == "Work" and .class == "normal"' >/dev/null

echo "ClawOS durable attention checks passed."
