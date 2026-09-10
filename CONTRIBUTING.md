# Contributing

Read [features/status](FEATURES.md), the [roadmap](ROADMAP.md), the [project scope](docs/SCOPE.md),
[hardware boundaries](docs/HARDWARE.md) and the [code of conduct](CODE_OF_CONDUCT.md). Use the
bug or feature issue template to propose focused work. Release maintainers should follow
[the release guide](docs/RELEASING.md); a green build is not permission to publish a
stable or hardware-supported release.

Start with a focused issue and a small branch. Describe the behavior changed, affected
runtime components, verification, and remaining risks. Preserve unrelated work and
distinguish unit tests from fresh-install proof. Issues and pull requests are read
best-effort by one maintainer with no promised response time, the same no-SLA terms as
[SECURITY.md](SECURITY.md). Report security problems as it says, never in a public issue.

## Finding work

The pinned [Start here issue](https://github.com/Solvely-Colin/ClawOS/issues/86)
collects newcomer entry points and source-only launch expectations.

Issues carry labels. `good first issue` and `help wanted` mark work open to newcomers.
Docs, CI (`ci`) and unit-tested modules need no VM; CI checks them on every pull request.
Installer, boot and fresh-install work (`installer`, `hardware`, `evidence`) is labeled
`needs-vm` and needs a disposable Arch VM with a blank disk. The separate visual
prototype must be ported and tested before it becomes runtime behavior.

## Environment

- Build ISOs and run install and boot tests in a disposable Arch VM.
- Use your own provider credentials through OpenClaw setup. Never commit auth
  databases, browser profiles, tokens, keys, VM disks, firmware variables,
  checkpoints, credential screenshots or personal transcripts.
- Review privileged scripts before execution. Installer/recovery experiments
  belong on disposable disks with an independent recovery route.

## Testing without Arch or KVM

`.github/workflows/ci.yml` runs four jobs on every push and pull request. None
needs provider keys, KVM or an ISO build, so a PR gets checked with no local
Arch install; a green run is source evidence only:

- `unit-tests` (ubuntu-latest): the m1 and m3 Python unit tests, the OpenClaw
  plugin Node tests and `git diff --check`.
- `arch-preflight` (`archlinux:base-devel` container): `./m1/bin/preflight-iso`,
  the same Arch source gate `tools/ci/build-release.sh` runs before an ISO build,
  followed by the D-Bus caller-boundary proof from `m3/README.md`, which runs as
  root against a private bus with real UIDs.

- `container-wrapper` exercises the contributor container entry point and D-Bus proof.
- `prototype` installs/builds the frozen visual prototype, runs its retained Sites
  tests, and checks dev/production rendering and Fast Refresh in Chromium. See
  [its README](shell-prototype/README.md) for local commands and limitations.

Local equivalents:

- The complete unit suite runs on Linux with Python 3.12+ and Node 24+
  (commands in the README). Some tests require `fcntl`, POSIX file operations
  and Linux paths; on Windows or macOS use the Linux container instead.
- The source gate runs on any Docker host with the ci.yml recipe (CI also pins
  the Arch snapshot from `m1/config/versions.env`; the recipe covers the source
  gate only, not the D-Bus proof):

  ```sh
  docker run --rm -v "$PWD:/src" -w /src archlinux:base-devel bash -c \
    'pacman -Syu --noconfirm git inetutils nodejs python jq shellcheck &&
     git config --global --add safe.directory /src && ./m1/bin/preflight-iso'
  ```

- `./m1/bin/run-qemu --software` boots a built ISO under QEMU's TCG emulator
  without KVM; slow, but it works where hardware virtualization is unavailable.
- `m1/tests/boot-smoke-qemu`, `m1/tests/m2-e2e-qemu` and `m1/bin/run-installer-qemu`
  currently require KVM.
- Windows hosts drive an already-provisioned QEMU (WHPX) VM with the scripts in
  [tools/windows/README.md](tools/windows/README.md); they are not an installer.

## Running the source gate without Arch

`./m1/bin/preflight-iso` needs an Arch userland. On any host with Docker or
Podman (Debian, Fedora, macOS, Windows with Git Bash), run it in the same
`archlinux:base-devel` container CI uses:

```sh
tools/dev/preflight-in-container.sh
```

The script pins the Arch package archive to `ARCH_SNAPSHOT` from
`m1/config/versions.env`, installs the same packages, mounts the checkout
read-only at `/src`, runs `./m1/bin/preflight-iso` and exits with its status.
`--dbus` also runs the D-Bus caller-boundary proof from `m3/README.md`;
`--help` lists the rest. Run it from a normal clone, not a linked worktree.
The recipe is the `arch-preflight` job in `.github/workflows/ci.yml`; change
both together. Boot and install tests still need a disposable Arch VM.

## Before submitting

1. Run focused tests and `./m1/bin/preflight-iso` for OS integration, in Arch
   or through `tools/dev/preflight-in-container.sh`.
2. Include the source revision and execution environment. Deployment evidence
   should include job ID, terminal receipt, checkpoint and file drift.
3. Verify UI changes visually and with keyboard navigation; follow Carapace
   and preserve focus/return behavior, not just colors.
4. Review the staged diff for generated or personal files. Secret-scan source
   and history before sharing a new baseline.

## License and merging

Contributions are accepted under the [MIT License](LICENSE): inbound terms equal outbound
terms, and there is no CLA. Do not submit code you cannot license that way. Third-party
material (copied files, snippets, artwork, fonts) must be listed in [NOTICE.md](NOTICE.md)
with its origin and license. Pull requests are merged with merge commits, as #1-#3 were;
that is the owner decision in #13. The active main ruleset permits merge commits
only, requires a PR and the four checks `unit-tests`, `arch-preflight`,
`container-wrapper`, and `prototype`, and blocks force-push and deletion.
Zero approvals are required; CODEOWNERS is informational. Administrators retain
bypass for recovery, not the normal contribution path; explain any use in the PR.
The `v*` tag ruleset restricts creation, update and deletion to administrators.

Since the 2026-09-10 public launch, Actions requires full-commit-SHA action pins
and permits only GitHub-owned or verified-creator actions. An unpinned action is
blocked even when GitHub owns it; a pinned action from an unapproved creator is
also blocked. Reusable workflows may use tags. All external contributors need
workflow-run approval. Workflow tokens default to read-only and cannot approve
PR reviews. These settings protect the repository workflow, not the guest OS.

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
