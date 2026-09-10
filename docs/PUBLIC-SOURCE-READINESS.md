# Public-source launch record

The owner approved the source-first launch on 2026-09-10. The repository became
public at `b5512920695f53dcc5286ea3f1f19fb3a54c4993` at approximately 13:11 UTC,
after the final scan and with no intervening push. No ISO release was published.
See [Start here](https://github.com/Solvely-Colin/ClawOS/issues/86) to contribute.

| Gate | Work and evidence needed | Status |
| --- | --- | --- |
| Reporting | Working private reporting contact; verification basis stated | Contact documented; owner confirmed the email works on 2026-09-10. This is owner confirmation, not an independently observed outside-sender test or inspection of mailbox rules (#7) |
| Attribution | Copied-source headers/licenses, assets and dependency notices reviewed; unknowns disclosed | Tracked-source inventory reviewed in NOTICE; binary-artifact distribution review is separate |
| Real setup | Current CI ISO, graphical encrypted install on a fresh virtual disk, first boot, default onboarding, SSH and network listeners | Verified on unmodified build 34432248984 at `de19c1b`: encrypted GTK install, disk-only boot, local/model-later/Full Root, API completion and Control UI; exact limits in HARDWARE-INSTALLER-VALIDATION.md (#8, #9, #12) |
| Privacy/history | Redacted scan at the publication SHA and all history, including the five recovered commits; tracked-file audit | Gitleaks 8.30.1 scanned 183 commits with zero findings at `b551292`; tracked-tree check passed for 280 files. Evidence is recorded in #15/private archive. Owner accepted retaining disclosed historical paths/session identifiers; no history rewrite |
| Reconciliation | Close only issues whose acceptance is evidenced; distinguish merged code from missing VM proof | Code-only versus VM-proof issues reconciled; new proof recorded. Owner approved the SECURITY.md socket-observation correction on 2026-09-10; no risk exclusions changed |

Private scan reports, logs, screenshots, test credentials and VM disks stay
outside Git. Record only redacted conclusions and artifact identities here.
If a credential is found, revoke/rotate it before removing it and rescanning;
making a public repository private again is not a remedy for disclosure.

The current tracked tree passes the host-path/artifact hygiene gate, but older
commits contain developer paths and generated-image identifiers. These are not
credential findings. Private evidence lists the affected revisions. The owner
accepted retaining this history after disclosure and review on 2026-09-10.
That history decision did not authorize ISO distribution; the later explicit
launch approval authorized public source only.

## Verified repository protections

Applied and read back on 2026-09-10: private vulnerability reporting, secret
scanning and push protection, Dependabot alerts and dependency graph, active
main and `v*` rulesets, CodeQL default setup, external-contributor workflow
approval, selected Actions with SHA pinning, and read-only workflow defaults.
Main requires a PR and all four source checks; administrators retain bypass.

The logged-out Security page exposes **Report a vulnerability**; opening its
submission route requires GitHub sign-in. No test vulnerability was submitted.
CodeQL's first run, 34481145478, passed for Python and JavaScript/TypeScript.
It raised two alerts, statically triaged in the private record: a source-test
regex performance issue and a single-replacement warning defeated by a local
parser invariant. Both remain open for maintainer disposition; this is not a
zero-alert claim or a full security certification. Secret-scanning and
Dependabot open-alert counts were zero at verification.

The initial CodeQL readback preceded asynchronous setup completion; a later
readback verified the configured languages. Apply/recheck logs are retained
privately. [FLIP-DAY.md](FLIP-DAY.md) remains the operational runbook.
A downloadable prerelease has the additional
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
artifacts. Do not delete future artifacts merely because this record names the decision.
