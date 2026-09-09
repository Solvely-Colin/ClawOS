# Roadmap

The detailed PLAN.md retains the original long-term vision. This page is the
current contributor work queue; checkboxes are acceptance criteria, not promises.
Each section maps to a GitHub milestone; issues carry the detail.

## 1. Make the source public without overstating readiness

Milestones: Flip-ready (gates the flip), Flip day (same sitting).

- [x] GitHub repository with history, contributor guide and unit CI.
- [x] Automated clean ISO build completes on `main` (release.yml run 34270708295).
- [x] Public license (MIT) with asset and dependency attribution in NOTICE.md.
- [ ] Every public document describes what `main` does: checklist, KNOWN-ISSUES,
  RELEASING, CONTRIBUTING, CODE_OF_CONDUCT reporting route, test counts.
- [x] docs/SCOPE.md, docs/GETTING-STARTED.md and docs/EVIDENCE.md exist; every
  ISO proof is a ledger row naming ISO SHA256, source commit and host.
- [ ] Live side of a CI-built ISO observed with key-only sshd; the GTK installer
  and onboarding past the first screen observed once on a fresh VM.
- [x] Real-bus broker authorization proof runs in CI (`arch-preflight`).
- [ ] Secret scan at the flip SHA including force-pushed commits; tree audit;
  owner approval ticked last; repository flipped at that SHA.
- [ ] Flip day: private vulnerability reporting, scanning alerts triaged, rulesets,
  CodeQL, action restrictions; SECURITY.md names the verified routes.

## 2. Prove the image in CI and ship a first prerelease

Milestones: Green Pipeline, v0.1.0-alpha.1.

- [ ] release.yml boots the just-built ISO under runner KVM and asserts key-only
  sshd; a passwordless install and installed boot follow under their own timeout.
- [ ] m2-e2e-qemu passes once on a CI-built ISO, or its failures are triaged.
- [ ] Gates run under TCG for contributors without KVM; WHPX evidence names a
  CI run via Get-CiIso.ps1.
- [ ] Bare metal refused unless `--experimental-hardware`; RAM, free-space and
  archive-reachability checks fail before any disk write.
- [ ] OpenClaw pinned by npm integrity; SBOM and license manifest with every
  build; build container pinned by digest; ISO provenance attested.
- [ ] Both install modes via the GTK installer, real inference, live update and
  rollback recorded against a CI ISO; GETTING-STARTED executed from the docs
  alone on a fresh host.
- [ ] Tag v0.1.0-alpha.1 as an explicitly experimental, VM-only draft prerelease.

## 3. Harden the boundaries and make everyday development reliable

Milestones: Post-flip hardening and contributor tooling; Runtime reliability.

- [ ] Every SECURITY.md bullet under "Constructed by reasoning" moved to Observed
  or reworded: polkit admin identity, exec-hook rail, cgroup and scope tricks,
  PID reuse in attestation, tailscaled exposure; plus the D-Bus bus policy,
  deploy-runtime hint and tty1 autologin items tracked as hardening issues.
- [ ] Contributor tooling: tree check, container preflight, shellcheck stage,
  m0 and shell-prototype READMEs; artwork decision recorded.
- [ ] Fix setup/fullscreen offset and clipping; verify pointer alignment with
  saved screenshots.
- [ ] Distinguish startup, locked, setup-incomplete, ready and repair-required
  states from one source of truth.
- [ ] Bind terminal, browser and build surfaces to their owning task; prove two
  simultaneous tasks cannot cross-route prompts or lose drafts.
- [ ] Prove boot/root/home compatibility during failed-update recovery.

## 4. Design physical installation as its own milestone

Milestone: Physical hardware.

- [ ] Inventory hardware and define the initial supported UEFI x86_64 matrix.
- [x] Experimental blank-disk selection with explicit confirmation, live-media
  protection and disk-identity rechecks; verified only in QEMU/WHPX.
- [ ] Establish Secure Boot, legacy BIOS and T2 policies rather than implying support.
- [ ] Install one blank-disk physical machine from a CI ISO and publish redacted results.

Keep runtime engineering moving while release preparation happens. Repository
polish does not resolve the outstanding OS acceptance criteria.
