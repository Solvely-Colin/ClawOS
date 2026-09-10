# Live ClawOS development

The core agent can deploy ClawOS runtime changes from inside the installed OS.
The developer checkout remains the editable source; a hash-versioned runtime
payload records the source commit, dirty state, file hashes and modes.

## Daily loop

From `/home/clawos/Work/ClawOS` (or the current ClawOS checkout):

```bash
./image/bin/deploy-runtime plan
./image/bin/deploy-runtime apply --session-key agent:main:YOUR_CURRENT_SESSION
sudo /usr/lib/clawos/clawos-deploy status JOB_ID
sudo /usr/lib/clawos/clawos-deploy status
sudo /usr/lib/clawos/clawos-deploy check
```

Plan and apply run the source preflight. Apply returns immediately after
dispatching an independent `clawos-deploy-<job>` system service. A root-owned
copy of the worker runs outside the desktop and Gateway service groups, so
restarting those services does not cancel deployment. Closing the initiating
terminal or SSH connection does not cancel the worker.

Gateway restart may drain an active agent turn for several minutes. The updater
allows 420 seconds for the pinned service's 330-second stop grace plus startup;
it must not treat the old 30-second command timeout as a failed update while a
systemd restart remains queued. OpenClaw provides restricted restart recovery.
Pass the actual current session key to apply to bind automatic completion
delivery before dispatch. The plugin supplies that key in the current turn's
machine context. A manual apply without this option is deliberately unbound.

The independent `clawos-deploy-delivery.timer` retries terminal receipt delivery
every 15 seconds. It never runs an agent or repeats apply. A root-private binding
records both the canonical session key and exact session ID; a replaced,
deleted, or archived conversation fails closed rather than receiving a result
for its predecessor. Work and decisions shows bound jobs until delivery.

The version-pinned OpenClaw adapter uses its transactional transcript append
with a stable job/outcome idempotency key. A lost acknowledgement can be retried
without a second transcript entry. Its supported version is 2026.8.2; future
OpenClaw upgrades must update and reverify this adapter, not bypass the guard.
The system notice is labelled ClawOS update and reports the verified result
without invoking the model or sending to an external channel.

Read the receipt until `complete`, `rolled-back`, `failed`, or
`recovery-required`. Never translate a successful dispatch into successful
installation. `rolled-back` means the candidate failed and previous files and
runtime health were restored. `recovery-required` means manual recovery must
be inspected; do not repeat an interrupted job blindly.

Operators can poll with the status command. Agents in restricted restart
recovery must instead use the read tool on
`/var/lib/clawos/deploy-receipts/JOB_ID.json`. This root-written, mode-0644
projection exposes job state, content version, checkpoint, timestamps and
verification flags, not raw errors, commands, prompts, backups or credentials.
If the outcome is still pending or unavailable, end the response honestly;
do not loop looking for privileged tools or repeat apply. A later requested
follow-up can read the terminal receipt in the same conversation.

Existing receipts can be republished using the root-only command
`sudo /usr/lib/clawos/clawos-deploy publish-receipts`.

`status` reports the installed content version and drift from its managed
manifest. No-op applies return `already-current` and avoid a service restart.
`check` runs the live broker, plugin, Gateway, and desktop health checks on demand.

## Deployment scope

Includes ClawOS scripts/modules, native and web UI assets, the bundled ClawOS
plugin, broker implementation, and the shell/broker service definitions.
Excludes OpenClaw account/provider config and state, machine preferences,
security-policy/sudoers files, Arch packages, kernels, initramfs, and boot files.
This is a trusted local development operation requiring root, not a signed
production release channel or a way around approval-gated machine policy.

Newly staged payloads live under `artifacts/runtime/<content-hash>` in the
checkout. Before applying, the updater copies and verifies the payload into
its private `/var/lib/clawos/deploy/jobs/<job>` directory. It refuses concurrent
deployments, unsafe target paths, symlink destinations, and corrupt payloads.
Only previously managed files may be retired; local modifications to a retiring
file prevent its deletion.

Before writes, the worker creates a read-only Btrfs root snapshot and a
file-level backup with permissions and ownership. Service reloads are limited
to the affected broker/Gateway plus the graphical session. Health checks cover
file parity, broker access, CLI startup, local Gateway HTTP health, loaded
ClawOS plugin, Sway Agent-window identity, and the native panel. Model-provider
requests and visual correctness are separate acceptance checks.

## Rollback and interrupted work

```bash
sudo /usr/lib/clawos/clawos-deploy rollback JOB_ID
sudo /usr/lib/clawos/clawos-deploy status JOB_ID
sudo journalctl -u clawos-deploy-JOB_ID
```

Rollback also runs independently. It restores changed/removed files, removes
newly added files, reloads services, validates the restored runtime, and restores
the previous installed manifest. It refuses to roll an older deployment over
a newer installed version. A queued job that never made a completed backup
cannot be rolled back through this command; inspect its service and receipt
first. An interrupted apply with a completed backup can be recovered with the
same explicit rollback command once its worker is no longer running.

Recovery freezes the invoked updater into a separate `recovery-worker.py` and
records its hash and start time in the receipt, preserving the original worker.
This permits a reviewed updater repair to recover a job created by a defective
older worker. File backups and the previous manifest still define the rollback
scope; the recovery worker does not expand it.

Snapshots, job backups, and staged versions are retained intentionally. This
slice does not automatically prune recovery material, resume interrupted work
after reboot, or atomically replace the entire root filesystem. It provides
file rollback for the declared runtime scope, not kernel or user-data rollback.

## Approval and work review contract

Full Root keeps routine typed changes automatic. The broker requires native
Polkit authorization for recovery rollback, scheduled power actions, role
switches, and security-level changes, and recomputes that requirement at commit.
The agent must not bypass a pending or denied approval using privileged exec.
This is the supported workflow, not containment of an untrusted root agent:
the owner's explicitly enabled passwordless root access still exists.

Waybar's `Review N` action and Work and decisions use the same work projection.
They share a private five-second snapshot to avoid duplicate CLI polling. The
panel refreshes asynchronously and preserves unchanged cards.
Failures are considered across the complete returned task list, not just the
ten recent cards. Opening the panel does not acknowledge them. Mark reviewed
acknowledges only the selected task or notice; new notices have distinct IDs.
Unavailable sources appear as review items rather than pretending the queue
is empty. A generic lifecycle notice is a fallback when no concrete item is
waiting, so the same event is not counted twice.

## Conversation attachment

The shell assigns `clawos-agent-canvas` to its Agent window using Chromium's
known bootstrap app identity. `clawos-agent-window` resolves that mark or the
known app identity and rejects ambiguity. Conversation titles are display
content and never determine identity. Browser can open the existing conversation
as a side panel; closing it returns focus to the original Browser container.

Regression tests cover title changes, unrelated title lookalikes, ambiguous
windows, payload tampering, forbidden targets, missing executable modes,
snapshot failure, success, explicit rollback, and automatic recovery of added,
modified and removed files after failed health checks.
