# Milestone 3 status

Last updated: 2026-09-01

## Active exit criterion

In default Full Root mode, an agent can complete a real typed OS change without
being blocked on a local approval. The broker records the exact result and a
read-only recovery point. Approval-gated and isolated modes remain selectable.

## Implemented in source

- Root-owned `clawosd` system D-Bus service and versioned introspection schema.
- Strict `package.install`, `openclaw.update`, `service.manage`,
  `system.time.configure`, `power.schedule`, `role.switch`,
  `security.level.configure`, `task.grant.create`, and `recovery.rollback`
  schemas.
- Coherent read-only machine inspection reports identity, kernel, boot,
  timezone, shell time format, configured service states, policy, uptime, and
  pending work without exposing credentials.
- Root-owned service allowlist with typed start, stop, and restart operations,
  resulting-state verification, and previous-state recovery metadata.
- Completed and failed operations remain addressable by UUID as durable,
  token-free action receipts for interruption/restart reconciliation.
- NetworkManager/device state and boot identity in typed machine inspection.
- Asynchronous reboot/poweroff receipts reconciled against the next boot;
  interrupted restarts are reported as uncertain rather than inferred from an
  active service.
- Root-owned target allowlist; no general package or command input.
- Two-minute, normalized, single-use approval tokens.
- Full Root auto-commit plus local Polkit authorization in approval-gated mode.
- Authoritative D-Bus peer UID/PID and explicitly self-reported/unavailable
  agent attribution.
- Read-only pre-change Btrfs snapshot, failed-change receipt, and staged
  next-boot rollback.
- Append-only root-owned JSONL audit records without bearer tokens.
- Native Carapace-aligned approval surface with exact effects and recovery.
- One native ClawOS Center now unifies those machine approvals with upstream
  OpenClaw approvals, active durable tasks, failed work, and recent terminal
  results. It resolves through the owning API, confirms cancellation, stores
  only a private bounded "seen" projection, and leaves OpenClaw as task source
  of truth.
- The first OS-native settings path: the core agent can set an installed IANA
  timezone and the ClawOS 12/24-hour shell clock through `system.time.configure`,
  with exact validation, Full Root auto-commit, live verification, audit, and
  previous-state recovery metadata.
- Full Root permits direct privileged execution; other levels block raw bypass
  paths and route privileged work through the typed broker.
- Full Root raw execution is projected only to the configured core `main`
  agent. Secondary agents remain behind broker policy even on a Full Root
  machine.
- A real separate `claw` runtime UID for User Limited, a `clawos-control`
  surface group, and `/srv/clawos/shared` as the explicit human/agent share.
- Authenticated machine security-level transitions migrate the OpenClaw
  runtime, add/remove the exact Full Root sudoers policy, and restore the prior
  runtime if activation fails.
- Gateway-cgroup-attested agent/run identity, rejection of spoofed agent
  metadata, root-owned per-agent action policy, and boot-bound expiring task
  grants with a narrow grantable-action set.
- Transactional Standalone/Node role operations through the root broker.
- Exact upstream OpenClaw 2026.8.2 update, upstream repair/plugin convergence,
  system-scope Gateway restart, and post-restart active-state verification.
- Automatic Agent-surface refresh after a core update so OpenClaw's strict
  Control UI build check never leaves the desktop on a stale protocol bundle.
- Narrow migration of the retired `ollama-cloud/kimi-k2.5:cloud` onboarding
  default to OpenClaw's supported `ollama-cloud/minimax-m2.7` default.

## Required verification

- [x] Pass unit, plugin, static profile, D-Bus schema, and policy checks.
- [x] Build a fresh ISO and pass the M2 regression gates.
- [x] In a disposable installed VM, prepare an allowlisted package action,
  render its native approval surface, commit it through `clawosd`, and verify
  the installed package, read-only Btrfs snapshot, token-free audit event, and
  single-use authorization.
- [x] In the installed VM, complete `openclaw.update` in Full Root with no
  approval prompt; verify 2026.8.2, a loaded `clawos-system` plugin, active
  Gateway, read-only Btrfs snapshot, and token-free completed audit receipt.
- [x] An Ollama Cloud `minimax-m2.7` agent used three consecutive
  `clawos_system` calls with zero failures to inspect the live machine, restart
  allowlisted `sshd.service`, verify it remained active, and retrieve the
  completed durable receipt by action ID.
- Build the current ISO, inject an executor change, and prove a separately
  approved rollback boots the prior root while retaining the failed root.

The successful clean-room path is retained in
`artifacts/m1/m2-e2e.NwKOfe/`. It was produced from ISO SHA-256
`9a2a14e498c225ab76f7096c1ed06fd51cbf7bf10a9cdbf9bbc8794b43fb70da`.

M3 remains active until the current source passes the fresh installed-VM
rollback/reboot proof. The broader typed service, power, role, security,
attribution, policy, and task-grant families now pass their source gates.
