# Flip-day runbook

The order of operations for the sitting in which `Solvely-Colin/ClawOS` becomes
public: issue #16 (GitHub-side protections) and issue #17 (the documentation
that goes stale the moment the repository is public). Everything here is
prepared in advance and executed by the owner in one sitting of about two
hours. Nothing in this file changes repository visibility by itself.

Issue #15 owns the last private steps (gitleaks at the flip SHA, tree audit,
checklist ticks, owner approval) and its order stands: commit the ticks, scan
that SHA, flip that SHA, with no push in between. This runbook starts where
#15 ends.

Conventions:

- `$EVIDENCE` is the private evidence archive named in #15: a host-only
  directory outside the repository. Its path is never written into the repo.
- Times are UTC and relative to the visibility change (T+0:00). Record the
  real times in `$EVIDENCE/flip-day-times.txt` as you go.
- `tools/release/flip-day.sh` is the script #16 calls
  `tools/github/enable-protections.sh`. It only needs `gh` authenticated as the
  repository admin.

## Before the sitting (T-1 day)

1. Dry-run the protections script against the still-private repository and
   file the output. It prints every API call and the current state; nothing is
   changed.

   ```sh
   tools/release/flip-day.sh --dry-run 2>&1 | tee "$EVIDENCE/flip-day-dry-run-$(date -u +%Y%m%d).txt"
   ```

   Expected on the private repository (observed 2026-09-09):
   private-vulnerability-reporting 404, vulnerability-alerts 404, rulesets 403,
   code-scanning/default-setup 403, fork-pr-contributor-approval 422,
   selected-actions 409, `allowed_actions` `all` and `sha_pinning_required`
   `false`, `default_workflow_permissions` already `read`.

2. Confirm the merge method. The script's main ruleset allows only one merge
   method and defaults to `merge`, the method PRs #1-#3 landed with. If #13
   recorded squash or rebase in CONTRIBUTING.md, plan to pass
   `--merge-method squash` (or `rebase`); that also adds the
   `required_linear_history` rule, which #16 wants only in that case.

3. Prepare the #17 edits on a local branch (`flip-day/follow-through`) but do
   not push it yet. Issue links (section "Issue links" below) may land before
   the flip; the PVR sentence, the ticks and the README wording must wait for
   the verified state.

4. Prepare the Start-here issue text (section "Start-here issue" below) in a
   local file outside the repository.

5. Have a second browser profile or private window ready for the logged-out
   PVR check, and `gh auth status` showing the owner account (it masks the
   token; never paste the token anywhere).

## T-0:15 Hand-off from #15

- `git rev-parse origin/main` equals the SHA gitleaks scanned and the SHA in
  the checklist tick. `gh api repos/Solvely-Colin/ClawOS/commits/main --jq .sha`
  agrees. Write the SHA to `$EVIDENCE/flip-sha.txt`.
- Checklist item 17 (owner approval) is ticked and pushed. No further pushes.
- `git remote -v` shows only `origin`.

## T+0:00 Flip

In the browser: Settings, General, Danger Zone, "Change repository
visibility", "Make public", type `Solvely-Colin/ClawOS`, confirm. Use the web
form so the owner performs the confirmation in person. Record the UTC time.

Verify from the shell:

```sh
gh api repos/Solvely-Colin/ClawOS --jq .visibility   # public
```

## T+0:02 Protections (#16)

Run the script in apply mode and keep the output. It runs the steps in the
order #16 mandates: PVR; secret scanning and push protection; historical
secret-scanning alert count; Dependabot alerts and dependency graph; rulesets
for `main` and `v*` tags; CodeQL default setup for `javascript-typescript` and
`python`; fork-PR approval for all outside collaborators; `sha_pinning_required`
and `allowed_actions=selected` with GitHub-owned and verified-creator actions;
and an assertion that workflow tokens stay read-only.

```sh
tools/release/flip-day.sh --apply 2>&1 | tee "$EVIDENCE/flip-day-apply-$(date -u +%Y%m%d).txt"
```

Exit 0 means every write returned the expected status and every re-read
matched. Exit 1 lists `FAIL:` lines; every step is idempotent, so fix the cause
and re-run, or re-run a subset:

```sh
tools/release/flip-day.sh --apply --only rulesets,codeql
```

Known timing: rulesets and code scanning become available a short while after
the visibility change. A 403 from those two right after the flip is a retry,
not a failure. Anything else that still fails is recorded verbatim in the
evidence file and gets an issue with the `security` and `release` labels; do
not skip a step silently.

What the rulesets do from this moment:

- `main`: no force-push, no deletion, changes arrive by pull request with zero
  required approvals (CODEOWNERS stays informational), `unit-tests` and
  `arch-preflight` from `.github/workflows/ci.yml` must pass, and only the
  configured merge method is offered. The repository admin (the owner) is in
  bypass. Use pull requests anyway so CI runs on every change; bypass is for
  emergencies.
- `release-tags`: only the owner can create, move or delete `v*` tags.
  `docs/RELEASING.md` no longer relies on discipline alone for tag creation.

What the Actions restriction does: a workflow that references a third-party
action without a full-length commit SHA, or an action that is neither
GitHub-owned nor from a verified creator, does not run. Both workflows already
pin `actions/*` by SHA, so nothing currently in `.github/workflows` is
affected.

## T+0:15 Secret-scanning triage (within the hour)

Open Security, Secret scanning, and confirm the count from the shell:

```sh
gh api 'repos/Solvely-Colin/ClawOS/secret-scanning/alerts?state=open&per_page=100' --jq length
```

Expected 0. Record the count and the UTC time in
`$EVIDENCE/secret-scanning-alerts-$(date -u +%Y%m%d).txt`. If it is not 0,
apply the incident rule from #15 before anything else in this runbook: rotate
or revoke first, then remove and re-scan; re-privatising is not a remedy.

## T+0:20 PVR verification

1. `gh api repos/Solvely-Colin/ClawOS/private-vulnerability-reporting --jq .enabled`
   prints `true` (the script already checked this).
2. In the logged-out browser open
   `https://github.com/Solvely-Colin/ClawOS/security/advisories/new`. The
   page offers "Report a vulnerability". Save a screenshot as
   `$EVIDENCE/pvr-logged-out-$(date -u +%Y%m%d).png`.

The date of this check is the date that goes into SECURITY.md below.

## T+0:30 CodeQL first run and ruleset spot-check

- Actions tab: a "CodeQL" run appears for the default setup. Let it finish
  (typically under 15 minutes for this tree). Security, Code scanning, shows
  either no alerts or alerts to triage. Record the run URL and the result in
  `$EVIDENCE/codeql-first-run-$(date -u +%Y%m%d).txt`.
- `gh api repos/Solvely-Colin/ClawOS/rulesets > "$EVIDENCE/rulesets-$(date -u +%Y%m%d).json"`.
  The `main` branch page shows the rules indicator; the #17 pull request below
  will show `unit-tests` and `arch-preflight` as required.
- Settings, Actions, General: "Allow Solvely-Colin, and select non-Solvely-Colin,
  actions and reusable workflows" with GitHub-owned and verified creators
  ticked; "Require actions to be pinned to a full-length commit SHA" on; fork
  pull request workflows require approval for all external contributors.

## T+0:45 Follow-through pull request (#17 and the #16 CONTRIBUTING note)

Push `flip-day/follow-through` and open a pull request. The ruleset now
requires `unit-tests` and `arch-preflight` to pass; merge with the configured
method. Line numbers below are as of commit `00f81c5`; grep for the quoted
text if they have moved.

### SECURITY.md: reporting route

Replace the bullet at SECURITY.md:20-21

> GitHub private vulnerability reporting is an additional route only after it
> has been enabled and verified. Do not assume the button exists at
> publication.

with

```markdown
- GitHub private vulnerability reporting:
  [Report a vulnerability](https://github.com/Solvely-Colin/ClawOS/security/advisories/new).
  Enabled and verified from a logged-out browser on YYYY-MM-DD. The mailbox
  above remains the fallback route.
```

### SECURITY.md: how fixes are communicated

At SECURITY.md:168-169, after "with the boundary they change noted in
`docs/KNOWN-ISSUES.md`", add: "and tracked under the `security` label in the
issue tracker". Leave the rest of the paragraph.

The other SECURITY.md items in #17 (the `ci.yml` job that runs
`verify_dbus_authorization.py`, the live-ISO sshd observation, the scope and
PID-reuse wording) belong to #14, #9 and #6. Include them in this pull request
only if those issues have landed their text; otherwise leave them to those
issues and say so in the PR description.

### Issue links

Add the issue number in parentheses at the end of each bullet. These may be
inserted before the flip.

| Bullet | Where | Issue |
| --- | --- | --- |
| polkit `auth_admin` identity | SECURITY.md "Which identity satisfies the `auth_admin` prompt" | #44 |
| tailscaled installed and enabled | SECURITY.md "`tailscaled` is installed and enabled", "An enabled but unconfigured `tailscaled`"; KNOWN-ISSUES "Remote access" | #42 |
| tty1 root autologin on the live ISO | SECURITY.md "Live ISO: the profile is archiso `releng`"; KNOWN-ISSUES "Authority" | #43 |
| OpenClaw integrity (version string only) | SECURITY.md "OpenClaw is pinned by version string only" | #29 (lockfile #31, SBOM #30) |
| deploy-runtime hint on every session | SECURITY.md "The OpenClaw plugin appends a `deploy-runtime` hint" | #38 |
| exec-hook rail | SECURITY.md same bullet and "The exec-hook regex is a guidance rail" | #41 |
| bare-metal guard | KNOWN-ISSUES "Fresh installs" and "Verification scope" | #26 |
| gateway attestation | SECURITY.md "`gateway-attested` checks the exact Gateway/Node unit" and "A process outside the gateway/node units" | #40 |
| rollback | SECURITY.md "Runtime rollback (`clawos-deploy`)"; KNOWN-ISSUES "Recovery" | #56 |
| startup state | KNOWN-ISSUES "Startup" | #53 |
| task routing | KNOWN-ISSUES "Task context" | #55 |
| fullscreen/layout | KNOWN-ISSUES "Fullscreen/layout" | #54 |
| releases | KNOWN-ISSUES "Releases" | #37 |

### ROADMAP.md 2.4

Replace lines 22-23

```markdown
- [ ] Approve a security/disclosure policy and enable an appropriate private
  reporting route before public visibility.
```

with

```markdown
- [x] Approve a security/disclosure policy and enable an appropriate private
  reporting route before public visibility. SECURITY.md approved; GitHub
  private vulnerability reporting enabled and verified YYYY-MM-DD.
```

### docs/PUBLIC-RELEASE-CHECKLIST.md item 10

Replace lines 9-10

```markdown
- [ ] Verify mailbox delivery before publication; optionally enable and verify
      GitHub private vulnerability reporting when available.
```

with

```markdown
- [x] Verify mailbox delivery before publication; optionally enable and verify
      GitHub private vulnerability reporting when available. Mailbox verified
      YYYY-MM-DD (#7); private vulnerability reporting enabled and verified
      YYYY-MM-DD (#16).
```

### README.md

Line 6, one word inserted and nothing else changed:

```markdown
This is **public, experimental, unreleased source**, not a production-ready
```

### CONTRIBUTING.md: the sha_pinning consequence (#16)

Add to the CI section #13 introduces, or to "Environment" if #13 has not
landed:

```markdown
- Repository settings allow only GitHub-owned and verified-creator actions and
  require every `uses:` reference to be pinned to a full-length commit SHA, as
  `.github/workflows/ci.yml` does. A workflow that references an unpinned or
  unlisted third-party action does not run.
```

## T+1:30 Start-here issue

Create and pin it. The labels named below exist in the tracker.

```sh
gh issue create -R Solvely-Colin/ClawOS --title "Start here" --label documentation --body-file start-here.md
gh issue pin <number> -R Solvely-Colin/ClawOS
```

`start-here.md`:

```markdown
ClawOS is an experimental Arch-based OS with OpenClaw as its primary agent
interface. The source is public; nothing is released. Read README.md,
CONTRIBUTING.md, docs/KNOWN-ISSUES.md and SECURITY.md first.

**Where to look**

- `good first issue`: work that needs no VM, or only a VM you already have.
- `help wanted`: work one maintainer cannot do alone (hardware, a second
  person running the getting-started steps).
- `needs-vm`: needs a booted ISO under WHPX or KVM.
- `decision`: waiting on an owner decision. Comment with evidence, not votes.
- `documentation`, `ci`, `security`, `installer`, `hardware`: by area.

**The ISO is build-it-yourself.** There is no downloadable image until
v0.1.0-alpha.1 (#37). Build with `sudo ./m1/bin/build-iso` inside a
disposable Arch VM (m1/README.md) and install only onto disposable disks.

**Security problems:** do not open an issue. Use the private routes in
SECURITY.md.

**Expectations:** one maintainer reads issues and pull requests best-effort.
There is no response-time promise. Small, focused pull requests that state
the verification actually run are the ones that land.
```

## T+1:45 Public page

Confirm on `https://github.com/Solvely-Colin/ClawOS` and from the shell:

```sh
gh api repos/Solvely-Colin/ClawOS --jq '{description, homepage, topics}'
```

Expected (set before the flip): description "Experimental Arch-based OS with
OpenClaw as its primary agent interface. VM-verified only; no releases yet.";
homepage `https://github.com/Solvely-Colin/ClawOS#readme`; topics `agent`,
`arch-linux`, `archiso`, `openclaw`, `operating-system`, `qemu`.

## T+2:00 Close out

Evidence filed in `$EVIDENCE`:

- `flip-day-dry-run-<date>.txt` and `flip-day-apply-<date>.txt`
- `flip-sha.txt` and `flip-day-times.txt`
- `secret-scanning-alerts-<date>.txt` (count and time)
- `pvr-logged-out-<date>.png`
- `codeql-first-run-<date>.txt`
- `rulesets-<date>.json`

Comment on #16 with the file names (not paths), the alert count and the PVR
verification date, and close it. Comment on #17 with the merged pull request
and the Start-here issue number, and close it. The `flip-gate` label has done
its job; leave it on the closed issues.

## If something goes wrong

- A secret or personal artifact surfaces after the flip: rotate or revoke
  first, then remove and re-scan. Re-privatising is not a remedy (#15).
- A protection cannot be enabled: record the exact response from the script
  output, open an issue with the `security` and `release` labels, and keep the
  rest of the order. Do not describe the repository as protected until the
  script exits 0.
- A ruleset blocks the owner from something urgent: the owner is a bypass
  actor. Say in the commit or PR why bypass was used.
- The wrong merge method was configured: re-run
  `tools/release/flip-day.sh --apply --only rulesets --merge-method <method>`;
  the ruleset is updated in place.
