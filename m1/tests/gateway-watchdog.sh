#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
watchdog="$repo_root/m1/profile-overlay/airootfs/usr/lib/clawos/clawos-gateway-watchdog"
port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()')"
server_pid=
target_pid=
watchdog_pid=

cleanup() {
  for pid in "$watchdog_pid" "$target_pid" "$server_pid"; do
    [[ "$pid" =~ ^[1-9][0-9]*$ ]] || continue
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

python3 -m http.server "$port" --bind 127.0.0.1 >/dev/null 2>&1 &
server_pid=$!
/usr/bin/sleep 60 &
target_pid=$!
"$watchdog" "$target_pid" "http://127.0.0.1:$port/" &
watchdog_pid=$!

# Let the watchdog observe one healthy response before simulating a restart.
/usr/bin/sleep 2
kill "$server_pid"
wait "$server_pid" 2>/dev/null || true
server_pid=

for _ in {1..12}; do
  if ! kill -0 "$target_pid" 2>/dev/null; then
    wait "$watchdog_pid"
    watchdog_pid=
    target_pid=
    echo "ClawOS Gateway watchdog checks passed."
    exit 0
  fi
  /usr/bin/sleep 0.5
done

echo "Gateway watchdog did not recycle its browser target." >&2
exit 1
