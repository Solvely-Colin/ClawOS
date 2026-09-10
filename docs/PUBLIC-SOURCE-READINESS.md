# Public-source preparation

This is a source-publication work plan, not approval to change visibility or
publish an ISO release. The repository remains private until the owner approves.
The publication candidate must be scanned again after its final commit.

| Gate | Work and evidence needed | Status |
| --- | --- | --- |
| Reporting | Outside-domain mail reaches the designated contact; spam/forwarding checked; conduct contact named | Contact documented; delivery and rule confirmation pending (#7) |
| Attribution | Copied-source headers/licenses, assets and dependency notices reviewed; unknowns disclosed | Source inventory reviewed in NOTICE; final candidate audit pending (#15) |
| Real setup | Current CI ISO, graphical encrypted install on a fresh virtual disk, first boot, default onboarding, SSH and network listeners | Verified on unmodified build 34432248984 at `de19c1b`: encrypted GTK install, disk-only boot, local/model-later/Full Root, API completion and Control UI; exact limits in HARDWARE-INSTALLER-VALIDATION.md (#8, #9, #12) |
| Privacy/history | Redacted scan of final candidate and all history, including the five recovered commits; tracked-file audit | Initial secret scan clean; historical developer paths/session identifiers found, owner disposition pending; final candidate scan pending (#15) |
| Reconciliation | Close only issues whose acceptance is evidenced; distinguish merged code from missing VM proof | Code-only versus VM-proof issues reconciled; new proof recorded. SECURITY.md socket-observation correction awaits owner approval; no risk exclusions changed |

Private scan reports, logs, screenshots, test credentials and VM disks stay
outside Git. Record only redacted conclusions and artifact identities here.
If a credential is found, revoke/rotate it before removing it and rescanning;
making a public repository private again is not a remedy for disclosure.

The current tracked tree passes the host-path/artifact hygiene gate, but older
commits contain developer paths and generated-image identifiers. These are not
credential findings. Private evidence lists the affected revisions; no history
rewrite or approval to expose those historical details has been inferred.

Final approval and GitHub-side protections are separate flip-day work
([FLIP-DAY.md](FLIP-DAY.md)). A downloadable prerelease has the additional
gates in [PUBLIC-RELEASE-CHECKLIST.md](PUBLIC-RELEASE-CHECKLIST.md).

## Actions artifacts are part of the visibility review

On 2026-09-10, GitHub retained four ISO artifacts (sources `6a2a456`, `00f81c5`,
`30541ba`, and `de19c1b`), with scheduled expiry on September 22 or 24.
[GitHub permits signed-in repository readers to download workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).
Consequently, a public repository can expose these experimental binaries even
without a release or tag. The source-only attribution inventory is not an
artifact redistribution review. Before the visibility change, explicitly
decide whether the retained ISO artifacts may become public, or preserve the
private evidence and arrange their expiry/removal with owner approval. Do not
delete them merely because this plan names the decision.
