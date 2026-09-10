#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
subject="$repo_root/image/profile-overlay/airootfs/usr/lib/clawos/clawos-enroll-local-node"
temporary="$(mktemp -d)"
trap 'rm -rf -- "$temporary"' EXIT

printf '%s\n' '{"securityLevel":"full-root"}' >"$temporary/security.json"

cat >"$temporary/openclaw" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
state="${CLAWOS_TEST_STATE:?}"
device_id=0123456789abcdef0123456789abcdef
public_key=local-public-key

case "$1 $2" in
  'config get') printf '%s\n' local ;;
  'node identity')
    printf '%s\n' "{\"deviceId\":\"$device_id\",\"publicKey\":\"$public_key\"}"
    ;;
  'devices list')
    if [[ -f "$state/device-approved" ]]; then
      printf '%s\n' "{\"pending\":[],\"paired\":[{\"deviceId\":\"$device_id\",\"publicKey\":\"$public_key\",\"roles\":[\"node\"]}]}"
    else
      printf '%s\n' "{\"pending\":[{\"requestId\":\"device-request\",\"deviceId\":\"$device_id\",\"publicKey\":\"$public_key\",\"clientId\":\"node-host\",\"clientMode\":\"node\",\"roles\":[\"node\"]}],\"paired\":[]}"
    fi
    ;;
  'devices approve') touch "$state/device-approved" ;;
  'node restart') : ;;
  'nodes status')
    if [[ -f "$state/surface-approved" ]]; then
      printf '%s\n' "{\"nodes\":[{\"nodeId\":\"$device_id\",\"paired\":true,\"connected\":true,\"approvalState\":\"approved\"}]}"
    else
      printf '%s\n' '{"nodes":[]}'
    fi
    ;;
  'nodes pending')
    printf '%s\n' "[{\"requestId\":\"surface-request\",\"nodeId\":\"$device_id\",\"displayName\":\"$(hostname)\",\"platform\":\"linux\",\"caps\":[\"clawos.system\"]}]"
    ;;
  'nodes approve') touch "$state/surface-approved" ;;
  *) echo "unexpected fake OpenClaw call: $*" >&2; exit 64 ;;
esac
EOF
chmod 0755 "$temporary/openclaw"

CLAWOS_TEST_STATE="$temporary" \
CLAWOS_OPENCLAW="$temporary/openclaw" \
CLAWOS_SECURITY_CONFIG="$temporary/security.json" \
CLAWOS_SLEEP=/usr/bin/true \
CLAWOS_ENROLL_ATTEMPTS=4 \
  "$subject"

test -f "$temporary/device-approved"
test -f "$temporary/surface-approved"

rm -f "$temporary/device-approved" "$temporary/surface-approved"
printf '%s\n' '{"securityLevel":"full-approvals"}' >"$temporary/security.json"
CLAWOS_TEST_STATE="$temporary" \
CLAWOS_OPENCLAW="$temporary/openclaw" \
CLAWOS_SECURITY_CONFIG="$temporary/security.json" \
CLAWOS_SLEEP=/usr/bin/true \
  "$subject"
test ! -e "$temporary/device-approved"
test ! -e "$temporary/surface-approved"

echo "ClawOS local node enrollment checks passed."
