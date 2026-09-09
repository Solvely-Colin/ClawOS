# Before public source

- [x] Owner approved MIT for ClawOS-owned code on 2026-09-08; LICENSE is present
      and third-party license exceptions remain documented in NOTICE.md.
- [x] Owner approved retaining the disclosed AI-generated artwork for the
      experimental launch on 2026-09-08; original branding remains a follow-up.
- [ ] Complete copied code, icons, fonts and artwork attribution/provenance review (NOTICE.md).
- [x] Add SECURITY.md with the maintainer-designated email reporting route.
- [ ] Verify mailbox delivery before publication; optionally enable and verify
      GitHub private vulnerability reporting when available.
- [ ] Repeat a redacted secret scan of source and all history at the publication SHA.
- [ ] Confirm no VM images, firmware variables, auth stores or personal paths/evidence are tracked.
- [x] README, FEATURES, ROADMAP, NOTICE, m1/README, /etc/issue, os-release and loader titles say
      "experimental, VM-verified only, no releases"; one repository URL everywhere
      (image files pinned by the identity block at the end of `m1/tests/validate-profile.sh`;
      the Markdown files checked by hand on 2026-09-08).
- [x] Historical files carry the frozen-record banner
      (`git grep -l '^> \*\*Historical record\.\*\*'` lists 14 files; 2026-09-08).
- [x] A clean checkout passes CI (`ci.yml`) and the full Arch preflight
      (both jobs green on `main` at `00f81c5`; preflight passed in the builder VM on the same commit).
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
