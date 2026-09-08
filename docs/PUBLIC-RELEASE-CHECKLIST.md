# Before public source

- [ ] Owner selects an open-source license; add LICENSE without replacing third-party licenses.
- [ ] Complete copied code, icons, fonts and artwork attribution/provenance review (NOTICE.md).
- [ ] Add SECURITY.md and enable a private vulnerability-reporting route.
- [ ] Repeat a redacted secret scan of source and all history at the publication SHA.
- [ ] Confirm no VM images, firmware variables, auth stores or personal paths/evidence are tracked.
- [ ] README, FEATURES, ROADMAP, NOTICE, m1/README, /etc/issue, os-release and loader titles say
      "experimental, VM-verified only, no releases"; one repository URL everywhere.
- [ ] Historical files carry the frozen-record banner.
- [ ] A clean checkout passes CI (`ci.yml`) and the full Arch preflight.
- [ ] Owner explicitly approves public visibility.

# Before the first prerelease

- [ ] `release.yml` completes once on a manual run; retain its artifact and hashes.
- [ ] Build an ISO from the tagged source, pass `validate-iso.sh`, and run a fresh
      disposable-disk install and first boot (encrypted and passwordless).
- [ ] Verify a real agent request, live update, rollback and completion delivery.
- [ ] Document known failures and recovery instructions in the release notes.
- [ ] Review the draft prerelease and its hashes; a green build is not a supported release.
- [ ] Owner explicitly approves publication of the draft.

This checklist does not change repository visibility or publish a release.
