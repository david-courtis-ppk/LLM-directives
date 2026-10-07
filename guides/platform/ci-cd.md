# CI/CD: how PrecisePK code is built, tested and released

This guide explains what runs when you open a pull request, how each artifact is built and published, and how the Jenkins build servers are run. Read it before you cut a release, publish a shared package, or change a workflow, Jenkinsfile or `amplify.yml`. Branch naming and the release flow are in [branching.md](../git/branching.md).

## At a glance

| Repository | Pull request checks | Artifact | How it is released |
| --- | --- | --- | --- |
| PreciseRx-Web | Build and unit tests | Static site | AWS Amplify builds each connected branch. |
| PreciseRx-Main, PreciseRx-Analytics, PreciseRx-Databridge | Unit tests | Docker images | Jenkins builds and pushes them when someone starts a job. |
| PreciseRx-Database | Unit tests against MySQL 8 | Docker images | Jenkins, as above. |
| PreciseRx-GenAI | None on `main` | None on `main` | No pipeline on `main`. |
| PK-Library | C++, Python-binding and Node-binding tests, plus CodeQL | `@preciserx/pk-library-js` on GitHub Packages | GitHub Actions publishes on a version change. |
| PreciseRx-Shared-JS | Lint, build and unit tests | `@preciserx/preciserx-shared-js` on GitHub Packages | `make publish`, plus GitHub Actions on `stable/*` branches. |
| PreciseRx-Shared-Python | None | A git tag | GitHub Actions tags each `stable/*` branch. |
| PreciseRx-Web-PK (umbrella) | None | None | It only runs the stack locally. |

The step that deploys the Docker images to ECS (Amazon Elastic Container Service) is defined outside these repositories.

## Pull request checks

Each repository keeps its workflows in `.github/workflows/`. Every repository also uses the same pull request template, with the sections Issue, Proposed Changes, Additional Info and Checklist (`.github/pull_request_template.md`).

- The Node workflows use Node 24 and activate pnpm 11.4.0 through Corepack. They install with `pnpm install --frozen-lockfile`, so a dependency change must include the updated `pnpm-lock.yaml`.
- PreciseRx-Web runs `pnpm build` and then `pnpm test` on every pull request (`PreciseRx-Web/.github/workflows/build-and-test-workflow.yml`). The build runs `tsc -b`, so type errors fail the check. No lint runs.
- Main, Analytics and Databridge run `pnpm test` on every pull request. They read private packages with the `PACKAGE_PAT` repository secret, exposed as `GIT_TOKEN` (for example `PreciseRx-Main/.github/workflows/unit-test-workflow.yml:1-4`). No lint runs.
- Database starts a MySQL 8 service container, installs `requirements.txt` with git rewritten to use `PACKAGE_PAT`, and runs `make test` (`PreciseRx-Database/.github/workflows/unit-test-workflow.yml`).
- PK-Library runs three jobs on pull requests into `main`: the GoogleTest suite, the Python binding tests and the Node binding tests (`PK-Library/.github/workflows/unit-test-workflow.yml`). CodeQL scans GitHub Actions, C and C++, JavaScript and TypeScript, and Python on pushes and pull requests to `main` and weekly on Sunday (`PK-Library/.github/workflows/codeql.yml:14-20`).
- Shared-JS runs `pnpm lint`, `pnpm build` and `pnpm test` on every pull request.
- The workflows run on the organization's larger runners (`ubuntu-latest-4-cores`, `ubuntu-latest-m` and `ubuntu-latest-arm64`).

## Frontend: AWS Amplify

Amplify builds PreciseRx-Web from `amplify.yml`:

1. It switches to the Node version in `.nvmrc` (24), because Amplify's image defaults to an older Node (`amplify.yml:6-12`).
2. It activates the pinned pnpm through Corepack and runs `pnpm install --frozen-lockfile` (`amplify.yml:13-21`).
3. It runs `pnpm run build` with a 4 GB Node heap and publishes `build/**` (`amplify.yml:22-37`).

- Amplify writes no `.env` file. Vite reads the `VITE_*` variables set on each Amplify branch straight from the environment (`amplify.yml:24-29`).
- `VITE_SERVER_API_VERSION` selects the blue-green lane: the `v1` or `v2` path segment that routes the frontend to one of two backend deployments. Every API path and the analytics socket path carry it (`PreciseRx-Web/src/actions/AxiosRequestWrappers/Constants.ts:4,26-48`).
- Amplify runs no tests. The pull request check is the only test gate for the frontend.
- The branch-to-environment mapping, the variable values, rewrites and response headers live in the Amplify console, not in the repository.
- The frontend and Main must ship matching versions. The app compares its `package.json` version with the version Main's `/status` returns and blocks with an upgrade-required state unless major, minor and patch all match (`PreciseRx-Web/src/utils/utils.ts:18-33`, `PreciseRx-Web/src/hooks/withAuth.tsx:107-115`, `PreciseRx-Main/src/controllers/main/get-status.js`).

## Backend images: Jenkins

Each service repository has a pair of Jenkinsfiles. `Jenkinsfile` builds `Dockerfile` into the production image repository, and `Jenkinsfile.staging` builds `Dockerfile.staging` into the staging one. Analytics has a second pair, `Jenkinsfile.worker` and `Jenkinsfile.worker.staging`, for the serum-level prediction worker. All images go to Docker Hub.

| Image | Production repository | Staging repository |
| --- | --- | --- |
| Main | `preciserx/precisepk-main-image` | `preciserx/preciserx-main-staging` |
| Database | `preciserx/precisepk-database-image` | `preciserx/preciserx-database-staging` |
| Analytics | `preciserx/precisepk-analytics-image` | `preciserx/preciserx-analytics-staging` |
| Analytics worker | `preciserx/precisepk-predict-level-worker-image` | `preciserx/preciserx-predict_level-worker-staging` |
| Databridge | `preciserx/precisepk-databridge-image` | `preciserx/preciserx-databridge-staging` |

- Every pipeline runs on an agent labelled `arm64`, so every image is built for linux/arm64 (`PreciseRx-Main/Jenkinsfile:2-4`).
- The image tag is the last `/`-separated segment of the branch name (`PreciseRx-Main/Jenkinsfile:9`). Building `stable/v3.6.0` pushes `v3.6.0`, and building `feature/rx-3703` pushes `rx-3703`. Two branches with the same last segment, such as `feature/rx-3703` and `hotfix/rx-3703`, push the same tag and overwrite each other.
- The build passes a GitHub token from the Jenkins credential store as the BuildKit secret `git_token` (`PreciseRx-Main/Jenkinsfile:10,26`). That credential is one engineer's personal token. Docker Hub credentials come from the same store.
- Main's production `Dockerfile` declares `ARG GIT_TOKEN` instead of mounting the `git_token` secret (`PreciseRx-Main/Dockerfile:4,22`). Its staging Dockerfile and the other services mount the secret (`PreciseRx-Main/Dockerfile.staging:20-22`). The token Jenkins passes therefore never reaches the production Main install.
- Jenkins runs no tests and no lint. It can push an image from a branch whose pull request checks failed.
- The Jenkinsfiles define no triggers. Someone starts each job in the Jenkins web UI.
- Each pipeline posts start, failure and success messages to the `#jenkins-alerts` Slack channel through the Slack plugin.

## Shared packages

Token scopes, prerelease naming and step-by-step release checklists are in [github-packages.md](../git/github-packages.md).

### PK-Library

`.github/workflows/publish.yml` runs on every push to any branch:

1. It detects whether the push changed `version` in `package.json`. It stops if the tag `v<version>` already exists or the registry already has that version (`publish.yml:15-55`).
2. A stable version, `X.Y.Z`, publishes only from a branch named exactly `stable/vX.Y.Z`. A prerelease version, such as `1.7.0-rx-3240.0`, publishes from any branch (`publish.yml:57-85`).
3. `prebuild.yml` builds native binaries for six targets: Linux x64 and arm64 on both glibc and musl, and macOS arm64 and x64 (`prebuild.yml:19-49`).
4. The workflow collects the binaries into `prebuilds/` and runs `pnpm publish` (`publish.yml:100-132`).
5. It then pushes the tag `v<version>` (`publish.yml:134-149`).

- To release, bump `version` in `package.json` and push it to `stable/vX.Y.Z`, or to your own branch for a prerelease.
- Published versions are immutable. For another prerelease attempt, increment the trailing counter.
- The manual `npm login` and `npm publish` steps in PK-Library's `README.md` are not the release path. `publish.yml` is.

### PreciseRx-Shared-JS

Run `make publish` from a clean working tree on the branch you want to release (`PreciseRx-Shared-JS/Makefile:7-27`):

1. The target prints the current version and asks for the new one. It refuses a version whose tag or `stable/v<version>` branch already exists.
2. It checks the token in the gitignored `.npmrc` and asks for one if the token is missing or rejected. Supply a token with the `write:packages` scope.
3. It rebuilds `lib/`, runs `pnpm version`, then creates and pushes `stable/v<version>`.
4. It runs `pnpm publish --no-git-checks` locally.

Pushing `stable/v<version>` also triggers `.github/workflows/stable_release_workflow.yml`, which publishes the same version. Whichever publish finishes second fails with `EPUBLISHCONFLICT`. The version is published either way, so check the registry before rerunning anything. The repository's `README.md` covers development versions and the version-number rules.

### PreciseRx-Shared-Python

Pushing a `stable/vX.Y.Z` branch makes `.github/workflows/stable_release_workflow.yml` tag the commit `vX.Y.Z`. Nothing is published to a registry. Consumers pin a git reference instead:

- Database pins the tag `v1.0.0` (`PreciseRx-Database/requirements.txt:14`).
- GenAI pins the branch `feature/rx-2857` (`PreciseRx-GenAI/pyproject.toml:17`). That branch no longer exists on the remote. The lock file records the commit it resolved to (`PreciseRx-GenAI/poetry.lock:1187-1191`).

### Consuming a new package version

- The services pin exact versions of the internal packages, for example `@preciserx/pk-library-js` 1.6.1 and `@preciserx/preciserx-shared-js` 1.13.5 (`PreciseRx-Main/package.json:23-24`). Nothing picks up a release automatically.
- Bump the version in each dependent `package.json`, run `pnpm install`, and commit the updated `pnpm-lock.yaml`.
- The services exempt the internal packages from the 72-hour release quarantine, so a fresh release installs immediately (`PreciseRx-Main/pnpm-workspace.yaml:5-8`).
- Do not rely on the `latest` or `dev` dist-tags. Both packages set `publishConfig.tag` to `dev`, but the Shared-JS `README.md` records that the tags have drifted.

## Dependency and security automation

- Dependabot opens daily version updates in the frontend, the Node services, Database, PK-Library and Shared-JS (`.github/dependabot.yml` in each).
- The frontend, the Node services and Shared-JS set a 3-day Dependabot cooldown. It mirrors pnpm's 72-hour quarantine, which Dependabot does not read (`PreciseRx-Web/.github/dependabot.yml:10-14`). The services exclude `@preciserx/*` from the cooldown.
- The Node services and Shared-JS ignore major ESLint updates, because `eslint-config-airbnb` 19 requires ESLint 8 (`PreciseRx-Main/.github/dependabot.yml:21-24`).
- Every pnpm repository hardens installs in its `pnpm-workspace.yaml`. It sets `minimumReleaseAge: 4320`, allows install scripts only for listed packages (`allowBuilds`), verifies store integrity, and enforces `engines`. CVE fixes for transitive dependencies go into `overrides` there (for example `PreciseRx-Web/pnpm-workspace.yaml:20-24`).
- CodeQL runs only in PK-Library.

## Jenkins server operations

This section is for whoever maintains the Jenkins servers. Hostnames, addresses, keys and tokens are not recorded here. The Jenkins credential store holds the GitHub and Docker Hub credentials, and the Slack plugin configuration holds the Slack token.

### Topology

| Server | Operating system and instance | Network | Role |
| --- | --- | --- | --- |
| Controller | Amazon Linux 2023, arm64, a small burstable instance (`t4g.micro`) with at least 20 GB of disk | Public subnet in the Jenkins VPC. Engineers reach it only from the office and VPN address ranges. | Serves the web UI on port 8080 behind a load-balancer target group, and schedules jobs. It runs no builds. |
| Agent | Amazon Linux 2023, arm64, at least 2 GB of RAM (`t4g.small`) and about 60 GB of disk | Private subnet. It accepts traffic only from the controller. | Builds and pushes the Docker images. |

- To move the Jenkins hostname to a new controller, replace the instance registered in the load balancer's target group, on port 8080.
- The controller and the agents use separate EC2 key pairs. One lets engineers reach the controller, and the other lets the controller reach the agents.
- An agent has no public address. Reach it by SSH from the controller, or through an [EC2 Instance Connect Endpoint](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-with-ec2-instance-connect-endpoint.html).

### Controller setup

1. Install Java and git with `sudo dnf install -y java-17-amazon-corretto git`. Check the [Java support policy](https://www.jenkins.io/doc/book/platform-information/support-policy-java/) before any Jenkins upgrade, because Jenkins drops older Java versions.
2. Install Jenkins with the [Red Hat-family steps](https://www.jenkins.io/doc/book/installing/linux/#red-hat-centos), which give the current repository key. Then enable and start it with `sudo systemctl enable --now jenkins`.
3. In Manage Jenkins, then System, set the number of executors to 0, so no build runs on the controller ([controller isolation](https://www.jenkins.io/doc/book/security/controller-isolation/)).
4. In Manage Jenkins, then Security, then Agents, set the TCP port for inbound agents to Random.
5. Install the [Slack Notification](https://plugins.jenkins.io/slack/) and [Docker Pipeline](https://plugins.jenkins.io/docker-workflow/) plugins. The Jenkinsfiles call `slackSend`, `docker.withRegistry` and `docker.build`.

### Agent setup

1. Install Java, git and Docker, then let the login user run Docker, and reboot:

```sh
sudo dnf install -y java-17-amazon-corretto git docker
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
sudo reboot
```

2. Create the node in Jenkins with these settings:

| Setting | Value | Why |
| --- | --- | --- |
| Name | `Jenkins-<arch>-Agent`, for example `Jenkins-arm64-Agent` | Names the architecture. |
| Labels | `arm64` | Must match `agent { label 'arm64' }` in every Jenkinsfile. |
| Number of executors | 2 | With a single executor, builds stall waiting for an executor. |
| Launch method | Launch agents via SSH, using the agent key pair and the agent's private IP | The controller then starts the agent process itself. |
| Host key verification | Known hosts file | Rejects an unexpected agent host key. |
| Disk space monitoring thresholds | Lower both free-temp-space thresholds (for example to 100 KiB) | The default thresholds exceed what the agent reports as free, so Jenkins marks it offline and it rejects jobs. |
| Tool locations | Git at `/usr/bin/git` | Without it, pipelines on the agent cannot find `git`. |

### Routine tasks

- If the controller does not come back after a reboot, run `sudo systemctl start jenkins`, and check it with `sudo systemctl status jenkins`.
- If an agent goes offline, relaunch it from its node page. The controller reconnects over SSH.
- When an agent's disk fills with old images, connect to it and run `docker system prune -a`.
- When an Amazon Linux AMI nears its end of support, launch a new instance from the current AMI and move the existing EBS volume to it.
