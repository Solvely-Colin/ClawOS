#!/usr/bin/env bash
# Run only in the disposable CI container, never on a developer workstation.
set -euo pipefail
[[ "$EUID" == 0 && "${GITHUB_ACTIONS:-}" == true && -f /.dockerenv && "$PWD" == /src ]] || {
  echo 'This helper requires the disposable GitHub Actions build container at /src.' >&2
  exit 1
}
source image/config/versions.env
[[ ${GITHUB_RUN_ID:-} =~ ^[0-9]+$ && ${GITHUB_SHA:-} =~ ^[0-9a-f]{40}$ ]] || {
  echo 'Expected the workflow run ID and exact source SHA.' >&2; exit 1;
}
[[ "$ARCH_SNAPSHOT" =~ ^[0-9]{4}/[0-9]{2}/[0-9]{2}$ ]] || exit 1
printf 'Server = https://archive.archlinux.org/repos/%s/$repo/os/$arch\n' "$ARCH_SNAPSHOT" >/etc/pacman.d/mirrorlist
pacman -Syyuu --noconfirm --needed --disable-download-timeout \
  base-devel archiso mkinitcpio git inetutils nodejs npm python jq rsync socat \
  openssh sudo shellcheck qemu-desktop edk2-ovmf
[[ "$(pacman -Q archiso)" == "archiso $ARCHISO_VERSION" ]] || {
  echo 'ArchISO build-tool version differs from the lock; review the build inputs.' >&2
  exit 1
}
useradd --create-home clawos-ci
chown -R clawos-ci:clawos-ci /src
git config --global --add safe.directory /src
runuser -u clawos-ci -- bash -c 'cd /src && ./image/bin/preflight-iso'
SUDO_USER=clawos-ci SUDO_UID="$(id -u clawos-ci)" ./image/bin/build-iso --release
out=/src/artifacts/m1/out
(
  cd "$out"
  shopt -s nullglob
  images=(*.iso)
  [[ ${#images[@]} == 1 ]] || { echo 'Expected one validated ISO.' >&2; exit 1; }
  sha256sum "${images[0]}" >SHA256SUMS
  sha256sum "${images[0]}" >"${images[0]}.sha256"
)
{
  printf 'Source commit: %s\n' "$GITHUB_SHA"
  printf 'Build channel: experimental development ISO\n'
  printf 'Validation: source preflight and ISO boot-chain structure\n'
  printf 'Live boot smoke: NOT RUN\n'
  printf 'Passwordless install smoke: NOT RUN\n'
  printf 'Onboarding/encrypted-install/hardware acceptance: NOT RUN by this workflow\n'
  printf 'Installer: experimental x86_64 UEFI blank disks; physical hardware NOT verified\n'
  cat image/config/versions.env
} >"$out/BUILD-METADATA.txt"
pacman -Q >"$out/BUILD-PACKAGES.txt"

# Same freshly built ISO and Arch/QEMU userspace; no host firmware-path guess.
shopt -s nullglob
images=("$out/"*.iso)
(( ${#images[@]} == 1 )) || { echo 'Expected one ISO for boot smoke.' >&2; exit 1; }
if CLAWOS_SMOKE_RUNTIME="$out/boot-smoke" \
    ./image/tests/boot-smoke-qemu "${images[0]}"; then
  sed -i "s/^Live boot smoke: NOT RUN$/Live boot smoke: RUN (KVM, run $GITHUB_RUN_ID)/" \
    "$out/BUILD-METADATA.txt"
else
  status=$?
  sed -i "s/^Live boot smoke: NOT RUN$/Live boot smoke: FAILED (KVM, run $GITHUB_RUN_ID)/" \
    "$out/BUILD-METADATA.txt"
  exit "$status"
fi

# Fresh disposable disk; at most 60 minutes, with ACPI-only guest cleanup.
if CLAWOS_INSTALL_RUNTIME="$out/install-smoke" \
    timeout --signal=TERM --foreground 60m ./image/tests/install-smoke-qemu "${images[0]}"; then
  sed -i "s/^Passwordless install smoke: NOT RUN$/Passwordless install smoke: RUN (KVM, run $GITHUB_RUN_ID)/" \
    "$out/BUILD-METADATA.txt"
else
  status=$?
  sed -i "s/^Passwordless install smoke: NOT RUN$/Passwordless install smoke: FAILED (KVM, run $GITHUB_RUN_ID)/" \
    "$out/BUILD-METADATA.txt"
  exit "$status"
fi
