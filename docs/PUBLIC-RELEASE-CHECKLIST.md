# Before public source

- [x] Owner approved MIT for ClawOS-owned code on 2026-09-08; LICENSE is present
      and third-party license exceptions remain documented in NOTICE.md.
- [x] Owner approved retaining the disclosed AI-generated artwork for the
      experimental launch on 2026-09-08; original branding remains a follow-up.
- [x] Complete the tracked-source attribution/provenance inventory review
      (NOTICE.md, 2026-09-10 UTC). Copied-source exceptions, generated artwork,
      the unknown screenshot capture tool and non-MIT prototype dependencies
      are disclosed. This is not ISO redistribution clearance or legal certification.
- [x] Add SECURITY.md with the maintainer-designated email reporting route.
- [x] Obtain confirmation of the reporting mailbox: owner confirmed it works
      on 2026-09-10. No independent outside-sender test or mailbox-rule inspection
      is claimed. GitHub private vulnerability reporting remains flip-day work.
- [x] Scan the preparation candidate and all local refs/history, including the
      five recovered commits, with gitleaks 8.30.1 and full redaction. Exact
      candidate SHA, command and result are recorded in #15/private evidence.
      Repeat at the actual visibility SHA if any commit changes after that scan.
- [x] Audit the current tracked tree for VM images, firmware, auth stores and
      personal paths/evidence. Private VM evidence remains outside Git.
- [x] Resolve historical developer paths/session identifiers: owner accepted
      retaining the disclosed history on 2026-09-10; no rewrite requested.
- [x] Resolve retained Actions ISO artifacts: owner authorized removal on
      2026-09-10. All four GitHub copies were deleted after local checksum and
      metadata verification; remote artifact count was verified zero (#15).
      Private bundles, VM disks/checkpoints and build logs remain retained.
      Recheck for newly created artifacts immediately before the visibility change.
- [x] README, FEATURES, ROADMAP, NOTICE, m1/README, /etc/issue, os-release and loader titles say
      "experimental, VM-verified only, no releases"; one repository URL everywhere
      (image files pinned by the identity block at the end of `m1/tests/validate-profile.sh`;
      the Markdown files checked by hand on 2026-09-08).
- [x] Historical files carry the frozen-record banner
      (`git grep -l '^> \*\*Historical record\.\*\*'` lists 14 files; 2026-09-08).
- [x] A clean checkout passes CI (`ci.yml`) and the full Arch preflight
      (all four jobs green on `main` at `30541ba`, run 34428511092; includes
      the full Arch preflight, D-Bus proof and prototype smoke tests).
- [ ] Owner explicitly approves public visibility.

# Before the first prerelease

- [x] `release.yml` completes once on a manual run; retain its artifact and hashes
      (run 34270708295 on `main` at `00f81c5`, 2026-09-08; row in EVIDENCE.md).
- [ ] Build an ISO from the tagged source, pass `validate-iso.sh`, and run a fresh
      disposable-disk install and first boot (encrypted and passwordless).
- [ ] Verify a real agent request, live update, rollback and completion delivery.
- [ ] Document known failures and recovery instructions in the release notes.
- [ ] Review the draft prerelease and its hashes; a green build is not a supported release.
- [ ] Owner explicitly approves publication of the draft.

This checklist does not change repository visibility or publish a release.
If a secret or private artifact surfaces, revoke/rotate affected credentials
first, then remove and re-scan. Re-privatising a repository is not a remedy.
See [current preparation evidence and pending gates](PUBLIC-SOURCE-READINESS.md).
