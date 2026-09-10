# Experimental release automation

The **Experimental ISO build** GitHub Actions workflow supports:

- **Manual run:** build the selected ref and require live KVM boot and passwordless install smoke tests.
  Scanned boot evidence is retained for 14 days. ISO upload defaults off;
  select `retain_iso` explicitly to expose the ISO/checksum/build metadata to
  repository readers. It does not create a release on a branch.
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

Before building, the hosted runner must expose readable/writable `/dev/kvm`
and successfully create a KVM VM. Missing acceleration fails the workflow;
there is no silent skip. This follows GitHub's
[hosted KVM setup](https://github.blog/changelog/2024-04-02-github-actions-hardware-accelerated-android-virtualization-now-available/),
with a live probe because runner capabilities can change.

The same Arch container then boots the exact newly built ISO using
`image/tests/boot-smoke-qemu`. Executed serial markers check ClawOS identity,
systemd health, DHCP, overlay root and effective SSH policy. The host then
requests acknowledged ACPI powerdown; the guest must shut down and QEMU must
exit successfully. Cleanup also requests ACPI, never QEMU
termination. If a failed guest refuses shutdown, the gate stays failed; the
disposable container/runner may subsequently be reclaimed by CI infrastructure.

`BUILD-METADATA.txt` records `Live boot smoke: RUN (KVM, run <id>)` only after
success; failed or unexecuted smoke never gets that claim. Serial, transcript
and QEMU logs are scanned before publication, including failure evidence. The
separate `clawos-boot-evidence-*` artifact contains no ISO, writable firmware
variables or sockets. Evidence containing secret-shaped text is not uploaded.

Next, `image/tests/install-smoke-qemu ISO` creates a new 32 GiB QCOW2 and
installs using `--vm-test --passwordless`. It checks the dedicated virtio disk
serial, obtains the installer's disk ID and supplies the exact erase confirmation.
Existing runtime directories or disks are never reused. This test needs KVM,
8 GiB guest memory and matching OVMF code/variable templates; the workflow gives
it a separate 60-minute limit. Both guest shutdowns use acknowledged ACPI.
After installation it boots the same disk and firmware variables with the ISO
detached, checks Btrfs root, zero failed units, desktop/broker/SSH/network
services, effective SSH policy and the pinned OpenClaw version, and captures
one fresh-guest screendump. The evidence artifact's `install/` directory retains
only explicitly listed, scanned logs and the screendump, never the disk or NVRAM.
Text-pattern scanning of image bytes is not OCR or a general screenshot secret
detector; this isolated guest receives no credentials or enrollment data.

`--vm-test` changes the installed console by enabling serial **root autologin**,
restricted by the installer to KVM, Q35 and `/dev/vda`. It proves the passwordless
install/boot chain, not the shipped serial-console posture. Successful execution
alone changes `Passwordless install smoke: NOT RUN` to `RUN (KVM, run <id>)`;
failure records `FAILED`. Encrypted install and full onboarding remain separate.

## What success does not mean

The 2026-09-10 public launch is source-only. Its four historical ISO artifacts
were removed after private backup verification; CodeQL SARIF artifacts are not
ISOs. New manual or tag builds can expose binaries to repository readers, so
review artifact distribution before dispatching them. The public entry point
is [building locally](GETTING-STARTED.md), not downloading an old CI run.

The live boot gate and separate passwordless install gate do not run a model
request, test physical hardware, or prove full-system rollback. They must not be described
as a verified stable release. See [hardware restrictions](HARDWARE.md) and the
[public-release checklist](PUBLIC-RELEASE-CHECKLIST.md).

Before publishing a draft, independently run the disposable QEMU boot/install
gates from image/README.md and attach redacted evidence at the same source SHA.
Every ISO proof, automated or manual, gets a row in [EVIDENCE.md](EVIDENCE.md).
The experimental installer accepts eligible blank x86_64 UEFI disks, but source
validation is not physical-hardware proof. Do not describe it as universal Arch
hardware support; record the exact machine and disk types actually tested.

Builds can fail if the pinned archive/tool versions are unavailable, hosted-runner
disk space is insufficient, or ArchISO needs kernel capabilities the hosted
container does not expose. Diagnose those failures rather than skipping gates.
The first green run on `main` was 34270708295 on 2026-09-08 (source commit
`00f81c5`, ISO SHA-256 beginning `9442e105`); a branch run had succeeded earlier
that day. At that time the workflow validated but did not boot; that artifact was booted
live by hand (EVIDENCE.md). Later run 34432248984 at `de19c1b` completed a
manual encrypted GTK install and default onboarding under WHPX on 2026-09-10;
provider inference and full update/recovery were not part of that proof.
Do not create a release tag just to make the
workflow look complete.

## Draft release-notes template

Fill this from the candidate's evidence, never from an older green run:

```text
ClawOS VERSION — experimental, VM-tested only
Source commit: FULL_SHA
ISO: FILENAME
SHA-256: FULL_HASH
Build/install evidence: RUN_URL and EVIDENCE.md row
Verified install modes and environment: EXACT_MODES / HOST / DISK
Agent inference, live update, delivery and rollback: PASS/FAIL/NOT RUN, evidence
Known failures: candidate-specific failures and links; list manual repairs
Not verified: encrypted/GTK/policy/hardware paths or other omitted acceptance

Recovery: Ctrl+Alt+F3 opens the independent local recovery console.
Log in using this installation's account policy. For a known runtime job,
inspect `sudo /usr/lib/clawos/clawos-deploy status JOB_ID` before acting.
Only an explicitly chosen job with a completed backup may be rolled back with
`sudo /usr/lib/clawos/clawos-deploy rollback JOB_ID`.
This restores managed runtime files, not packages, boot files, credentials or
user data. For boot failure or recovery-required, inspect the retained recovery
checkpoint and instructions; do not replay apply or claim full-system rollback.

Distribution: maintainer-reviewed draft; no supported-hardware or stability claim.
```
