# Git branching

This guide covers how branches are named, where each kind of branch starts and merges, how a release moves from `main` to production, how fixes reach a release that has already been cut, and how to keep branches aligned across the umbrella's submodules. Read it before you create a branch, cut a release, or port a fix. For titles, descriptions and review, see [Pull requests](pull-requests.md).

## Keys in branch names

- `RX-####` is a ticket in the RX Jira project. Branch names use it in lowercase, as `rx-####`. PR titles use it in uppercase.
- `BLITZ-X.Y.Z-N` is item `N` on the bug list from the release blitz for version `X.Y.Z`. The release blitz is the team's round of testing a release before it reaches production. A blitz item has no Jira ticket of its own.

## Branch types

| Branch | Purpose | Starts from | PR into |
| --- | --- | --- | --- |
| `main` | The mainline. Every change reaches it eventually. | | |
| `feature/rx-####` | A story, or a parent branch that collects a group of related tickets. | `main` | `main` |
| `bugfix/rx-####` or `bug/rx-####` | A bug ticket. Both prefixes are in current use. | `main` | `main` |
| `hotfix/rx-####` or `hotfix/rx-####-stable` | A fix ported to a release that has already been cut. | `stable/vX.Y.Z` | `stable/vX.Y.Z` |
| `bug/blitz-X.Y.Z-N` | A fix for release blitz item `N`. | `stable/vX.Y.Z` | `stable/vX.Y.Z` |
| `revert/rx-####` or `revert/rx-####-stable` | Undoes a merged change. | The branch being reverted | The same branch |
| `junk/<description>` | Experiments and throwaway work. | Anywhere | Nothing. Never merge it. |
| `rc/vX.Y.Z` | The release candidate. | `main` | Nothing. No PRs target it. |
| `stable/vX.Y.Z` | The release line. Production runs from it. | `main` | Receives hotfix and blitz PRs. |
| `dependabot/...` | Opened by Dependabot. | `main` | `main` |
| `RX-####-<slug>` | A Dependabot security fix made with the `fix-dependabot` Claude Code skill (`PreciseRx-Web/.claude/skills/fix-dependabot/SKILL.md:103`). | `main` | `main` |

A suffix marks a copy of the same change aimed at another branch:

- `-stable` ports a fix from `main` to the release line, for example `hotfix/rx-3625-stable`.
- `-main` forward-ports a fix from the release line to `main`, for example `bug/blitz-3.6.0-1-main`.
- `-preview` and `-pre-prod` carry a PreciseRx-Web release fix to the lane branches described under [Frontend lane branches](#frontend-lane-branches).

A ticket that depends on unmerged work starts from its parent feature branch and opens its PR against that branch. For example, `bug/rx-3681` merged into `feature/rx-3590`, and `feature/rx-3590` goes to `main` as a whole. Long-lived parent branches such as `feature/rx-2901` take regular merges from `main`.

PK-Library, Shared-JS and Shared-Python also use `stable/vX.Y.Z`, but for their own package versions. Those numbers are unrelated to the PrecisePK release number. See [GitHub Packages](github-packages.md).

## Release flow

A PrecisePK release uses one version number across the repos that ship it. For example, `stable/v3.6.0` exists in PreciseRx-Web, Main, Database, Analytics and Databridge.

1. Cut `rc/vX.Y.Z` from `main` as the release candidate.
2. Create `stable/vX.Y.Z` from `main`. Until the release is frozen, merge `main` into it to pick up late work.
3. After the freeze, change `stable/vX.Y.Z` only through hotfix and blitz PRs. Pair each one with a PR into `main`, as described in the next section.
4. Deploy production from `stable/vX.Y.Z`.

Jenkins tags backend images with the last segment of the branch name (`PreciseRx-Main/Jenkinsfile:9`). So `stable/v3.6.0` builds the tag `v3.6.0`, and `hotfix/rx-3625-stable` builds `rx-3625-stable`. `rc/v3.6.0` and `stable/v3.6.0` both build `v3.6.0`, so a later build from either branch replaces the earlier image in that job's repository.

## Fixing a release that has been cut

Every fix to a cut release needs two PRs. One goes into `stable/vX.Y.Z`. The other goes into `main`, so the fix survives into the next release. Both orders are in use.

| Order | First PR | Second PR | Example |
| --- | --- | --- | --- |
| `main` first | `bug/rx-3625` into `main` | `hotfix/rx-3625-stable` into `stable/v3.6.0`, titled "Port ... to the 3.6.0 release line" | PreciseRx-Main #640, then #641 |
| Release first | `bug/blitz-3.6.0-1` into `stable/v3.6.0` | `bug/blitz-3.6.0-1-main` into `main`, titled "Forward-port: ..." | PreciseRx-Web #2405, then #2417 |

Build the second branch by cherry-picking the first PR's squash commit:

```sh
git fetch origin
git switch -c hotfix/rx-3625-stable origin/stable/v3.6.0
git cherry-pick <squash-commit-of-the-first-PR>
git push -u origin hotfix/rx-3625-stable
```

- Link the counterpart PR in each description's Additional Info section.
- Expect the release-line commit to carry both PR numbers once it is squashed, as in `... (RX-3625) (#640) (#641)`.
- In PreciseRx-Web, also bring the lane branches level, as described next.
- In a package repo, the same pattern applies against the package's own `stable/` branch. For example, `hotfix/rx-3703` targets PK-Library's `stable/v1.6.2` and `feature/rx-3703` targets its `main`.

## Frontend lane branches

PreciseRx-Web has two twins of each release branch, `stable/vX.Y.Z-preview` and `stable/vX.Y.Z-pre-prod`. They exist so AWS Amplify can build the same code with different environment variables. The variable `VITE_SERVER_API_VERSION` picks the blue-green lane, which is the `v1` or `v2` path segment that routes the frontend to one of two backend deployments (`PreciseRx-Web/amplify.yml:24-29`, `src/actions/AxiosRequestWrappers/Constants.ts:4`). The `-preview` twin builds the `v2` lane for the Preview environment, and `-pre-prod` builds pre-production (PreciseRx-Web #2419, #2440).

- Never commit anything to a twin that `stable/vX.Y.Z` does not also get.
- After a PR merges into `stable/vX.Y.Z`, bring each twin level. Either open a PR from `stable/vX.Y.Z` into the twin (#2419), or open the same fix against each twin from a `-preview` or `-pre-prod` branch (#2440, #2441).
- Compare content, not commits. Repos allow squash merges only, so a twin always gets new commits even when its code matches.

Check that a twin matches its release branch:

```sh
git fetch origin
git diff --stat origin/stable/v3.6.0 origin/stable/v3.6.0-preview
```

Empty output means the twin carries the same code.

## Keeping submodules on matching branches

Work that spans repos uses the same branch name in every repo it touches. For example, `feature/rx-3464` exists in PreciseRx-Web, Main, Database and PK-Library.

`make checkout-all` in the PreciseRx-Web-PK umbrella switches the root repo and every submodule to the first listed branch that exists on `origin`, falls back to `main` where none exists, and pulls (`Makefile:328-358`). List several names in order of precedence when repos named the branch differently.

```sh
git fetch && git submodule foreach git fetch
make checkout-all feature/rx-3445-server-side feature/rx-3445
```

- Fetch first. The target checks remote-tracking refs and does not fetch before it looks, so a branch pushed since your last fetch counts as missing.
- Pass at least one branch. With none, the target prints its usage and exits, although `make help` says it defaults to `main` (`Makefile:60-64`, `329-331`).
- Ignore the final `No rule to make target '<branch>'` error. Make reads the branch names as extra goals after the checkout has already finished.
- Don't sync with `git submodule update`. The umbrella rarely updates its recorded submodule commits, so that command checks out old code. Use `make checkout-all main` instead.

For a fresh clone, check out the submodules and then move them all to `main`:

```sh
git clone --recurse-submodules https://github.com/PreciseRx/PreciseRx-Web-PK.git
cd PreciseRx-Web-PK
make checkout-all main
```
