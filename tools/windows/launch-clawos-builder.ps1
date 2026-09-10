[CmdletBinding()]
param(
    [ValidateSet("Install", "Start", "Unlock", "Shutdown", "Restart", "Status", "Logs", "Checkpoint", "SSH")]
    [string]$Action = "Status",
    [string]$CheckpointName = (Get-Date -Format "yyyyMMdd-HHmmss"),
    [ValidateRange(1, 10000)]
    [int]$Tail = 100,
    [switch]$Follow,
    [switch]$NoRestart
)

$ErrorActionPreference = "Stop"
$TaskName = "ClawOS Builder VM"
$VmRoot = $PSScriptRoot
$Disk = Join-Path $VmRoot "clawos-builder-windows.qcow2"
$Vars = Join-Path $VmRoot "clawos-builder-vars.fd"
$SerialLog = Join-Path $VmRoot "clawos-builder-serial.log"
$Runner = Join-Path $VmRoot "run-clawos-builder.ps1"
$CheckpointRoot = Join-Path $VmRoot "checkpoints"
$UnlockSecretPath = Join-Path $VmRoot "clawos-builder-unlock.dpapi"
$QemuImg = Join-Path $env:ProgramFiles "qemu\qemu-img.exe"
$Ssh = Join-Path $env:WINDIR "System32\OpenSSH\ssh.exe"
$SshKeyCandidates = @(
    (Join-Path $env:USERPROFILE ".ssh\clawos_vm_ed25519"),
    (Join-Path $env:USERPROFILE ".ssh\clawos_codex")
)

function Get-ClawOSProcess {
    @(Get-CimInstance Win32_Process -Filter "Name='qemu-system-x86_64.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*clawos-builder-windows.qcow2*" })
}

function Test-ClawOSPort {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect("127.0.0.1", 2222, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(1000)) { return $false }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Test-ClawOSQmp {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect("127.0.0.1", 4444, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(1000)) { return $false }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Test-ClawOSSsh {
    try {
        $key = Get-ClawOSKey
        & $Ssh -i $key -p 2222 -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=3 -o StrictHostKeyChecking=accept-new clawos@127.0.0.1 true 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Get-ClawOSKey {
    $key = $SshKeyCandidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $key) {
        throw "No ClawOS SSH key found. Expected one of: $($SshKeyCandidates -join ', ')"
    }
    $key
}

function Get-ClawOSUnlockSecret {
    if (-not (Test-Path -LiteralPath $UnlockSecretPath -PathType Leaf)) {
        throw "The Windows-user-protected unlock credential is missing: $UnlockSecretPath"
    }
    $secure = Get-Content -LiteralPath $UnlockSecretPath -Raw | ConvertTo-SecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Unlock-ClawOS {
    if ((Get-ClawOSProcess).Count -eq 0) { throw "ClawOS is not running." }
    if (Test-ClawOSSsh) {
        Write-Host "ClawOS is already unlocked and authenticated SSH is ready."
        return
    }

    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    while ([DateTime]::UtcNow -lt $deadline -and -not (Test-ClawOSQmp)) {
        Start-Sleep -Seconds 1
    }
    if (-not (Test-ClawOSQmp)) { throw "QEMU management channel did not become ready." }

    $promptImage = Join-Path $env:TEMP ("clawos-unlock-check-" + [Guid]::NewGuid().ToString('N') + '.png')
    $client = [System.Net.Sockets.TcpClient]::new("127.0.0.1", 4444)
    try {
        $stream = $client.GetStream()
        $stream.ReadTimeout = 5000
        $reader = [System.IO.StreamReader]::new($stream)
        $writer = [System.IO.StreamWriter]::new($stream)
        $writer.NewLine = "`n"
        $writer.AutoFlush = $true
        [void]$reader.ReadLine()
        $writer.WriteLine('{"execute":"qmp_capabilities"}')
        [void]$reader.ReadLine()
        $promptVerified = $false
        $promptDeadline = [DateTime]::UtcNow.AddSeconds(90)
        while ([DateTime]::UtcNow -lt $promptDeadline) {
            $writer.WriteLine((@{execute='screendump';arguments=@{filename=$promptImage;format='png'}} | ConvertTo-Json -Compress))
            do { $reply = $reader.ReadLine() | ConvertFrom-Json } while ($reply.event)
            if ($reply.error) { throw 'Could not inspect the encrypted-root prompt.' }
            & "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -File (Join-Path $VmRoot 'Test-ClawOSUnlockScreen.ps1') -ImagePath $promptImage
            if ($LASTEXITCODE -eq 0) { $promptVerified = $true; break }
            if ($LASTEXITCODE -eq 2) { throw 'Unlock-screen verification unavailable; no credential was sent.' }
            Start-Sleep -Seconds 2
        }
        if (-not $promptVerified) { throw 'Encrypted-root prompt was not verified; no credential was sent.' }
        $secret = Get-ClawOSUnlockSecret
        if ($secret -notmatch '^[a-z0-9-]+$') { throw 'Stored unlock credential contains unsupported virtual-key characters.' }
        foreach ($character in $secret.ToCharArray()) {
            $key = if ($character -eq '-') { "minus" } else { [string]$character }
            $payload = @{ execute = "human-monitor-command"; arguments = @{ "command-line" = "sendkey $key 120" } } | ConvertTo-Json -Compress
            $writer.WriteLine($payload)
            [void]$reader.ReadLine()
            Start-Sleep -Milliseconds 160
        }
        Start-Sleep -Milliseconds 250
        $payload = @{ execute = "human-monitor-command"; arguments = @{ "command-line" = "sendkey ret 120" } } | ConvertTo-Json -Compress
        $writer.WriteLine($payload)
        [void]$reader.ReadLine()
        Write-Host "Submitted the Windows-user-protected encrypted-root credential through QEMU."
    } finally {
        $secret = $null
        Remove-Item -LiteralPath $promptImage -Force -ErrorAction SilentlyContinue
        if ($reader) { $reader.Dispose() }
        if ($writer) { $writer.Dispose() }
        $client.Dispose()
    }
}

function Invoke-ClawOSSsh {
    param(
        [Parameter(Mandatory)]
        [string]$RemoteCommand,
        [int]$ConnectTimeout = 8
    )
    $key = Get-ClawOSKey
    & $Ssh -i $key -p 2222 -o IdentitiesOnly=yes -o BatchMode=yes -o "ConnectTimeout=$ConnectTimeout" -o StrictHostKeyChecking=accept-new clawos@127.0.0.1 $RemoteCommand
    if ($LASTEXITCODE -ne 0) {
        throw "SSH command failed with exit code $LASTEXITCODE."
    }
}

function Send-AcpiPowerButton {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $client.Connect("127.0.0.1", 4444)
        $stream = $client.GetStream()
        $stream.ReadTimeout = 5000
        $reader = [System.IO.StreamReader]::new($stream)
        $writer = [System.IO.StreamWriter]::new($stream)
        $writer.NewLine = "`n"
        $writer.AutoFlush = $true
        [void]$reader.ReadLine()
        $writer.WriteLine('{"execute":"qmp_capabilities"}')
        [void]$reader.ReadLine()
        $writer.WriteLine('{"execute":"system_powerdown"}')
        [void]$reader.ReadLine()
    } finally {
        if ($reader) { $reader.Dispose() }
        if ($writer) { $writer.Dispose() }
        $client.Dispose()
    }
}

function Wait-ClawOSStopped {
    param([int]$TimeoutSeconds = 180)
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ((Get-ClawOSProcess).Count -eq 0) { return }
        Start-Sleep -Seconds 2
    }
    throw "ClawOS did not power off within $TimeoutSeconds seconds. QEMU was NOT hard-stopped; inspect serial logs and retry a graceful shutdown."
}

function Stop-ClawOSGracefully {
    if ((Get-ClawOSProcess).Count -eq 0) {
        Write-Host "ClawOS is already stopped."
        return
    }

    $requested = $false
    if (Test-ClawOSPort) {
        try {
            Write-Host "Requesting guest shutdown over SSH..."
            Invoke-ClawOSSsh -RemoteCommand "sudo -n systemctl poweroff"
            $requested = $true
        } catch {
            Write-Warning "SSH shutdown was unavailable: $($_.Exception.Message)"
        }
    }
    if (-not $requested) {
        Write-Host "Sending an ACPI power-button event through QEMU..."
        Send-AcpiPowerButton
    }
    Wait-ClawOSStopped
    Write-Host "ClawOS shut down cleanly; QEMU exited on its own."
}

function Start-ClawOS {
    $alreadyRunning = (Get-ClawOSProcess).Count -gt 0
    if (-not $alreadyRunning) {
        $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if (-not $task) {
            throw "Scheduled Task '$TaskName' is not installed. Run: .\launch-clawos-builder.ps1 Install"
        }
        Start-ScheduledTask -TaskName $TaskName
    }

    if (-not (Test-ClawOSSsh)) { Unlock-ClawOS }
    $deadline = [DateTime]::UtcNow.AddSeconds(180)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ((Get-ClawOSProcess).Count -gt 0 -and (Test-ClawOSSsh)) {
            Write-Host "ClawOS is running and authenticated SSH is ready at clawos@127.0.0.1:2222."
            return
        }
        Start-Sleep -Seconds 2
    }
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue
    throw "ClawOS did not become authenticated-SSH-ready within 180 seconds. It may be waiting at the encrypted-root Unlock ClawOS screen. QEMU remains running under Scheduled Task control. Scheduled Task result: $($taskInfo.LastTaskResult)."
}

function Install-ClawOSTask {
    foreach ($required in @($Disk, $Vars, $Runner)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing required file: $required" }
    }
    $powerShell = Join-Path $env:WINDIR "System32\WindowsPowerShell\v1.0\powershell.exe"
    $arguments = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$Runner`""
    $action = New-ScheduledTaskAction -Execute $powerShell -Argument $arguments -WorkingDirectory $VmRoot
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Persistent host-managed QEMU lifecycle for the ClawOS Arch development VM." -Force | Out-Null
    Write-Host "Installed Scheduled Task '$TaskName'. It starts on logon and can be started on demand."
}

function Show-ClawOSStatus {
    $processes = Get-ClawOSProcess
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    $taskInfo = if ($task) { Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction SilentlyContinue } else { $null }
    [pscustomobject]@{
        TaskInstalled = [bool]$task
        TaskState = if ($task) { $task.State } else { "NotInstalled" }
        QemuRunning = $processes.Count -gt 0
        QemuPid = ($processes.ProcessId -join ",")
        SshListening = Test-ClawOSPort
        SshAuthenticated = if ($processes.Count -gt 0) { Test-ClawOSSsh } else { $false }
        SshEndpoint = "clawos@127.0.0.1:2222"
        LastTaskRun = if ($taskInfo) { $taskInfo.LastRunTime } else { $null }
        LastTaskResult = if ($taskInfo) { $taskInfo.LastTaskResult } else { $null }
        Disk = $Disk
        SerialLog = $SerialLog
    } | Format-List
}

switch ($Action) {
    "Install" {
        Install-ClawOSTask
    }
    "Start" {
        Start-ClawOS
    }
    "Unlock" {
        Unlock-ClawOS
    }
    "Shutdown" {
        Stop-ClawOSGracefully
    }
    "Restart" {
        Stop-ClawOSGracefully
        Start-ClawOS
    }
    "Status" {
        Show-ClawOSStatus
    }
    "Logs" {
        if (-not (Test-Path -LiteralPath $SerialLog)) { throw "Serial log does not exist yet: $SerialLog" }
        Get-Content -LiteralPath $SerialLog -Tail $Tail -Wait:$Follow
    }
    "Checkpoint" {
        if ($CheckpointName -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$') {
            throw "CheckpointName must start with a letter or digit and contain only letters, digits, dot, underscore, or hyphen (64 characters maximum)."
        }
        if (-not (Test-Path -LiteralPath $QemuImg -PathType Leaf)) { throw "Missing qemu-img: $QemuImg" }
        $wasRunning = (Get-ClawOSProcess).Count -gt 0
        if ($wasRunning) { Stop-ClawOSGracefully }
        New-Item -ItemType Directory -Path $CheckpointRoot -Force | Out-Null
        $checkpointDir = Join-Path $CheckpointRoot $CheckpointName
        if (Test-Path -LiteralPath $checkpointDir) { throw "Checkpoint metadata directory already exists: $checkpointDir" }
        New-Item -ItemType Directory -Path $checkpointDir | Out-Null
        try {
            & $QemuImg snapshot -c $CheckpointName $Disk
            if ($LASTEXITCODE -ne 0) { throw "qemu-img snapshot failed with exit code $LASTEXITCODE" }
            Copy-Item -LiteralPath $Vars -Destination (Join-Path $checkpointDir "clawos-builder-vars.fd")
            if (Test-Path -LiteralPath $UnlockSecretPath -PathType Leaf) {
                $checkpointUnlock = Join-Path $checkpointDir "clawos-builder-unlock.dpapi"
                Copy-Item -LiteralPath $UnlockSecretPath -Destination $checkpointUnlock
                Set-Acl -LiteralPath $checkpointUnlock -AclObject (Get-Acl -LiteralPath $UnlockSecretPath)
            }
            @(
                "checkpoint=$CheckpointName"
                "created_utc=$([DateTime]::UtcNow.ToString('o'))"
                "disk=$Disk"
                "qemu_img_snapshot=internal"
                "uefi_vars=clawos-builder-vars.fd"
                "unlock_credential=clawos-builder-unlock.dpapi"
            ) | Set-Content -LiteralPath (Join-Path $checkpointDir "checkpoint.txt") -Encoding UTF8
            Write-Host "Created recovery checkpoint '$CheckpointName' and backed up UEFI variables."
        } catch {
            if (Test-Path -LiteralPath $checkpointDir) { Remove-Item -LiteralPath $checkpointDir -Recurse -Force }
            throw
        } finally {
            if ($wasRunning -and -not $NoRestart) { Start-ClawOS }
        }
    }
    "SSH" {
        if (-not (Test-ClawOSPort)) { throw "SSH is not listening on 127.0.0.1:2222. Start the VM first." }
        $key = Get-ClawOSKey
        & $Ssh -i $key -p 2222 -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new clawos@127.0.0.1
    }
}
