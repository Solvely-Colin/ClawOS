> **Historical record.** Describes design or state at that time, not current release acceptance. `artifacts/...` paths cited below were local, git-ignored build outputs and are not in this repository.

# Milestone 4 status

Last updated: 2026-09-02

## Implemented in source

- Remote Gateway enrollment and local display of the controller Control UI.
- Persistent upstream node-host installation and identity verification.
- Compatible controller/node `clawos-system` command registration using the
  supported OpenClaw plugin SDK node APIs.
- Typed local-or-node routing with ambiguity refusal and no raw command relay.
- Local recovery independence from the controller.
- Separate Standalone/Node config and secret-reference profiles.
- Transactional role switching with injected-failure restoration coverage.
- Exact-identity Full Root enrollment through OpenClaw's distinct device and
  node command-surface approvals. Less-permissive security modes remain manual.
- Real remote-controller reachability in the native status surface; configured
  but unreachable controllers are no longer reported online.
- A loopback-only QEMU VNC path for validating the actual ClawOS framebuffer on
  a private VPS or nested host without creating a parallel web desktop.

## Required final verification

- Build the fresh ISO containing this source.
- Install it on a disposable encrypted VM.
- Pair it to a separate compatible controller, observe reconnect after a
  controller outage, and complete one remotely routed typed system action.
- Prove automatic local enrollment from a clean Full Root install and explicit
  pending approval under Full User + Approvals.
- Switch Standalone -> Node -> Standalone on that same installation and verify
  that both the local Gateway identity and node identity remain usable.

M4 is feature-complete in source but is not marked complete until the
two-endpoint installed-VM verification above is retained as evidence.
