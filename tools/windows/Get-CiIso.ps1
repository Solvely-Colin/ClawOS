<#
.SYNOPSIS
Download a CI-built ClawOS ISO, verify it and record which run built it.

.DESCRIPTION
Takes a run id of the "Experimental ISO build" workflow (.github/workflows/
release.yml), or -Latest for the newest successful run on a branch, and runs
`gh run download <id> -n clawos-iso-<sha>` into a staging directory under
-Destination. Every SHA256SUMS entry is checked with Get-FileHash, the Source
commit is read from BUILD-METADATA.txt and compared with the run's head
commit, and only then are the files moved into -Destination together with
CI-ISO-MANIFEST.txt (run id, source commit, ISO SHA-256, download time).
Nothing in -Destination is overwritten; an existing file of the same name is
an error. A failed download or verification leaves no files behind.

Windows PowerShell 5.1 compatible. Needs the GitHub CLI (gh) on PATH and
logged in with read access to the repository's Actions artifacts. It does
not start a VM; point -Destination at the directory your WHPX harness reads
ISOs from and keep the manifest beside the image.

.PARAMETER RunId
Numeric id of a completed, successful release.yml run.

.PARAMETER Latest
Use the newest successful release.yml run on -Branch (default main).

.PARAMETER Destination
Directory that receives the ISO, the build metadata files and the manifest.
Created when missing.

.PARAMETER Repo
GitHub repository in OWNER/REPO form. Default Solvely-Colin/ClawOS.

.PARAMETER Branch
Branch filter for -Latest. Default main.

.EXAMPLE
.\Get-CiIso.ps1 -RunId 34270708295 -Destination C:\ClawOS\iso\run-34270708295

.EXAMPLE
.\Get-CiIso.ps1 -Latest -Destination C:\ClawOS\iso\latest-main
#>
[CmdletBinding(DefaultParameterSetName = 'RunId')]
param(
    [Parameter(ParameterSetName = 'RunId', Mandatory = $true, Position = 0)]
    [ValidatePattern('^[0-9]+$')]
    [string]$RunId,

    [Parameter(ParameterSetName = 'Latest', Mandatory = $true)]
    [switch]$Latest,

    [Parameter(Mandatory = $true)]
    [string]$Destination,

    [ValidatePattern('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')]
    [string]$Repo = 'Solvely-Colin/ClawOS',

    [Parameter(ParameterSetName = 'Latest')]
    [string]$Branch = 'main'
)

$ErrorActionPreference = 'Stop'
$WorkflowFile = 'release.yml'
$ManifestName = 'CI-ISO-MANIFEST.txt'
# Fixed names release.yml's build helper writes next to the ISO.
$KnownArtifactNames = @('SHA256SUMS', 'BUILD-METADATA.txt', 'BUILD-PACKAGES.txt', 'BUILD-CONTAINER.txt')

function Invoke-Gh {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    # gh's own messages stay on stderr for the operator; only stdout is captured.
    $output = & gh @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "gh $($Arguments -join ' ') failed with exit code $LASTEXITCODE."
    }
    $output
}

function ConvertFrom-GhJson {
    param([AllowNull()][object[]]$Output)
    $text = (@($Output) -join "`n").Trim()
    if ($text -eq '') { throw 'gh returned no JSON output.' }
    $text | ConvertFrom-Json
}

function Resolve-CiRun {
    if ($Latest) {
        $json = Invoke-Gh @('run', 'list', '-R', $Repo, '-w', $WorkflowFile, '-b', $Branch,
            '-s', 'success', '-L', '1', '--json', 'databaseId,headSha,url')
        # ForEach-Object unrolls the JSON array; Windows PowerShell otherwise
        # hands an empty array over as a single object.
        $runs = @(ConvertFrom-GhJson $json | ForEach-Object { $_ } | Where-Object { $null -ne $_ })
        if ($runs.Count -eq 0) {
            throw "No successful $WorkflowFile run found on branch '$Branch' of $Repo."
        }
        $run = $runs[0]
    } else {
        $json = Invoke-Gh @('run', 'view', $RunId, '-R', $Repo,
            '--json', 'databaseId,headSha,url,status,conclusion')
        $run = ConvertFrom-GhJson $json
        if ($null -eq $run) { throw "gh run view $RunId returned no run." }
        if ($run.status -ne 'completed' -or $run.conclusion -ne 'success') {
            throw "Run $RunId is $($run.status)/$($run.conclusion); only completed, successful runs carry a verified artifact."
        }
    }
    if (-not $run.databaseId -or -not $run.headSha) {
        throw 'gh returned a run without an id or head commit.'
    }
    $run
}

function Get-SourceCommit {
    param([Parameter(Mandatory = $true)][string]$MetadataPath)
    $lines = @(Get-Content -LiteralPath $MetadataPath | Where-Object { $_ -match '^Source commit:' })
    if ($lines.Count -ne 1) {
        throw "BUILD-METADATA.txt must carry exactly one 'Source commit:' line; found $($lines.Count)."
    }
    if ($lines[0] -notmatch '^Source commit:\s*(?<sha>[0-9a-f]{40})\s*$') {
        throw "Unrecognized Source commit line in BUILD-METADATA.txt: '$($lines[0])'"
    }
    $Matches['sha']
}

function Test-ArtifactChecksums {
    # Returns one object per SHA256SUMS entry after Get-FileHash agreed with it.
    param([Parameter(Mandatory = $true)][string]$Root)
    $sumsPath = Join-Path $Root 'SHA256SUMS'
    if (-not (Test-Path -LiteralPath $sumsPath -PathType Leaf)) {
        throw 'SHA256SUMS is missing from the artifact.'
    }
    $entries = @()
    foreach ($line in @(Get-Content -LiteralPath $sumsPath)) {
        if ($line.Trim() -eq '') { continue }
        # sha256sum writes "<hash>  <name>"; some ports write "<hash> *<name>".
        if ($line -notmatch '^(?<hash>[0-9a-fA-F]{64})\s+\*?(?<name>\S.*)$') {
            throw "Unrecognized SHA256SUMS line: '$line'"
        }
        $expected = $Matches['hash'].ToLowerInvariant()
        $name = $Matches['name'].Trim()
        if ($name -match '[\\/]') {
            throw "SHA256SUMS names a path outside the artifact directory: '$name'"
        }
        $file = Join-Path $Root $name
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "SHA256SUMS lists '$name' but the artifact does not contain it."
        }
        $actual = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) {
            throw "SHA-256 mismatch for '$name': SHA256SUMS says $expected, the file hashes to $actual."
        }
        $entries += [pscustomobject]@{ Name = $name; Hash = $actual }
    }
    if ($entries.Count -eq 0) { throw 'SHA256SUMS has no entries.' }
    $entries
}

if (-not $Latest -and -not $RunId) {
    throw '-Latest:$false selects no run. Pass -RunId <id> or -Latest.'
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) is not on PATH. Install it and run 'gh auth login' with read access to $Repo."
}

if ([System.IO.Path]::IsPathRooted($Destination)) {
    $destinationPath = $Destination
} else {
    $destinationPath = Join-Path (Get-Location).ProviderPath $Destination
}
$destinationPath = [System.IO.Path]::GetFullPath($destinationPath)
if (Test-Path -LiteralPath $destinationPath -PathType Leaf) {
    throw "Destination '$destinationPath' is a file, not a directory."
}

$run = Resolve-CiRun
$runIdText = [string]$run.databaseId
$headSha = [string]$run.headSha
if ($headSha -notmatch '^[0-9a-f]{40}$') {
    throw "Run $runIdText reports an unexpected head commit '$headSha'."
}
$artifactName = "clawos-iso-$headSha"
$staging = Join-Path $destinationPath ".get-ci-iso-$runIdText.partial"
$manifestPath = Join-Path $destinationPath $ManifestName

# Fail before spending the download on a directory that already holds an ISO.
if (Test-Path -LiteralPath $destinationPath) {
    $present = @(Get-ChildItem -LiteralPath $destinationPath -File |
        Where-Object { $KnownArtifactNames -contains $_.Name -or $_.Name -eq $ManifestName -or
            $_.Extension -eq '.iso' -or $_.Extension -eq '.sha256' })
    if ($present.Count -gt 0) {
        throw "Refusing to overwrite in ${destinationPath}: $(($present | ForEach-Object { $_.Name }) -join ', '). Use an empty directory per ISO."
    }
} else {
    New-Item -ItemType Directory -Path $destinationPath | Out-Null
}
if (Test-Path -LiteralPath $staging) {
    throw "Staging directory '$staging' exists from another attempt. Make sure no download is running, then remove it."
}

Write-Host "Run $runIdText of $WorkflowFile at $headSha ($($run.url))"
Write-Host "Downloading artifact $artifactName from $Repo ..."

$completed = $false
$moved = 0
New-Item -ItemType Directory -Path $staging | Out-Null
try {
    Invoke-Gh @('run', 'download', $runIdText, '-R', $Repo, '-n', $artifactName, '-D', $staging) | Out-Null
    $downloadedAt = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')

    $metadata = @(Get-ChildItem -LiteralPath $staging -Recurse -File -Filter 'BUILD-METADATA.txt')
    if ($metadata.Count -ne 1) {
        throw "Expected exactly one BUILD-METADATA.txt in artifact $artifactName; found $($metadata.Count)."
    }
    $artifactRoot = $metadata[0].DirectoryName
    $staged = @(Get-ChildItem -LiteralPath $artifactRoot -File)
    $everything = @(Get-ChildItem -LiteralPath $staging -Recurse -File)
    if ($everything.Count -ne $staged.Count) {
        throw "Artifact $artifactName contains files outside its metadata directory; refusing to guess the layout."
    }

    $entries = @(Test-ArtifactChecksums -Root $artifactRoot)
    $isos = @($staged | Where-Object { $_.Extension -eq '.iso' })
    if ($isos.Count -ne 1) {
        throw "Expected exactly one .iso in artifact $artifactName; found $($isos.Count)."
    }
    $iso = $isos[0]
    $isoEntry = @($entries | Where-Object { $_.Name -eq $iso.Name })
    if ($isoEntry.Count -ne 1) {
        throw "SHA256SUMS does not cover '$($iso.Name)'."
    }
    $isoHash = $isoEntry[0].Hash

    $sourceCommit = Get-SourceCommit -MetadataPath $metadata[0].FullName
    if ($sourceCommit -ne $headSha) {
        throw "BUILD-METADATA.txt says Source commit $sourceCommit but run $runIdText built $headSha."
    }

    $entryNoun = 'entries'
    if ($entries.Count -eq 1) { $entryNoun = 'entry' }
    $verified = "$($entries.Count) SHA256SUMS $entryNoun with Get-FileHash"
    $manifest = @(
        "Run id: $runIdText",
        "Run URL: $($run.url)",
        "Repository: $Repo",
        "Artifact: $artifactName",
        "Source commit: $sourceCommit",
        "ISO: $($iso.Name)",
        "ISO SHA-256: $isoHash",
        "Downloaded at: $downloadedAt",
        "Verified: $verified"
    )
    $stagedManifest = Join-Path $artifactRoot $ManifestName
    if (Test-Path -LiteralPath $stagedManifest) {
        throw "Artifact $artifactName already contains $ManifestName; refusing to replace it."
    }
    # LF and no byte-order mark, like the Linux-written files beside it.
    [System.IO.File]::WriteAllText($stagedManifest, (($manifest -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding($false)))

    $toMove = @(Get-ChildItem -LiteralPath $artifactRoot -File)
    $collisions = @($toMove | Where-Object { Test-Path -LiteralPath (Join-Path $destinationPath $_.Name) })
    if ($collisions.Count -gt 0) {
        throw "Refusing to overwrite in ${destinationPath}: $(($collisions | ForEach-Object { $_.Name }) -join ', ')"
    }
    foreach ($file in $toMove) {
        Move-Item -LiteralPath $file.FullName -Destination (Join-Path $destinationPath $file.Name)
        $moved++
    }
    $completed = $true
} finally {
    if (Test-Path -LiteralPath $staging) {
        Remove-Item -LiteralPath $staging -Recurse -Force
        if (-not $completed -and $moved -eq 0) {
            Write-Warning "Removed the incomplete download at $staging; nothing was placed in $destinationPath."
        } elseif (-not $completed) {
            Write-Warning "Removed $staging after a partial move; $moved file(s) already reached $destinationPath. Clear that directory before retrying."
        }
    }
}

Write-Host ''
Write-Host "Run id:        $runIdText"
Write-Host "Source commit: $sourceCommit"
Write-Host "ISO:           $(Join-Path $destinationPath $iso.Name)"
Write-Host "ISO SHA-256:   $isoHash"
Write-Host "Verified:      $verified"
Write-Host "Manifest:      $manifestPath"
