# Repository protection maintenance

The public repository uses private vulnerability reporting, secret scanning and
push protection, Dependabot alerts, CodeQL, main/tag rulesets and restricted
Actions permissions. Current values should be read from GitHub, not inferred
from a historical checklist. Report vulnerabilities through [SECURITY.md](../SECURITY.md).

An authenticated repository administrator can inspect the settings without
changing them:

```sh
tools/github/enable-protections.sh --dry-run --repo Solvely-Colin/ClawOS
```

`--apply` changes and verifies settings; it refuses private repositories and
does not change visibility. Use only for an authorized maintenance task, retain
its output privately, and investigate failures rather than reporting success.
CodeQL initial setup is asynchronous: a premature readback can fail before the
first run completes. Check that run, then repeat the relevant readback.

Main requires PRs and `unit-tests`, `arch-preflight`, `container-wrapper` and
`prototype`. Merge commits are the selected method; administrators retain
bypass, zero reviews are required and CODEOWNERS is informational. `v*` tag
creation/update/deletion is restricted to administrators. These are repository
workflow protections, not OS runtime containment.

The owner-approved [history reset](HISTORY.md) uses the existing administrator
bypass for one protected-main replacement. Rules remain enabled; this is not
a new permission for ordinary force-pushes or unchecked changes.

All external contributors require workflow approval. Actions require full SHA
pins and approved creators; workflow tokens default to read-only. See
[Contributing](../CONTRIBUTING.md). A successful analysis can still raise alerts;
triage those separately. Private reporting requires GitHub sign-in to submit.

No repository setting authorizes publishing an ISO. Review artifact exposure,
release evidence and explicit publication approval through the
[release checklist](PUBLIC-RELEASE-CHECKLIST.md).
