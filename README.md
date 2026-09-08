![ClawOS — an agent-native operating system](docs/assets/clawos-header.png)

# ClawOS

An experimental Arch-based OS with OpenClaw as its primary agent interface.
This is **experimental, unreleased source**, not a production-ready
distribution. There are no releases or tags yet, and every install so far has
been inside a virtual machine.

[Features](FEATURES.md) · [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md) ·
[Hardware support](docs/HARDWARE.md) · [Release builds](docs/RELEASING.md)

**Installer boundary:** the experimental installer accepts eligible blank SATA,
NVMe, virtio and eMMC disks on x86_64 UEFI systems and refuses boot media,
mounted/in-use disks and nonblank disks. It has only ever run in virtual
machines: a full `--passwordless` install plus reboot and an encrypted install
were verified on Windows QEMU (WHPX) on 2026-09-06/07
([validation record](docs/HARDWARE-INSTALLER-VALIDATION.md)). No physical
machine has been installed. Installed systems enable `sshd` (key-only: password
and root login are refused) and `tailscaled`. In encrypted mode the disk
passphrase is also the `root` and `clawos` account password; the passwordless
option leaves both accounts with empty passwords, no encryption and no screen
lock. "Full Root" means the `clawos` account has passwordless sudo. See
[hardware support](docs/HARDWARE.md).

The aim is an agent that can inspect and change its own machine, deploy ClawOS
runtime changes live, and return verified results to the originating conversation.
ClawOS owns machine integration and recovery; OpenClaw owns models, credentials,
conversations and agent execution. Carapace is the intended design language.

## Start contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [known issues](docs/KNOWN-ISSUES.md).
Use a disposable Linux VM, not your daily-driver installation.

On Arch Linux, review and install build dependencies, then run the source gate:

```sh
./m1/bin/install-build-deps
./m1/bin/preflight-iso
```

For non-privileged unit checks on Linux with Python 3.12+ and Node 24+:

```sh
python3 -m unittest discover -s m1/tests -p 'test_*.py'
python3 -m unittest discover -s m3/tests -p 'test_*.py'
node --test m2/openclaw-plugin/test/*.test.js
```

See [M1 build instructions](m1/README.md) for ISO construction and disposable-disk
testing, and [live development](m2/SELF-DEVELOPMENT.md) for checkpointed runtime
deployment. ISO builds run inside Linux. Windows manages QEMU through the
[host launcher scripts](tools/windows/README.md).

## Code map

| Path | Purpose |
| --- | --- |
| `m1/` | ArchISO, installer, shell, onboarding, runtime deployment and checks |
| `m2/openclaw-plugin/` | Machine tools, activity integration and deployment notices |
| `m3/` | Privileged broker, approval UI, recovery and tests |
| `m4/` | Standalone/remote-node role switching and tests |
| `shell-prototype/` | Separate visual prototype, not the installed OS runtime |
| `m0/` | Historical compositor experiment and retained regression checks |
| `tools/windows/` | Host lifecycle source, without VM images or credentials |

## Evidence and limits

All evidence so far comes from virtual machines. The development VM has
demonstrated runtime deployment, file-level rollback, native provider/model
setup, high-impact broker approvals, and idempotent completion notices; fresh
QEMU/WHPX guests have completed encrypted and passwordless installs and booted
without the ISO. Unit checks are not proof of fresh installation, arbitrary OS
rollback, hardware compatibility or safe root-agent behavior. Full Root
intentionally grants the `clawos` account unrestricted passwordless sudo.

Source gates reject known Omarchy dependencies. Historical references and
negative tests remain intentionally; removing those words would weaken checks.
This is not a complete package/asset provenance certification.

`PLAN.md` and milestone `STATUS.md` files include superseded designs. Treat
current code and executable tests as evidence, not every historical "proven"
statement as current release acceptance.

ClawOS is released under the [MIT License](LICENSE). Third-party components,
derived configuration files and artwork keep their own licenses and are listed
in [NOTICE.md](NOTICE.md). Security expectations and how to report a problem
are in [SECURITY.md](SECURITY.md). Use the
[public-release checklist](docs/PUBLIC-RELEASE-CHECKLIST.md) before announcing
installable releases.
