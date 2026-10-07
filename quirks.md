# Quirks

Facts that are hard to find from the code alone.

## GenAI needs OpenAI and Logfire keys that no dev secret holds

The GenAI service reads `OPENAI_API_KEY` and `LOGFIRE_TOKEN` (`PreciseRx-GenAI/preciserx_genai/config.py:58-62`). Neither key is in `Development-Server-Secrets`, the secret that `make generate-env-file` copies into the umbrella's `.env`. The GenAI README says to add the OpenAI key to `.env.local` but not where to get it (`PreciseRx-GenAI/README.md:8`).

The Staging GenAI task (ECS task definition `genai-staging-task:45`) reads both keys from the Secrets Manager secret `preciserx/staging/server/env-vars` in the Staging account. The `precisepk-staging-developer` profile can read it. From the umbrella root:

```sh
aws secretsmanager get-secret-value --profile precisepk-staging-developer \
    --secret-id preciserx/staging/server/env-vars --query SecretString --output text \
    | jq -r '"OPENAI_API_KEY=\(.OPENAI_API_KEY)", "LOGFIRE_TOKEN=\(.LOGFIRE_TOKEN)"' >> .env.local
```

- These are the Staging server's keys. Prefer your own OpenAI key: ask to be added to the team's OpenAI project, create a personal key there, and put it in `.env.local` in place of the server's. Usage then shows under your name, not the key creator's.
- Local OpenAI usage bills to the same account as the server. On startup, GenAI printed `kenny/starter-project` as the Logfire project for this token (2026-09-28), so local traces land in that project. It is unconfirmed whether the team intends this or keeps separate development keys.
- The OpenAI account behind that key is prepaid, and Staging and Preview share it. On 2026-09-28, an eval sweep of about 4,000 model and judge calls, about $40 on OpenAI's dashboard, used up its remaining credits. That broke the deployed assistant. Get a separate key or budget before running large evals.
- On `feature/rx-2901`, `docker-compose.yml` lists `.env.local` as an `env_file` for the Gen-AI server. Compose refuses to start if the file is missing, so create it even when it is empty.
- The GenAI Makefile loads only its own `src/apis/PreciseRx-GenAI/.env`, not the umbrella's files. To run `make run-support-evals` from the host, run `make generate-env-files` in the GenAI directory and append the two keys to that `.env`.
