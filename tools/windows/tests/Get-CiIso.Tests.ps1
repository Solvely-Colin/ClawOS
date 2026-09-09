<#
.SYNOPSIS
Check Get-CiIso.ps1 against small fixtures with gh replaced by a mock.

.DESCRIPTION
Runs under Windows PowerShell 5.1 and downloads nothing. For the duration of
the run a global function named gh shadows the GitHub CLI, so gh does not need
to be installed. The mock answers `run view` and `run list` with canned JSON
and `run download` by copying a fixture (a 4 KiB stand-in ISO, SHA256SUMS,
BUILD-METADATA.txt and the other files release.yml uploads) into the -D
directory Get-CiIso.ps1 asked for. Fixtures and destinations live in a fresh
directory under the user's temp path; it is removed when every check passes
and kept for inspection otherwise. Exit code 0 on success, 1 when a check
fails.

.PARAMETER KeepFiles
Keep the temporary directory after a successful run.

.EXAMPLE
.\tests\Get-CiIso.Tests.ps1
#>
[CmdletBinding()]
param([switch]$KeepFiles)

$ErrorActionPreference = 'Stop'
$Script = Join-Path (Split-Path -Parent $PSScriptRoot) 'Get-CiIso.ps1'
$Root = Join-Path ([System.IO.Path]::GetTempPath()) ('get-ci-iso-tests-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
$Repo = 'Solvely-Colin/ClawOS'
$RunId = '34270708295'
$Sha = '00f81c5da8e540d043bff9e94706ca6bc04a3e35'
$OtherSha = '6a2a456c55bf0715e34d8db05f49a16850c7e30d'
$IsoName = 'clawos-2026.09.08-x86_64.iso'
$RunUrl = "https://github.com/$Repo/actions/runs/$RunId"
$script:Failures = 0

function Assert([bool]$Condition, [string]$Message) {
    if ($Condition) {
        Write-Host "PASS  $Message"
    } else {
        Write-Host "FAIL  $Message"
        $script:Failures++
    }
}

function Expect-Throw([scriptblock]$Block, [string]$Pattern, [string]$Message) {
    try {
        & $Block | Out-Null
        Assert $false "$Message (no error was raised)"
    } catch {
        Assert ($_.Exception.Message -match $Pattern) "$Message -> $($_.Exception.Message)"
    }
}

function New-Fixture {
    # Writes what release.yml uploads: one ISO, its .sha256, SHA256SUMS and the
    # three BUILD-*.txt files. Returns the ISO's SHA-256.
    param(
        [string]$Dir,
        [string]$SourceCommit = $Sha,
        [switch]$Star,           # "<hash> *<name>" instead of "<hash>  <name>"
        [switch]$CorruptSums,    # SHA256SUMS carries a wrong hash for the ISO
        [switch]$NoSourceCommit, # BUILD-METADATA.txt without a Source commit line
        [switch]$MissingListed,  # SHA256SUMS lists a file that is not there
        [switch]$SecondIso       # a second .iso, also listed
    )
    New-Item -ItemType Directory -Path $Dir -Force | Out-Null
    $iso = Join-Path $Dir $IsoName
    $bytes = New-Object byte[] 4096
    (New-Object System.Random 42).NextBytes($bytes)
    [System.IO.File]::WriteAllBytes($iso, $bytes)
    $hash = (Get-FileHash -LiteralPath $iso -Algorithm SHA256).Hash.ToLowerInvariant()
    $listed = $hash
    if ($CorruptSums) { $listed = '0' * 64 }
    $sep = '  '
    if ($Star) { $sep = ' *' }
    $sums = "$listed$sep$IsoName`n"
    if ($MissingListed) { $sums += "$hash$sep" + "not-there.bin`n" }
    if ($SecondIso) {
        $second = Join-Path $Dir 'clawos-second-x86_64.iso'
        [System.IO.File]::WriteAllText($second, 'second image')
        $sums += (Get-FileHash -LiteralPath $second -Algorithm SHA256).Hash.ToLowerInvariant() + $sep + "clawos-second-x86_64.iso`n"
    }
    [System.IO.File]::WriteAllText((Join-Path $Dir 'SHA256SUMS'), $sums)
    [System.IO.File]::WriteAllText((Join-Path $Dir "$IsoName.sha256"), "$hash$sep$IsoName`n")
    $meta = "Build channel: experimental development ISO`nValidation: source preflight and ISO boot-chain structure`n# Milestone 1 build-input lock.`nARCH_SNAPSHOT=2026/08/25`nARCHISO_VERSION=89-1`n"
    if (-not $NoSourceCommit) { $meta = "Source commit: $SourceCommit`n" + $meta }
    [System.IO.File]::WriteAllText((Join-Path $Dir 'BUILD-METADATA.txt'), $meta)
    [System.IO.File]::WriteAllText((Join-Path $Dir 'BUILD-PACKAGES.txt'), "archiso 89-1`n")
    [System.IO.File]::WriteAllText((Join-Path $Dir 'BUILD-CONTAINER.txt'), "[`"archlinux@sha256:0000`"]`n")
    $hash
}

function Get-DownloadCalls {
    @($global:GetCiIsoMock.Calls | Where-Object { $_ -like 'run download*' })
}

# State the mock reads. Everything it needs is in here rather than in script
# variables, because the function runs in Get-CiIso.ps1's scope when called.
$global:GetCiIsoMock = @{
    Fixture  = $null       # directory whose files `run download` copies
    Layout   = 'flat'      # flat | nested | nested-stray
    Fail     = $false      # every call exits 1
    Calls    = @()         # argument strings, for assertions
    Artifact = "clawos-iso-$Sha"
    RunView  = @{ databaseId = [int64]$RunId; headSha = $Sha; url = $RunUrl; status = 'completed'; conclusion = 'success' }
    RunList  = @(@{ databaseId = [int64]$RunId; headSha = $Sha; url = $RunUrl })
}

function global:gh {
    $mock = $global:GetCiIsoMock
    $mock.Calls += ,($args -join ' ')
    if ($mock.Fail) {
        [Console]::Error.WriteLine('mock gh: simulated failure')
        $global:LASTEXITCODE = 1
        return
    }
    switch ("$($args[0]) $($args[1])") {
        'run view' {
            $global:LASTEXITCODE = 0
            return ($mock.RunView | ConvertTo-Json -Compress)
        }
        'run list' {
            $global:LASTEXITCODE = 0
            if ($mock.RunList.Count -eq 0) { return '[]' }
            return (ConvertTo-Json -InputObject @($mock.RunList) -Compress)
        }
        'run download' {
            $name = $args[[array]::IndexOf($args, '-n') + 1]
            $target = $args[[array]::IndexOf($args, '-D') + 1]
            if ($name -ne $mock.Artifact) {
                [Console]::Error.WriteLine("mock gh: no artifact named $name")
                $global:LASTEXITCODE = 1
                return
            }
            $into = $target
            if ($mock.Layout -ne 'flat') {
                $into = Join-Path $target $name
                New-Item -ItemType Directory -Path $into | Out-Null
            }
            Copy-Item -Path (Join-Path $mock.Fixture '*') -Destination $into
            if ($mock.Layout -eq 'nested-stray') {
                [System.IO.File]::WriteAllText((Join-Path $target 'stray.txt'), 'not part of the artifact')
            }
            $global:LASTEXITCODE = 0
            return
        }
        default {
            [Console]::Error.WriteLine("mock gh: unexpected call '$($args -join ' ')'")
            $global:LASTEXITCODE = 2
        }
    }
}

New-Item -ItemType Directory -Path $Root | Out-Null
Write-Host "Script:   $Script"
Write-Host "Work dir: $Root"
Write-Host ''

try {
    # --- 0. static ------------------------------------------------------------
    $tokens = $null; $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($Script, [ref]$tokens, [ref]$errors) | Out-Null
    Assert ($errors.Count -eq 0) "0 script parses without syntax errors ($($errors.Count) errors)"
    foreach ($e in $errors) { Write-Host "      $($e.Extent.StartLineNumber): $($e.Message)" }

    # --- 1. happy path by run id ---------------------------------------------
    $fxGood = Join-Path $Root 'fixture-good'
    $goodHash = New-Fixture -Dir $fxGood
    $global:GetCiIsoMock.Fixture = $fxGood
    $dest1 = Join-Path $Root 'dest1'
    $out = & $Script -RunId $RunId -Destination $dest1 6>&1 | Out-String
    Assert (Test-Path -LiteralPath (Join-Path $dest1 $IsoName)) '1 ISO placed in destination'
    Assert (@(Get-ChildItem -LiteralPath $dest1 -File).Count -eq 7) '1 six artifact files plus the manifest'
    Assert (@(Get-ChildItem -LiteralPath $dest1 -Directory).Count -eq 0) '1 staging directory removed'
    $manifestPath = Join-Path $dest1 'CI-ISO-MANIFEST.txt'
    $m = Get-Content -LiteralPath $manifestPath
    Assert ($m -contains "Run id: $RunId") '1 manifest has run id'
    Assert ($m -contains "Run URL: $RunUrl") '1 manifest has run URL'
    Assert ($m -contains "Repository: $Repo") '1 manifest has repository'
    Assert ($m -contains "Artifact: clawos-iso-$Sha") '1 manifest names the artifact'
    Assert ($m -contains "Source commit: $Sha") '1 manifest has Source commit'
    Assert ($m -contains "ISO: $IsoName") '1 manifest names the ISO'
    Assert ($m -contains "ISO SHA-256: $goodHash") '1 manifest has ISO SHA-256'
    Assert (@($m | Where-Object { $_ -match '^Downloaded at: 20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' }).Count -eq 1) '1 manifest has a UTC download time'
    Assert ($m -contains 'Verified: 1 SHA256SUMS entry with Get-FileHash') '1 manifest records the verification'
    $raw = [System.IO.File]::ReadAllBytes($manifestPath)
    Assert (-not ($raw[0] -eq 0xEF -and $raw[1] -eq 0xBB)) '1 manifest has no byte-order mark'
    Assert (-not ([System.IO.File]::ReadAllText($manifestPath).Contains("`r"))) '1 manifest uses LF line endings'
    Assert ($out -match "Source commit: $Sha") '1 console output prints the Source commit'
    Assert ($out -match "ISO SHA-256:\s+$goodHash") '1 console output prints the ISO SHA-256'
    Assert ($out -match 'Verified:\s+1 SHA256SUMS entry with Get-FileHash') '1 console output prints the verification'
    Assert (@($global:GetCiIsoMock.Calls | Where-Object { $_ -like "run view $RunId -R $Repo --json *" }).Count -eq 1) '1 run resolved with gh run view'
    Assert (@($global:GetCiIsoMock.Calls | Where-Object { $_ -like "run download $RunId -R $Repo -n clawos-iso-$Sha -D *" }).Count -eq 1) '1 gh run download called with -n clawos-iso-<sha>'

    # --- 2. populated destination is refused before any download ---------------
    $global:GetCiIsoMock.Calls = @()
    $before = Get-Content -LiteralPath $manifestPath -Raw
    Expect-Throw { & $Script -RunId $RunId -Destination $dest1 6>&1 3>&1 } 'Refusing to overwrite' '2 second run into the same directory refuses'
    Assert ((Get-DownloadCalls).Count -eq 0) '2 refusal happens before any download'
    Assert ((Get-Content -LiteralPath $manifestPath -Raw) -eq $before) '2 existing manifest untouched'
    Assert (@(Get-ChildItem -LiteralPath $dest1).Count -eq 7) '2 no staging left behind'

    # --- 3. corrupt SHA256SUMS -------------------------------------------------
    $fx3 = Join-Path $Root 'fixture-corrupt'
    New-Fixture -Dir $fx3 -CorruptSums | Out-Null
    $global:GetCiIsoMock.Fixture = $fx3
    $dest3 = Join-Path $Root 'dest3'
    Expect-Throw { & $Script -RunId $RunId -Destination $dest3 6>&1 3>&1 } 'SHA-256 mismatch' '3 hash mismatch is rejected'
    Assert ((Test-Path -LiteralPath $dest3) -and @(Get-ChildItem -LiteralPath $dest3).Count -eq 0) '3 nothing left in the destination, staging removed'

    # --- 4. Source commit differs from the run's head ---------------------------
    $fx4 = Join-Path $Root 'fixture-othersha'
    New-Fixture -Dir $fx4 -SourceCommit $OtherSha | Out-Null
    $global:GetCiIsoMock.Fixture = $fx4
    $dest4 = Join-Path $Root 'dest4'
    Expect-Throw { & $Script -RunId $RunId -Destination $dest4 6>&1 3>&1 } "Source commit $OtherSha but run $RunId built $Sha" '4 metadata/run commit disagreement is rejected'
    Assert (@(Get-ChildItem -LiteralPath $dest4).Count -eq 0) '4 nothing left in the destination'

    # --- 5. run not successful -------------------------------------------------
    $global:GetCiIsoMock.Fixture = $fxGood
    $global:GetCiIsoMock.Calls = @()
    $savedView = $global:GetCiIsoMock.RunView.Clone()
    $global:GetCiIsoMock.RunView.conclusion = 'failure'
    $dest5 = Join-Path $Root 'dest5'
    Expect-Throw { & $Script -RunId $RunId -Destination $dest5 6>&1 3>&1 } 'completed/failure' '5 failed run is rejected'
    Assert (-not (Test-Path -LiteralPath $dest5)) '5 destination not created for a rejected run'
    Assert ((Get-DownloadCalls).Count -eq 0) '5 no download attempted'
    $global:GetCiIsoMock.RunView = $savedView

    # --- 6. gh fails -------------------------------------------------------------
    $global:GetCiIsoMock.Fail = $true
    $dest6 = Join-Path $Root 'dest6'
    Expect-Throw { & $Script -RunId $RunId -Destination $dest6 6>&1 3>&1 } 'failed with exit code 1' '6 gh failure surfaces'
    $global:GetCiIsoMock.Fail = $false
    Assert (-not (Test-Path -LiteralPath $dest6)) '6 no destination created when gh fails before the download'
    # Fail only the download itself: the run resolves, then `run download` exits 1.
    # ForEach-Object sees each merged record as it is written, so the warning
    # from the script's finally block is kept although the script then throws.
    $global:GetCiIsoMock.Artifact = 'clawos-iso-somebody-else'
    $captured = New-Object System.Collections.ArrayList
    $message = ''
    try {
        & $Script -RunId $RunId -Destination $dest6 6>&1 3>&1 | ForEach-Object { [void]$captured.Add("$_") }
    } catch {
        $message = $_.Exception.Message
    }
    $global:GetCiIsoMock.Artifact = "clawos-iso-$Sha"
    Assert ($message -match 'run download .* failed with exit code 1') "6 failed download surfaces -> $message"
    Assert ((Test-Path -LiteralPath $dest6) -and @(Get-ChildItem -LiteralPath $dest6).Count -eq 0) '6 staging removed, destination empty after a failed download'
    Assert (@($captured | Where-Object { $_ -match 'Removed the incomplete download' }).Count -eq 1) '6 warning names the removed staging directory'

    # --- 7. "<hash> *<name>" checksum format -----------------------------------
    $fx7 = Join-Path $Root 'fixture-star'
    $starHash = New-Fixture -Dir $fx7 -Star
    $global:GetCiIsoMock.Fixture = $fx7
    $dest7 = Join-Path $Root 'dest7'
    & $Script -RunId $RunId -Destination $dest7 6>&1 | Out-Null
    Assert ((Get-Content -LiteralPath (Join-Path $dest7 'CI-ISO-MANIFEST.txt')) -contains "ISO SHA-256: $starHash") '7 star-form SHA256SUMS accepted'

    # --- 8. -Latest -------------------------------------------------------------
    $global:GetCiIsoMock.Fixture = $fxGood
    $global:GetCiIsoMock.Calls = @()
    $dest8 = Join-Path $Root 'dest8'
    & $Script -Latest -Destination $dest8 6>&1 | Out-Null
    Assert ((Get-Content -LiteralPath (Join-Path $dest8 'CI-ISO-MANIFEST.txt')) -contains "Run id: $RunId") '8 -Latest resolves the newest successful run'
    Assert (@($global:GetCiIsoMock.Calls | Where-Object { $_ -like "run list -R $Repo -w release.yml -b main -s success -L 1 --json *" }).Count -eq 1) '8 -Latest filters release.yml, main, success'
    $global:GetCiIsoMock.Calls = @()
    & $Script -Latest -Branch 'feature/x' -Repo 'someone/ClawOS' -Destination (Join-Path $Root 'dest8b') 6>&1 | Out-Null
    Assert (@($global:GetCiIsoMock.Calls | Where-Object { $_ -like 'run list -R someone/ClawOS -w release.yml -b feature/x -s success *' }).Count -eq 1) '8 -Branch and -Repo reach gh run list'
    Assert (@($global:GetCiIsoMock.Calls | Where-Object { $_ -like "run download $RunId -R someone/ClawOS -n *" }).Count -eq 1) '8 -Repo reaches gh run download'

    # --- 9. -Latest with no runs ------------------------------------------------
    $savedList = $global:GetCiIsoMock.RunList
    $global:GetCiIsoMock.RunList = @()
    Expect-Throw { & $Script -Latest -Branch nothing-here -Destination (Join-Path $Root 'dest9') 6>&1 3>&1 } "No successful release.yml run found on branch 'nothing-here'" '9 empty run list is an error'
    $global:GetCiIsoMock.RunList = $savedList

    # --- 10. relative destination with spaces -----------------------------------
    Push-Location $Root
    try {
        & $Script -RunId $RunId -Destination 'rel dest' 6>&1 | Out-Null
    } finally {
        Pop-Location
    }
    Assert (Test-Path -LiteralPath (Join-Path $Root 'rel dest\CI-ISO-MANIFEST.txt')) '10 relative destination resolves against the current directory'

    # --- 11. parameter validation -----------------------------------------------
    $global:GetCiIsoMock.Calls = @()
    $dest11 = Join-Path $Root 'dest11'
    Expect-Throw { & $Script -RunId 'abc' -Destination $dest11 } 'ValidatePattern|does not match' '11 non-numeric run id rejected'
    Expect-Throw { & $Script -RunId $RunId -Latest -Destination $dest11 } 'Parameter set cannot be resolved' '11 -RunId and -Latest are exclusive'
    Expect-Throw { & $Script -RunId $RunId -Destination $dest11 -Repo 'not a repo' } 'ValidatePattern|does not match' '11 malformed -Repo rejected'
    Expect-Throw { & $Script -Latest:$false -Destination $dest11 } 'Pass -RunId <id> or -Latest' '11 -Latest:$false without -RunId rejected'
    Assert ($global:GetCiIsoMock.Calls.Count -eq 0) '11 parameter errors happen before any gh call'
    Assert (-not (Test-Path -LiteralPath $dest11)) '11 parameter errors create no destination'

    # --- 12. BUILD-METADATA.txt without a Source commit -------------------------
    $fx12 = Join-Path $Root 'fixture-nosource'
    New-Fixture -Dir $fx12 -NoSourceCommit | Out-Null
    $global:GetCiIsoMock.Fixture = $fx12
    Expect-Throw { & $Script -RunId $RunId -Destination (Join-Path $Root 'dest12') 6>&1 3>&1 } "exactly one 'Source commit:' line; found 0" '12 missing Source commit rejected'

    # --- 13. SHA256SUMS lists an absent file ------------------------------------
    $fx13 = Join-Path $Root 'fixture-missing'
    New-Fixture -Dir $fx13 -MissingListed | Out-Null
    $global:GetCiIsoMock.Fixture = $fx13
    Expect-Throw { & $Script -RunId $RunId -Destination (Join-Path $Root 'dest13') 6>&1 3>&1 } "lists 'not-there.bin' but the artifact does not contain it" '13 SHA256SUMS entry without a file rejected'

    # --- 14. two ISOs -----------------------------------------------------------
    $fx14 = Join-Path $Root 'fixture-twoisos'
    New-Fixture -Dir $fx14 -SecondIso | Out-Null
    $global:GetCiIsoMock.Fixture = $fx14
    Expect-Throw { & $Script -RunId $RunId -Destination (Join-Path $Root 'dest14') 6>&1 3>&1 } 'Expected exactly one .iso' '14 artifact with two ISOs rejected'

    # --- 15. destination path is an existing file --------------------------------
    $file15 = Join-Path $Root 'dest15-file'
    [System.IO.File]::WriteAllText($file15, 'x')
    Expect-Throw { & $Script -RunId $RunId -Destination $file15 6>&1 3>&1 } 'is a file, not a directory' '15 file destination rejected'

    # --- 16. stale staging directory from an earlier attempt ---------------------
    $global:GetCiIsoMock.Fixture = $fxGood
    $global:GetCiIsoMock.Calls = @()
    $dest16 = Join-Path $Root 'dest16'
    $stale = Join-Path $dest16 ".get-ci-iso-$RunId.partial"
    New-Item -ItemType Directory -Path $stale | Out-Null
    [System.IO.File]::WriteAllText((Join-Path $stale 'part.bin'), 'half a download')
    Expect-Throw { & $Script -RunId $RunId -Destination $dest16 6>&1 3>&1 } 'exists from another attempt' '16 stale staging directory is an error'
    Assert (Test-Path -LiteralPath (Join-Path $stale 'part.bin')) '16 stale staging directory left for the operator'
    Assert ((Get-DownloadCalls).Count -eq 0) '16 no download attempted'

    # --- 17. artifact layout -----------------------------------------------------
    $global:GetCiIsoMock.Layout = 'nested'
    $dest17 = Join-Path $Root 'dest17'
    & $Script -RunId $RunId -Destination $dest17 6>&1 | Out-Null
    Assert (Test-Path -LiteralPath (Join-Path $dest17 $IsoName)) '17 files in a subdirectory of the download are found'
    Assert (@(Get-ChildItem -LiteralPath $dest17 -Directory).Count -eq 0) '17 no subdirectory copied into the destination'
    $global:GetCiIsoMock.Layout = 'nested-stray'
    $dest17b = Join-Path $Root 'dest17b'
    Expect-Throw { & $Script -RunId $RunId -Destination $dest17b 6>&1 3>&1 } 'files outside its metadata directory' '17 files beside the metadata directory are rejected'
    Assert (@(Get-ChildItem -LiteralPath $dest17b).Count -eq 0) '17 rejected layout leaves nothing behind'
    $global:GetCiIsoMock.Layout = 'flat'
} finally {
    Remove-Item -Path function:gh -ErrorAction SilentlyContinue
    Remove-Variable -Name GetCiIsoMock -Scope Global -ErrorAction SilentlyContinue
}

Write-Host ''
if ($script:Failures -eq 0) {
    Write-Host 'ALL CHECKS PASSED'
    if ($KeepFiles) {
        Write-Host "Kept $Root"
    } else {
        Remove-Item -LiteralPath $Root -Recurse -Force
    }
    exit 0
}
Write-Host "$($script:Failures) CHECK(S) FAILED; fixtures kept in $Root"
exit 1
