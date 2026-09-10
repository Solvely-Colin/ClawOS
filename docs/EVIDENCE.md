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

Full hashes are in the private copies and in the run artifacts; the ledger
shows the first and last characters so a row can be matched to a file.
