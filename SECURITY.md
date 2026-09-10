# Security policy

ClawOS is an experimental, Arch-based "agent OS": OpenClaw is the desktop, a root
broker (`clawosd`) exposes typed machine actions, and an installer writes an
encrypted or (with `--passwordless`) unencrypted system to a blank disk. It is a
development project. Read this file before running it on anything you care about.

## Supported versions

None. There are no supported releases and no backports. Only the head of `main`
is looked at. ISO images produced by `docs/RELEASING.md` are build evidence, not
supported versions.

## Reporting

Do not open a public issue for a security problem.

Report vulnerabilities through [GitHub private vulnerability reporting](https://github.com/Solvely-Colin/ClawOS/security/advisories/new). This route was enabled and verified on 2026-09-10; submitting requires GitHub sign-in. Do not include live credentials in an initial report.

Include the commit SHA, install mode (encrypted or passwordless), security level
(Full Root, Full Approvals, User Limited), and how to reproduce. Redact tokens and
keys from anything you send.

**There is no SLA.** This is a one-maintainer project. Reports are read when
there is time; there is no promised acknowledgement window, fix window, or
coordinated disclosure timeline. If you need one, do not report here.

## Threat model

The trusted parties are the machine owner and, in Full Root, the core agent
(`main`). Full Root means the owner has delegated unrestricted root to that agent;
a model that misbehaves in Full Root is a trusted party misbehaving, not a
vulnerability in ClawOS. The boundaries the code does try to hold are:

1. The installer never writes to a disk other than the eligible blank disk the
   user confirmed, and rechecks identity before the first format.
2. In approval modes, a privileged change requires the exact typed action plus a
   local Polkit decision; in Full Root, the four high-impact actions still do.
3. Mutating broker requests and approval tokens are limited to root, the
   configured owner account, and the configured restricted runtime in its
   Gateway/Node user unit. Requests carrying agent metadata also pass policy or
   an active task grant. This does not isolate malicious processes sharing a
   trusted account/unit or cryptographically authenticate their agent metadata.
4. Credentials must not be written to public logs or world-readable files.
   The LUKS key reaches `passwd` over stdin. OpenClaw gateway credentials are
   deliberately passed in owner-process environments; the owning UID and root
   can inspect them. Audit receipts omit approval tokens, but CLI commit/cancel
   arguments contain those tokens and are not secret from the same trusted UID.
5. No password or root login over SSH, in either install mode.

Not defended: a Full Root agent using root; physical or console access to a
passwordless machine; the npm registry and OpenClaw supply chain; the live ISO
console; a compromised model making the core agent do what the owner allowed it
to do.

## Scope

Welcome:

- Bypasses of the installer's disk-identity or eligibility checks (writing to a
  non-blank, mounted, boot-media, or different disk than confirmed).
- Broker authorization bypasses: unrelated UIDs performing mutations, taking
  another account's token, committing an approval-mode/high-impact action without
  Polkit, or using expired, used, unbound or wrong-boot tokens. The owner/root
  approval handoff is intentional. Grants must match their recorded agent/run.
- Credentials exposed to unrelated accounts, public logs or world-readable
  files. Owner-process credential environments and same-UID access are not a
  promised isolation boundary; see the explicit contract above.
- Anything that lets a process running as a different UID than the gateway/node
  unit become `gateway-attested`, or lets a non-core agent take core actions
  without a grant. Same-UID escapes inside that unit are the known, untested
  gap: reports are welcome, but isolation there is not a promised boundary.

Out of scope:

- Full Root doing root things. Unrestricted root is the feature.
- Physical access to, or console access on, a passwordless machine.
- Anything requiring you to already be `clawos` or root on a Full Root machine.
- Prompt injection that drives the core agent within its configured authority.

## By design, not a vulnerability

Each item is a current, deliberate limitation. The first list is what the code
does; the second is what we believe follows from it but have not observed or
tested.

### Observed in code

- Full Root installs `clawos ALL=(ALL:ALL) NOPASSWD: ALL`. The installer copies
  that file into `/etc/sudoers.d` on every install; the broker removes it when
  the level leaves `full-root` and reinstalls it when the level returns. The
  shipped default level is `full-root`. It is a trusted-agent mode, not
  containment.
- In Full Root only `recovery.rollback`, `power.schedule`, `role.switch` and
  `security.level.configure` go through Polkit; every other action executes on
  commit without a prompt.
- Public read-only broker methods remain available. Mutations and token-bearing
  pending lists check the authenticated D-Bus UID against OS-resolved configured
  accounts. Direct owner/root administration may omit agent context; Gateway/Node
  preparation may not. An unrelated UID cannot opt out by omitting `agentId`.
- `gateway-attested` checks the exact Gateway/Node unit component below the
  caller UID's user slice. The separate runtime account is accepted only in
  User Limited. Metadata is bound by the plugin's SDK factory/per-call hooks;
  it is still not cryptographic isolation from malicious code in the same unit.
- Tokens bind to requester UID and boot. The owner/root UI can review and act
  on restricted-runtime requests, with Polkit still required by mode/action.
  Runtime callers cannot take owner tokens. Commit rechecks current agent policy
  and grants; old unbound approvals must be prepared again after this upgrade.
- Onboarding writes the chosen level through `security.level.configure` and the
  Polkit gate, skipping the call when the level is unchanged. The default choice
  is `full-root`, which matches the shipped config, so the default path does not
  prompt.
- OpenClaw is pinned by version string only. `build-iso` installs
  `openclaw@$OPENCLAW_VERSION` from npm into the ISO tree and checks
  `openclaw --version`; `OPENCLAW_COMMIT` is recorded but never compared; the
  installer copies the ISO tree and rechecks the string; runtime
  `openclaw.update` installs from npm and checks `package.json`. No checksum,
  signature or lockfile.
- `tailscaled` is installed and enabled on every install. Nothing in this
  repository runs `tailscale up` or supplies an auth key.
  In an encrypted WHPX test on 2026-09-10, `tailscale status` reported NeedsLogin
  with no tailnet or assigned Tailscale IPs, while `ss -lntup` showed UDP 41641
  on IPv4 and IPv6 before any `tailscale up`. This is socket-level evidence,
  not proof of tailnet connectivity or security of the listener. The
  default-service decision remains tracked in #42.
- Live ISO: the profile is archiso `releng` plus an overlay, and the overlay does
  not override releng's root autologin on `tty1`. Root autologin on `ttyS0`
  happens only on KVM with the Q35 product string. The live graphical session
  runs as `clawos-live` on `tty2` and may `pkexec` the installer without
  authentication. Installed systems get serial root autologin only with
  `--vm-test`. The live image runs sshd on port 22 under the same key-only
  drop-in (`00-clawos.conf` sorts ahead of archiso's `10-archiso.conf`); the
  live root account has no password and root login is refused outright, so no
  account can log in over SSH until a key is installed for `clawos-live`.
- Passwordless mode: no LUKS, `root` and `clawos` passwords deleted,
  `/etc/clawos-passwordless-entry` written, and `clawos-lock` exits without
  locking when that root-owned 0644 file says `enabled`. Without the file it
  still refuses to lock an account with no password and shows a warning instead.
- Encrypted mode: one key file formats LUKS2 and becomes both the `root` and
  `clawos` account password. It must live at `/run/user/<uid>/clawos-install.key`.
- Runtime rollback (`clawos-deploy`) restores managed runtime files only.
  `recovery.rollback` renames `@` to `@failed-<time>` and recreates `@` from a
  read-only snapshot of `/`; `@home`, `@var_log`, `@pkg`, `@snapshots` and the ESP
  are separate and untouched, and a reboot is required.
- The OpenClaw plugin appends a `deploy-runtime` hint to the system context of
  the core agent in Full Root only, and only for sessions whose key matches
  `agent:<id>:<...>`. Its `before_tool_call` hook
  blocks only `exec` calls. It splits the command the way a shell would
  (newlines, `;`, `&&`, `||`, `|`, `&`, subshells, `$(...)`, backticks and
  unquoted heredoc bodies), skips leading `VAR=value` assignments, redirections,
  reserved words and `function NAME`, removes quotes and decodes backslash and
  `$'...'` escapes, strips a wrapper allowlist (`env`, `nice`, `nohup`, `time`,
  `timeout`, `exec`, `command`, `builtin`, `xargs`, `stdbuf`, `setsid`, `ionice`,
  `chrt`, `taskset`, `watch`) and blocks when the basename of a command word is
  `sudo`, `sudoedit`, `su`, `doas`, `pkexec`, `run0`, `pacman`, `systemctl`,
  `bootctl`, `mkinitcpio`, `cryptsetup`, `mount`, `umount`, `btrfs` or
  `clawosctl commit`, recursing into `sh`/`bash`/`zsh`/`dash`/`ksh`/`ash -c`
  strings, `eval`, `watch` and `find -exec`. A command word that still holds a
  brace, glob or variable expansion fails closed; the block is off entirely
  in Full Root for the core agent, and an `exec` without an agent id counts as
  core.
- The exec rail is a guidance rail, not a sandbox. Its tests state what passes
  it: script files (`bash install.sh`, `./install.sh`, `source x`,
  `curl ... | bash`, `echo ... | sh`), other interpreters (`python -c`,
  `perl -e`, `node -e`), command strings that are themselves command output
  (`sh -c "$(cat cmd)"`), aliases and shell functions defined outside the
  command, wrappers not in the allowlist (`chroot`, `nsenter`, `ssh localhost`,
  `make`, `tmux`), and any tool other than `exec`, including a file written with
  another tool and run later. See the `uncaught` table in
  `m2/openclaw-plugin/test/embodiment.test.js`.

- Caller-boundary regression tests include a real private D-Bus daemon with
  different OS UIDs and a fake machine runner. They do not constitute a complete
  system compromise test or prove isolation between agents sharing a runtime.
  The suite runs on every push and pull request in the `arch-preflight` job in
  `.github/workflows/ci.yml`.

### Constructed by reasoning, not observed

- Which identity satisfies the `auth_admin` prompt for commits. The repository
  ships the action with `auth_admin`, no Polkit rules for it, and creates
  `clawos` in `video,input,clawos-control`, not `wheel`. Whether the prompt
  resolves to root, an empty admin group, or something else depends on polkit
  defaults on the target and has not been observed. In passwordless mode the
  accounts are empty, so the installer expects the prompt to succeed without a
  secret; untested here.
- A process outside the gateway/node units should not be able to appear inside
  them in `/proc/<pid>/cgroup`; cgroup or systemd-scope tricks have not been
  tested.
- Attestation reads the caller's PID from the bus and then its cgroup from
  `/proc/<pid>/cgroup`; a PID reused between those two reads would be
  misattributed. The window is small and has not been measured or exploited.

## Tracking known limitations

Public tracking links do not change reportability or establish that a gap is fixed: [Polkit identity #44](https://github.com/Solvely-Colin/ClawOS/issues/44), [Tailscale #42](https://github.com/Solvely-Colin/ClawOS/issues/42), [live-console autologin #43](https://github.com/Solvely-Colin/ClawOS/issues/43), [OpenClaw integrity #29](https://github.com/Solvely-Colin/ClawOS/issues/29), [dependency locking #31](https://github.com/Solvely-Colin/ClawOS/issues/31), [deploy hint #38](https://github.com/Solvely-Colin/ClawOS/issues/38), [exec rail #41](https://github.com/Solvely-Colin/ClawOS/issues/41), [attestation #40](https://github.com/Solvely-Colin/ClawOS/issues/40), [D-Bus policy #39](https://github.com/Solvely-Colin/ClawOS/issues/39), [recovery #56](https://github.com/Solvely-Colin/ClawOS/issues/56), [passwordless warning #45](https://github.com/Solvely-Colin/ClawOS/issues/45), and [fresh-install policy/inference proof #33](https://github.com/Solvely-Colin/ClawOS/issues/33).

## How fixes are communicated

Fixes land as ordinary commits on `main`, with the boundary they change noted in
`docs/KNOWN-ISSUES.md`. There are no GitHub security advisories, CVEs, release
notes, or backports yet. If you want credit, say so in the report and you will be
named in the commit message.

Public security follow-up uses the [security label](https://github.com/Solvely-Colin/ClawOS/labels/security). New vulnerability reports must still use the private routes above.
