# Public source baseline

On 2026-09-10 the maintainer approved a clean public Git baseline. It preserves
the current source, license notices and verification records while retiring the
earlier development branch history. The earlier reachable history and remote
refs were verified and archived privately before publication. Existing local
worktrees were preserved, including two integration branches not merged by
ancestry. This reset does not claim that the code was written from scratch or
change third-party ownership; [NOTICE.md](../NOTICE.md) and LICENSES still apply.

## Historical evidence

Earlier entries in [EVIDENCE.md](EVIDENCE.md) and the installer validation record
keep the original source hashes, CI run IDs and ISO checksums. Those hashes
identify the pre-baseline source that was actually tested; they are not hashes
of this new root commit and may not be fetchable through the current branches.
No old result has been relabeled as a new test. The build-input validation now
checks ClawOS identity, the pinned Arch archive and the permitted package
repositories directly. It is not a complete transitive-provenance certification.

GitHub can retain historical PR references and cached commit views, and existing
clones can retain the old history. Retiring public branch heads is not a promise
of erasing every prior copy. See [GitHub's history-rewrite guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

## Working after the reset

Use a fresh clone of the public repository for new contributions. Do not merge
or force-push an old branch into this baseline: that can restore the retired
history. Preserve unfinished work separately and reapply reviewed changes to a
new branch. Keep the private archive and old worktrees out of publication.

The owner authorized a one-time protected-main force-push for this reset using
the existing administrator bypass. Main/tag rules and required checks remain
enabled. Normal work still uses checked pull requests and merge commits; the
reset is not a standing exception or permission to publish a binary release.
