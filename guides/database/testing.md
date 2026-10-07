# Testing PreciseRx-Database

This guide covers how to run the PreciseRx-Database (Python data API) test suite safely and how to write new tests for it. Read it before you run `make test` for the first time or add a test.

Paths are relative to `src/apis/PreciseRx-Database` in the umbrella repository.

> **Warning: the suite drops and recreates MySQL databases.** Any test that uses the `engine`, `session` or `engines` fixture drops and recreates the databases `testing`, `1683`, `1119` and `1401` on `root:root@127.0.0.1:3306` (`app.ini`, `test/conftest.py:29-41, 134-141`). Run it only against a disposable local MySQL that holds nothing you want to keep. Make sure no tunnel or port-forward to a shared or production database is listening on local port 3306.

## Set up

The suite needs Python 3.12 (the version in `Dockerfile`), the packages in `requirements.txt`, and a throwaway MySQL 8.0 server with user `root` and password `root`, which is what CI uses.

1. Start a disposable MySQL bound to localhost only:

   ```bash
   docker run -d --name rxdb-test -e MYSQL_ROOT_PASSWORD=root -p 127.0.0.1:3306:3306 mysql:8.0
   ```

2. Create a virtual environment and install the requirements:

   ```bash
   python3.12 -m venv .venv && source .venv/bin/activate
   make install-requirements
   ```

   `requirements.txt` installs `PreciseRx-Shared-Python` from a private GitHub repository by git URL (`requirements.txt:14`). Your git credentials must be able to clone it. CI does this by rewriting GitHub URLs with a token (`.github/workflows/unit-test-workflow.yml:23-27`).

3. Remove the container when you are done with `docker rm -f rxdb-test`.

## Run the tests

```bash
make test                         # every test
make test k="site_test.py"        # one file
make test k="test_benchmark_N"    # tests whose names match
```

`make test` runs `python3 -m pytest --envfile ./.env.dev`, and `k` is passed to pytest's `-k` filter (`Makefile:5-10`). `.env.dev` is not checked in. The conftest sets placeholder values for `RDS_SECRET_ARN` and `PPK_CLIENT_URL` so the app factory can start without real configuration (`test/conftest.py:6-9`). Database URLs in tests are hard-coded to the local server (`app.ini`, `app/config.py:11-22`).

CI runs `make test` on every pull request (`.github/workflows/unit-test-workflow.yml`). It starts the runner's own MySQL and creates `testing`, and it also declares a `mysql:8.0` service container with no port mapping, so the tests most likely hit the runner's MySQL.

## Where tests go

| Folder | Holds |
| --- | --- |
| `test/app/` | Tests. Newer tests mirror the current source tree, for example `test/app/routes/dataaccess/site_test.py` for `app/routes/dataaccess/site.py` and `test/app/middlewares/` for `app/middlewares/`. |
| `test/app/main/` | Older tests that mirror the source layout before the 2025 file move (RX-2740). They still run; put new tests in the current-layout folders. |
| `test/testdata/` | Fixtures and generators for reusable data, such as `generate_patient` and `generate_case`. |
| `test/tables/` | Row data for specific tables. |
| `test/example/` | A small example of tests and fixtures. |
| `test/utils.py` | `create_test_app`, which builds a bare Flask app with chosen middlewares, and `assert_route_middlewares`, which checks the chain a route runs. |

There is no pytest configuration file, so pytest's default discovery applies: files named `test_*.py` or `*_test.py`, and functions named `test_*` ([pytest discovery rules](https://docs.pytest.org/en/stable/explanation/goodpractices.html#conventions-for-python-test-discovery)). Both file styles exist in the suite.

## Fixtures

| Fixture | What it gives you | Database it drops |
| --- | --- | --- |
| `engine` | An engine on `testing` with every ORM table created. | `testing` |
| `session` | A session on `testing`, with all `Patient` rows deleted first. | `testing`, through `engine` |
| `mock_app` | A Flask app context with `g.session` set to `session`. | `testing` |
| `mock_site_api`, `mock_iam_api` | A Flask app with the site or IAM blueprint and the error handler registered. | `testing` |
| `engines` | Engines for four schemas: `testing` (keyed as `licenseinfo`), `1683`, `1119` and `1401`. | All four |
| `licenseinfo_session`, `ppk_session`, `ucsd_session`, `ucla_session` | Sessions on those four engines. | All four, through `engines` |
| `mock_aws_lambda_api` | A Flask app context with `g.licenseinfo_session` set. | All four |
| `engine_benchmark`, `session_benchmark` | An engine and session on `1119` without dropping it, for the query benchmarks. | None |

Source: `test/conftest.py`. Two details there are easy to trip on:

- `licenseinfo_session` is defined twice. The second definition, on the `engines` fixture, wins. The first refers to a `licenseinfo_engine` fixture that does not exist (`test/conftest.py:77-82, 144-151`).
- The fixtures are function-scoped, so every test that requests one drops and recreates its databases. That is what makes the MySQL-backed tests slow, so keep them few and focused. The extra `db_setup` step only deletes `Patient` rows (`test/conftest.py:109-111`).

## Writing a test

- Use synthetic data only, through the generators in `test/testdata/`. Never copy real patient data into a test or fixture.
- Prefer a fake session for route logic. `test/app/main/service/dataaccess/license/license_test.py` builds a bare Flask app, sets `g.licenseinfo_session` to a `MagicMock`, and asserts on the response. This needs no MySQL at all.
- Use the `session` fixture when the test needs real SQL, such as a query, a constraint or a cascade.
- Check a route's middleware chain with `assert_route_middlewares` instead of calling the route through real authentication (`test/app/routes/dataaccess/settings_test.py`).
- Call `create_app("testing")` when you need the registered routes. The testing config skips the boot-time Valkey connection (`app/__init__.py:177-186`).

```python
from test.testdata.patient import generate_patient
from app.models.hospital.patient import Patient


def test_saves_a_patient(session):
    session.add(generate_patient(patient_id="MRN-TEST"))
    session.commit()

    assert session.query(Patient).filter(Patient.patient_id == "MRN-TEST").count() == 1
```

## Benchmarks

`test/app/main/model/hospital/benchmark_test.py` uses `pytest-benchmark`. The active benchmarks build their own data on `testing` through the `session` fixture. The query benchmarks further down the file are commented out. They read a pre-loaded schema named `1119` through `session_benchmark`, so running them means uncommenting them and loading a representative dataset into a local `1119`. Use de-identified data only. Any full-suite run drops `1119`, because the `engines` fixture recreates it.
