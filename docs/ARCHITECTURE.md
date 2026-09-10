# ClawOS component boundaries

ClawOS integrates an Arch-based machine with upstream OpenClaw. OpenClaw owns
models, credentials, conversations and agent execution. ClawOS owns the OS
image, desktop surfaces, typed machine integration and recovery tooling.
This is experimental source; [known issues](KNOWN-ISSUES.md) and the
[evidence ledger](EVIDENCE.md) distinguish implementation from verified behavior.

| Component | Source | Responsibility |
| --- | --- | --- |
| Image assembly | `image/bin/materialize-profile`, `image/bin/build-iso` | Combine the ArchISO overlay, plugin and broker into a Linux-built image |
| Installed desktop and setup | `image/profile-overlay/airootfs` | Sway session, panel, installer, onboarding, application registry and supporting surfaces |
| OpenClaw integration | `integrations/openclaw` | Typed tools and minimal activity projection; no parallel conversation store |
| System broker | `services/clawosd/src`, `services/clawosd/dbus`, `services/clawosd/polkit` | Machine actions, approval boundaries and receipts; see SECURITY.md |
| Role integration | `clawos-role` in the overlay; `tests/integration/roles` | Standalone/remote-node switching and fixture-based regression checks |
| Host lifecycle | `tools/windows` | Windows-managed QEMU, SSH/ACPI shutdown and checkpoints |

Terminal, browser and build windows are inspection surfaces around the agent
workspace, not separate agents. The application registry and surface broker
connect human controls and typed tools. Correct association with each owning
task remains an explicit roadmap item; existing single-main behavior is not
proof of multi-task isolation.

The ISO materializer and runtime deployer each map source into installed
destinations. A source-directory migration must update both and verify payload
equivalence. Installed paths should not change merely to remove milestone names.
See [the contributor map](CONTRIBUTOR-MAP.md) and
[live development](SELF-DEVELOPMENT.md).

`experiments/host-session` is a historical executable fixture still checked by preflight.
`shell-prototype` is a frozen browser prototype with regression CI, not the
installed UI. Neither should be deleted while its checks still depend on it.
Private operator notes and old milestone diaries are deliberately not public
project documentation. [Document ownership](DOCUMENTATION.md) explains what belongs here.
