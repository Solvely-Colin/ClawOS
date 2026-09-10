#!/usr/bin/env bash
# Run ./m1/bin/preflight-iso, the pre-ISO source gate, inside the same
# archlinux:base-devel container that CI uses, so a contributor on Debian,
# Fedora, macOS or Windows (Git Bash) can run it with Docker or Podman instead
# of an Arch install.
#
# .github/workflows/ci.yml, job arch-preflight, is the source of truth for the
# recipe. Its steps run here in the same order: pin the Arch package archive to
# ARCH_SNAPSHOT from m1/config/versions.env, `pacman -Syyuu` the same package
# list, verify Node 24+ and Python 3.12+, add git safe.directory, run
# ./m1/bin/preflight-iso. The one step not repeated is "install git so the
# checkout is a real repository": that exists for actions/checkout, while here
# the checkout already exists on the host and is bind-mounted, so git arrives
# with the other packages. When ci.yml changes, change this script to match.
#
# The checkout is mounted read-only at /src. Every gate writes only under /tmp
# inside the container (mktemp, tempfile), Python skips __pycache__ on a
# read-only filesystem, and `git diff --check` skips its index refresh when it
# cannot take the lock. The container is removed on exit (--rm); nothing is
# written on the host. --writable mounts read-write for a future gate that
# needs it; on Linux that can leave root-owned __pycache__ in the tree.
#
# The exit status is preflight-iso's. With --dbus, the D-Bus caller-boundary
# proof from m3/README.md (m3/tests/verify_dbus_authorization.py) runs after a
# passing preflight, as CI does, and its failure also fails this script.
set -euo pipefail

image=archlinux:base-devel
# Same list as ci.yml; --dbus appends what verify_dbus_authorization.py needs.
packages=(git inetutils nodejs python jq shellcheck)
dbus_packages=(dbus python-dbus python-gobject)

usage() {
  cat <<'EOF'
Usage: tools/dev/preflight-in-container.sh [options]

Run ./m1/bin/preflight-iso inside archlinux:base-devel with the Arch package
snapshot pinned from m1/config/versions.env, exactly as CI's arch-preflight job
does (.github/workflows/ci.yml). Needs Docker or Podman and network access to
archive.archlinux.org. Exit status is preflight-iso's.

Options:
  --engine docker|podman  Container engine (default: docker if found, else
                          podman; CONTAINER_ENGINE in the environment also works)
  --dbus                  Also run m3/tests/verify_dbus_authorization.py after a
                          passing preflight, with the extra packages CI installs
  --writable              Mount the checkout read-write instead of read-only
  -h, --help              Show this help

Run it from a normal clone. The checkout is mounted at /src; nothing is written
outside the container.
EOF
}

die() {
  printf 'preflight-in-container: %s\n' "$@" >&2
  exit 1
}

# ----------------------------------------------------------------------------
# Container side. Reached only through the `docker run`/`podman run` below;
# it rewrites /etc/pacman.d/mirrorlist and runs pacman -Syyuu, so it refuses
# to run anywhere but the disposable container this script starts.
# ----------------------------------------------------------------------------
run_inside() {
  local dbus=$1 owner log status

  [[ "${CLAWOS_PREFLIGHT_CONTAINER:-}" == 1 && "$PWD" == /src ]] &&
    [[ -f /.dockerenv || -f /run/.containerenv ]] ||
    die '--inside is internal: it runs only in the container this script starts.'

  # ci.yml "Install preflight tooling from the pinned Arch snapshot"
  # shellcheck source=m1/config/versions.env
  source m1/config/versions.env
  [[ "$ARCH_SNAPSHOT" =~ ^[0-9]{4}/[0-9]{2}/[0-9]{2}$ ]] || die 'ARCH_SNAPSHOT must be YYYY/MM/DD'
  printf 'Server = https://archive.archlinux.org/repos/%s/$repo/os/$arch\n' "$ARCH_SNAPSHOT" >/etc/pacman.d/mirrorlist
  if (( dbus )); then
    packages+=("${dbus_packages[@]}")
  fi
  pacman -Syyuu --noconfirm --needed --disable-download-timeout "${packages[@]}"

  # ci.yml "Verify the toolchain the README promises"
  node --version; python3 --version; jq --version; git --version
  node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 24 ? 0 : 1)'
  python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'

  # ci.yml "Trust the checkout owned by the runner account"; here the checkout
  # belongs to the host user, and the container runs as root.
  git config --global --add safe.directory /src

  # ci.yml "Run the pre-ISO source gate". Its status is this script's status.
  status=0
  ./m1/bin/preflight-iso || status=$?
  (( status == 0 )) || exit "$status"
  (( dbus )) || exit 0

  # The proof resolves openclaw.ownerUser through the OS account database, so
  # the account must exist; nobody ships with Arch's filesystem package.
  owner="$(jq -er '.openclaw.ownerUser' m3/config/clawosd.json)"
  [[ "$owner" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || die "unexpected ownerUser: $owner"
  id -u "$owner" >/dev/null 2>&1 || useradd --create-home "$owner"
  id "$owner"
  id nobody

  # Same command as m3/README.md minus sudo (the container is root). The
  # script exits non-zero on a failed assertion; the grep also fails this run
  # if its PASS line is ever missing.
  echo "[dbus] m3/tests/verify_dbus_authorization.py"
  log="$(mktemp)"
  python3 m3/tests/verify_dbus_authorization.py "$PWD" | tee "$log"
  grep -q '^PASS: ' "$log"
}

# ----------------------------------------------------------------------------
# Host side.
# ----------------------------------------------------------------------------
engine="${CONTAINER_ENGINE:-}"
dbus=0
mount_mode=:ro
inside=0

while (( $# )); do
  case "$1" in
    --inside) inside=1 ;;
    --dbus) dbus=1 ;;
    --writable) mount_mode= ;;
    --engine) [[ $# -ge 2 ]] || die '--engine needs a value: docker or podman'; engine=$2; shift ;;
    --engine=*) engine=${1#--engine=} ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; die "unknown option: $1" ;;
  esac
  shift
done

if (( inside )); then
  run_inside "$dbus"
  exit 0
fi

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$repo_root"

# Refuse to run outside a repository checkout. preflight-iso ends with
# `git diff --check`, which needs the repository, and the checkout's own
# .git directory must travel with the bind mount: a linked worktree or
# submodule keeps a `.git` file that points outside the tree, which the
# container cannot follow.
for marker in m1/bin/preflight-iso m1/config/versions.env .github/workflows/ci.yml; do
  [[ -f "$marker" ]] || die "$repo_root is not a ClawOS checkout: $marker is missing."
done
[[ -e .git ]] || die "$repo_root is not a git checkout (no .git); clone the repository instead of downloading it."
[[ -d .git && -f .git/HEAD ]] ||
  die "$repo_root/.git is not the repository directory (a git worktree or submodule?). Run this from a normal clone."

# Fail before pulling an image if the pin is malformed; the container checks it again.
# shellcheck source=m1/config/versions.env
source m1/config/versions.env
[[ "${ARCH_SNAPSHOT:-}" =~ ^[0-9]{4}/[0-9]{2}/[0-9]{2}$ ]] || die 'ARCH_SNAPSHOT in m1/config/versions.env must be YYYY/MM/DD'

if [[ -z "$engine" ]]; then
  if command -v docker >/dev/null 2>&1; then
    engine=docker
  elif command -v podman >/dev/null 2>&1; then
    engine=podman
  else
    die 'neither docker nor podman was found; install one, or run ./m1/bin/preflight-iso on Arch.'
  fi
fi
case "$engine" in
  docker|podman) ;;
  *) die "--engine must be docker or podman, not '$engine'" ;;
esac
command -v "$engine" >/dev/null 2>&1 || die "$engine was requested but is not on PATH."

# Git Bash on Windows rewrites arguments that look like POSIX paths before a
# native program such as docker.exe sees them, turning "/d/repo:/src" into a
# Windows path list. Hand Docker a drive-letter path and turn that rewriting
# off for this one invocation.
mount_source="$repo_root"
tty_ok=1
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    if command -v cygpath >/dev/null 2>&1; then
      mount_source="$(cygpath -m "$repo_root")"
    fi
    export MSYS_NO_PATHCONV=1
    # docker.exe cannot attach a pseudo-terminal from mintty without winpty.
    tty_ok=0
    ;;
esac

run=("$engine" run --rm
  --env CLAWOS_PREFLIGHT_CONTAINER=1
  --volume "${mount_source}:/src${mount_mode}"
  --workdir /src)
if [[ "$engine" == podman ]]; then
  # Rootless Podman on an SELinux host would otherwise need :Z, which relabels
  # the checkout on the host; disabling labeling for this container avoids
  # writing anything there.
  run+=(--security-opt label=disable)
fi
if (( tty_ok )) && [[ -t 0 && -t 1 ]]; then
  run+=(--tty)
fi
inside_args=(--inside)
if (( dbus )); then
  inside_args+=(--dbus)
fi
run+=("$image" bash /src/tools/dev/preflight-in-container.sh "${inside_args[@]}")

mount_desc=read-write
if [[ -n "$mount_mode" ]]; then
  mount_desc=read-only
fi
printf 'preflight-in-container: %s, %s, Arch snapshot %s, %s mounted %s at /src\n' \
  "$engine" "$image" "$ARCH_SNAPSHOT" "$repo_root" "$mount_desc"
exec "${run[@]}"
