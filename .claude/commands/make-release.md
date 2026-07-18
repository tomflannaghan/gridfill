---
description: Bump the project version, commit, tag, and push a release
argument-hint: <version, e.g. 0.2.0 or v0.2.0>
---

Cut a release of gridfill at version `$ARGUMENTS`.

## Steps

1. **Resolve the version.** Strip a leading `v` from `$ARGUMENTS` if present to
   get the bare version (e.g. `0.2.0`); the tag itself will be `v0.2.0`. If no
   argument was given, ask the user for the version instead of guessing. Sanity
   check it looks like a version (digits and dots, optionally with a
   pre-release suffix) — if it clearly isn't, stop and ask.

2. **Check repo state.** Run `git status`. If there are uncommitted changes
   (staged or unstaged), stop and tell the user — don't stash or discard
   anything. Also check the current branch is `master` and is up to date with
   `origin/master` (`git fetch origin && git status`); if it's behind, ask
   before continuing.

3. **Check the version is actually new.** Confirm `v<version>` doesn't already
   exist as a git tag (`git tag -l`) and that the target version differs from
   the current one in `python/pyproject.toml`. Stop and ask if it already exists.

4. **Bump the version in both places it's declared:**
   - [python/pyproject.toml](../../python/pyproject.toml) — the
     `version = "..."` line under `[project]`.
   - [python/src/gridfill/__init__.py](../../python/src/gridfill/__init__.py) —
     the `__version__ = "..."` line.

   Use Edit for both; don't touch anything else in these files.

5. **Commit.** Stage exactly those two files and commit with message:

   ```
   Bump version to v<version>
   ```

6. **Tag.** Create an annotated tag `v<version>` on that commit, e.g.:

   ```
   git tag -a v<version> -m "v<version>"
   ```

7. **Confirm before pushing.** Pushing to `origin/master` and pushing a tag are
   both visible, hard-to-reverse actions — show the user the commit and tag
   you're about to push and get explicit confirmation first. Mention that
   pushing the tag triggers
   [.github/workflows/build.yml](../../.github/workflows/build.yml), which
   builds the standalone executables and publishes a GitHub release.

8. **Push.** Once confirmed:

   ```
   git push origin master
   git push origin v<version>
   ```

   Push the branch first so the tagged commit is reachable from `master` on
   the remote before the tag (and the release build it triggers) shows up.

9. Report the release tag and a link to the Actions run / releases page if
   `gh` is available (e.g. `gh run list --workflow=build.yml -L 1`), otherwise
   just confirm what was pushed.

## Notes

- Never use `--force` when pushing.
- If any step fails partway (e.g. push rejected), stop and report the exact
  state (what's committed/tagged/pushed locally vs. remotely) rather than
  trying to force through it.
