# Public-source preparation

This is a source-publication work plan, not approval to change visibility or
publish an ISO release. The repository remains private until the owner approves.
The publication candidate must be scanned again after its final commit.

| Gate | Work and evidence needed | Status |
| --- | --- | --- |
| Reporting | Outside-domain mail reaches the designated contact; spam/forwarding checked; conduct contact named | Contact documented; delivery and rule confirmation pending (#7) |
| Attribution | Copied-source headers/licenses, assets and dependency notices reviewed; unknowns disclosed | Source inventory reviewed in NOTICE; final candidate audit pending (#15) |
| Real setup | Current CI ISO, graphical encrypted install on a fresh virtual disk, first boot, default onboarding, SSH and network listeners | Build 34429154651 verified and booted; live SSH passed but GTK actions were clipped. Layout fix verified in a temporary live process; rebuilt-ISO install proof pending (#8, #9, #12, #54) |
| Privacy/history | Redacted scan of final candidate and all history, including the five recovered commits; tracked-file audit | Initial secret scan clean; historical developer paths/session identifiers found, owner disposition pending; final candidate scan pending (#15) |
| Reconciliation | Close only issues whose acceptance is evidenced; distinguish merged code from missing VM proof | In progress |

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
