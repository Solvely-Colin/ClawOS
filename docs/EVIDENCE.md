# Evidence ledger

One row per ISO proof. "Result" says what was observed, not what was hoped.
Private evidence (screendumps, serial transcripts, build metadata, the ISO
itself) lives outside this repository on the maintainer's host; "not retained"
means it no longer exists anywhere. Later validation notes append rows here
instead of prose.

| Date | Source commit | ISO SHA-256 | Build | Proof | Host | Result | Private evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-09-06 | `3d16178` tree, installer refreshed to `47b6e44` before install | `dbc1f556…8c4094` | local fast, builder VM | passwordless install driven from live tty1, reboot through the registered firmware entry, login and service checks | Windows QEMU (WHPX, OVMF) | pass | screendumps and serial log retained |
| 2026-09-07 | `ee2f4f1` | `11ccf162…64d3d` | local fast, builder VM | encrypted and passwordless installs, first boot of each, key-only `sshd -T` on both installed systems, LUKS unlock by typed passphrase | Windows QEMU (WHPX, OVMF) | pass; live side still `PasswordAuthentication yes` (drop-in renamed afterwards in `7244a54`) | screendumps and serial logs retained |
| 2026-09-08 | `6a2a456` (`track-c/ci-honest`) | see run artifact | `release.yml` run 34241236444 | preflight, `mkarchiso`, `validate-iso.sh` | GitHub-hosted runner | built and validated, not booted | artifact expires 2026-09-22 |
| 2026-09-08 | `00f81c5` (`main`) | `9442e105…816fd` | `release.yml` run 34270708295 | preflight, `mkarchiso`, `validate-iso.sh`, `sha256sum -c SHA256SUMS` after download | GitHub-hosted runner | built and validated, not booted; first green run | artifact expires 2026-09-22; ISO, `SHA256SUMS`, `BUILD-METADATA.txt`, `BUILD-PACKAGES.txt`, `BUILD-CONTAINER.txt` retained privately |

Full hashes are in the private copies and in the run artifacts; the ledger
shows the first and last characters so a row can be matched to a file.
