# Near-term roadmap

The detailed PLAN.md retains the original long-term vision. This page is the
current contributor work queue; checkboxes are acceptance criteria, not promises.

## 1. Make everyday development reliable

- [ ] Fix setup/fullscreen offset and clipping; verify pointer alignment at
  windowed, maximized and fullscreen sizes with saved screenshots.
- [ ] Make cold-boot desktop ownership deterministic; distinguish startup,
  locked, setup-incomplete, ready and repair-required states.
- [ ] Bind terminal, browser and build surfaces to their owning task; prove
  two simultaneous tasks cannot cross-route prompts or lose drafts.
- [ ] Re-run clean-disk onboarding, live update, interrupted delivery and rollback
  against an ISO produced by CI, not an accumulated developer VM.

## 2. Invite contributors without overstating readiness

- [x] Private GitHub repository with history, contributor guide and unit CI.
- [ ] Validate an automated clean ISO build and retain its evidence.
- [ ] Select a public license and complete asset/dependency attribution.
- [ ] Approve a security/disclosure policy and enable an appropriate private
  reporting route before public visibility.
- [ ] Publish an explicitly experimental, VM-only prerelease after human review.

## 3. Design physical installation as its own milestone

- [ ] Inventory hardware and define the initial supported UEFI x86_64 matrix.
- [x] Implement experimental blank-disk selection with explicit confirmation,
  live-media protection and disk-identity rechecks; validation is still required
  on fresh SATA/NVMe VMs and physical machines.
- [ ] Validate NVMe/SATA, graphics, networking, firmware, suspend and input.
- [ ] Prove boot/root/home compatibility during failed-update recovery.
- [ ] Establish Secure Boot and T2 hardware policies rather than implying support.

Keep runtime engineering moving while release preparation happens. Repository
polish does not resolve the outstanding OS acceptance criteria.
