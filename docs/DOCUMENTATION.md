# What belongs in the public repository

Keep source, build configuration, tests and fixtures, CI workflows, reusable
contributor instructions, architecture, license/provenance notices and redacted
verification results. Evidence must identify the revision, environment, observed
result and limitations without including credentials or private transcripts.

Keep operator handoffs, private demo instructions, model prompts, screenshot
diaries, machine-specific state and publication checklists with personal
decisions outside Git. Use ignored `.local/`, `local-notes/`, `docs/local/` or
`*.local.md` for new notes; these are conventions, not encryption or access control.
Keep an independent private backup before changing branches or cleaning a checkout.

The tracked-tree audit classified every file in the source tree. Nineteen old
milestone, design-QA, generation and launch-operation documents were removed
from tracking with checksum-verified local preservation. Historical Git commits
were not rewritten. Public architecture and repository-protection guidance
replace the reusable parts; attribution and test evidence remain public.

Ignore rules do not remove already tracked files. The shared ignore tests reject
force-added files covered by those rules and ensure source/assets remain visible.
Do not ignore whole source directories to conceal unfinished migration work.

Useful entry points: [Getting started](GETTING-STARTED.md),
[architecture](ARCHITECTURE.md), [code map](CONTRIBUTOR-MAP.md),
[known issues](KNOWN-ISSUES.md), [hardware](HARDWARE.md),
[evidence](EVIDENCE.md), [release guide](RELEASING.md),
[release checklist](PUBLIC-RELEASE-CHECKLIST.md), and
[repository protections](GITHUB-PROTECTIONS.md).
