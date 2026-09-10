# Current development boundaries

- **Source-test robustness:** the ISO posture test's marker parser no longer
  uses overlapping regex alternatives for continuation lines. A subprocess
  timeout regression covers malformed input without hanging the suite. This
  affects test execution, not an installed OS service. The separate CodeQL
  redirect-replacement alert is a false positive: the local operator can
  contain at most one ampersand at that expression; runtime parsing is unchanged.

- **Fullscreen/layout:** Windows QEMU has an absolute tablet, but setup-window
  offset/scaling is not fully solved. The GTK installer's clipped Back/Erase
  actions were fixed in #81 and verified in CI ISO run 34432248984 at 1440x900;
  that does not establish all QEMU fullscreen/pointer behavior (#54).
- **Task context:** supporting-surface prompts can still target the fixed main
  session instead of the conversation owning the terminal/browser/build
  ([#55](https://github.com/Solvely-Colin/ClawOS/issues/55)).
- **Startup:** configuration presence, onboarding completion, model readiness,
  desktop readiness and repair state need a coherent model. Gateway reachability
  is not proof of successful model inference
  ([#53](https://github.com/Solvely-Colin/ClawOS/issues/53)).
- **Recovery:** runtime file rollback works; coordinated root/home/credential/
  database/boot rollback is not proven
  ([#56](https://github.com/Solvely-Colin/ClawOS/issues/56)).
- **Authority:** typed high-impact actions require approval, but the `clawos`
  account has unrestricted passwordless sudo (`/etc/sudoers.d/90-clawos-full-root`).
  Full Root is a trusted-agent mode, not containment. The archiso base also
  autologs root on the live ISO's tty1
  ([#43](https://github.com/Solvely-Colin/ClawOS/issues/43)).
- **Broker upgrade:** mutations and approval-token access now require a trusted
  OS account/runtime, and tokens bind to UID and boot. Re-prepare outstanding
  approvals from the older unbound-token broker. Owner/root approval handoff is
  retained; agent metadata is not isolation from another process in the same UID
  ([#40](https://github.com/Solvely-Colin/ClawOS/issues/40),
  [#39](https://github.com/Solvely-Colin/ClawOS/issues/39)).
- **Fresh installs:** repeat the full build/install/onboarding/agent-update loop
  on a clean disk. Existing VM state can hide provisioning defects. Offline
  installation and physical T2 hardware need further proof.
  The hardware-capable installer is blank-disk-only. Fresh QEMU/WHPX passwordless
  and encrypted installs passed on 2026-09-06/07; physical-machine acceptance is
  still missing. Existing partitions are intentionally refused.
  The encrypted graphical CI-ISO path through default onboarding was verified
  on 2026-09-10; provider inference and the complete update/recovery loop remain
  separate gates ([#33](https://github.com/Solvely-Colin/ClawOS/issues/33)).
  Bare-metal guard work remains [#26](https://github.com/Solvely-Colin/ClawOS/issues/26).
  See [the exact proof](HARDWARE-INSTALLER-VALIDATION.md).
- **Verification scope:** every install and boot proof is from QEMU (Linux KVM
  or Windows WHPX). No physical machine has been installed
  ([#58](https://github.com/Solvely-Colin/ClawOS/issues/58)).
- **Remote access:** installed systems enable `sshd` and `tailscaled` at boot.
  sshd refuses password, keyboard-interactive and root login
  (`/etc/ssh/sshd_config.d/00-clawos.conf`) and nothing installs an authorized
  key, so SSH is unusable until one is added locally; Tailscale is enabled but
  not enrolled. The live ISO also runs sshd on port 22 with the same key-only
  policy and a passwordless root account (observed on a CI-built image,
  2026-09-08).
  On the 2026-09-10 installed CI image, un-enrolled Tailscale reported NeedsLogin
  but listened on UDP 41641 on IPv4/IPv6. Do not equate no tailnet with no
  listener; the default-service decision remains #42. Host-forwarded SSH
  intermittently timed out during bootstrap/downloads; successful key login
  and a usable recovery console were also observed.
- **Credentials:** in encrypted installs the LUKS passphrase is also the `root`
  and `clawos` account password (Polkit prompts, session unlock). Passwordless
  installs leave both accounts with empty passwords, no encryption and no
  screen lock. Follow-ups: [Polkit identity #44](https://github.com/Solvely-Colin/ClawOS/issues/44)
  and [passwordless warning #45](https://github.com/Solvely-Colin/ClawOS/issues/45).
- **Releases:** no tags exist and there is no downloadable release. `release.yml`
  went green for the first time on `main` on 2026-09-08 (run 34270708295; an
  earlier branch run is in the ledger). The workflow validates the ISO but does
  not boot it automatically. Run 34432248984 was manually verified through an
  encrypted graphical install and default onboarding on 2026-09-10. All four
  retained ISO artifacts were removed from GitHub before the public launch,
  with verified private backups. Future builds retain artifacts for 14 days;
  they are not supported releases. Release gates remain
  [#37](https://github.com/Solvely-Colin/ClawOS/issues/37).
  Build locally with `sudo ./m1/bin/build-iso`, or
  see [the evidence ledger](EVIDENCE.md).
- **Compatibility:** the version-checked OpenClaw delivery adapter needs review
  when upgrading that dependency. Supply-chain follow-ups:
  [integrity #29](https://github.com/Solvely-Colin/ClawOS/issues/29) and
  [dependency locking #31](https://github.com/Solvely-Colin/ClawOS/issues/31).
- **Design/docs:** plans and prototype guidance include superseded layouts.
  Consolidate the current Carapace adapter and acceptance checklist
  ([#50](https://github.com/Solvely-Colin/ClawOS/issues/50),
  [#52](https://github.com/Solvely-Colin/ClawOS/issues/52)).
- **Omarchy:** targeted source/runtime checks found no active dependency, but
  do not certify every asset and package's provenance.
- **Public release:** source became public on 2026-09-10 after owner approval,
  final history scanning, attribution review and artifact cleanup. The MIT
  license and NOTICE.md are in place; no supported or downloadable release
  was published. See the [evidence ledger](EVIDENCE.md) and
  [remaining prerelease gates](PUBLIC-RELEASE-CHECKLIST.md).
