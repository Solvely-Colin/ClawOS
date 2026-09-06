# Windows development-VM lifecycle

These scripts manage an existing ClawOS QEMU disk through Scheduled Tasks.
Install QEMU and provision a disposable disk using the Linux build instructions.
Keep private machine files beside these scripts, never in Git:

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
