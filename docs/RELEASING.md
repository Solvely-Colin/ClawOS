# Experimental release automation

The **Experimental ISO build** GitHub Actions workflow supports:

- **Manual run:** build the selected ref and retain ISO/checksum/build metadata
  as an Actions artifact for 14 days. It does not create a release on a branch.
- **Version tag:** a tag such as `v0.1.0-alpha.1` builds an ISO and creates a
  **draft prerelease** after a successful build. A maintainer must review and
  publish it. Existing releases/assets are not overwritten automatically.

The privileged build runs inside a disposable Arch container on a hosted Linux
runner, never on the Windows development host or an unattended personal runner.
It reclaims unused Android/.NET/Haskell SDK directories only after verifying
the hosted-runner environment and exact target paths, then requires 20 GB free.
No provider credentials or VM disks are passed to it. Build has read-only repo
permissions; only the separate draft-publication job can write release assets.

The helper uses the repository's Arch snapshot and checks the ArchISO version.
It runs full source preflight, builds the release-compressed ISO, validates its
boot-chain structure, and records the source SHA, package list, container digest
and SHA256 checksums. The bootstrap container tag is resolved at build time and
its digest recorded; this is not a claim of bit-for-bit reproducibility.

## What success does not mean

The workflow does not boot the image, install a fresh disk, run a model request,
test physical hardware, or prove full-system rollback. It must not be described
as a verified stable release. See [hardware restrictions](HARDWARE.md) and the
[public-release checklist](PUBLIC-RELEASE-CHECKLIST.md).

Before publishing a draft, independently run the disposable QEMU boot/install
gates from m1/README.md and attach redacted evidence at the same source SHA.
The current installer intentionally refuses physical hardware; do not remove
that protection merely to broaden release claims.

Builds can fail if the pinned archive/tool versions are unavailable, hosted-runner
disk space is insufficient, or ArchISO needs kernel capabilities the hosted
container does not expose. Diagnose those failures rather than skipping gates.
First successful automated build remains an acceptance item until its run is
verified. Do not create a release tag just to make the workflow look complete.
