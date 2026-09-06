# Working in ClawOS

Read README.md, CONTRIBUTING.md and docs/KNOWN-ISSUES.md before runtime changes.
Preserve unrelated working-tree changes. Subdirectory instructions apply only
to that component; prototype guidance is not the installed runtime contract.

Build Linux artifacts in Linux. Do not run OS installers or recovery commands
on an unrelated host. Use disposable VMs for dangerous tests. Routine changes
may proceed; destructive actions need explicit approval and checkpoints.
Never hard-stop QEMU during normal operation.

Do not commit or print credentials, VM/browser state or private transcripts.
Use supported OpenClaw credential management and retain independent recovery.
Implement and verify requested changes; audit/status requests do not authorize
unrelated implementation. Keep unit, live-runtime and fresh-install proof distinct.
