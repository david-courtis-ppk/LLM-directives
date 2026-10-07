# Pull requests

This guide covers how to title, describe, check, review and merge a pull request in the PreciseRx repositories, and what the resulting commit on `main` looks like. Read it before you open or review a PR. For which branch a PR should target, see [Git branching](branching.md).

## Title

- Write a sentence-case summary of the change in behaviour, then the uppercase Jira key in parentheses. For example: `Refresh on whichever token expires sooner, not the access token alone (RX-3625)`.
- Separate several keys with commas, as in `(RX-3302, RX-3582)`.
- Use the blitz key for a release blitz fix, as in `(BLITZ-3.6.0-1)`.
- Name a port after the release line it reaches, as in `Port the token pairing check to the 3.6.0 release line (RX-3606)`.
- Start the `main` counterpart of a release-first fix with `Forward-port:`.
- Don't use conventional-commit prefixes such as `fix:` or `feat:`. The history doesn't use them.
- Write the key in uppercase so the Jira integration can link the PR to its ticket ([Atlassian: reference issues in your development work](https://support.atlassian.com/jira-software-cloud/docs/reference-issues-in-your-development-work/)).

## Commit messages

No tool checks commit messages: no repository has commitlint, husky or a commit hook. The convention comes from how PRs are merged.

Every PreciseRx repository allows squash merges only, so each PR lands as one commit. The repositories set `squash_merge_commit_title` to `COMMIT_OR_PR_TITLE` and `squash_merge_commit_message` to `COMMIT_MESSAGES` ([GitHub docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-squashing-for-pull-requests)). Read the settings with `gh api repos/PreciseRx/<repo> --jq '.squash_merge_commit_title, .squash_merge_commit_message'`.

- **Subject.** GitHub uses the PR title when the PR has several commits, and the commit's own subject when it has one. It then appends the PR number.
- **Body.** GitHub lists every commit message from the branch as a bullet.

So a commit on `main` looks like this (PreciseRx-Web `c1d47c364`):

```text
Drug Monitoring interval tooltip shows hour bounds for day-interval drugs (RX-3682) (#2410)

* Convert the Drug Monitoring interval tooltip to the drug's display unit (RX-3682)

RX-3545 converted the interval validation bounds to the drug's display unit on
...
```

Every branch commit message ends up on `main`, so write each one as you would a PR title: a sentence-case summary of the change, followed by the Jira key. Explain the why in the body.

- For a single-commit PR, write that commit's subject in the title format above, or fix the subject in the merge dialog.
- Clean up fixup and "wip" commits before you merge, either by rebasing the branch or by editing the body in the merge dialog. Otherwise they appear in the body on `main`.
- Conventional-commit prefixes such as `fix:` or `feat(scope):` are not the convention. Only 2 of the last 300 commits on PreciseRx-Web `main` use one, and none of the last 300 in Main, Database, the umbrella or PK-Library do.
- A commit that is cherry-picked to another branch and squashed again keeps both PR numbers, as in `... (RX-3625) (#640) (#641)`.

## Description

Every repository has a template at `.github/pull_request_template.md` with four sections: Issue, Proposed Changes, Additional Info and Checklist. The template is identical in PreciseRx-Web, PreciseRx-Web-PK, Main, Database, Analytics, Databridge, Shared-JS and Shared-Python. PK-Library and GenAI omit the Translations checklist item. Fill in every section.

| Section | What to write |
| --- | --- |
| Issue | State what is wrong or missing, what causes it, and why it matters. Link the Jira ticket and any design document. A developer reading it months later should understand the goal. |
| Proposed Changes | Describe what the PR changes. Explain the new logic in detail for a rework. A short list is enough for a small fix. |
| Additional Info | List the alternatives you rejected, any unrelated changes you made, problems you noticed but left for another ticket, counterpart PRs on other branches, and steps that must happen after deploy. |
| Checklist | Tick an item only when it is true. When you could not check something, leave it unticked and say why. The Translations item comes pre-ticked, so replace the tick with a real answer. |

To open a PR from the command line, copy the template into a file, fill it in, and pass it as the body:

```sh
gh pr create --base main \
  --title "Refresh on whichever token expires sooner, not the access token alone (RX-3625)" \
  --body-file pr-body.md
```

### Write for a human reader

PreciseRx-Web (`CLAUDE.md:3-17`) and PreciseRx-Web-PK (`CLAUDE.md:3-18`) set these rules for issues, PR descriptions and docs:

- Open with one or two sentences that say what the change is and why it matters, before any structured section (PreciseRx-Web-PK `CLAUDE.md:7`).
- Gloss internal shorthand the first time it appears. Write "RX-3480 (the async license-update rework)", not a bare key.
- Explain what a thing does before you name its identifier. A list of backticked names or `a` → `b` arrows is not an explanation.
- Write each list item as a complete sentence a reviewer can act on.
- Put one idea in each sentence. Prefer short sentences and active voice.
- Use prose for rationale, bullets for lists, and tables to compare three or more things. Keep the template's headings.
- Rewrite anything a teammate outside the workstream couldn't grasp in one read.

The submodules have no `CLAUDE.md` of their own. Claude Code reads `CLAUDE.md` files in parent directories, so it applies the umbrella's rules when it works inside a submodule of a PreciseRx-Web-PK checkout ([Claude Code memory](https://docs.claude.com/en/docs/claude-code/memory)).

## Checks

GitHub Actions runs these jobs, defined in each repository's `.github/workflows/`:

| Repository | Check | What it runs | Runs on |
| --- | --- | --- | --- |
| PreciseRx-Web | `Build-and-Test` | `pnpm install --frozen-lockfile`, `pnpm build` and `pnpm test` on Node 24 | Every PR |
| Main, Analytics, Databridge | `Run-Tests` | `pnpm install --frozen-lockfile` and `pnpm test` | Every PR |
| Database | `Run-Tests` | `pip3 install -r requirements.txt` and `make test` against a MySQL 8 service | Every PR |
| Shared-JS | `Run-Tests` | `pnpm lint`, `pnpm build` and `pnpm test` | Every PR |
| PK-Library | `Cpp-Tests`, `Python-Tests`, `NodeJs-Tests` | The C++ GoogleTest suite and the Python and Node binding tests | PRs into `main` only |
| PreciseRx-Web-PK, GenAI, Shared-Python | None | | |

- CodeQL also scans PRs. Its jobs appear as `Analyze (<language>)` plus a `CodeQL` result.
- PK-Library PRs also show `version-check` and skipped publish jobs. They come from the publish workflow, not from tests (see [GitHub Packages](github-packages.md)).

## Merge rules

Each repository has a ruleset named "Branch Protection Settings" that covers `main` and branches matching `stable/**/*`. Read it with `gh api repos/PreciseRx/<repo>/rulesets`. The ruleset does the following:

- It requires a PR with at least one approving review.
- It requires every review thread to be resolved.
- It blocks the merge when CodeQL reports an error-level alert or a security alert of high severity or above.
- It blocks force-pushes and branch deletion.

The test jobs are not required status checks, so a failing test run does not disable the merge button. The author and the reviewer must check the results themselves. Branches are not deleted on merge, except in PK-Library.

## Review

Before you approve, check each of these:

- The PR targets the right branch. A fix to a cut release has its counterpart PR (see [Git branching](branching.md#fixing-a-release-that-has-been-cut)).
- The title and description follow this guide. Request changes when they don't.
- The checks passed. A PK-Library PR into any branch other than `main` runs no tests, so run `make build-test-cpp && make test-cpp` yourself or ask the author for the output.
- The change works when you run it, and neighbouring features still work.
- No PHI (protected health information) reaches logs, URLs or third-party telemetry. PrecisePK handles PHI under HIPAA.
