# Make commands

This guide lists the make targets engineers use in each PrecisePK repository, grouped by task. Use it to look up what a target does before you run it. First-time machine setup is in [setup-macos.md](setup-macos.md) and [setup-windows.md](setup-windows.md).

Paths are relative to the repository that owns the Makefile. Submodules live under `PreciseRx-Web-PK/src/`.

## PreciseRx-Web-PK/Makefile (umbrella)

Run these from the umbrella root. `make help` prints the main ones (`Makefile:25-65`).

### Start the local backend

Each target first checks your AWS session, writes `.env` from Secrets Manager if it is missing, and checks your GitHub token (`Makefile:231-233`). It then runs `docker compose up --build --remove-orphans` in the foreground under the project name `preciserx-web-pk`. Press Ctrl-C to stop.

| Target | Compose profile | What starts |
| --- | --- | --- |
| `make docker-compose-up` | `default` | Redis, Main, Database, Analytics, the Analytics worker, Databridge and the gateway. |
| `make docker-compose-up-core` | `core` | The same without Databridge, to save memory. |
| `make docker-compose-up-gen-ai` | `gen-ai` | Everything above plus GenAI. It also reads `.env.local` from the umbrella root (`docker-compose.yml:165-167`), where you put your own `OPENAI_API_KEY` (`PreciseRx-GenAI/README.md`). |

Add `reset_env=true` to any of them to fetch `.env` again, for example `make docker-compose-up reset_env=true`.

| Container | Host port | Built from |
| --- | --- | --- |
| `API-Gateway-Core`, `API-Gateway-All` or `API-Gateway-GenAI` (one per target) | 80 | `src/services/nginx` |
| `Main-Server` | 8000 | `src/apis/PreciseRx-Main/Dockerfile.dev` |
| `DB-Server` | 8001 | `src/apis/PreciseRx-Database/Dockerfile.dev` |
| `Databridge-Server` | 8002 | `src/apis/PreciseRx-Databridge/Dockerfile.dev` |
| `Analytics-Server` | 8003 | `src/apis/PreciseRx-Analytics/src/Dockerfile.dev` |
| `Analytics-Worker` | none | `src/apis/PreciseRx-Analytics/src/workers/predict-serum-level/Dockerfile.dev` |
| `Gen-AI-Server` | 8004 | `src/apis/PreciseRx-GenAI/Dockerfile.dev` |
| `Redis` | 6379 | `redis:alpine` |

The gateway reaches the services through their published host ports, not the Compose network (`src/services/nginx/api_backends.conf:1-29`). Redis is published on `localhost:6379`, so any Redis client can inspect it.

### Use local builds of PK-Library or Shared-JS

The services normally install the published `@preciserx` packages. These targets swap in your local checkout.

| Target | What it does |
| --- | --- |
| `make link-pk-library-js` | Builds your PK-Library checkout for Linux with Docker buildx (`src/packages/cpp/PK-Library/scripts/prebuild-linux/`). It then symlinks it into `Main-Server`, `Analytics-Server` and `Databridge-Server` and restarts them (`Makefile:163-183`). Run it again after each C++ change. |
| `make link-preciserx-shared-js` | Symlinks your Shared-JS checkout into the same three containers, then runs a TypeScript watch build on the host (`Makefile:145-160`). It never exits, so give it its own terminal. |
| `make link-pk-library-js-local` | Builds PK-Library natively on the host, then runs `pnpm link` into Main, Analytics and Databridge for host-side tests (`Makefile:191-196`). The build uses `ccache` with `gcc` and `g++` (`PK-Library/package.json:24`). |
| `make link-shared-js-local` | Installs Shared-JS, then runs `pnpm link` into Main, Analytics and Databridge on the host (`Makefile:185-189`). |
| `make clean-pk-library-js` | Runs PK-Library's own `make clean`. |

- `Analytics-Worker` is not linked. It keeps the published PK-Library.
- The container links live only in each container's writable layer. To return to the published packages, remove the linked containers with `docker rm -f Main-Server Analytics-Server Databridge-Server` and start the stack again.
- `pnpm link` records the link in the target project's `pnpm-workspace.yaml` (see the comment at `Makefile:109-117`). After a host-side link, run `git status` in each service and discard those changes before you commit.

### Run backend tests on the host

| Target | What it does |
| --- | --- |
| `make install-packages` | Runs `pnpm install` in Analytics, Main and Databridge with `GIT_TOKEN` exported from `.git-token` (`Makefile:204-207`). |
| `make prepare-tests` | Runs `install-packages`. Add `link_shared_js=true` or `link_pk_library_js=true` to test against your local packages (`Makefile:211-220`). |

Then run the suites from the VS Code Jest extension, or with `pnpm test` in each service directory. CI runs `pnpm install --frozen-lockfile` and `pnpm test` in the same directories.

### Move every repository to a branch

`make checkout-all <branch> [<branch> ...]` checks out the umbrella and every submodule, recursively, to the first listed branch that exists on `origin`, and pulls it (`Makefile:328-358`). A repository that has none of the branches falls back to `main`.

```sh
make checkout-all main
make checkout-all bugfix/rx-1234 feature/rx-1234   # first match wins in each repository
```

- A checkout fails when uncommitted changes in that repository would be overwritten. The target then prints `!! Failed in <path>` and carries on.
- PK-Library's nested `third-party/eigen` submodule has no `main` branch, so it always prints one `!! Failed` line. That is harmless.
- Commit and open pull requests in each submodule's own repository. The umbrella records submodule commits only when someone bumps the pointers in an umbrella pull request, so its recorded commits lag behind. `git submodule update` would move you back to them.

### Debug and clean up Docker

| Target | What it does |
| --- | --- |
| `make spawn-docker-shell server=<container>` | Opens `/bin/sh` inside a running container, for example `server=Main-Server` (`Makefile:251-252`). |
| `make docker-prune` | Runs `docker system prune`, which removes stopped containers, unused networks, dangling images and build cache. |
| `make docker-prune-all` | Runs `docker system prune -a --volumes`, which also removes every unused image and volume. |
| `sudo make clear_cache` | On WSL only, drops the Linux page cache and compacts memory (`Makefile:225-228`). It needs root. |

### Credential helpers

The start targets call these for you. Run one directly only to repair a single step.

| Target | What it does |
| --- | --- |
| `make check-aws-session` | Runs `scripts/aws-sso-guard.sh`, which checks the AWS CLI, `jq` and your SSO session. |
| `make fetch-env-file` | Always fetches `.env` from the Secrets Manager secret `Development-Server-Secrets`. It replaces `.env` only on success (`Makefile:279-295`). |
| `make generate-env-file` | Fetches `.env` only if it is missing, or when `reset_env=true`. |
| `make check-git-pat` | Creates `.git-token` if needed and checks the token against the GitHub packages API. |
| `make input-git-pat` | Prompts for a new token, writes `.git-token`, then exits with an error so you rerun your command. |

## PreciseRx-Web/Makefile

| Target | What it does |
| --- | --- |
| `make generate-env` | Writes `.env` from `Development-Client-Secrets`. `stage=staging` reads `PreciseRx-Client-Secrets` instead (`Makefile:130-139`). |
| `make AWS_PROFILE=<profile> generate-env stage=production` | Reads `PrecisePK-Client-Secrets`, which lives in the production account, so it needs a production profile (`Makefile:8-19`). |
| `make start-development` | Runs `generate-env` for development, then `pnpm start`. |
| `make check-aws-session` | Checks `aws`, `jq` and your session. Unlike the umbrella's guard, it only prints the profile block and never writes `~/.aws/config` (`Makefile:40-107`). |

Day-to-day frontend work uses the pnpm scripts in `package.json:62-69`: `pnpm start`, `pnpm build`, `pnpm typecheck`, `pnpm test` and `pnpm serve`. The `pnpm docs` script fails because its `jsdoc.json` config file does not exist.

## PK-Library/Makefile

Run these in `src/packages/cpp/PK-Library`. The C++ build needs CMake 3.17 or newer, Ninja, `ccache` and a C++20 compiler. CMake downloads GoogleTest on first configure, and Google Benchmark only for the benchmark targets. Eigen comes from a nested submodule.

| Target | What it does |
| --- | --- |
| `make build-test-cpp` | Configures `build/` with Ninja and builds the library and its GoogleTest suite (`Makefile:23-27`). |
| `make test-cpp` | Runs `build/test/PKLibrary_tst`. To filter, run the binary with `--gtest_filter='<Suite>.*'`. |
| `make build-pk-library-js` | Builds the Node.js binding with `node-gyp rebuild`. Run `pnpm install` first. |
| `make test-pk-library-js` | Runs the binding's Jest tests in `bindings/nodejs_test`. Add `t='<test name>'` to filter. |
| `make build-pk-library-python` | Builds the pybind11 binding into `bindings/python/build`. |
| `make test-pk-library-python` | Builds the Python binding, then runs its pytest suite. Add `k=<expression>` to filter. |
| `make build-benchmark`, `make run-benchmark` | Builds and runs the `PKLibrary_bench` benchmarks. |
| `make build-csv-generator`, `make run-cefepime`, `make run-linezolid` | Builds and runs the CSV generator tools in `tools/csv_generator`. |
| `make clean` | Removes build output, `node_modules` and prebuilds, clears `ccache`, and prunes the buildx cache that `link-pk-library-js` uses (`Makefile:69-79`). It runs one `sudo rm`, so it may ask for your password. |

CI runs `make build-test-cpp` with `make test-cpp`, `make build-pk-library-python` with `make test-pk-library-python`, and `make build-pk-library-js` with `make test-pk-library-js` (`.github/workflows/unit-test-workflow.yml`).

## PreciseRx-Database/Makefile

| Target | What it does |
| --- | --- |
| `make install-requirements` | Runs `pip3 install -r requirements.txt`. The private `PreciseRx-Shared-Python` dependency is cloned over HTTPS (`requirements.txt:14`), so your host git must be able to authenticate to GitHub. The target's token substitution changes nothing, because `requirements.txt` contains no `${GIT_TOKEN}` placeholder. |
| `make test` | Runs pytest with `--envfile ./.env.dev`. Add `k=<expression>` to filter. CI runs it without `.env.dev`, because `test/conftest.py:6-9` supplies the variables the tests need. |

The tests drop and recreate whole MySQL databases, including `testing`, on the server named in `app.ini`, which is `127.0.0.1:3306` as `root` (`test/conftest.py:28-40`). Run them against a disposable MySQL 8 container, the same version CI uses, and never against a shared server:

```sh
docker run -d --name precisepk-test-mysql -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=<the root password in app.ini> mysql:8.0
```

## PreciseRx-Shared-JS/Makefile

| Target | What it does |
| --- | --- |
| `make publish` | Publishes a new version of `@preciserx/preciserx-shared-js`. The full release flow is in [ci-cd.md](../platform/ci-cd.md#preciserx-shared-js). |
| `make check-npmrc-pat`, `make input-npmrc-pat` | Check or replace the token that `make publish` writes into this repository's gitignored `.npmrc`. |

`check-npmrc-pat` prints the token itself in its success and failure messages (`Makefile:52-55`). Do not run it while sharing your screen or in a logged job.

## PreciseRx-GenAI/Makefile

| Target | What it does |
| --- | --- |
| `make start-server` | Runs `poetry install`, then uvicorn with reload on port 3002, outside Docker. Inside the local stack, GenAI runs in `Gen-AI-Server` on port 8004 instead. |
