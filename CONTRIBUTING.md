# Contributing

Start with a focused issue and a small branch. Describe the behavior changed,
affected runtime components, verification, and remaining risks. Preserve
unrelated work and distinguish unit tests from fresh-install proof.

## Environment

- Build ISOs and run full preflight in a disposable Arch VM. Fast Python/Node
  checks run in CI without root or provider keys.
- Use your own provider credentials through OpenClaw setup. Never commit auth
  databases, browser profiles, tokens, keys, VM disks, firmware variables,
  checkpoints, credential screenshots or personal transcripts.
- Review privileged scripts before execution. Installer/recovery experiments
  belong on disposable disks with an independent recovery route.
- Windows scripts manage an already-provisioned development VM, not a complete
  Windows installation wizard.

## Before submitting

1. Run focused tests and `./m1/bin/preflight-iso` in Arch for OS integration.
2. Include the source revision and execution environment. Deployment evidence
   should include job ID, terminal receipt, checkpoint and file drift.
3. Verify UI changes visually and with keyboard navigation; follow Carapace
   and preserve focus/return behavior, not just colors.
4. Review the staged diff for generated or personal files. Secret-scan source
   and history before sharing a new baseline.

## Safety and boundaries

- Routine reversible work may proceed within the task. Ask before destructive
  actions, even when root access exists. Checkpoint before risky changes.
- Runtime rollback covers managed files, not root/home/boot or external services
  as a single transaction. Full Root is not an untrusted-agent sandbox.
- Never hard-stop QEMU in normal operation; use guest shutdown or ACPI. Forced
  recovery termination needs explicit approval.
- OpenClaw owns conversations, model selection and credentials. Do not create
  a second provider catalog or independent transcript store.
- Keep Omarchy wrappers, repositories, themes and runtime dependencies out of
  shipping paths. Retain historical notes and negative tests.
- Delivery uses an OpenClaw 2026.8.2 adapter. Dependency changes require adapter
  and end-to-end verification, not removal of its version guard.

Good first areas are listed in [known issues](docs/KNOWN-ISSUES.md): task routing,
startup state, window layout, fresh-install proof and failure UX. The separate
visual prototype must be ported and tested before it becomes runtime behavior.
