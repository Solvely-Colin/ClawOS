$ErrorActionPreference = "Stop"


$disk = Join-Path $PSScriptRoot "clawos-builder-windows.qcow2"
$vars = Join-Path $PSScriptRoot "clawos-builder-vars.fd"
$serialLog = Join-Path $PSScriptRoot "clawos-builder-serial.log"
$hostLog = Join-Path $PSScriptRoot "clawos-builder-host.log"
$qemu = Join-Path $env:ProgramFiles "qemu\qemu-system-x86_64.exe"
$qemuRoot = Split-Path $qemu -Parent
$firmware = Join-Path $qemuRoot "share\edk2-x86_64-code.fd"

foreach ($required in @($qemu, $firmware, $vars, $disk)) {
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
    -device "virtio-vga,xres=1440,yres=900" `
    -device "usb-tablet,id=clawos-pointer" `
    -display "sdl,window-close=off" `
    -monitor "none" `
    -chardev "file,id=serial0,path=$serialLog,append=on" `
    -serial "chardev:serial0" `
    -qmp "tcp:127.0.0.1:4444,server=on,wait=off" `
    -nic "user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:2222-:22" 2>> $hostLog

exit $LASTEXITCODE
