#!/usr/bin/env bash
set -euo pipefail

# shellcheck disable=SC2154  # status is assigned inside the trap string itself
trap 'status=$?; printf "ClawOS image profile validation failed at line %s (exit %s).\n" "$LINENO" "$status" >&2' ERR

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
profile="${1:-$repo_root/m1/profile-overlay}"

# shellcheck source=../config/versions.env
source "$repo_root/m1/config/versions.env"

node_check() {
  local script="$1"
  if command -v node >/dev/null 2>&1; then
    node --check "$script"
    return
  fi

  # pkexec and sudo intentionally provide root with a restricted PATH. The
  # developer's Node runtime is sufficient for a read-only syntax check, but
  # it must stay under the invoking UID rather than executing user-owned code
  # as root during an ISO build.
  local caller_uid="${SUDO_UID:-${PKEXEC_UID:-}}"
  local caller_name=
  if [[ $EUID -eq 0 && "$caller_uid" =~ ^[0-9]+$ ]]; then
    caller_name="$(getent passwd "$caller_uid" | cut -d: -f1)"
  fi
  if [[ -n "$caller_name" ]] &&
     runuser -u "$caller_name" -- /usr/bin/bash -lc 'node --check "$1"' _ "$script"; then
    return
  fi

  echo "Node.js is required to validate $script." >&2
  return 1
}

grep -Fq 'materialize-profile" "$profile"' "$repo_root/m1/bin/build-iso"
grep -Fq 'm2/openclaw-plugin/.' "$repo_root/m1/bin/materialize-profile"
grep -Fq 'find "$generated_dir" -depth -delete' "$repo_root/m1/bin/build-iso"
grep -Fq -- '-device virtio-vga,xres=1440,yres=900' "$repo_root/m1/bin/run-qemu"

grep -Fqx 'SigLevel = Required DatabaseOptional' "$repo_root/m1/profile-overlay/pacman.conf"
if grep -RniE 'SigLevel[[:space:]]*=[[:space:]]*(Never|Optional)' \
  "$repo_root/m1/profile-overlay" "$repo_root/m1/config"; then
  echo "Weak package signature policy detected." >&2
  exit 1
fi

if grep -RniE 'omarchy|omacom|basecamp/omarchy' \
  "$repo_root/m1/profile-overlay" "$repo_root/m1/config"; then
  echo "Omarchy contamination detected in build inputs." >&2
  exit 1
fi

grep -Fqx "Server = https://archive.archlinux.org/repos/${ARCH_SNAPSHOT}/\$repo/os/\$arch" \
  "$repo_root/m1/config/mirrorlist"

for package in base chromium foot fuzzel gtk-layer-shell gtk3 inter-font linux linux-firmware lxqt-policykit mesa mkinitcpio-archiso networkmanager nodejs noto-fonts npm openssh orca plymouth python-gobject sway swaybg syslinux waybar zsh; do
  grep -Fqx "$package" "$repo_root/m1/profile-overlay/packages.x86_64"
done

# ArchISO's releng initramfs includes the memdisk hook even for a UEFI-only
# image. syslinux supplies memdiskfind, which that hook runs before archiso can
# discover and mount the live root filesystem.
archiso_mkinitcpio="$profile/airootfs/etc/mkinitcpio.conf.d/archiso.conf"
if [[ -f "$archiso_mkinitcpio" ]] && grep -Fq 'memdisk' "$archiso_mkinitcpio"; then
  grep -Fqx 'syslinux' "$repo_root/m1/profile-overlay/packages.x86_64"
fi

if [[ -f "$archiso_mkinitcpio" ]] && grep -Fq 'archiso' "$archiso_mkinitcpio"; then
  grep -Fqx 'mkinitcpio-archiso' "$repo_root/m1/profile-overlay/packages.x86_64"
fi

if [[ -f "$profile/airootfs/etc/passwd" ]] && \
   grep -Eq '^root:.*:/usr/bin/zsh$' "$profile/airootfs/etc/passwd"; then
  grep -Fqx 'zsh' "$repo_root/m1/profile-overlay/packages.x86_64"
fi

grep -Fq "bootmodes=('uefi.systemd-boot')" "$repo_root/m1/profile-overlay/profiledef.sh"
if grep -Fq 'bios.' "$repo_root/m1/profile-overlay/profiledef.sh"; then
  echo "Legacy BIOS boot mode is outside the ClawOS UEFI target." >&2
  exit 1
fi

if [[ -d "$profile/airootfs" ]]; then
  "$repo_root/m1/tests/no-omarchy.sh" "$profile/airootfs"
fi

installer="$profile/airootfs/usr/local/bin/clawos-install-dev"
if [[ -f "$installer" ]]; then
  test -s "$profile/airootfs/usr/share/licenses/clawos-radix-icons/LICENSE"
  grep -Fq 'install -D -m 0644 /usr/share/licenses/clawos-radix-icons/LICENSE' "$installer"
  grep -Fq '"$mount_root/usr/share/licenses/clawos-radix-icons/LICENSE"' "$installer"
  # Pin the guard placement, not just its existence: the pre-erase validate
  # must sit directly above sfdisk and an identity recheck above the first format.
  grep -Fq 'recheck validate --confirm "$confirmation" >/dev/null' "$installer"
  grep -Fq 'if $vm_test; then' "$installer"
  grep -A4 -F 'recheck validate --confirm "$confirmation" >/dev/null' "$installer" | grep -Fq 'sfdisk --wipe always'
  grep -A1 -F 'recheck check-identity' "$installer" | grep -Fq 'mkfs.fat'
  # bootctl must run from the live system (a chroot silently skips NVRAM).
  grep -Fq 'bootctl --esp-path="$mount_root/boot" --graceful install' "$installer"
  ! grep -Fq 'arch-chroot "$mount_root" bootctl' "$installer"
  grep -Fq -- '--passwordless) passwordless=true' "$installer"
  grep -Fq 'clawos-passwordless-entry' "$installer"
  # A passwordless install must announce itself on the installed machine, and
  # only there: the login-prompt and MOTD drop-ins have to sit inside the
  # passwordless account block, after the clawos-lock opt-in file and before
  # that block's else branch.
  passwordless_block="$(grep -A20 -F 'chmod 0644 "$mount_root/etc/clawos-passwordless-entry"' "$installer" | sed -n '1,/^else$/p')"
  grep -Fq 'install -d -m 0755 "$mount_root/etc/issue.d" "$mount_root/etc/motd.d"' <<<"$passwordless_block"
  grep -Fq '"$mount_root/etc/issue.d/clawos-passwordless.issue"' <<<"$passwordless_block"
  grep -Fq '"$mount_root/etc/motd.d/clawos-passwordless"' <<<"$passwordless_block"
  notice="$(sed -n "/clawos-passwordless.issue\" <<'EOF'\$/,/^EOF\$/p" <<<"$passwordless_block")"
  grep -Fqx 'Passwordless ClawOS install: no disk encryption, empty account passwords, no screen lock.' <<<"$notice"
  grep -Fqx 'Anyone with access to this machine can use it and read its data.' <<<"$notice"
  # agetty expands backslashes in issue files; the notice must stay literal.
  # A negated command never trips set -e or the ERR trap, so test explicitly.
  if grep -Fq '\' <<<"$notice"; then
    echo "Passwordless notice must not contain backslashes; agetty expands them." >&2
    exit 1
  fi
  # Remote password login must be off in both install modes: the account
  # password is the LUKS passphrase or empty.
  sshd_dropin="$profile/airootfs/etc/ssh/sshd_config.d/00-clawos.conf"
  grep -Fqx 'PasswordAuthentication no' "$sshd_dropin"
  grep -Fqx 'KbdInteractiveAuthentication no' "$sshd_dropin"
  grep -Fqx 'PermitRootLogin no' "$sshd_dropin"
  grep -Fq 'install -m 0644 /etc/ssh/sshd_config.d/00-clawos.conf' "$installer"
  grep -B12 -F 'install -m 0644 /etc/ssh/sshd_config.d/00-clawos.conf' "$installer" | grep -Fq 'install -m 0440 /etc/clawos/full-root.sudoers'
  grep -Fq "Disk identity changed {when}" "$profile/airootfs/usr/lib/clawos/clawos_install_targets.py"
  grep -Fq "when='since selection; inspect and select again'" "$profile/airootfs/usr/lib/clawos/clawos_install_targets.py"
  grep -Fq "'pttype'" "$profile/airootfs/usr/lib/clawos/clawos_install_targets.py"
  grep -Fq 'clawos-live-serial-getty' "$profile/airootfs/etc/systemd/system/serial-getty@ttyS0.service.d/autologin.conf"
  grep -Fq 'Standard PC (Q35 + ICH9, 2009)' "$profile/airootfs/usr/lib/clawos/clawos-live-serial-getty"
  grep -Fq 'systemd-detect-virt --vm' "$installer"
  grep -Fq 'Kernel did not expose the expected EFI and system partitions.' "$installer"
  grep -Fq 'Standard PC (Q35 + ICH9, 2009)' "$installer"
  grep -Fq '/run/user/[0-9]+/clawos-install' "$installer"
  grep -Fq 'clawos-session@clawos.service' "$installer"
  packages="$profile/airootfs/usr/lib/clawos/clawos-install-packages.sh"
  bash -n "$packages"
  grep -Fq 'chromium foot fuzzel sway swaybg waybar' "$packages"
  grep -Fq 'noto-fonts inter-font otf-geist-mono-nerd' "$packages"
  ! grep -Eq 'otf-geist-mono-nerd[[:space:]]+\+' "$packages"
  grep -Fq 'networkmanager openssh sudo zsh tmux curl jq' "$packages"
  grep -Fq 'nodejs npm polkit lxqt-policykit plymouth tailscale' "$packages"
  grep -Fq 'prepare_install_packages "$download_root"' "$installer"
  grep -Fq 'pacstrap -K -U -C "$download_root/local.conf"' "$installer"
  grep -Fq 'LocalFileSigLevel = Required' "$packages"
  grep -Fq 'cp -a /usr/lib/node_modules/openclaw' "$installer"
  ! grep -Fq 'npm install --global' "$installer"
  grep -Fq 'umask 022' "$installer"
  grep -Fq 'runuser -u clawos -- openclaw --version' "$installer"
  grep -Fq 'block plymouth sd-encrypt' "$installer"
  grep -Fq 'quiet splash loglevel=3' "$installer"
  grep -Fq 'plymouth.ignore-serial-consoles' "$installer"
  grep -Fq 'cp -a /usr/share/plymouth/themes/clawos/.' "$installer"
  grep -Fq 'clawos-panel-status' "$installer"
  grep -Fq 'clawos-clock-status' "$installer"
  grep -Fq 'clawos-refresh-agent-ui' "$installer"
  grep -Fq 'gtklock gtklock-userinfo-module gtk-layer-shell python-gobject orca' "$packages"
  grep -Fq 'passwd --root "$mount_root" --stdin clawos <"$key_file"' "$installer"
  grep -Fq 'clawos-panel' "$installer"
  grep -Fq 'clawos-command' "$installer"
  grep -Fq 'clawos-build' "$installer"
  grep -Fq 'clawos-browse' "$installer"
  grep -Fq 'clawosd.service clawos-session@clawos.service' "$installer"
fi

m3_root="$repo_root/m3"
for m3_file in \
  clawosd/clawosd_core.py clawosd/clawosd_service.py clawosd/clawosctl.py \
  clawosd/clawos_approval.py config/clawosd.json systemd/clawosd.service \
  dbus/org.clawos.System.conf dbus/org.clawos.System.service \
  dbus/org.clawos.System.xml polkit/org.clawos.system.policy; do
  test -f "$m3_root/$m3_file"
done
python3 -c 'import ast, pathlib, sys; [ast.parse(pathlib.Path(path).read_text()) for path in sys.argv[1:]]' \
  "$m3_root/clawosd/clawosd_core.py" "$m3_root/clawosd/clawosd_service.py" \
  "$m3_root/clawosd/clawosctl.py" "$m3_root/clawosd/clawos_approval.py"
python3 - "$m3_root/clawosd/clawos_approval.py" <<'PY'
import ast
import pathlib
import sys

tree = ast.parse(pathlib.Path(sys.argv[1]).read_text())
center_css = next(
    ast.literal_eval(node.value)
    for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(target, ast.Name) and target.id == "CENTER_CSS" for target in node.targets)
)
assert b"#center-panel" in center_css
assert b"@claw_coral" in center_css
PY
python3 -c 'import sys, xml.etree.ElementTree as ET; [ET.parse(path) for path in sys.argv[1:]]' \
  "$m3_root/dbus/org.clawos.System.xml" "$m3_root/polkit/org.clawos.system.policy"
jq -e '.version == 1 and .securityLevel == "full-root" and (.packages.allow | index("tree")) and (.services.allow | index("sshd.service")) and .openclaw.promotedVersion and .openclaw.agentUser == "claw" and .agentPolicies.coreAgentId == "main" and .agentPolicies.requireTrustedAttribution == true and (.agentPolicies.agents.main | index("*")) and (.taskGrants.grantableActions | index("service.manage"))' \
  "$m3_root/config/clawosd.json" >/dev/null
grep -Fq 'clawos ALL=(ALL:ALL) NOPASSWD: ALL' \
  "$repo_root/m1/profile-overlay/airootfs/etc/clawos/full-root.sudoers"
grep -Fq '90-clawos-full-root' \
  "$repo_root/m1/profile-overlay/airootfs/usr/local/bin/clawos-install-dev"
grep -Fq 'ProtectSystem=strict' "$m3_root/systemd/clawosd.service"
grep -Fq 'RuntimeDirectory=clawosd' "$m3_root/systemd/clawosd.service"
if grep -Eq '^(NoNewPrivileges|CapabilityBoundingSet)=' "$m3_root/systemd/clawosd.service"; then
  echo "clawosd may not strip privileges required by an approved package transaction" >&2
  exit 1
fi
grep -Fq 'auth_admin' "$m3_root/polkit/org.clawos.system.policy"
grep -Fq 'm3/clawosd/clawosd_core.py' "$repo_root/m1/bin/materialize-profile"
grep -Fq 'title="ClawOS Center"' "$m3_root/clawosd/clawos_approval.py"
grep -Fq 'header.set_size_request(-1, 86)' "$m3_root/clawosd/clawos_approval.py"
grep -Fq 'from clawos_attention import collect, acknowledge, actionable_failure' "$m3_root/clawosd/clawos_approval.py"
grep -Fq 'openclaw("approvals", "resolve"' "$m3_root/clawosd/clawos_approval.py"
! grep -Fq '[APPCTL, "clear-attention"]' "$m3_root/clawosd/clawos_approval.py"

for launch_file in \
  usr/lib/clawos/clawos-session \
  usr/lib/clawos/clawos-browser \
  usr/lib/clawos/clawos-entry \
  usr/lib/clawos/clawos-onboard \
  usr/lib/clawos/clawos-onboard-ui \
  usr/lib/clawos/clawos-onboard-server \
  usr/lib/clawos/clawos-install-node \
  usr/lib/clawos/clawos-panel \
  usr/lib/clawos/clawos-panel-status \
  usr/lib/clawos/clawos-clock-status \
  usr/lib/clawos/clawos-activity-status \
  usr/lib/clawos/clawos-activity-action \
  usr/lib/clawos/clawos-actions-menu \
  usr/lib/clawos/clawos-agent-panel \
  usr/lib/clawos/clawos-agent-panel-status \
  usr/lib/clawos/clawos-agent-submit \
  usr/lib/clawos/clawos-agent-run \
  usr/lib/clawos/clawos-agent-request \
  usr/lib/clawos/clawos-agent-recover \
  usr/lib/clawos/clawos-screen-reader-toggle \
  usr/lib/clawos/clawos-attention-status \
  usr/lib/clawos/clawos-surface \
  usr/lib/clawos/clawos-surfaced \
  usr/lib/clawos/app-registry.cjs \
  usr/lib/clawos/clawos-appctl \
  usr/lib/clawos/clawos-app-from-fuzzel \
  usr/lib/clawos/clawos-intent-palette \
  usr/lib/clawos/clawos-app-palette \
  usr/lib/clawos/clawos-webapp \
  usr/lib/clawos/clawos-return-to-setup \
  usr/lib/clawos/clawos-role \
  usr/lib/clawos/clawos-security-mode \
  usr/lib/clawos/clawos-lock \
  usr/lib/clawos/clawos-power-menu \
  usr/lib/clawos/clawos-system-menu \
  usr/lib/clawos/clawos-power-action \
  usr/lib/clawos/clawos-command \
  usr/lib/clawos/clawos-build \
  usr/lib/clawos/clawos-build-activity \
  usr/lib/clawos/clawos-browse \
  usr/lib/clawos/clawos-open-url \
  usr/share/applications/clawos-browser.desktop \
  usr/share/applications/clawos-agent.desktop \
  usr/share/applications/clawos-terminal.desktop \
  usr/share/applications/clawos-browser-surface.desktop \
  usr/share/applications/clawos-gmail.desktop \
  usr/share/applications/clawos-outlook.desktop \
  usr/share/clawos/webapps/gmail.json \
  usr/share/clawos/webapps/outlook.json \
  etc/xdg/mimeapps.list \
  etc/clawos/sway.conf \
  etc/clawos/fuzzel.ini \
  etc/clawos/intent-fuzzel.ini \
  etc/clawos/waybar/config.jsonc \
  etc/clawos/waybar/style.css \
  etc/clawos/design-system.css \
  etc/clawos/system-menu.css \
  etc/clawos/gtklock/config.ini \
  etc/clawos/gtklock/style.css \
  etc/clawos/foot.ini \
  etc/clawos/zshrc \
  etc/clawos/tmux.conf \
  etc/plymouth/plymouthd.conf \
  usr/share/clawos/theme/background.png \
  usr/share/clawos/theme/clawos-pin.svg \
  usr/share/clawos/theme/clawos-pin.png \
  usr/share/clawos/icons/arrow-left.svg \
  usr/share/clawos/icons/reload.svg \
  usr/share/licenses/clawos-radix-icons/LICENSE \
  usr/share/clawos/onboarding/index.html \
  usr/share/clawos/onboarding/styles.css \
  usr/share/clawos/onboarding/app.js \
  usr/share/clawos/browser/start.html \
  usr/share/plymouth/themes/clawos/clawos.plymouth \
  usr/share/plymouth/themes/clawos/clawos.script \
  usr/share/plymouth/themes/clawos/background.png \
  etc/systemd/system/clawos-session@.service; do
  test -f "$profile/airootfs/$launch_file"
done
python3 -c 'import ast, pathlib, sys; [ast.parse(pathlib.Path(path).read_text()) for path in sys.argv[1:]]' \
  "$profile/airootfs/usr/lib/clawos/clawos-agent-submit" \
  "$profile/airootfs/usr/lib/clawos/clawos-agent-run" \
  "$profile/airootfs/usr/lib/clawos/clawos-agent-request"
bash -n "$profile/airootfs/usr/lib/clawos/clawos-agent-recover"
bash -n "$profile/airootfs/usr/lib/clawos/clawos-role"
bash -n "$profile/airootfs/usr/lib/clawos/clawos-security-mode"
grep -Fq '"$mount_root/usr/lib/clawos/clawos-role"' "$installer"
grep -Fq '"$mount_root/usr/lib/clawos/clawos-security-mode"' "$installer"
grep -Fq 'useradd --system --create-home --home-dir /var/lib/clawos/agent-home' "$installer"
grep -Fq 'clawos-control' "$installer"
grep -Fq '/run/clawos-control/surface.sock' "$profile/airootfs/usr/lib/clawos/clawos-surfaced"
grep -Fq 'd /run/clawos-control 0770 clawos clawos-control' \
  "$profile/airootfs/usr/lib/tmpfiles.d/clawos-control.conf"

for live_file in \
  usr/lib/clawos/clawos-live-session \
  usr/lib/clawos/clawos-live-welcome \
  usr/lib/clawos/clawos-live-reboot \
  usr/lib/sysusers.d/clawos-live.conf \
  usr/lib/tmpfiles.d/clawos-live.conf \
  etc/polkit-1/rules.d/49-clawos-live-installer.rules \
  etc/clawos/live-sway.conf \
  etc/systemd/system/clawos-live-session.service \
  etc/systemd/system/multi-user.target.d/clawos-live.conf; do
  test -f "$profile/airootfs/$live_file"
done

if [[ -f "$profile/airootfs/usr/lib/clawos/clawosd/clawosd_core.py" ]]; then
  test -x "$profile/airootfs/usr/lib/clawos/clawosctl"
  test -x "$profile/airootfs/usr/lib/clawos/clawos-approval"
  test -x "$profile/airootfs/usr/lib/clawos/clawosd/clawosd_service.py"
  test -f "$profile/airootfs/etc/systemd/system/clawosd.service"
  test -f "$profile/airootfs/etc/dbus-1/system.d/org.clawos.System.conf"
  test -f "$profile/airootfs/usr/share/dbus-1/interfaces/org.clawos.System.xml"
  test -f "$profile/airootfs/usr/share/polkit-1/actions/org.clawos.system.policy"
fi

for live_executable in clawos-live-session clawos-live-welcome clawos-live-reboot; do
  test -x "$profile/airootfs/usr/lib/clawos/$live_executable"
done
bash -n "$profile/airootfs/usr/lib/clawos/clawos-live-session"
bash -n "$profile/airootfs/usr/lib/clawos/clawos-live-reboot"
python3 -c 'import ast, pathlib, sys; ast.parse(pathlib.Path(sys.argv[1]).read_text())' \
  "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq 'Wants=clawos-live-session.service' \
  "$profile/airootfs/etc/systemd/system/multi-user.target.d/clawos-live.conf"
grep -Fq 'User=clawos-live' \
  "$profile/airootfs/etc/systemd/system/clawos-live-session.service"
grep -Fq 'Ctrl+Alt+F3' "$profile/airootfs/etc/clawos/live-sway.conf"
grep -Fq 'Inspect system' "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq 'The full Agent workspace is created after installation.' \
  "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq 'Install ClawOS' "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq 'confirmation_token(target)' "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq '"--disk-id", disk_id' "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq "selector.append('', 'Select a blank disk" "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq "selector.set_active(0)" "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq '"--passwordless"' "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq 'I accept the risk.' "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq 'Gdk.KEY_Escape' "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
grep -Fq 'program === "/usr/local/bin/clawos-install-dev"' \
  "$profile/airootfs/etc/polkit-1/rules.d/49-clawos-live-installer.rules"
grep -Fq 'program === "/usr/lib/clawos/clawos-live-reboot"' \
  "$profile/airootfs/etc/polkit-1/rules.d/49-clawos-live-installer.rules"
grep -Fq 'subject.user !== "clawos-live"' \
  "$profile/airootfs/etc/polkit-1/rules.d/49-clawos-live-installer.rules"
if grep -Fq 'program === "/usr/bin/systemctl"' \
  "$profile/airootfs/etc/polkit-1/rules.d/49-clawos-live-installer.rules"; then
  echo "The live policy must not authorize arbitrary systemctl operations." >&2
  exit 1
fi

grep -Fq 'openclaw onboard' "$profile/airootfs/usr/lib/clawos/clawos-onboard"
grep -Fq 'openclaw config get gateway.mode' "$profile/airootfs/usr/lib/clawos/clawos-entry"
grep -Fq '/usr/lib/clawos/clawos-onboard-ui' "$profile/airootfs/usr/lib/clawos/clawos-entry"
grep -Fq 'onboard' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq -- '--non-interactive' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq -- '--accept-risk' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq '127.0.0.1' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq '"--secret-input-mode", "ref"' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq '"--gateway-token-ref-env"' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq 'policyKey = "tools.alsoAllow"' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq '"clawos_surface", "clawos_activity", "clawos_app"' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq 'plugins.entries.clawos-system.hooks.allowConversationAccess' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq 'plugins.entries.clawos-system.hooks.allowPromptInjection' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq 'plugins.entries.browser.enabled' "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq "\${token:+#token=\$token}" "$profile/airootfs/usr/lib/clawos/clawos-browser"
grep -Fq 'Bringing the agent online' "$profile/airootfs/usr/lib/clawos/clawos-browser"
grep -Fq "fetch(gateway, { mode: 'no-cors'" "$profile/airootfs/usr/lib/clawos/clawos-browser"
if grep -Fq 'for _ in {1..60}' "$profile/airootfs/usr/lib/clawos/clawos-entry"; then
  echo "The Agent surface must not wait behind Gateway health polling." >&2
  exit 1
fi
grep -Fq -- '--app="$start_url"' "$profile/airootfs/usr/lib/clawos/clawos-browser"
grep -Fq -- '--class="$app_id"' "$profile/airootfs/usr/lib/clawos/clawos-browser"
if grep -Fq -- '--kiosk' "$profile/airootfs/usr/lib/clawos/clawos-browser"; then
  echo "Chromium kiosk mode blocks the native ClawOS shell." >&2
  exit 1
fi
grep -Fq 'exec --no-startup-id /usr/lib/clawos/clawos-entry' \
  "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq '/usr/lib/clawos/clawos-panel' \
  "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq -- '--config /etc/clawos/waybar/config.jsonc' \
  "$profile/airootfs/usr/lib/clawos/clawos-panel"
grep -Fq '1:Main' "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq 'custom/activity' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq 'clawos-activity-status' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq 'clawos-activity-action' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq 'clawos-attention-status' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq 'title="^ClawOS Center$"' "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq 'GtkLayerShell.set_namespace(self, "clawos-center")' \
  "$m3_root/clawosd/clawos_approval.py"
grep -Fq 'screen.get_width() - 64' "$m3_root/clawosd/clawos_approval.py"
grep -Fq 'screen_width - 48' "$profile/airootfs/usr/lib/clawos/clawos-agent-shelf"
! grep -Fq 'min-width: 860px' "$profile/airootfs/etc/clawos/agent-shelf.css"
! grep -Fq 'floating enable, resize set 1040 740' "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq '"interval": 5' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq '[openclaw, "tasks", "list", "--json"]' \
  "$profile/airootfs/usr/lib/clawos/clawos_attention.py"
grep -Fq '[openclaw, "approvals", "pending", "--json"]' \
  "$profile/airootfs/usr/lib/clawos/clawos_attention.py"
grep -Fq 'command === "clear-attention"' "$profile/airootfs/usr/lib/clawos/clawos-appctl"
grep -Fq 'fs.existsSync("/run/clawos-control")' "$profile/airootfs/usr/lib/clawos/clawos-appctl"
grep -Fq 'class: ($class | split(" "))' \
  "$profile/airootfs/usr/lib/clawos/clawos-activity-status"
grep -Fq 'class="surface-return $class"' \
  "$profile/airootfs/usr/lib/clawos/clawos-activity-status"
! grep -Fq '←' "$profile/airootfs/usr/lib/clawos/clawos-activity-status"
grep -Fq '/usr/share/clawos/icons/arrow-left.svg' \
  "$profile/airootfs/etc/clawos/waybar/style.css"
grep -Fq '"/icons/arrow-left.svg"' \
  "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq 'data-back]::before' \
  "$profile/airootfs/usr/share/clawos/onboarding/styles.css"
grep -Fq 'clawos-arrow-left' "$profile/airootfs/usr/lib/clawos/clawos-live-welcome"
python3 -c 'import sys, xml.etree.ElementTree as ET; ET.parse(sys.argv[1])' \
  "$profile/airootfs/usr/share/clawos/icons/arrow-left.svg"
python3 -c 'import sys, xml.etree.ElementTree as ET; ET.parse(sys.argv[1])' \
  "$profile/airootfs/usr/share/clawos/icons/reload.svg"
grep -Fq 'set_name("header-icon")' "$m3_root/clawosd/clawos_approval.py"
grep -Fq 'Gtk.Label(label="Back")' "$m3_root/clawosd/clawos_approval.py"
! grep -Fq 'Gtk.Button(label="Refresh")' "$m3_root/clawosd/clawos_approval.py"
if grep -Eq 'custom/(agent|actions)' "$profile/airootfs/etc/clawos/waybar/config.jsonc"; then
  echo "Agent and Actions must live in the command shelf, not duplicate the top bar." >&2
  exit 1
fi
grep -Fq 'clawos-surface terminal' "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq 'clawos-surfaced' "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq 'clawos-agent-shelf' "$profile/airootfs/etc/clawos/sway.conf"
test -x "$profile/airootfs/usr/lib/clawos/clawos-agent-shelf"
grep -Fq '"$mount_root/usr/lib/clawos/clawos-agent-shelf"' \
  "$profile/airootfs/usr/local/bin/clawos-install-dev"
grep -Fq '"$mount_root/usr/lib/clawos/clawos-agent-submit"' \
  "$profile/airootfs/usr/local/bin/clawos-install-dev"
grep -Fq '"$mount_root/usr/lib/clawos/clawos-agent-run"' \
  "$profile/airootfs/usr/local/bin/clawos-install-dev"
grep -Fq '"$mount_root/usr/lib/clawos/clawos-agent-request"' \
  "$profile/airootfs/usr/local/bin/clawos-install-dev"
grep -Fq '"$mount_root/usr/lib/clawos/clawos-agent-recover"' \
  "$profile/airootfs/usr/local/bin/clawos-install-dev"
test -f "$profile/airootfs/etc/clawos/agent-shelf.css"
grep -Fq 'clawos-agent-panel' "$profile/airootfs/usr/lib/clawos/clawos-agent-shelf"
grep -Fq 'clawos-actions-menu' "$profile/airootfs/usr/lib/clawos/clawos-agent-shelf"
grep -Fq '["/usr/lib/clawos/clawos-agent-submit"]' \
  "$profile/airootfs/usr/lib/clawos/clawos-agent-shelf"
! grep -Fq '"--message", prompt' "$profile/airootfs/usr/lib/clawos/clawos-agent-shelf"
grep -Fq '"--message-file"' "$profile/airootfs/usr/lib/clawos/clawos-agent-run"
grep -Fq 'StandardOutput=null' "$profile/airootfs/usr/lib/clawos/clawos-agent-submit"
grep -Fq 'O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600' \
  "$profile/airootfs/usr/lib/clawos/clawos-agent-submit"
grep -Fq 'command === "attention"' "$profile/airootfs/usr/lib/clawos/clawos-appctl"
grep -Fq 'surface not in {"Agent", "Setup", "Machine", "Terminal", "Build"}' \
  "$profile/airootfs/usr/lib/clawos/clawos-agent-shelf"
grep -Fq 'clawos-intent-palette' "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq 'Mod1+Escape exec /usr/lib/clawos/clawos-activity-action' "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq 'clawos-intent-palette' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
! grep -Fq '"on-click": "/usr/lib/clawos/clawos-app-palette"' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq 'placeholder=What do you want to do?' "$profile/airootfs/etc/clawos/intent-fuzzel.ini"
grep -Fq 'launch-prefix=/usr/lib/clawos/clawos-app-from-fuzzel' "$profile/airootfs/etc/clawos/fuzzel.ini"
grep -Fq 'X-ClawOS-AppId=web:gmail' "$profile/airootfs/usr/share/applications/clawos-gmail.desktop"
grep -Fq 'X-ClawOS-AppId=web:outlook' "$profile/airootfs/usr/share/applications/clawos-outlook.desktop"
grep -Fq 'X-ClawOS-BrowserProfile=clawos-gmail' "$profile/airootfs/usr/share/applications/clawos-gmail.desktop"
grep -Fq 'X-ClawOS-BrowserProfile=clawos-outlook' "$profile/airootfs/usr/share/applications/clawos-outlook.desktop"
grep -Fq -- '--remote-debugging-port="$cdp_port"' "$profile/airootfs/usr/lib/clawos/clawos-webapp"
if grep -Fq 'sway/workspaces' "$profile/airootfs/etc/clawos/waybar/config.jsonc"; then
  echo "The panel must expose activities, not fixed application workspaces." >&2
  exit 1
fi
grep -Fq 'tmux -f /etc/clawos/tmux.conf new-session -A -s command -c "$HOME"' \
  "$profile/airootfs/usr/lib/clawos/clawos-command"
grep -Fq 'tmux -f /etc/clawos/tmux.conf new-session -d -s build' \
  "$profile/airootfs/usr/lib/clawos/clawos-build"
grep -Fq -- '--remote-debugging-address=127.0.0.1' \
  "$profile/airootfs/usr/lib/clawos/clawos-browse"
grep -Fq -- '--remote-debugging-port=9222' \
  "$profile/airootfs/usr/lib/clawos/clawos-browse"
grep -Fq 'x-scheme-handler/https=clawos-browser.desktop' \
  "$profile/airootfs/etc/xdg/mimeapps.list"
grep -Fq 'Exec=/usr/lib/clawos/clawos-open-url %U' \
  "$profile/airootfs/usr/share/applications/clawos-browser.desktop"
grep -Fq -- '--user-data-dir="$profile_dir"' \
  "$profile/airootfs/usr/lib/clawos/clawos-open-url"
grep -Fq 'Ctrl+Alt+F3' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq 'clawos-return-to-setup' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq 'clawos-power-menu' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
jq -e '."custom/attention"."on-click" == "/usr/lib/clawos/clawos-approval"' \
  "$profile/airootfs/etc/clawos/waybar/config.jsonc" >/dev/null
grep -Fq 'lxqt-policykit-agent' "$profile/airootfs/etc/clawos/sway.conf"
if grep -Fq 'custom/system' "$profile/airootfs/etc/clawos/waybar/config.jsonc"; then
  echo "The ClawOS wordmark must be the sole system-menu control." >&2
  exit 1
fi
grep -Fq 'swayidle -w timeout 900' "$profile/airootfs/etc/clawos/sway.conf"
grep -Fq 'gtklock' "$profile/airootfs/usr/lib/clawos/clawos-lock"
grep -Fq 'clawos-system-menu' "$profile/airootfs/usr/lib/clawos/clawos-power-menu"
grep -Fq 'clawos-intent-palette' "$profile/airootfs/usr/lib/clawos/clawos-actions-menu"
grep -Fq 'panel.set_margin_top(6)' \
  "$profile/airootfs/usr/lib/clawos/clawos-system-menu"
grep -Fq '@define-color oc_accent_primary #f5654a;' "$profile/airootfs/etc/clawos/design-system.css"
grep -Fq '@import url("../design-system.css");' "$profile/airootfs/etc/clawos/waybar/style.css"
grep -Fq 'Restarting ClawOS' "$profile/airootfs/usr/share/plymouth/themes/clawos/clawos.script"
grep -Fq -- '--headless-vnc' "$repo_root/m1/bin/run-qemu"
grep -Fq -- '-vnc "127.0.0.1:$vnc_display"' "$repo_root/m1/bin/run-qemu"
if grep -Fq -- '-vnc "0.0.0.0' "$repo_root/m1/bin/run-qemu"; then
  echo "QEMU VNC must never bind publicly by default." >&2
  exit 1
fi
grep -Fq 'Setup required' "$profile/airootfs/usr/lib/clawos/clawos-panel-status"
grep -Fq 'Enter Agent workspace' "$profile/airootfs/usr/share/clawos/onboarding/index.html"
! grep -Fq 'setup-header' "$profile/airootfs/usr/share/clawos/onboarding/index.html"
grep -Fq 'Choose providers and models through OpenClaw setup' \
  "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq '"height": 48' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq '"fixed-center": false' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq 'GeistMono Nerd Font' "$profile/airootfs/etc/clawos/waybar/style.css"
grep -Fxq 'otf-geist-mono-nerd' "$profile/packages.x86_64"
jq empty "$profile/airootfs/etc/clawos/waybar/config.jsonc"
for shell_file in \
  clawos-session clawos-browser clawos-entry clawos-onboard clawos-install-node clawos-enroll-local-node \
  clawos-gateway-watchdog clawos-panel \
  clawos-panel-status clawos-return-to-setup clawos-lock clawos-power-menu clawos-power-action \
  clawos-activity-status clawos-activity-action clawos-surface \
  clawos-actions-menu clawos-agent-panel clawos-agent-panel-status clawos-screen-reader-toggle \
  clawos-attention-status \
  clawos-app-from-fuzzel clawos-intent-palette clawos-app-palette clawos-webapp \
  clawos-command clawos-build clawos-build-activity clawos-browse clawos-open-url \
  clawos-onboard-ui; do
  test -x "$profile/airootfs/usr/lib/clawos/$shell_file"
  bash -n "$profile/airootfs/usr/lib/clawos/$shell_file"
done
test -x "$profile/airootfs/usr/lib/clawos/clawos-clock-status"
test -x "$profile/airootfs/usr/lib/clawos/clawos-system-menu"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' \
  "$profile/airootfs/usr/lib/clawos/clawos-system-menu"
python3 -c 'import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")' \
  "$profile/airootfs/usr/lib/clawos/clawos-clock-status"
grep -Fq '"custom/clock"' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq '/usr/lib/clawos/clawos-clock-status' "$profile/airootfs/etc/clawos/waybar/config.jsonc"
grep -Fq '"clockFormat":"12h"' "$profile/airootfs/etc/clawos/preferences.json"
test -x "$profile/airootfs/usr/lib/clawos/clawos-surfaced"
test -x "$profile/airootfs/usr/lib/clawos/clawos-appctl"
test -x "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
node_check "$profile/airootfs/usr/lib/clawos/clawos-surfaced"
node_check "$profile/airootfs/usr/lib/clawos/clawos-appctl"
node_check "$profile/airootfs/usr/lib/clawos/app-registry.cjs"
for session_wrapper in clawos-panel clawos-command clawos-build clawos-browse clawos-entry; do
  grep -Fq 'session_alive || exit 0' "$profile/airootfs/usr/lib/clawos/$session_wrapper"
done
for chromium_launcher in clawos-browser clawos-browse clawos-open-url clawos-onboard-ui; do
  grep -Fq -- '--hide-crash-restore-bubble' "$profile/airootfs/usr/lib/clawos/$chromium_launcher"
done
for persistent_surface in clawos-browser clawos-browse clawos-open-url; do
  grep -Fq -- '--disable-background-mode' "$profile/airootfs/usr/lib/clawos/$persistent_surface"
done
node_check "$profile/airootfs/usr/lib/clawos/clawos-onboard-server"
grep -Fq '/usr/bin/swaybg -i /usr/share/clawos/theme/background.png -m fill' \
  "$profile/airootfs/etc/clawos/sway.conf"
grep -Fqx 'Theme=clawos' "$profile/airootfs/etc/plymouth/plymouthd.conf"
grep -Fqx 'DeviceScale=1' "$profile/airootfs/etc/plymouth/plymouthd.conf"
grep -Fq 'After=systemd-user-sessions.service plymouth-quit-wait.service' \
  "$profile/airootfs/etc/systemd/system/clawos-session@.service"
if grep -Fq 'ExecStopPost=+/usr/bin/chvt 1' \
  "$profile/airootfs/etc/systemd/system/clawos-session@.service"; then
  echo "The graphical session must not fall through to tty1 during a normal stop." >&2
  exit 1
fi
if [[ -d "$profile/airootfs/usr/share/clawos-launch" ]]; then
  echo "A parallel ClawOS web shell is not allowed; use upstream OpenClaw Control UI." >&2
  exit 1
fi

if [[ "$profile" == "$repo_root/m1/profile-overlay" ]]; then
  "$repo_root/m1/tests/onboarding-static.sh"
fi

echo "ClawOS image profile validation passed."

# Image identity: one repository URL, no stale milestone/proof naming.
repo_url='https://github.com/Solvely-Colin/ClawOS'
grep -Fqx "HOME_URL=\"$repo_url\"" "$profile/airootfs/etc/os-release"
grep -Fqx 'PRETTY_NAME="ClawOS Live (experimental)"' "$profile/airootfs/etc/os-release"
grep -Fqx "iso_publisher=\"ClawOS <$repo_url>\"" "$profile/profiledef.sh"
grep -Fq "<vendor_url>$repo_url</vendor_url>" "$m3_root/polkit/org.clawos.system.policy"
if grep -R -n -E 'github\.com/(clawos|openclaw)\b' "$profile/airootfs/etc" "$m3_root/polkit"; then
  echo "Stale project URL in image identity." >&2
  exit 1
fi
if [[ -f "$installer" ]]; then
  grep -Fqx 'PRETTY_NAME="ClawOS (experimental)"' "$installer"
  grep -Fqx "HOME_URL=\"$repo_url\"" "$installer"
  grep -Fqx 'title ClawOS (experimental)' "$installer"
  if grep -n -E 'Milestone 1|Installed Proof|not included|no OpenClaw runtime' \
    "$profile/airootfs/etc/issue" "$profile/airootfs/root/README.txt" \
    "$profile/airootfs/etc/os-release" "$profile"/efiboot/loader/entries/*.conf "$installer"; then
    echo "Stale image self-description." >&2
    exit 1
  fi
fi
