# PrecisePK onboarding

This guide explains what PrecisePK is, which repositories make it up, what each one is built with, and how work is tracked. Read it on your first day, then follow the links to the setup, Git and frontend guides.

## What PrecisePK is

PrecisePK is clinical dosing software for therapeutic drug monitoring. A pharmacist enters a patient, a drug, the doses given and the measured blood levels. The software estimates that patient's pharmacokinetics, meaning how their body distributes and clears the drug, and recommends a regimen that reaches a target such as a trough level or an AUC (area under the concentration-time curve).

All of that maths lives in one C++ library, PK-Library, which supports 28 drugs (`src/drug/drug.cpp:176-207` in PK-Library). The other repositories store cases, sign people in, import data from hospital EHRs (electronic health records), draw the charts and report on patient populations.

PrecisePK is the product name users see. It is the page title (`index.html`) and the package name (`package.json`) of the web app. PreciseRx is the name of the GitHub organization, of the repositories (`PreciseRx-*`) and of the private packages (`@preciserx/*`). Population reporting is not a separate application. It ships inside the same web app as the Analytics section.

The web app has these areas, declared in `src/routes.tsx` in PreciseRx-Web:

| Area | Routes | What it is for |
| --- | --- | --- |
| User | `/home`, `/patient-info`, `/drug-monitoring`, `/steady-state-analysis`, `/settings` | The clinical workflow for one patient case. |
| Admin | `/admin/*` | Institution settings, dosing protocols, edit history and the patient database. |
| IAM (identity and access management) | `/iam/user-accounts` | Creating and managing user accounts. |
| Analytics | `/analytics/model-analytics`, `/analytics/advanced-analytics`, `/analytics/therapeutic-settings` | Model accuracy and population reports. |
| EHR import | `/ehr` | The wizard that imports a patient from Epic, Oracle Health or Sentri7. |

## Repositories

The frontend is its own repository. Everything else is a git submodule of the umbrella repository PreciseRx-Web-PK.

| Repository | Path in the umbrella | Built with | What it does |
| --- | --- | --- | --- |
| PreciseRx-Web | separate repository | TypeScript, React 18, Vite 7 | The browser app clinicians use. |
| PreciseRx-Web-PK | umbrella root | Make, Docker Compose, nginx | Runs the whole backend locally behind one gateway on `http://localhost`. |
| PreciseRx-Main | `src/apis/PreciseRx-Main` | JavaScript, Express 4 | Dosing calculations through PK-Library, sign-in and user administration. |
| PreciseRx-Database | `src/apis/PreciseRx-Database` | Python 3.12, Flask 3, SQLAlchemy 2 | Stores patients, cases, settings and licenses in MySQL. |
| PreciseRx-Databridge | `src/apis/PreciseRx-Databridge` | JavaScript, Express 4 | Handles Epic and Oracle Health launches and the Sentri7 import, and maps imported data into a case. |
| PreciseRx-Analytics | `src/apis/PreciseRx-Analytics` | JavaScript, Express 4, Socket.IO | Serves population reports, and runs a worker that back-tests model accuracy (`src/workers/predict-serum-level`). |
| PreciseRx-GenAI | `src/apis/PreciseRx-GenAI` | Python 3.12, FastAPI, Poetry | An early proof of concept for an LLM assistant. |
| PK-Library | `src/packages/cpp/PK-Library` | C++20, CMake | The pharmacokinetic engine, published to the Node services as `@preciserx/pk-library-js`. |
| PreciseRx-Shared-JS | `src/packages/node/PreciseRx-Shared-JS` | TypeScript | Cognito token checks, cookies, logging and error middleware shared by the Node services. |
| PreciseRx-Shared-Python | `src/packages/python/PreciseRx-Shared-Python` | Python | Error classes and a Flask error handler. |

- There is no ML server repository. The frontend still defines a `machine_learning/` API prefix (`src/actions/AxiosRequestWrappers/Constants.ts:30` in PreciseRx-Web), but no gateway route serves it.
- The umbrella's `.gitmodules` also lists PreciseRx-QtSimpleCrypt. The umbrella does not record it as a submodule, so it is never checked out.

## Stack

| Layer | What is used | Where it is set |
| --- | --- | --- |
| Package manager | pnpm 11 and Node 24 or newer in every JavaScript repository. Installs refuse packages published less than 72 hours ago, run install scripts only for an allowlist, and verify the store's integrity. | `packageManager` and `engines` in each `package.json`; `pnpm-workspace.yaml` |
| Frontend | React 18.2, TypeScript 5.8, Vite 7, Chakra UI 2.8, Redux Toolkit 1.9 with hand-written reducers and thunks, react-router 6, i18next, Datadog RUM. Tests use Vitest 4, Testing Library and MSW 2. | PreciseRx-Web `package.json` |
| Node services | CommonJS JavaScript, Express 4 and Jest 30. Main also uses supertest. Main, Analytics and Databridge pin `@preciserx/pk-library-js` 1.6.1. | Each service's `package.json` |
| Database service | Python 3.12, Flask 3.1, SQLAlchemy 2.0, PyMySQL, gunicorn and pytest. Its tests drop and recreate the local MySQL databases. | `requirements.txt`, `Dockerfile` |
| GenAI service | Python 3.12, FastAPI and uvicorn, managed with Poetry. | `pyproject.toml` |
| PK-Library | C++20 built with CMake, Ninja and ccache, tested with GoogleTest. A node-addon-api binding is published as `@preciserx/pk-library-js`. Formatting follows its own `.clang-format`. | `CMakeLists.txt`, `Makefile`, `.clang-format` |
| Private packages | `@preciserx/*` packages come from GitHub Packages. Installing them needs a GitHub token with `read:packages`. The frontend has no private dependencies. | See [GitHub Packages](git/github-packages.md). |
| Hosting | AWS Amplify builds and hosts the frontend. The backend services run on ECS behind WAF, API Gateway, a VPC Link and an internal load balancer. Sign-in uses Cognito user pools. | `amplify.yml`; the comment at `src/controllers/index.js:45` in PreciseRx-Main |
| CI and images | GitHub Actions builds and tests pull requests. Jenkins builds and pushes the backend Docker images when someone starts a job. The ECS deployment itself is defined outside these repositories. | See [CI/CD](platform/ci-cd.md). |

## Getting set up

- Follow [Set up a Mac](environment/setup-macos.md) or [Set up Windows](environment/setup-windows.md) to get the whole stack running locally.
- Sign in to AWS through IAM Identity Center with `aws sso login --profile precisepk-staging-developer`. Long-lived access keys in `~/.aws/credentials` are no longer used.
- Use [Make commands](environment/make-commands.md) as the reference for the umbrella's targets, such as `make docker-compose-up` and `make checkout-all`.
- Read the frontend guides before changing PreciseRx-Web: [React](frontend/react.md), [Redux](frontend/redux.md), [Testing](frontend/testing.md), [ESLint](frontend/eslint.md) and [JSDoc](frontend/jsdoc.md).

## How work is tracked

- Development work lives in the RX Jira project, named "PrecisePK Development Board". Its keys look like `RX-3682`.
- RX issue types include Story, Bug, Investigation and Subtask. An Investigation is a spike whose outcome should be follow-up stories or bugs.
- Fixes found while testing a release are named `BLITZ-X.Y.Z-N`, after the release version `X.Y.Z` and a sequence number `N`. Jira has no BLITZ project, so a BLITZ name is not a Jira key. It appears in branch names and pull request titles. These fixes land on the release's `stable/vX.Y.Z` branch first and are then forward-ported to `main`.
- Branch names carry the key in lowercase, for example `feature/rx-3590`, `bug/rx-3691` or `bug/blitz-3.6.0-6`. See [Git branching](git/branching.md) for every branch type and the release flow.
- Pull requests use the template in `.github/pull_request_template.md`, with the sections Issue, Proposed Changes, Additional Info and Checklist. They are squash-merged. The title is a plain-language summary followed by the key, for example `Return -1/0/1 from the patient list sort comparators (RX-3640)`. See [Pull requests](git/pull-requests.md).
- Record decisions you make during a ticket as comments on that ticket, and move the ticket's status as the work progresses.
- File a bug you find outside your ticket's scope as a new RX Bug instead of fixing it on the same branch.
