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

- Once the repository is public: use GitHub private vulnerability reporting
  (Security tab, "Report a vulnerability").
- Until then: email `[OWNER EMAIL - fill in before publishing]`.

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
3. A non-core agent can only take the actions its policy or an active task grant
   names, and only with gateway attribution.
4. Secrets stay out of logs, arguments and environment: audit records drop
   tokens; the LUKS key reaches `passwd` over stdin.
5. No password or root login over SSH, in either install mode.

Not defended: a Full Root agent using root; physical or console access to a
passwordless machine; the npm registry and OpenClaw supply chain; the live ISO
console; a compromised model making the core agent do what the owner allowed it
to do.

## Scope

Welcome:

- Bypasses of the installer's disk-identity or eligibility checks (writing to a
  non-blank, mounted, boot-media, or different disk than confirmed).
- Broker authorization bypasses: committing an approval-mode action without
  Polkit, committing a high-impact action in Full Root without Polkit, or using an
  expired, used, wrong-boot, or wrong-run token or grant.
- Secrets (LUKS key, account password, provider credentials) landing in the
  audit log, journal, process arguments, environment, or world-readable files.
- Anything that lets a process outside the gateway/node units become
  `gateway-attested`, or lets a non-core agent take core actions without a grant.

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
- Any local D-Bus client may call every broker method. Agent policy is applied
  only when the caller supplies an `agentId`; an empty context skips it. So in
  Full Root any local UID can prepare and commit a non-high-impact action as
  root; `commit` records who committed but does not check them.
- `gateway-attested` is a substring check for `openclaw-gateway.service` or
  `openclaw-node.service` in `/proc/<pid>/cgroup`. `agentId`, `sessionKey` and
  `runId` are copied from caller-supplied context. Any process in those units can
  claim any agent id, including `main`, which is allowed `*`.
- `ListPending` returns approval tokens to whoever calls it; `GetAction` and
  status counts strip them. Tokens also travel as `clawosctl` arguments. A token
  still meets Polkit in approval modes; in Full Root a non-high-impact token
  commits immediately. Tokens are not secrets from local users.
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
- Live ISO: the profile is archiso `releng` plus an overlay, and the overlay does
  not override releng's root autologin on `tty1`. Root autologin on `ttyS0`
  happens only on KVM with the Q35 product string. The live graphical session
  runs as `clawos-live` on `tty2` and may `pkexec` the installer without
  authentication. Installed systems get serial root autologin only with
  `--vm-test`.
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
  every session whose key matches `agent:<id>:<...>`. Its `before_tool_call` hook
  blocks only `exec` calls whose command matches a regex of privileged binaries
  at the start of the command or after `;`, `&`, `|`; the block is off entirely
  in Full Root for the core agent, and an `exec` without an agent id counts as
  core.

### Constructed by reasoning, not observed

- Which identity satisfies the `auth_admin` prompt for commits. The repository
  ships the action with `auth_admin`, no Polkit rules for it, and creates
  `clawos` in `video,input,clawos-control`, not `wheel`. Whether the prompt
  resolves to root, an empty admin group, or something else depends on polkit
  defaults on the target and has not been observed. In passwordless mode the
  accounts are empty, so the installer expects the prompt to succeed without a
  secret; untested here.
- The exec-hook regex is a guidance rail, not a sandbox. `env sudo`, `bash -c`,
  a script file, or any tool other than `exec` should pass it. Not tested.
- A process outside the gateway/node units should not be able to appear inside
  them in `/proc/<pid>/cgroup`; cgroup or systemd-scope tricks have not been
  tested.
- An enabled but unconfigured `tailscaled` should expose nothing until someone
  runs `tailscale up`; not verified against the installed image.
- Because the only interactive account in Full Root already has passwordless
  sudo, the practical delta of "any local UID can commit" is a compromised
  system service account gaining allowlisted root actions. Not measured.

## How fixes are communicated

Fixes land as ordinary commits on `main`, with the boundary they change noted in
`docs/KNOWN-ISSUES.md`. There are no GitHub security advisories, CVEs, release
notes, or backports yet. If you want credit, say so in the report and you will be
named in the commit message.
