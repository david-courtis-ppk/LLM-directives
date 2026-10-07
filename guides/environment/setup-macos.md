# Set up a Mac for PrecisePK development

This guide takes a new Mac to the point where the whole PrecisePK stack runs locally: every backend service in Docker behind a local gateway, and the React frontend on a Vite dev server. Read it on your first day, or when `make docker-compose-up` stops working after an AWS or GitHub change. On Windows, start with [setup-windows.md](setup-windows.md), which links back here for the shared steps.

## What you are setting up

PrecisePK lives in two top-level repositories:

- `PreciseRx-Web` is the React frontend.
- `PreciseRx-Web-PK` is the umbrella repository. Its git submodules hold every backend service and shared package, and its `Makefile` and `docker-compose.yml` run them locally.

The local backend is not self-contained. Its containers use the staging AWS account through your single sign-on (SSO) session. That means the staging Cognito user pools, the staging SQS queue, and the shared development database that `RDS_SECRET_ARN` in `.env` points to (`PreciseRx-Database/app/database/secrets.py:160-175`). Other engineers can see anything you create locally.

## Accounts and access

Get these before the first run:

- Ask for membership in the PreciseRx GitHub organization, with read access to its private repositories and packages.
- Ask an IAM Identity Center administrator to assign you the `AWSPowerUserAndSupport` permission set on the PrecisePK staging account. Logging in cannot make up for a missing assignment, and the guard script says so when it detects one (`PreciseRx-Web-PK/scripts/aws-sso-guard.sh:185-198`).
- Ask an administrator with the IAM role to invite you as an app user from the user accounts page (`/iam/user-accounts`), so you can sign in to the local app.

## Install the tools

| Tool | Version | Why it is needed |
| --- | --- | --- |
| Xcode Command Line Tools | current | Compilers for Homebrew and for native Node modules. |
| [Homebrew](https://brew.sh/) | current | Installs the command-line tools below. |
| [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/) | current | Runs the backend. It provides Compose v2 profiles, BuildKit secrets and buildx, which the Makefiles use. |
| AWS CLI | 2.15 or newer | Older versions have no SSO sessions, and the guard script refuses them (`scripts/aws-sso-guard.sh:31-61`). |
| jq | any | Turns the Secrets Manager JSON into `.env`. |
| Node.js | 24 | Every Node repository sets `engines.node` to `>=24` in `package.json`, and pnpm enforces it. |
| pnpm | 11.4.0 | Pinned by `packageManager` in every Node repository. Corepack installs it. |

```sh
xcode-select --install
brew install awscli jq
nvm install 24        # nvm, or any other Node version manager
corepack enable       # activates the pnpm version each repo pins
```

If your Node build has no `corepack` command, install it with `npm install -g corepack`.

Install these only for the work that needs them:

| Task | Extra tools |
| --- | --- |
| Run PK-Library's C++ tests on the host | `brew install cmake ninja ccache`. CMake 3.17 or newer and a C++20 compiler are required (`PK-Library/CMakeLists.txt:1-5`). |
| Run Database tests on the host | Python 3.12 (the version in `PreciseRx-Database/Dockerfile.dev`) and a disposable MySQL 8 server. See [make-commands.md](make-commands.md#preciserx-databasemakefile). |
| Run GenAI outside Docker | [Poetry](https://python-poetry.org/docs/#installation) and Python 3.12 or newer (`PreciseRx-GenAI/pyproject.toml:9`). |

## Get the code

```sh
git clone --recurse-submodules https://github.com/PreciseRx/PreciseRx-Web-PK.git
git clone https://github.com/PreciseRx/PreciseRx-Web.git
cd PreciseRx-Web-PK
make checkout-all main
```

- The clone checks out each submodule at the commit the umbrella last recorded. Those pointers are bumped only occasionally, so they usually lag well behind `main`.
- `make checkout-all main` moves the umbrella and every submodule to `main` and pulls. Do not run `git submodule update` afterwards, because it moves the submodules back to the recorded commits.
- Expect one `!! Failed` line for PK-Library's nested `third-party/eigen` submodule. Eigen has no `main` branch, so it stays on its recorded commit, which is what you want.
- The submodule URLs use HTTPS (`PreciseRx-Web-PK/.gitmodules`). If you use SSH keys for GitHub, either set up an HTTPS credential helper (`gh auth login`, then `gh auth setup-git`) or rewrite the URLs with `git config --global url."git@github.com:".insteadOf "https://github.com/"`.

## Sign in to AWS

Local development uses the AWS profile `precisepk-staging-developer`, which signs in through IAM Identity Center. Long-lived access keys in `~/.aws/credentials` are not used.

1. Run `make docker-compose-up` in `PreciseRx-Web-PK`. Before touching AWS it runs `scripts/aws-sso-guard.sh`.
2. If the profile is missing, the script offers to append it, plus a shared `[sso-session preciserx-sso]` block, to `~/.aws/config` (`scripts/aws-sso-guard.sh:90-141`). Answer `Y`. If you decline, it prints the exact block to paste, including the start URL and account ID.
3. The script never logs you in. Log in, then rerun the make command:

```sh
aws sso login --profile precisepk-staging-developer
make docker-compose-up
```

- Log in again whenever the session expires. The containers mount your `~/.aws` and select the same profile (`docker-compose.yml:20-22`), so they depend on this session too.
- Both Makefiles pin the profile with `=`, so an exported `AWS_PROFILE` is ignored (`PreciseRx-Web-PK/Makefile:87-89`). To use a different profile, pass it on the command line: `make AWS_PROFILE=<profile> docker-compose-up`.

## Create the GitHub token

The services install the private packages `@preciserx/pk-library-js` and `@preciserx/preciserx-shared-js` from GitHub Packages. The Database and GenAI images also clone the private `PreciseRx-Shared-Python` repository (`PreciseRx-Database/Dockerfile.dev:17-21`, `PreciseRx-GenAI/Dockerfile.dev:21-37`). One token covers both.

1. Create a [personal access token (classic)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic) with the `read:packages` and `repo` scopes. The GitHub Packages npm registry accepts only classic tokens. The `repo` scope lets the image builds clone `PreciseRx-Shared-Python`.
2. Run any `docker-compose-up` target. On the first run it creates `PreciseRx-Web-PK/.git-token`, asks for the token, saves it and exits (`Makefile:267-272`). Run the command again.
3. Every run checks the token against GitHub's packages API. If the check fails, it asks for a new token and exits again (`Makefile:309-325`).

`.git-token` is gitignored. Compose passes it to every image build as the BuildKit secret `git_token` (`docker-compose.yml:223-225`), and the Makefile exports it as `GIT_TOKEN` for its own targets (`Makefile:70`). Each service's `.npmrc` reads `${GIT_TOKEN}`, so export it yourself before running `pnpm install` by hand in a service directory:

```sh
export GIT_TOKEN="$(cat <path-to>/PreciseRx-Web-PK/.git-token)"
```

The frontend has no private dependencies and needs no token. [github-packages.md](../git/github-packages.md) explains how CI, Docker and Jenkins use the token.

## First run

```sh
cd PreciseRx-Web-PK
make docker-compose-up
```

The target checks your AWS session, writes `.env` from the Secrets Manager secret `Development-Server-Secrets` if `.env` does not exist yet, checks the GitHub token, then builds and starts the containers in the foreground (`Makefile:231-238`). Press Ctrl-C to stop them.

- The gateway listens on `http://localhost` (port 80). It routes `/main/v1`, `/database/v1`, `/databridge/v1`, `/analysis/v1` and `/gen-ai/v1` to the services (`src/services/nginx/conf.d/`).
- `.env` is written only once. Add `reset_env=true` to fetch it again after someone changes the secret. The fetch replaces `.env` only when it succeeds (`Makefile:279-305`).
- Use `make docker-compose-up-core` to skip Databridge and save memory. [make-commands.md](make-commands.md) lists every target and container.
- Node services reload on save through nodemon, which watches their `src` folders and the shared packages (`PreciseRx-Main/nodemon.json`). Database runs gunicorn without reload, so run `docker restart DB-Server` after a Python change.

## Start the frontend

```sh
cd PreciseRx-Web
pnpm install
make generate-env     # writes .env from Development-Client-Secrets
pnpm start            # Vite on http://localhost:3000
```

- `make start-development` runs the last two steps together.
- In development the app always calls the local gateway at `http://localhost/` (`PreciseRx-Web/src/utils/utils.ts:40-53`). Start the backend first.
- The frontend's `package.json` version must equal Main's `package.json` version exactly, including the patch number. Otherwise the app shows an upgrade-required state instead of loading (`src/utils/utils.ts:18-33`, `src/hooks/withAuth.tsx:107-115`, `PreciseRx-Main/src/controllers/main/get-status.js`). Keep the frontend and the umbrella on matching branches.
- `pnpm test` runs Vitest, which stays in watch mode in an interactive terminal. Add `--run` for a single pass. `pnpm typecheck` runs the TypeScript compiler without emitting.

## Editor and browser

- Open the `PreciseRx-Web-PK` folder itself in VS Code. Its `.vscode/settings.json` sets up the Jest extension for Main, Analytics and Databridge (`pnpm test --`), C++ TestMate and CMake Tools for PK-Library, and Black formatting on save for Python.
- Do not use `.vscode/PreciseRx-Web-PK.code-workspace`. It lists a `PreciseRx-Fhir` folder that no longer exists and omits Databridge, GenAI and the shared packages.
- The C/C++ settings expect Homebrew GCC 14 at `/opt/homebrew/bin/g++-14` (`.vscode/settings.json:134`). Run `brew install gcc@14`, or override `C_Cpp.default.compilerPath` in your user settings.
- Install the React Developer Tools and Redux DevTools browser extensions. The store enables Redux DevTools in every environment except production (`PreciseRx-Web/src/store.ts:42-54`).

## Common failures

| Symptom | Cause and fix |
| --- | --- |
| `No AWS profile named 'precisepk-staging-developer'` | The profile is missing. Accept the guard script's offer, or paste the block it prints into `~/.aws/config`. |
| `No active AWS session for profile ...` | The session expired or never started. Run `aws sso login --profile precisepk-staging-developer`, then rerun. |
| `AWS refused to issue credentials` | Your sign-in works, but the permission set is not assigned to you. Logging in again will not help. Ask an IAM Identity Center administrator. |
| `Profile ... authenticates to account ..., not Staging` | The profile points at another account. Correct `sso_account_id` using the block the script prints. |
| `AWS CLI 2.15 or newer is required` or `jq is not installed` | Run `brew upgrade awscli` or `brew install jq`. |
| `PAT is invalid.` and the command exits | The token expired or lacks `read:packages`. Paste a new token at the prompt, then rerun. |
| The DB-Server or Gen-AI-Server image build fails while cloning `PreciseRx-Shared-Python` | The token lacks the `repo` scope. Create a new one and save it with `make input-git-pat`. |
| `could not generate .env ... value(s) contain # or a newline` | A secret value contains a character that `.env` parsers truncate. Your existing `.env` is untouched. Ask the secret's owner to change the value. |
| A new secret value never reaches the containers | `.env` is written only once. Rerun with `reset_env=true`. |
| `ERR_PNPM_UNSUPPORTED_ENGINE` | Your Node version is older than 24. Run `nvm use 24`. |
| `401` from `npm.pkg.github.com` during a manual `pnpm install` | `GIT_TOKEN` is not exported in that shell. Export it as shown above. |
| pnpm cannot find a version published in the last three days | Every pnpm repository sets `minimumReleaseAge: 4320`, a 72-hour quarantine on new public releases (for example `PreciseRx-Web/pnpm-workspace.yaml:5`). Wait, or choose an older version. The services exempt the internal `@preciserx` packages. |
| The gateway container fails with `Bind for 0.0.0.0:80 failed` | Another process holds port 80. Find it with `sudo lsof -i :80` and stop it. |
| The frontend shows an upgrade-required screen | The frontend and Main versions differ. Check out matching branches in both repositories. |
