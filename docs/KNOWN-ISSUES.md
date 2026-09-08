# Current development boundaries

- **Fullscreen/layout:** Windows QEMU has an absolute tablet, but setup-window
  offset/clipping remains under investigation. Scaling is not fully solved.
- **Task context:** supporting-surface prompts can still target the fixed main
  session instead of the conversation owning the terminal/browser/build.
- **Startup:** configuration presence, onboarding completion, model readiness,
  desktop readiness and repair state need a coherent model. Gateway reachability
  is not proof of successful model inference.
- **Recovery:** runtime file rollback works; coordinated root/home/credential/
  database/boot rollback is not proven.
- **Authority:** typed high-impact actions require approval, but the `clawos`
  account has unrestricted passwordless sudo (`/etc/sudoers.d/90-clawos-full-root`).
  Full Root is a trusted-agent mode, not containment. The archiso base also
  autologs root on the live ISO's tty1.
- **Broker upgrade:** mutations and approval-token access now require a trusted
  OS account/runtime, and tokens bind to UID and boot. Re-prepare outstanding
  approvals from the older unbound-token broker. Owner/root approval handoff is
  retained; agent metadata is not isolation from another process in the same UID.
- **Fresh installs:** repeat the full build/install/onboarding/agent-update loop
  on a clean disk. Existing VM state can hide provisioning defects. Offline
  installation and physical T2 hardware need further proof.
  The hardware-capable installer is blank-disk-only. Fresh QEMU/WHPX passwordless
  and encrypted installs passed on 2026-09-06/07; physical-machine acceptance is
  still missing. Existing partitions are intentionally refused.
- **Verification scope:** every install and boot proof is from QEMU (Linux KVM
  or Windows WHPX). No physical machine has been installed.
- **Remote access:** installed systems enable `sshd` and `tailscaled` at boot.
  sshd refuses password, keyboard-interactive and root login
  (`/etc/ssh/sshd_config.d/00-clawos.conf`) and nothing installs an authorized
  key, so SSH is unusable until one is added locally; Tailscale is enabled but
  not enrolled.
- **Credentials:** in encrypted installs the LUKS passphrase is also the `root`
  and `clawos` account password (Polkit prompts, session unlock). Passwordless
  installs leave both accounts with empty passwords, no encryption and no
  screen lock.
- **Releases:** no tags exist and there is no downloadable release. `release.yml`
  completed for the first time on 2026-09-08 (run 34270708295 on `main`); its
  ISO artifact is kept for 14 days and was validated but not booted. Build
  locally with `sudo ./m1/bin/build-iso`, or see [the evidence ledger](EVIDENCE.md).
- **Compatibility:** the version-checked OpenClaw delivery adapter needs review
  when upgrading that dependency.
- **Design/docs:** plans and prototype guidance include superseded layouts.
  Consolidate the current Carapace adapter and acceptance checklist.
- **Omarchy:** targeted source/runtime checks found no active dependency, but
  do not certify every asset and package's provenance.
- **Public release:** the license (MIT) and NOTICE.md are in place. Still open
  before the source goes public: the reporting-mailbox check, the secret scan at
  the publication commit, and the owner's approval. See the
  [public-release checklist](PUBLIC-RELEASE-CHECKLIST.md) and the `flip-gate`
  issues.
