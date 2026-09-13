# Public release checklist

Source publication is complete; this is the reusable gate for future binary
releases, not a diary of the maintainer's launch session. See
[repository protections](GITHUB-PROTECTIONS.md) and [evidence](EVIDENCE.md).

## Before distributing an image

- [ ] Review licenses, dependency/asset provenance and notices for the actual
  image, not only ClawOS-owned source.
- [ ] Scan source/history and inspect the image and candidate upload for
  credentials, private evidence and machine-specific state.
- [ ] Confirm the private reporting route in SECURITY.md and repository
  protection readbacks.
- [ ] Pass all four source CI jobs and the full Arch preflight at the exact
  candidate revision; inspect CodeQL and dependency findings.
- [ ] Review the artifact list and distribution decision. Public Actions
  artifacts can distribute binaries even without a GitHub release.
- [ ] State experimental status, VM-only verification and unsupported hardware
  clearly. Do not imply supported releases or arbitrary OS rollback.

## Before the first prerelease

- [x] The release workflow has completed on main; dated build records are in
  EVIDENCE.md. Historical ISO copies were removed from GitHub for source-first
  publication; retained private proof is not a public download.
- [ ] Build an ISO from the tagged source, pass validate-iso.sh, and run fresh
  disposable-disk installation and first boot in encrypted and passwordless modes.
  - [x] Passwordless automation established on a branch in hosted KVM run
    34511620906: fresh disk, install, disk-only boot and ACPI shutdown.
    This does not tick the tagged-source or encrypted-mode requirement above.
  - [x] Private candidate `f2da7a6` passed GTK passwordless install and a
    separate encrypted CLI install, disk-only boots and first-boot provider
    handoff under WHPX/e1000e on 2026-09-13. It remains pre-tag evidence: the
    encrypted passphrase was not submitted through GTK, and the tagged-source
    both-mode requirement above remains open.
- [x] Verify a real agent request, live update, rollback and completion delivery.
  - Passed on the unmodified CI ISO from run 34522981039 at `7a2c464`, in a fresh
    passwordless WHPX guest, without runtime repair. Includes lost-ack retry and
    exact 101-target restoration; see HARDWARE-INSTALLER-VALIDATION.md. Repeat
    for a materially changed release candidate; this does not satisfy both-mode GTK.
- [ ] Document known failures and recovery instructions in release notes.
- [ ] Review the draft prerelease and its hashes; a green build is not a supported release.
- [ ] Obtain explicit owner approval to publish the draft.

This checklist does not change visibility, create a tag or publish a release.
If a credential or private artifact surfaces, revoke/rotate affected credentials
first, then remove and re-scan. Re-privatising is not a remedy for disclosure.
