#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
root="$repo_root/m1/profile-overlay/airootfs"
entry="$root/usr/lib/clawos/clawos-entry"
onboard="$root/usr/lib/clawos/clawos-onboard"
browser="$root/usr/lib/clawos/clawos-browser"
node_install="$root/usr/lib/clawos/clawos-install-node"
installer="$root/usr/local/bin/clawos-install-dev"

bash -n "$entry" "$onboard" "$browser" "$node_install" "$installer"

grep -Fq 'openclaw onboard' "$onboard"
grep -Fq -- '--classic' "$onboard"
grep -Fq -- '--mode local' "$onboard"
grep -Fq -- '--mode remote' "$onboard"
grep -Fq -- '--gateway-auth token' "$onboard"
grep -Fq -- '--flow manual' "$onboard"
grep -Fq -- '--install-daemon' "$onboard"
grep -Fq -- '--skip-daemon' "$onboard"
grep -Fq -- '--skip-ui' "$onboard"
grep -Fq -- '--suppress-gateway-token-output' "$onboard"
grep -Fq 'nmtui-connect' "$onboard"
grep -Fq 'gateway.mode' "$entry"
grep -Fq 'clawos-install-node' "$entry"
grep -Fq 'output Virtual-1 mode 1440x900 scale 1' "$root/etc/clawos/sway.conf"
grep -Fq 'gateway.remote.url' "$node_install"
grep -Fq 'ws://127.0.0.1:$port' "$node_install"
grep -Fq 'umask 077' "$browser"
grep -Fq 'file://$bootstrap' "$browser"
grep -Fq 'read_config_string gateway.auth.token' "$browser"
if grep -Eq 'config get gateway\.(auth|remote)\.token' "$browser"; then
  echo "ClawOS browser must not use OpenClaw's redacted config output as a token." >&2
  exit 1
fi
grep -Fq 'npm install --global' "$installer"
grep -Fq '"openclaw@$OPENCLAW_VERSION"' "$installer"
grep -Fq -- "--allow-scripts='openclaw,@google/genai,tree-sitter-bash,protobufjs'" "$installer"
grep -Fq 'umask 022' "$installer"
grep -Fq 'runuser -u clawos -- openclaw --version' "$installer"

if grep -Eq -- '--(openai|anthropic|gemini|remote)-.*key' "$onboard"; then
  echo "ClawOS onboarding must not pass provider secrets on the command line." >&2
  exit 1
fi

if [[ -d "$root/usr/share/clawos-launch" ]]; then
  echo "Parallel ClawOS web shell detected." >&2
  exit 1
fi

echo "ClawOS onboarding static checks passed."
