# Evidence ledger

Historical entries retain their original pre-baseline source hashes and CI run
IDs. They are not proof of a newly built baseline image. See [HISTORY.md](HISTORY.md)
for the public-history reset and archive boundary; records are not rewritten
to imply that old tests ran on a different commit.

One row per ISO proof. "Result" says what was observed, not what was hoped.
Private evidence (screendumps, serial transcripts, build metadata, the ISO
itself) lives outside this repository on the maintainer's host; "not retained"
means it no longer exists anywhere. Later validation notes append rows here
instead of prose.

| Date | Source commit | ISO SHA-256 | Build | Proof | Host | Result | Private evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-09-06 | `3d16178` tree, installer refreshed to `47b6e44` before install | `dbc1f556…8c4094` | local fast, builder VM | passwordless install driven from live tty1, reboot through the registered firmware entry, login and service checks | Windows QEMU (WHPX, OVMF) | pass | screendumps and serial log retained |
| 2026-09-07 | `47b6e44` tree with the download fix (pre-`eb630cd`) | `8826f15d…99a5fc` | local fast, builder VM | encrypted NVMe and passwordless SATA installs, first boot of each through the registered firmware entry, LUKS unlock, onboarding entry screen; with networking disabled the installer exhausted its three attempts and left the disk untouched | Windows QEMU (WHPX, OVMF), 40 GiB disks | pass; the passwordless guest's first paint stalled until keyboard input (cause unconfirmed) | serial logs retained |
| 2026-09-07 | `ee2f4f1` | `11ccf162…764d3d` | local fast, builder VM | encrypted and passwordless installs, first boot of each, key-only `sshd -T` on both installed systems, LUKS unlock by typed passphrase | Windows QEMU (WHPX, OVMF) | pass; live side still `PasswordAuthentication yes` (drop-in renamed afterwards in `7244a54`) | screendumps and serial logs retained |
| 2026-09-08 | `6a2a456` (`track-c/ci-honest`) | see run artifact | `release.yml` run 34241236444 | preflight, `mkarchiso`, `validate-iso.sh` | GitHub-hosted runner | built and validated, not booted | artifact expires 2026-09-22 |
| 2026-09-08 | `00f81c5` (`main`) | `9442e105…6816fd` | `release.yml` run 34270708295 | preflight, `mkarchiso`, `validate-iso.sh`, `sha256sum -c SHA256SUMS` after download | GitHub-hosted runner | built and validated, not booted; first green run on `main` | artifact expires 2026-09-22; ISO, `SHA256SUMS`, `BUILD-METADATA.txt`, `BUILD-PACKAGES.txt`, `BUILD-CONTAINER.txt` retained privately |
| 2026-09-08 | `00f81c5` (`main`) | `9442e105…6816fd` | `release.yml` run 34270708295 artifact | live boot only, no install: `sshd -T` key-only, `00-clawos.conf` first in `sshd_config.d`, sshd listening on 22, live root has no password | Windows QEMU (WHPX, OVMF) | pass | serial transcript retained |
| 2026-09-09 | `00f81c5` (`main`) | `9442e105d287c300e08b8ce9821859fa684067d761afd3b69491552a956816fd` | `release.yml` run 34270708295 artifact | `Get-CiIso.ps1 -RunId`: workflow identity, source commit and ISO checksum verified; a real non-release run was refused before download | Windows PowerShell host | download/verification pass; no new boot or installation attempted | ISO, checksums, build metadata and CI-ISO-MANIFEST.txt retained privately |
| 2026-09-10 | `30541badb58dc09eb11e7faef3f13437703f1b7f` | `9c36f76a02c3054ae775d700323eac818d9b4adbe1a673cc1840c3e924b3b22e` | `release.yml` run 34429154651; Get-CiIso verification | live boot, key-only sshd and listener inspection, graphical Welcome/Inspect/disk selection | Windows QEMU 11.1/WHPX, OVMF, 8 GiB RAM, blank 40 GiB NVMe, 1440x900 | live SSH policy passed; GTK Back/Erase controls were clipped, so no install was attempted. A temporary layout patch was then visually checked at 1440x900 and 1280x768, including confirmation gating; that is not fresh-ISO acceptance | ISO, manifest, build log, live posture output and before/after screenshots retained privately |
| 2026-09-10 | `de19c1bccc839a47696afd4c7009f6717c43d934` | `119768a247fd5e76f15a0df1914f554cc9bd2f5f4a53db3c810d68693a5ede32` | `release.yml` run 34432248984; Get-CiIso verification | unmodified ISO: graphical encrypted install, disk-only boot/LUKS unlock, local Gateway/model-later/Full Root onboarding, API completion, Control UI, SSH and listener checks | Windows QEMU 11.1/WHPX, OVMF, fresh 40 GiB NVMe, 8 GiB RAM, 1440x900 | pass for this path; archive resets recovered on attempt 3; intermittent host-forwarded SSH timeouts recorded; no inference or non-default policy proof | full observations, screenshots, metadata and offline checkpoints retained privately; see HARDWARE-INSTALLER-VALIDATION.md |
| 2026-09-10 | `01655a6012d74610d37fbb829740c7d7f49cfb5f` | `1b6a0f43a405eae95c0b4c4551a4e53a88dc025c0169490ffbf81e49a4f45767` | local fast build, `clawos-fast-2026.09.10-x86_64.iso` | clean build after component-directory migration; ISO boot-chain, runtime-version and SSH-policy validation | Windows-managed QEMU/WHPX Linux builder with isolated virtio scratch storage | build and validation passed; this ISO was not newly booted or installed | ISO, checksum and logs retained privately; no release or public binary artifact published |
| 2026-09-10 | `0b2f80b9899067a20f0e17fba5e6efb310978b7d` | `ebf236162e3bb0362918a7ca62d9579dbd8da3a7ce33fc4547519935a231b3d6` | `release.yml` run 34505506520 | clean build and live KVM smoke: identity, systemd, DHCP, overlay root, SSH policy and serial-shell poweroff | GitHub-hosted Ubuntu runner, Arch container, QEMU/KVM | passed; preliminary shutdown path superseded by the ACPI run below | scanned boot evidence retained; ISO retention disabled; no release |
| 2026-09-10 | `82afc7051c055305dc983b61fc0f4ee45a1271b0` | `8d30dfc6b95a0c290e1f09c298c96fd1c6a04bf994b21b1abe66f7669094cb40` | `release.yml` run 34507795187 | clean build, all seven live smoke markers, acknowledged ACPI request, kernel Power down and normal QEMU exit | GitHub-hosted Ubuntu runner, Arch container, QEMU/KVM | passed; no installation, onboarding or inference tested | scanned boot evidence retained; ISO retention disabled; no release |
| 2026-09-10 | `dd8cd8d4179eafc82faec771e7dc1193be909086` | `4ce4a4c62344fb8e5534c2f9b00758e9a1ac7bf83ed9e5fa4a4409bf84b20122` | `release.yml` run 34511620906 | clean build, live smoke, passwordless install to new 32 GiB virtio disk, disk-only boot, installed services/SSH/OpenClaw checks, screendump and ACPI shutdowns | GitHub-hosted Ubuntu runner, Arch container, QEMU/KVM, Q35/OVMF, 8 GiB install guest | passed; test-only serial root autologin; screenshot shows desktop/top bar, not completed onboarding | scanned evidence downloaded and re-scanned; no ISO, disk or firmware uploaded; no release |
| 2026-09-10 | ISO `de19c1bccc839a47696afd4c7009f6717c43d934`; runtime candidate `aad7829` plus one agent-authored comment | `119768a247fd5e76f15a0df1914f554cc9bd2f5f4a53db3c810d68693a5ede32` | retained CI run 34432248984 ISO | new normal passwordless CLI install and real inference; checkpointed updater repair, then agent-driven update, lost-ack delivery retry, rollback and same-session follow-up | Windows QEMU/WHPX, Q35/OVMF, new 40 GiB virtio disk, 8 GiB RAM | original image failed updater readiness; repaired loop passed with exact restoration of 101 targets and one notice per outcome; not an unmodified-candidate pass | private checkpoints and scanned response/history evidence; details in HARDWARE-INSTALLER-VALIDATION.md |
| 2026-09-10 | `4e9767f44bc410a386e7247720392a54247ced2b` | `081ec3fe13d54f6204836eff23ce420fcc92fec712edf9981a5026c27dce08d2` | `release.yml` run 34519540819 | unmodified live boot, passwordless install, disk-only boot, DEPLOY_READY_OK and other installed assertions, ACPI shutdowns, disk check | GitHub-hosted Ubuntu/Arch container, QEMU/KVM, Q35/OVMF, 32 GiB disk, 8 GiB install guest | passed, including executable updater and installed/enabled delivery units; no provider/agent-loop run on this binary | artifact 10170028322 downloaded, re-scanned and screenshot inspected; no ISO/disk upload or release |
| 2026-09-10 | `7a2c464d2708c833fba6411774177610e1770f4d` | `9e0f75342931a10ee73f052e1b085ea2873d382ac37e33232fffa7c80ed96b9b` | `release.yml` run 34522981039 | all hosted live/install/updater gates; verified private ISO download | GitHub-hosted Ubuntu/Arch, QEMU/KVM | passed; source and checksum independently matched | ISO artifact 10171296669 temporarily retained with approval, then deleted after private verification; scanned evidence 10171286463 remains; no release |
| 2026-09-10 | ISO `7a2c464d2708c833fba6411774177610e1770f4d`; runtime test adds one agent-authored comment | `9e0f75342931a10ee73f052e1b085ea2873d382ac37e33232fffa7c80ed96b9b` | retained run 34522981039 ISO | unmodified ISO, normal passwordless CLI install, disk-only boot, native provider setup, real inference, agent-led update, lost-ack retry, rollback and same-session receipt read | Windows QEMU/WHPX, Q35/OVMF, new 40 GiB virtio disk, 8 GiB RAM | core loop passed without runtime repair: 29 s update, 28 s rollback, all 101 targets restored, one notice per outcome; initial auth request failed and unchanged credential/model retry passed | private ISO, checkpoints and scanned/redacted evidence retained; see HARDWARE-INSTALLER-VALIDATION.md for limits |

| 2026-09-11 (UTC) | `4ad401a71f8692c5381bed0dc8ac2530fb92629d` | `46ea9456fac767d3d33dd7ac7444a18c7f97b31daf3c38b8f2557667fbbe4c37` | clean local release-compressed build in the Linux builder VM, ArchISO 89-1; Windows transfer hash matched | source and image validation; fresh live boot with 2 GiB; VM observation `qemu`; only the intended blank 40 GiB target offered; GTK form observed with no default disk and Erase disabled; CLI passwordless preparation refused in 4 seconds (1386 MiB required, 968 MiB free in RAM-backed `/tmp`) | Windows QEMU/WHPX, Q35/OVMF, fresh virtio disk | pass for this bounded refusal: exit 1 before erase, no disk filesystem/partitions, acknowledged ACPI shutdown and QEMU exit 0; offline `qemu-img compare` found the entire logical disk identical to a fresh blank reference. Not a completed GUI install, both-mode acceptance, a CI-built image, or an integrity-enforced build (predates PR #105) | ISO, hash, build/refusal logs and screenshots retained privately; no tag, release or ISO upload |

Full hashes are in the private copies and in the run artifacts; the ledger
shows the first and last characters so a row can be matched to a file.

## Automated live boot gate

On 2026-09-10, [run 34505506520](https://github.com/Solvely-Colin/ClawOS/actions/runs/34505506520)
at `0b2f80b9899067a20f0e17fba5e6efb310978b7d` built
`clawos-2026.09.10-x86_64.iso`, SHA-256
`ebf236162e3bb0362918a7ca62d9579dbd8da3a7ce33fc4547519935a231b3d6`,
and booted that exact image in the Arch build container using hosted-runner KVM.
The KVM device/API/VM-creation probe passed. Executed serial markers confirmed
ClawOS identity, systemd health, QEMU DHCP address, overlay root and key-only SSH
configuration; QEMU exited normally after guest poweroff. Result metadata says
`Live boot smoke: RUN (KVM, run 34505506520)` and `Graceful shutdown: PASS`.

Only the scanned `clawos-boot-evidence-*` artifact was uploaded (serial,
transcript, QEMU log, metadata, result and checksum). Its logs were scanned
again after download. ISO retention was disabled; the release job was skipped.
This proves live boot, not installation, onboarding, inference or hardware.
Follow-up commits tighten the optional ISO upload allowlist, record failed
attempts explicitly, and switch successful shutdown from a serial-shell
poweroff command to acknowledged ACPI. That final path passed in
[run 34507795187](https://github.com/Solvely-Colin/ClawOS/actions/runs/34507795187)
at `82afc7051c055305dc983b61fc0f4ee45a1271b0`: every marker was present,
the serial log ended with `reboot: Power down`, and QEMU exited normally.
Only the six-file scanned evidence artifact was uploaded; result and metadata
checksums agreed. Later probe-error diagnostics and documentation changes do
not change the tested boot harness or image content.

## Automated passwordless install gate

[Run 34511620906](https://github.com/Solvely-Colin/ClawOS/actions/runs/34511620906)
passed at the exact source and ISO hash listed above. A fresh 32 GiB QCOW2 was
the only writable block disk. The live guest verified its dedicated serial and
the installer's disk ID before passing the exact erase confirmation. After
installation and ACPI powerdown, the harness restarted with the same disk and
firmware variables but no ISO attached.

Executed markers confirmed Btrfs root on `/dev/vda2[/@]`, zero failed units,
active desktop/broker/SSH/NetworkManager services, effective key-only SSH policy,
OpenClaw 2026.8.2 and passwordless-entry configuration. The live and installed
serial logs end with kernel `reboot: Power down`; the offline QCOW2 check found
no errors. The retained screendump shows the installed desktop and top bar,
not an onboarding completion or model inference result.

Only artifact `10166886222` (`clawos-boot-evidence-dd8cd8d4179eafc82faec771e7dc1193be909086-1`)
was uploaded. Its explicit whitelist contains logs, checksum/metadata and a
fresh-guest screendump, not ISO, QCOW2, writable firmware or credentials. Logs
and image bytes were re-scanned after download; the image was visually reviewed.
Binary pattern scanning is not OCR. No release was created.

The installer ran with `--vm-test --passwordless`: serial root autologin is
test-only, not proof of the shipped console policy. Encrypted installation,
onboarding, inference, update/recovery and physical hardware remain separate.
Follow-up changes add regression tests and reject a guest that exits before
the required ACPI request; they do not change image contents. That stricter
failure guard passed Linux source CI, not a second full ISO installation run.

## Component-layout runtime verification

Compared with pre-migration source `7233f4d`, assembled profile and runtime
payload comparisons found no removed destinations or mode changes. Reviewed
differences were the new source-path instructions/deployer mappings and plugin
README. A checkpointed live deployment of the path-migrated runtime completed
with desktop/broker ready and plugin loaded, then rolled back. Hash, mode,
ownership, excluded-configuration and dirty source-checkout comparisons matched
their pre-test state. The final follow-up payload differs from the live-tested
one only in plugin README prose. Model inference and full-system rollback are
not established by this test. Detailed receipts remain private; review is #96.
