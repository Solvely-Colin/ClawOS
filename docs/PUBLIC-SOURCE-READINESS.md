# Public-source preparation

This is a source-publication work plan, not approval to change visibility or
publish an ISO release. The repository remains private until the owner approves.
The publication candidate must be scanned again after its final commit.

| Gate | Work and evidence needed | Status |
| --- | --- | --- |
| Reporting | Working private reporting contact; verification basis stated | Contact documented; owner confirmed the email works on 2026-09-10. This is owner confirmation, not an independently observed outside-sender test or inspection of mailbox rules (#7) |
| Attribution | Copied-source headers/licenses, assets and dependency notices reviewed; unknowns disclosed | Tracked-source inventory reviewed in NOTICE; binary-artifact distribution review is separate |
| Real setup | Current CI ISO, graphical encrypted install on a fresh virtual disk, first boot, default onboarding, SSH and network listeners | Verified on unmodified build 34432248984 at `de19c1b`: encrypted GTK install, disk-only boot, local/model-later/Full Root, API completion and Control UI; exact limits in HARDWARE-INSTALLER-VALIDATION.md (#8, #9, #12) |
| Privacy/history | Redacted scan of the preparation candidate and all history, including the five recovered commits; tracked-file audit | Candidate scan/command/result recorded in #15 and private evidence; repeat if publication SHA changes. Owner accepted retaining the disclosed historical paths/session identifiers on 2026-09-10; no history rewrite |
| Reconciliation | Close only issues whose acceptance is evidenced; distinguish merged code from missing VM proof | Code-only versus VM-proof issues reconciled; new proof recorded. Owner approved the SECURITY.md socket-observation correction on 2026-09-10; no risk exclusions changed |

Private scan reports, logs, screenshots, test credentials and VM disks stay
outside Git. Record only redacted conclusions and artifact identities here.
If a credential is found, revoke/rotate it before removing it and rescanning;
making a public repository private again is not a remedy for disclosure.

The current tracked tree passes the host-path/artifact hygiene gate, but older
commits contain developer paths and generated-image identifiers. These are not
credential findings. Private evidence lists the affected revisions. The owner
accepted retaining this history after disclosure and review on 2026-09-10.
This is not approval to change repository visibility or expose retained ISO artifacts.

Final approval and GitHub-side protections are separate flip-day work
([FLIP-DAY.md](FLIP-DAY.md)). A downloadable prerelease has the additional
gates in [PUBLIC-RELEASE-CHECKLIST.md](PUBLIC-RELEASE-CHECKLIST.md).

## Actions artifacts are part of the visibility review

On 2026-09-10, the owner authorized a source-first launch. All four retained
GitHub ISO artifacts (sources `6a2a456`, `00f81c5`, `30541ba`, and `de19c1b`)
were deleted after verifying complete local bundles, ISO checksums and source
metadata. The remote artifact count was verified zero. Private backups,
VM disks/checkpoints and workflow logs were preserved; the receipt is recorded
in #15 and the restricted local evidence archive.

This does not disable future manual/tag builds, which can create new artifacts.
[GitHub permits signed-in repository readers to download workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).
Consequently, a public repository can expose these experimental binaries even
without a release or tag. The source-only attribution inventory is not an
artifact redistribution review. Recheck the artifact list before the visibility
change and obtain an explicit distribution/retention decision for any new ISO
artifacts. Do not delete future artifacts merely because this plan names the decision.
