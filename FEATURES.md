# Features and implementation status

Status describes the current development code, not a supported-hardware promise.
The three buckets below are the ones [docs/SCOPE.md](docs/SCOPE.md) uses; every
install and boot proof is from QEMU (Linux KVM or Windows WHPX).

## Supported in a VM

| Capability | Current state |
| --- | --- |
| Arch-based live image and encrypted install | Experimental blank-disk installer for x86_64 UEFI; guarded physical and virtual target selection; optional passwordless (unencrypted, no lock) setup; fresh QEMU/WHPX encrypted and passwordless installs passed on 2026-09-06/07 |
| Credentials on installed systems | In encrypted installs the LUKS passphrase is also the `root` and `clawos` account password (Polkit prompts, session unlock); passwordless installs leave both accounts with empty passwords, no encryption and no screen lock |
| Remote access on installed systems | `sshd` and `tailscaled` enabled at boot; sshd refuses password, keyboard-interactive and root login and nothing installs an authorized key; Tailscale is enabled but not enrolled |

## Experimental

| Capability | Current state |
| --- | --- |
| OpenClaw as the primary interface | Running in the development VM and on fresh QEMU installs; no hardware evidence |
| Typed OS inspection and changes | Broker and plugin implemented; Full Root remains trusted |
| High-impact approvals | Typed rollback, power, role and security-level changes are gated |
| Live ClawOS runtime updates | Versioned payloads, checkpoints, health checks and file rollback |
| Completion notices | Bound to the original conversation; idempotent delivery and retries |
| Work and decisions | Shared attention projection, reviewable notices and pending deployments |
| Terminal/browser/build surfaces | Available; task association and fullscreen layout need work |
| Windows VM lifecycle | Scheduled Task, SSH/ACPI shutdown, absolute tablet and protected unlock |
| Remote-node roles | Implementation and isolated tests; broader live acceptance remains |
| Physical hardware installation | Eligible blank SATA/NVMe/eMMC disks accepted; verified only in QEMU/WHPX, no physical machine installed yet; not "any Arch hardware" |
| CI-built ISO | `release.yml` completed once (run 34270708295 on `main`; validated, not booted); artifacts expire after 14 days and there is no downloadable release |

## Not implemented or by design

| Capability | Current state |
| --- | --- |
| Provider and model selection | Delegated to OpenClaw's native wizard; no ClawOS provider catalog, by design |
| Existing-disk or dual-boot installation | Existing partitions are intentionally refused; blank whole disks only |
| Untrusted-agent containment | Full Root gives the `clawos` account unrestricted passwordless sudo; it is a trusted-agent mode, not containment |
| Fully offline production installation | Not delivered; current installer is network-backed |
| Signed, production-ready releases | Not delivered |

For detail, see [known issues](docs/KNOWN-ISSUES.md) and [the next work](ROADMAP.md).
