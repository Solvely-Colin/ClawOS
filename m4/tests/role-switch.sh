#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
fixture="$repo_root/m4/tests/fixtures"
runtime="$(mktemp -d /tmp/clawos-role-test.XXXXXX)"
trap 'rm -rf -- "$runtime"' EXIT
export HOME="$runtime/home"
export XDG_STATE_HOME="$runtime/state"
export XDG_RUNTIME_DIR="$runtime/run"
export CLAWOS_OPENCLAW_BIN="$fixture/fake-openclaw"
export CLAWOS_SYSTEMCTL_BIN="$fixture/fake-systemctl"
export CLAWOS_NODE_INSTALLER="$fixture/fake-node-installer"
role="$repo_root/m1/profile-overlay/airootfs/usr/lib/clawos/clawos-role"

mkdir -p "$HOME/.openclaw" "$XDG_RUNTIME_DIR"
printf '{"gateway":{"mode":"local","auth":{"token":"local-reference"}}}\n' >"$HOME/.openclaw/openclaw.json"
printf 'OPENCLAW_GATEWAY_TOKEN=local-secret\n' >"$HOME/.openclaw/.env"
"$role" profile-save

printf '{"gateway":{"mode":"remote","remote":{"url":"wss://controller.example"}}}\n' >"$HOME/.openclaw/openclaw.json"
printf 'OPENCLAW_GATEWAY_TOKEN=remote-secret\n' >"$HOME/.openclaw/.env"
"$role" profile-save

install -m 0600 "$XDG_STATE_HOME/clawos/roles/local/openclaw.json" "$HOME/.openclaw/openclaw.json"
install -m 0600 "$XDG_STATE_HOME/clawos/roles/local/.env" "$HOME/.openclaw/.env"
"$role" switch node
test "$("$CLAWOS_OPENCLAW_BIN" config get gateway.mode)" = remote
grep -Fq 'remote-secret' "$HOME/.openclaw/.env"

"$role" switch standalone
test "$("$CLAWOS_OPENCLAW_BIN" config get gateway.mode)" = local
CLAWOS_TEST_FAIL_NODE=1 "$role" switch node >/dev/null 2>&1 && exit 1
test "$("$CLAWOS_OPENCLAW_BIN" config get gateway.mode)" = local
grep -Fq 'local-secret' "$HOME/.openclaw/.env"
test -s "$XDG_STATE_HOME/clawos/roles/remote/openclaw.json"
echo "Transactional Standalone/Node role switching passed."
