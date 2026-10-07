# Licensing

This guide explains how a user's license decides which institution's data they reach, when their access expires, and which sites, sign-in types, drugs, features and AI token limits apply. Read it before you change authentication, IAM, the drug list, feature gating, or anything that reads the `custom:license_name` claim.

Paths are prefixed with their repository. Main, Database, Databridge and GenAI live under `src/apis/` in the umbrella repository. Database paths are service-relative; the frontend adds `database/<version>` or `main/<version>` in front (`PreciseRx-Web/src/actions/AxiosRequestWrappers/Constants.ts:25-31`).

## Terms

| Term | Meaning |
| --- | --- |
| Institution | A customer tenant: one row in `licenseinfo.institution`, keyed by `Institution_ID`. |
| Per-institution schema | The MySQL schema that holds one institution's patients, cases, sites and Cognito group rows. Its name is the institution's `Institution_ID`. |
| `licenseinfo` | The shared MySQL schema that holds institutions, licenses and the lookup tables every sign-in path uses. |
| License name | The string stored on every Cognito user as `custom:license_name` and carried in the id token. It encodes the institution and the expiry date. |
| License Tool | `PreciseRx-License-Tool`, a separate repository that creates and changes institutions, licenses and users directly in the database and Cognito (`PreciseRx-Database/app/__init__.py:52-54`). |

## Where license data lives

These repositories contain no migrations or DDL for `licenseinfo`, so the ORM models in `PreciseRx-Database/app/models/licenseinfo/` are the only schema description here. No service in these repositories writes institution, license, drug-package or identity-mapping rows.

| Table | Holds | Read by |
| --- | --- | --- |
| `institution` | `Institution_ID`, `Institution_Name`, `site_type`. | `/license/info`, EHR tenant lookups. |
| `license` | `License_ID`, `Institution_ID`, `License_Name`, `isTrial`, contact fields, `First_Activation`. An institution can have many rows. | The per-request schema lookup and `/license/info`. |
| `license_update` | One row per institution. `New_License_Name` names the current license. | SSO, Sentri7 and EHR lookups. |
| `web_license` | `License_Type` per license. | Returned as `license_type` by `/license/info`. Nothing in Web, Main, Databridge or Analytics reads it. |
| `license_limits` | `Max_Licenses` per license. | Returned as `limit` by `/license/info`. No code in these repositories enforces a user cap. |
| `institution_user_type` | The sign-in types an institution uses. | `/license/info`. |
| `drug`, `institution_drug_package` | Drug names and each institution's allowed drugs. | `/license/drug-package`. |
| `institution_feature_flag` | Feature names enabled per institution. | `/license/assistant-permission`. |
| `federated_identity_provider`, `wk_hospital_identifier`, `ehr_tenant_identifier`, `epic_issuer`, `oracle_health_issuer` | Maps from an external identity to an institution. | SSO, Sentri7, Epic and Oracle Health lookups. |
| `llm_rate_limit`, `llm_usage` | Monthly AI token limits and a log of AI calls. | `/license/tokens/*` and `/license/llm-usage`. |

Each per-institution schema also holds `iam_groups`, whose `TYPE` is one of `All`, `user`, `admin`, `IAM`, `analytics`, `site` or `site_admin` (`PreciseRx-Database/app/models/hospital/iamgroups.py:6-13`), plus `site` and `user_info`.

## The license name

The license name has the form `<institution name> <MM-DD-YYYY>`, and the date is the expiry. There is no separate expiry column. Four places parse it, each in its own way:

| Consumer | What it does | Source |
| --- | --- | --- |
| Database expiry check | Takes the last space-separated word as `MM-DD-YYYY`. Access is valid through the end of that date in the container's local time; the Dockerfiles set no time zone. After that, every request fails with 403 `ExpiredLicenseError`. | `PreciseRx-Database/app/middlewares/validate_token.py:224-232` |
| Database schema lookup | Matches the whole string against `license.License_Name` and uses that row's `Institution_ID` as the schema name. No match fails with 403 `InvalidLicenseError`. The result is cached per process for one hour. | `validate_token.py:207-221` |
| Main feature allowlists | Treats everything before the last space as the institution name. | `PreciseRx-Main/src/feature-whitelist.js:82-94` |
| Web | Strips a trailing space and 10-character token to show the institution name. | `PreciseRx-Web/src/selectors/ProfileSelectors.ts:16-21` |

Consequences to keep in mind:

- A renewal is a new license name, and a user sees the new expiry only after their `custom:license_name` is rewritten and they get a new id token. Databridge rewrites the attribute from `license_update` on every Epic and Oracle Health launch (`PreciseRx-Databridge/src/utilities/epic/utilities.js:335-341`, `src/utilities/oracle-health/utilities.js:190-195`). For email users, nothing in these repositories rewrites it.
- An old license row still resolves to the institution's schema. Only the date in the string stops an expired name.
- A date suffix that does not parse raises an unhandled error in the expiry check, so the request fails as a server error rather than a clean 403.
- Main gives users that an IAM admin invites the admin's own license name (`PreciseRx-Main/src/controllers/iam/users/put-users.js:33-50, 122-142`). IAM actions on another user require both license names to match exactly (`PreciseRx-Main/src/utils/validate-same-license.js`).

## What Database checks on each request

The authenticated chains in `PreciseRx-Database/app/middlewares/before_requests.py` run in this order:

1. The XSS screen checks the body and headers.
2. A `licenseinfo` session opens, on the reader endpoint for GET requests.
3. Token validation verifies both token signatures and that the tokens pair up, then reads `custom:license_name`, checks expiry and resolves the schema (`validate_token.py:54-79, 184-207`).
4. The revocation check rejects disabled or deleted users.
5. The role check runs.
6. A session opens on the institution's schema (`PreciseRx-Database/app/middlewares/session.py:40-63`).
7. The caller's email is resolved.

The frontend calls `GET /license/validation` after it loads the user profile. The route returns 204 when the chain passes, and the frontend shows the error message when it fails (`PreciseRx-Database/app/routes/dataaccess/license/__init__.py:66-68`, `PreciseRx-Web/src/hooks/withAuth.tsx:58-64`, `PreciseRx-Web/src/actions/UserActions.ts:120-148`). The login page and the EHR launch page make the same call (`src/components/Login/Login.tsx:84`, `src/components/ExternalPlatform/ExternalPlatformLogin.tsx:116`).

## License routes

All `/license/*` routes accept any of the user, admin or IAM roles (`PreciseRx-Database/app/__init__.py:98`).

| Method and path | Returns | Source (`license/__init__.py`) |
| --- | --- | --- |
| GET `/license/info` | The license row (name, trial flag, first activation, limit, license type), its institution (ID, name, site type), the institution's sites and user types. | `:21-38` |
| GET `/license/validation` | 204 when the license is valid. | `:66-68` |
| GET `/license/sso/logout-url` | The identity provider's logout URL for an SSO user. | `:41-63` |
| GET `/license/drug-package` | The institution's allowed drug names. | `:125-131` |
| GET `/license/assistant-permission` | `{ enabled }` for the AI assistant. | `:103-122` |
| GET `/license/tokens/usage`, GET `/license/tokens/limit`, POST `/license/llm-usage` | AI token usage, limits and usage logging. See the LLM section below. | `:134-233` |
| GET `/license/limits/<id>`, POST `/license/get_schema_ids` | Always fail. The first calls `.serialize` on a query object, and the second uses `Engine.execute`, which SQLAlchemy 2 removed. | `:71-100` |

## Sign-in paths and the current license

Users who sign in through an identity provider or an EHR are not created with a fixed license name. Their `custom:license_name` comes from `license_update.New_License_Name` for the institution their identity maps to. Database accepts tokens from six Cognito user pools: email, SSO, Sentri7 V1, Sentri7 V2, Epic and Oracle Health (`PreciseRx-Database/app/middlewares/vendor_info.py:31-60`).

| Sign-in path | Mapping table | Database route | Caller |
| --- | --- | --- | --- |
| SSO (SAML) | `federated_identity_provider`, by provider name and entity ID | GET `/aws/lambda/sso-providers/info` | Cognito Lambda triggers outside these repositories, with the Lambda API key. Source: `app/routes/dataaccess/aws_lambda.py:21-80, 149-168`. |
| Sentri7 (Wolters Kluwer) | `wk_hospital_identifier`, by provider name and hospital ID | GET `/aws/lambda/wk-providers/info` | Cognito Lambda triggers. Source: `aws_lambda.py:83-146, 171-190`. |
| Epic | `epic_issuer` validates the issuer; `ehr_tenant_identifier` maps the tenant to an institution | GET `/ehr/epic/issuers`, GET `/ehr/epic/tenants/<tenant_id>/groups` | Databridge, with the Databridge API key. Source: `app/routes/dataaccess/ehr/epic_api.py:49-146`, `ehr/utilities.py:9-50`. |
| Oracle Health | `oracle_health_issuer`; `ehr_tenant_identifier` | GET `/ehr/oracle-health/issuers`, GET `/ehr/oracle-health/tenants/<tenant_id>/groups` | Databridge. Source: `ehr/oracle_health_api.py:18-60`. |

Each lookup returns the current license name and the institution's `iam_groups` rows, which the caller uses to set the user's attribute and Cognito groups.

## Site types

`institution.site_type` is `single` or `multi` (`PreciseRx-Web/src/components/GlobalVariables.ts:652-655`). A multi-site institution splits users and cases into sites. Each site is a row in the institution's `site` table tied to an `iam_groups` row of type `site`.

- Main's `GET /user/information` returns `license.site_type`, `license.sites` and `license.user_types` from `/license/info`. It also returns `site_info`, the first site whose Cognito group the user belongs to, or "Unassigned" (`PreciseRx-Main/src/controllers/user/get-information.js:66-90`).
- The frontend stores these under `profile.license` and turns on site selection and site filters when the type is `multi` (`PreciseRx-Web/src/selectors/ProfileSelectors.ts:7-12`).
- Database does not restrict reads by site. Site filters come from the caller, and a case loads by its number alone (`PreciseRx-Database/app/routes/dataaccess/cases.py:196-202`).

## User types

`institution_user_type` records which sign-in types an institution uses. The values are `email`, `sso`, `wolters_kluwer`, `wolters_kluwer_v2`, `oracle_health` and `epic` (`PreciseRx-Web/src/components/IAM/Constants.ts:54-61`). Database returns them through `/license/info`, cached per process for one hour (`PreciseRx-Database/app/services/institution/institution_service.py:52-70`).

The frontend uses them for one check. When a multi-site institution has both `email` and `epic` users, editing a user's groups asks Main to refuse assignment to an Epic facility's site group (`PreciseRx-Web/src/components/IAM/UserAccounts/EditUserAttributes/EditUserAttributes.tsx:133-134`, `PreciseRx-Main/src/controllers/iam/user/put-group.js:44-56`).

## Drug packages

A drug package restricts an institution to a subset of the supported drugs, for example for an integration partner that supports fewer drugs or for a smaller commercial tier.

- `licenseinfo.drug` lists drugs by `Drug_ID` and `Drug_Name`. `institution_drug_package` lists the drug IDs each institution may use. An institution with no rows gets every drug.
- Main's `drugFilter` middleware runs on the `/drug` routes. It calls Database `GET /license/drug-package`, which joins the two tables and returns drug names, cached per Database process for one hour. An empty result becomes the full PK-Library list (`PreciseRx-Main/src/middleware/drugFilter.js:6-17`, `PreciseRx-Database/app/services/institution/institution_service.py:28-50`).
- `GET /drug/list` takes PK-Library's supported drugs, applies the feature allowlist below, then keeps only names in the package (`PreciseRx-Main/src/services/drug.js:16-38`).
- Packages are not carried in the token. Main asks Database on every `/drug` request.

Gaps:

- Only the drug list is filtered. `/drug/factors`, `/drug/routes`, `/drug/metadata`, `POST /drug` and every non-`/drug` route accept any drug (`drugFilter.js:15`).
- Matching is by exact name, so `drug.Drug_Name` must equal PK-Library's display name, such as `Levofloxacin/Ofloxacin` (`PK-Library/src/common/pkconstants.cpp:968`). `Drug_ID` values do not need to follow any engine ordering.

## Feature flags and allowlists

Features are gated in five places. Four of them are hard-coded lists, so changing them needs a code change and a deploy.

| Mechanism | Keyed by | Controls | Source |
| --- | --- | --- | --- |
| `institution_feature_flag` row with `feature_name = 'assistant'` | Institution ID | Whether the AI assistant is enabled, through `GET /license/assistant-permission`. | `PreciseRx-Database/app/routes/dataaccess/license/__init__.py:103-122` |
| Drug allowlist | Institution name from the license name, per `NODE_ENV` | Teicoplanin, cefepime, linezolid and adalimumab are hidden from the drug list except for listed institutions. In production only the internal development and sales demo institutions are listed; staging adds some customers. Any other `NODE_ENV` value disables the filter. | `PreciseRx-Main/src/feature-whitelist.js:3-6, 39-73, 178-195` |
| Model allowlist | Institution name | The mechanism exists but the list is empty, so no model is hidden. | `feature-whitelist.js:27, 104-168` |
| Sentri7 analytics allowlist | Institution ID | `GET /main/<version>/auth/analytics` returns `true` only for a hard-coded list of institution IDs. Sentri7 users see the analytics apps in the application switcher only when it returns `true`; every other user always sees them. This gate exists only in the frontend. | `PreciseRx-Main/src/controllers/authentication/get-analytics.js:4-28`, `PreciseRx-Web/src/components/Application/ApplicationSwitcher/ApplicationSwitcherPopover.tsx:44-76` |
| EHR import race-factor opt-out | Institution name | Skips the FHIR-derived race drug factor during EHR import for listed institutions. | `PreciseRx-Web/src/components/ExternalPlatform/Constants.ts:22-38` |

The name-keyed lists match the text before the date in the license name. Renaming an institution's license therefore silently removes its access to anything those lists grant.

## LLM token limits

- `llm_rate_limit` holds one row per institution with `user_tokens_per_month`, `institution_tokens_per_month` and `is_active` (`PreciseRx-Database/app/models/licenseinfo/llm_rate_limits.py`).
- `GET /license/tokens/limit` returns `{ license_limit, user_limit: { monthly } }` from the active row, or nulls when there is none so the caller falls back to its own defaults (`license/__init__.py:193-230`).
- `GET /license/tokens/usage` sums input plus output tokens since the start of the current UTC month, for the caller and for the whole institution, and skips calls that recorded an error (`license/__init__.py:134-190`).
- `POST /license/llm-usage` logs one AI call. `endpoint` is required, and the model, token counts, request and tool-call counts, latency and error are optional (`license/post_llm_usage.py:10-80`).
- The GenAI service's `feature/rx-2901` branch calls these routes. GenAI `main` does not.

## Licensing redesign in progress

The licensing overhaul (Jira epic RX-3523) replaces `licenseinfo` with a new `precisepk` schema that has an explicit expiry date and an active-license pointer, and replaces `custom:license_name` with a stable `custom:institution_id` attribute. The work lives on feature branches: `feature/rx-3520`, `feature/rx-3523` and `feature/rx-3527` in Database, and `feature/rx-3523` and `feature/rx-3529` in Main and Databridge. None of it is on `main`, so everything above describes the running system.
