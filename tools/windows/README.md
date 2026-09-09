# Windows development-VM lifecycle

The launch, run and unlock scripts manage an existing ClawOS QEMU disk through
Scheduled Tasks. Install QEMU and provision a disposable disk using the Linux
build instructions. Keep private machine files beside these scripts, never in Git:

- `clawos-builder-windows.qcow2`
- `clawos-builder-vars.fd` (that VM's writable UEFI variables)
- `clawos-builder-unlock.dpapi` (that Windows user's protected disk-unlock key)

The scripts expect the `clawos` guest account and an existing SSH key named
`clawos_vm_ed25519` or `clawos_codex` in the Windows user's `.ssh` directory.
Never copy someone else's credential or bypass unlock-screen verification.

```powershell
.\launch-clawos-builder.ps1 Install
.\launch-clawos-builder.ps1 Start
.\launch-clawos-builder.ps1 Status
.\launch-clawos-builder.ps1 Logs
.\launch-clawos-builder.ps1 Checkpoint
.\launch-clawos-builder.ps1 Shutdown
```

SSH is loopback-only on port 2222; QMP uses port 4444. Shutdown uses SSH or ACPI.
The unlock helper verifies the encrypted-root screen before sending credentials
and fails closed if recognition is unavailable. The absolute USB tablet avoids
relative-mouse dependence, but fullscreen layout remains a known issue.
These scripts are not a turnkey Windows installer.

## Getting a CI-built ISO for acceptance runs

Acceptance runs (the WHPX install and boot proofs recorded in
`docs/HARDWARE-INSTALLER-VALIDATION.md` and the evidence ledger) use ISOs built
by the **Experimental ISO build** workflow (`.github/workflows/release.yml`)
only. Guest-built `sudo ./m1/bin/build-iso --fast` images are for edit/build
loops in the builder VM: they have no CI run id and their `Source commit` is
whatever working tree was checked out, so they do not go in the ledger.

`Get-CiIso.ps1` fetches one CI artifact and ties it to its run. It runs in
Windows PowerShell 5.1 like the other scripts here and needs the GitHub CLI
logged in with read access to the repository (`gh auth login`).

```powershell
# a specific run id (from the Actions tab or `gh run list -w release.yml`)
.\Get-CiIso.ps1 -RunId 34270708295 -Destination C:\ClawOS\iso\run-34270708295

# the newest successful release.yml run on main
.\Get-CiIso.ps1 -Latest -Destination C:\ClawOS\iso\latest-main
```

Pass `-Repo OWNER/REPO` for a fork and `-Branch <name>` with `-Latest` for a
branch other than `main`. The script:

1. resolves the run with `gh run view` (or `gh run list -w release.yml -s success`)
   and refuses runs that did not complete successfully;
2. runs `gh run download <run-id> -n clawos-iso-<head-sha>` into a staging
   directory inside `-Destination`;
3. checks every `SHA256SUMS` entry with `Get-FileHash`, requires exactly one
   `.iso`, and requires the `Source commit:` line of `BUILD-METADATA.txt` to
   equal the run's head commit;
4. writes `CI-ISO-MANIFEST.txt` and moves it, the ISO and the build metadata
   files into `-Destination`. Nothing there is overwritten; use one empty
   directory per ISO. A failed download or check removes the staging directory
   and leaves `-Destination` as it was.

Point `-Destination` at the directory your WHPX harness boots ISOs from. The
harness itself is not part of this repository and is not configured here.

The manifest is plain `key: value` lines:

```
Run id: 34270708295
Run URL: https://github.com/Solvely-Colin/ClawOS/actions/runs/34270708295
Repository: Solvely-Colin/ClawOS
Artifact: clawos-iso-<head-sha>
Source commit: <head-sha>
ISO: clawos-<date>-x86_64.iso
ISO SHA-256: <sha256>
Downloaded at: <UTC time>
Verified: 1 SHA256SUMS entry with Get-FileHash
```

### Filling a `docs/EVIDENCE.md` row

Each acceptance run adds one row to the evidence ledger. The manifest supplies
the build side of the row; the harness run supplies the rest.

| Ledger column | Source |
| --- | --- |
| date | the day of the harness run (`Downloaded at` only dates the download) |
| source commit | `Source commit` |
| ISO SHA256 | `ISO SHA-256` |
| build | `CI run <Run id>` |
| harness or manual proof, host, result | the WHPX run itself |
| where private evidence lives | your private record, or `not retained` |

Copy the hash and commit from the manifest instead of retyping them, and keep
`CI-ISO-MANIFEST.txt` with the private evidence for that row.
