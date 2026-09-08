# Features and implementation status

Status describes the current development code, not a supported-hardware promise.

| Capability | Current state |
| --- | --- |
| Arch-based live image and encrypted install | Experimental blank-disk installer for x86_64 UEFI; guarded physical and virtual target selection; optional passwordless (unencrypted, no lock) setup |
| OpenClaw as the primary interface | Running in the development VM |
| Provider and model selection | Delegated to OpenClaw's native wizard; no ClawOS provider catalog |
| Typed OS inspection and changes | Broker and plugin implemented; Full Root remains trusted |
| High-impact approvals | Typed rollback, power, role and security-level changes are gated |
| Live ClawOS runtime updates | Versioned payloads, checkpoints, health checks and file rollback |
| Completion notices | Bound to the original conversation; idempotent delivery and retries |
| Work and decisions | Shared attention projection, reviewable notices and pending deployments |
| Terminal/browser/build surfaces | Available; task association and fullscreen layout need work |
| Windows VM lifecycle | Scheduled Task, SSH/ACPI shutdown, absolute tablet and protected unlock |
| Remote-node roles | Implementation and isolated tests; broader live acceptance remains |
| Physical hardware installation | Eligible blank SATA/NVMe/eMMC disks accepted; compatibility remains unverified, not "any Arch hardware" |
| Fully offline production installation | Not delivered; current installer is network-backed |
| Signed, production-ready releases | Not delivered |

For detail, see [known issues](docs/KNOWN-ISSUES.md) and [the next work](ROADMAP.md).
