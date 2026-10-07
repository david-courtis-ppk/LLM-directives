# GitHub Packages and shared libraries

This guide covers the private packages the PreciseRx services depend on: the `@preciserx` npm packages on GitHub Packages, and the Shared-Python library installed from git. It explains which GitHub token you need, where the token lives, how builds use it, and how to publish PK-Library and Shared-JS. Read it when you set up a machine, when an install fails against `npm.pkg.github.com`, or before you publish a package.

## Packages

| Package | Source repo | Installed from | Used by | Published by |
| --- | --- | --- | --- | --- |
| `@preciserx/pk-library-js` | PK-Library | GitHub Packages (npm) | Main, Analytics, Databridge | The `publish.yml` workflow, when `version` changes |
| `@preciserx/preciserx-shared-js` | PreciseRx-Shared-JS | GitHub Packages (npm) | Main, Analytics, Databridge | `make publish` on a developer machine |
| `preciserxshared` | PreciseRx-Shared-Python | A git tag or branch of the private repo | Database, GenAI | A `stable/vX.Y.Z` branch, which a workflow tags |

- Each service pins exact versions in its `package.json`, for example `PreciseRx-Main/package.json:23-24`.
- To change a pin, run `pnpm add @preciserx/preciserx-shared-js@<version>` in the service directory with `GIT_TOKEN` exported (see below). The workspace setting `saveExact: true` keeps the pin exact.
- PreciseRx-Web uses none of these packages and needs no token.

## Personal access token

The GitHub Packages npm registry authenticates with a personal access token (classic) ([GitHub docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-npm-registry#authenticating-to-github-packages)). Create one at <https://github.com/settings/tokens>, give it an expiry date, and select these scopes:

| Scope | Needed for |
| --- | --- |
| `read:packages` | Installing `@preciserx` packages, locally and in Docker builds. |
| `repo` | Building the Database and GenAI images, which clone the private PreciseRx-Shared-Python repo with the same token ([GitHub scopes](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)). |
| `write:packages` | Publishing Shared-JS with `make publish`. PK-Library publishes from CI, so it needs no personal write access. |

Store and use the token like this:

- Save it in `.git-token` at the root of your PreciseRx-Web-PK checkout. The file is gitignored (`.gitignore:73`).
- Let the umbrella prompt for it. `make docker-compose-up` and its `-core` and `-gen-ai` variants run `make check-git-pat` first (`Makefile:231-233`). When `.git-token` is empty, that target prompts for the token, saves it, and exits, so run your command again (`Makefile:267-272`, `309-316`).
- Know what the check covers. `make check-git-pat` asks the GitHub API for the org's npm packages and prompts for a new token on any non-200 answer, including an expired token (`Makefile:318-325`). That request needs only `read:packages`, so a token without `repo` passes the check and fails later, when the Database image build clones Shared-Python.
- Export it when you run pnpm directly. The umbrella Makefile exports `GIT_TOKEN` from `.git-token` for its own targets (`Makefile:70`), but a pnpm command in a service directory sees only your shell:

```sh
export GIT_TOKEN="$(cat <path-to-PreciseRx-Web-PK>/.git-token)"
pnpm install
```

CI jobs don't use your token. They read the `PACKAGE_PAT` repository secret (`PreciseRx-Main/.github/workflows/unit-test-workflow.yml:2-3`). Dependabot uses its own `GIT_TOKEN` secret (`PreciseRx-Main/.github/dependabot.yml:3-7`).

## .npmrc

Main, Analytics and Databridge commit an `.npmrc` that sends only the `@preciserx` scope to GitHub Packages and reads the token from the environment at install time (`PreciseRx-Main/.npmrc:1-4`):

```ini
@preciserx:registry=https://npm.pkg.github.com/
//npm.pkg.github.com/:_authToken=${GIT_TOKEN}
```

- Never replace `${GIT_TOKEN}` with a real token in a committed `.npmrc`.
- PK-Library's `.npmrc` has the same two lines. Shared-JS commits none. Its `make publish` writes one containing the literal token, and `.gitignore:130-131` keeps that file out of git.
- Expect a fresh publish to install at once. Each service's `pnpm-workspace.yaml` exempts both `@preciserx` packages from the 72-hour minimum release age (`PreciseRx-Main/pnpm-workspace.yaml:5-8`).

## Docker builds

Docker builds receive the token as a BuildKit secret named `git_token`, so it never lands in an image layer.

- The umbrella's `docker-compose.yml` defines the secret from `.git-token` (`docker-compose.yml:223-225`) and passes it to every service build.
- The Node Dockerfiles mount it for the install step only (`PreciseRx-Main/Dockerfile.dev:22-24`).
- Database rewrites `https://github.com/` URLs to carry the token, so pip can clone Shared-Python (`PreciseRx-Database/Dockerfile.dev:17-21`).
- GenAI hands the token to Poetry as HTTP basic credentials (`PreciseRx-GenAI/Dockerfile:36-39`).
- Jenkins passes the secret from its credential store with `--secret id=git_token,env=GIT_TOKEN` (`PreciseRx-Main/Jenkinsfile:26`).
- Main's production `Dockerfile` is the exception. It declares `ARG GIT_TOKEN`, and its install step mounts no secret (`PreciseRx-Main/Dockerfile:4`, `22`).
- Never pass the token with `--build-arg`. Build arguments are recorded in the image ([Docker build secrets](https://docs.docker.com/build/building/secrets/)).

To build one image by hand, run this from the umbrella root:

```sh
docker build --secret id=git_token,src=.git-token -f src/apis/PreciseRx-Main/Dockerfile.dev .
```

## Versions and dist-tags

- Stable versions are `X.Y.Z`. Follow semantic versioning: bump major for breaking changes, minor for backward-compatible additions, and patch for fixes.
- Prerelease versions carry the ticket. PK-Library uses `X.Y.Z-rx-####.N`, for example `1.7.0-rx-3464.0`. Shared-JS uses `X.Y.Z-rx-####`, for example `1.13.4-rx-3576`.
- Test unmerged package work in a service with a prerelease. Publish it, pin that exact version on the service's feature branch, and open the service PR. For example, Main's `feature/rx-3464` pins `@preciserx/pk-library-js` at `1.7.0-rx-3464.0`.
- Install by exact version, never by dist-tag. Both packages set `publishConfig.tag` to `dev` (`PK-Library/package.json:5-8`, `PreciseRx-Shared-JS/package.json:4-7`). Every publish, stable or prerelease, therefore moves the `dev` tag and leaves `latest` alone ([pnpm publish](https://pnpm.io/cli/publish#--tag-tag)).
- Link instead of publishing when you only need the change in your local stack. Run `make link-pk-library-js` or `make link-preciserx-shared-js` in the umbrella while the containers are up. The Shared-JS target stays in watch mode, so run it in its own terminal.

## Publishing PK-Library

The `publish.yml` workflow runs on every push to every branch (`.github/workflows/publish.yml:5`). It publishes only when all of these conditions hold (`publish.yml:15-85`):

- The pushed commit changes `version` in `package.json`.
- No `v<version>` tag exists, and the registry does not have that version yet.
- A stable version (`X.Y.Z`) is pushed on the branch `stable/vX.Y.Z` exactly. A prerelease can publish from any branch.

When a condition fails, the run still succeeds and simply skips its publish jobs. Check that `prebuild` and `collect-and-publish` ran before you assume a version exists. A publishing run builds prebuilt binaries for Linux (glibc and musl, each on x64 and arm64) and macOS (arm64 and x64) (`prebuild.yml:18-50`). It then publishes and pushes the tag `v<version>` (`publish.yml:134-149`).

To release a stable version:

1. Create `stable/vX.Y.Z` from `main`, or from the previous `stable/` branch for a hotfix.
2. Set `version` to `X.Y.Z` in `package.json` on that branch, and push.
3. Confirm the run published and the tag `vX.Y.Z` exists.
4. Bring the version bump back to `main`, then raise the pin in each service. The 1.6.1 release did this with PK-Library #187 and PreciseRx-Main #625.

PK-Library's `README.md` still describes publishing with `npm publish` from a developer machine. Use the workflow instead.

## Publishing Shared-JS

Run `make publish` in the Shared-JS checkout, on the branch whose code you want to release (`Makefile:7-27`). The target does the following:

1. It prompts for the new version. It stops if the tag `v<version>` or a local `stable/v<version>` branch already exists.
2. It checks the token in Shared-JS's `.npmrc` and prompts for one if the file is missing or the token is rejected. Supply a token with `write:packages`.
3. It runs `pnpm version <version>`, creates `stable/v<version>` from the current branch, pushes that branch, and runs `pnpm publish --no-git-checks`.

Keep these points in mind:

- The token check prints the token to the terminal (`Makefile:52`, `54`). Don't run it while sharing your screen or recording terminal output.
- Pushing `stable/v<version>` also starts `stable_release_workflow.yml`, which tries to publish the same version (`stable_release_workflow.yml:3-6`, `48-51`). The two publishes race, and the loser fails with `409 Conflict ... Cannot publish over existing version`. The workflow usually loses, so a failed run on a new `stable/` branch is expected.
- Make sure the version bump also reaches `main`, normally through the PR for your change. Then raise the pin in each service.

## Shared-Python

PreciseRx-Shared-Python is not on a package registry. Services install it straight from the private repository at a git ref:

- Database pins the tag `v1.0.0` (`PreciseRx-Database/requirements.txt:14`).
- GenAI pins the branch `feature/rx-2857` (`PreciseRx-GenAI/pyproject.toml:17`).

To release a version, set `version` in `pyproject.toml` (`pyproject.toml:3`), merge the change to `main`, and push a branch named `stable/vX.Y.Z`. The workflow tags that commit with the last segment of the branch name (`.github/workflows/stable_release_workflow.yml:18-23`). Keep the `v` in the branch name, because Database refers to tags in the form `vX.Y.Z`.
