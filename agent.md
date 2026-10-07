# Agent instructions

Instructions for AI coding agents working all repositories on the PC.

All changes must be run through YAGNI+SOLID+DRY+KISS principles and only what passes should be kept. Enforce this before every commit. Most commits, you'll find you built too much shit and have to delete most of it.

Do not scope creep at any cost.

## Rules

1. **Single scope.** One change per branch/PR: a single fix or one narrowly-scoped feature. Do not bundle large refactors, formatting, or unrelated improvements with a fix. Large multi-scope changes are rejected on the spot. Minimize lines changed and blast radius.
2. **Benchmarks for performance work.** Every performance change needs before/after numbers with methodology. Multiple performance changes in one PR each need their own benchmark.
3. **Consider the failure modes.** For fixes and performance changes, reason explicitly about edge cases, trade-offs, and regressions before finishing, and record the conclusions in the PR description.
4. **No private references.** Comments, test names, and log strings must never contain absolute machine paths, private documentation references, or names of specific third-party character cards. Comments are 1-2 sentences, state the why (constraint, invariant, gotcha), and default to absent. No em dashes in comments or log strings. No explaining the code below.

## Handoffs

When instructed to write a handoffs, they should adopt the structure:

```txt
./handoffs/<ticket number>/
```

It should contain:

```txt
pages/
references/
scripts/
tools/
HANDOFF.md
```

## Process

Do not commit, push, or interact with Jira, Slack, Drive, or Calendar integrations without explicit permission from the user.

## Starting work on a ticket

When a conversation starts work on a new feature or fix:

1. Ask the user for the Jira ticket number if they have not given it.
2. Read the ticket in Jira. Reading a ticket needs no extra permission; writing to Jira still does.
3. Create the branch, or a worktree if the user prefers, before changing any code. Name and base it as `guides/git/branching.md` describes, for example `feature/rx-3699` from `main`. In the PreciseRx-Web-PK umbrella, use the same branch name in every repository the change touches.

## Git and GitHub

- `style.md` and `guides/git/` hold the PreciseRx rules for branch names, PR titles, the PR template, checks and review.
- PreciseRx repositories squash-merge, so what lands on `main` is the PR title, or the commit subject of a single-commit PR. Branch commits follow rule 4. The subject of a single-commit PR must use the PR-title format in `guides/git/pull-requests.md`.
