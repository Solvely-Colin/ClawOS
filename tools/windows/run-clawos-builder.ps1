$ErrorActionPreference = "Stop"


$disk = Join-Path $PSScriptRoot "clawos-builder-windows.qcow2"
$vars = Join-Path $PSScriptRoot "clawos-builder-vars.fd"
$buildDisk = Join-Path $PSScriptRoot "clawos-v01-build.qcow2"
$serialLog = Join-Path $PSScriptRoot "clawos-builder-serial.log"
$hostLog = Join-Path $PSScriptRoot "clawos-builder-host.log"
$qemu = Join-Path $env:ProgramFiles "qemu\qemu-system-x86_64.exe"
$qemuRoot = Split-Path $qemu -Parent
$firmware = Join-Path $qemuRoot "share\edk2-x86_64-code.fd"

Add-Type -TypeDefinition @'
using System.Runtime.InteropServices;
public static class ClawOSPrimaryDisplay {
    [DllImport("user32.dll")]
    public static extern int GetSystemMetrics(int index);
}
'@
$displayWidth = [ClawOSPrimaryDisplay]::GetSystemMetrics(0)
$displayHeight = [ClawOSPrimaryDisplay]::GetSystemMetrics(1)
if ($displayWidth -lt 1024 -or $displayWidth -gt 7680 -or
    $displayHeight -lt 600 -or $displayHeight -gt 4320) {
    throw "Unsupported primary display geometry: ${displayWidth}x${displayHeight}."
}

foreach ($required in @($qemu, $firmware, $vars, $disk, $buildDisk)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Missing required ClawOS VM file: $required"
    }
}

$existing = @(Get-CimInstance Win32_Process -Filter "Name='qemu-system-x86_64.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*clawos-builder-windows.qcow2*" })
if ($existing.Count -gt 0) {
    throw "A ClawOS QEMU process is already running (PID $($existing.ProcessId -join ','))."
}

Add-Content -LiteralPath $serialLog -Value "`r`n===== host launch $([DateTime]::UtcNow.ToString('o')) ====="
Add-Content -LiteralPath $hostLog -Value "`r`n===== scheduled launch $([DateTime]::UtcNow.ToString('o')) ====="
Add-Content -LiteralPath $hostLog -Value "Preferred guest display: ${displayWidth}x${displayHeight} (Windows primary display)"

& $qemu `
    -name "ClawOS Builder" `
    -machine "q35" `
    -accel "whpx" `
    -m "8192" `
    -smp "cores=4" `
    -usb `
    -drive "if=pflash,format=raw,readonly=on,file=$firmware" `
    -drive "if=pflash,format=raw,file=$vars" `
    -drive "file=$disk,if=virtio,format=qcow2" `
    -drive "file=$buildDisk,if=none,id=clawos-v01-build,format=qcow2" `
    -device "virtio-blk-pci,drive=clawos-v01-build,serial=CLAWOS-V01-BUILD,addr=0x10" `
    -device "virtio-vga,xres=$displayWidth,yres=$displayHeight" `
    -device "usb-tablet,id=clawos-pointer" `
    -display "gtk,zoom-to-fit=on,keep-aspect-ratio=on,full-screen=off,show-menubar=off,grab-on-hover=off,show-cursor=on,window-close=off" `
    -monitor "none" `
    -chardev "file,id=serial0,path=$serialLog,append=on" `
    -serial "chardev:serial0" `
    -qmp "tcp:127.0.0.1:4444,server=on,wait=off" `
    -nic "user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:2222-:22" 2>> $hostLog

exit $LASTEXITCODE
