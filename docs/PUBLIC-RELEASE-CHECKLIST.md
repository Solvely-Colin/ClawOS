# Before opening the repository to the public

- [ ] Owner selects an open-source license; add it without replacing third-party licenses.
- [ ] Complete copied code, icons, fonts and artwork attribution/provenance review.
- [ ] Approve SECURITY.md and a private vulnerability-reporting route.
- [ ] Repeat a redacted secret scan of source and all history at the publication SHA.
- [ ] Confirm no VM images, firmware variables, auth stores or personal evidence is tracked.
- [ ] Confirm README, features and release notes say VM-only development installer.
- [ ] Verify a clean checkout passes CI and the full Arch preflight.
- [ ] Build an ISO and verify a fresh disposable-disk install and first boot.
- [ ] Verify a real agent request, live update, rollback and completion delivery.
- [ ] Document known failures and recovery instructions; do not hide them in release notes.
- [ ] Review a draft prerelease and its hashes; a successful build is not a supported release.
- [ ] Owner explicitly approves public visibility and publication.

This checklist does not change repository visibility or publish a release.
