# Roadmap

This page is the current contributor work queue; checkboxes are acceptance
criteria, not promises. See [architecture](docs/ARCHITECTURE.md) for component boundaries.
Each section maps to a GitHub milestone; issues carry the detail.

## 1. Make the source public without overstating readiness

Milestones: Flip-ready (gates the flip), Flip day (same sitting).

- [x] GitHub repository with history, contributor guide and unit CI.
- [x] Automated clean ISO build completes on `main` (release.yml run 34270708295).
- [x] Public license (MIT) with asset and dependency attribution in NOTICE.md.
- [x] Contributor entry points reconciled for the source launch: local-build
  walkthrough, scope/features evidence, release boundaries, reporting routes
  and contribution defaults (2026-09-10). Historical plans are now
  local-only; ongoing documentation improvements remain #52.
- [x] docs/SCOPE.md, docs/GETTING-STARTED.md and docs/EVIDENCE.md exist; every
  ISO proof is a ledger row naming ISO SHA256, source commit and host.
- [x] Live side of a CI-built ISO observed with key-only sshd; the GTK installer
  and default onboarding observed on a fresh VM (2026-09-10, run 34432248984;
  exact limits in docs/HARDWARE-INSTALLER-VALIDATION.md).
- [x] Real-bus broker authorization proof runs in CI (`arch-preflight`).
- [x] Secret scan at the flip SHA including force-pushed commits; tree audit;
  owner approval ticked last; repository flipped at `b551292` on 2026-09-10.
- [x] Flip day: private vulnerability reporting, scanning alerts triaged, rulesets,
  CodeQL, action restrictions; SECURITY.md names the verified routes (2026-09-10).
  Two initial CodeQL alerts were recorded after static triage; see
  docs/KNOWN-ISSUES.md and GitHub code scanning for current states. No ISO release was published.

## 2. Prove the image in CI and ship a first prerelease

Milestones: Green Pipeline, v0.1.0-alpha.1.

- [x] release.yml boots the just-built ISO under runner KVM and asserts key-only
  sshd plus graceful shutdown (#20; run 34505506520, 2026-09-10).
- [ ] A passwordless install and installed boot follow under their own timeout (#21).
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
- [x] Component-directory migration with reviewed ISO/live-deploy payload
  comparison, clean Linux ISO build/validation and checkpointed VM deployment
  plus rollback (#92, #96). Installed OS paths stayed unchanged; evidence is
  recorded in docs/EVIDENCE.md.
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
