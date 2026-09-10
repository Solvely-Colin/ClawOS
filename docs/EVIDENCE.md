# Evidence ledger

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

Full hashes are in the private copies and in the run artifacts; the ledger
shows the first and last characters so a row can be matched to a file.

## Component-layout migration verification

On 2026-09-10, source `01655a6012d74610d37fbb829740c7d7f49cfb5f` produced
`clawos-fast-2026.09.10-x86_64.iso`, SHA-256
`1b6a0f43a405eae95c0b4c4551a4e53a88dc025c0169490ffbf81e49a4f45767`,
in a Windows-managed QEMU/WHPX Linux builder using isolated virtio scratch storage.
The clean fast build and ISO boot-chain, runtime-version and SSH-policy validator
passed. This locally built image was not newly booted or installed; no release
or public binary artifact was published.

Compared with pre-migration source `7233f4d`, assembled profile and runtime
payload comparisons found no removed destinations or mode changes. Reviewed
differences were the new source-path instructions/deployer mappings and plugin
README. A checkpointed live deployment of the path-migrated runtime completed
with desktop/broker ready and plugin loaded, then rolled back. Hash, mode,
ownership, excluded-configuration and dirty source-checkout comparisons matched
their pre-test state. The final follow-up payload differs from the live-tested
one only in plugin README prose. Model inference and full-system rollback are
not established by this test. Detailed receipts remain private; review is #96.
