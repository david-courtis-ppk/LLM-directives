# Local population models

A local population model refits a published PK model's covariate coefficients to one institution's patients, so that institution gets better starting estimates before Bayesian fitting. This guide covers how PK-Library fits the coefficients, where the Database service stores them, how Main and the frontend apply them as the "Local" prior, and how an institution gets one. Read it before you build a local model or change any of these code paths.

Paths are prefixed with their repository. PK-Library lives at `src/packages/cpp/PK-Library` in the umbrella repository, and Main and Database live under `src/apis/`.

## What a local model changes

A population PK model has three parts. The structural model is the compartments and their equations. The covariate model is the set of formulas that turn patient covariates into typical parameter values, through coefficients. The statistical model is the between-patient variability and residual error.

A local model keeps the structure and the formulas and replaces only the coefficients. The prior spreads stay those of the published model. For example, Rodvold 1988 clearance keeps its prior CV of 0.5 whatever the coefficients are (`PK-Library/src/pharmacokinetics/study/vancomycin/vancomycinrodvold1988.hpp:45`).

A model can be refit only if it overrides `Model::coefficients()` with at least one coefficient for every fitted parameter. Rodvold 1988, for instance, declares `CRCL` and `ADJUSTED_WEIGHT` for CL and `DOSING_WEIGHT` for Vdβ (`vancomycinrodvold1988.hpp:20-28`). The base class declares empty maps, which makes fitting throw (`PK-Library/src/pharmacokinetics/model/model.cpp:321-326`). `Model::can_fit()` also exists, but nothing reads it.

## How the coefficients are fitted

The Node binding `fit_population(drugName, modelName, cases)` takes one entry per case with `patient`, `general_prior_pk` (the published-model prior) and `general_post_pk` (that patient's individual Bayesian fit). It returns `{ coefficients }` and uses default engine settings, not the institution's (`PK-Library/bindings/nodejs/pklibraryjs.cpp:1861-1903`).

`PopulationFittingRegress` then runs one Bayesian linear regression per fitted parameter (`PK-Library/src/pharmacokinetics/bayesianfitting/populationfitting_regress.cpp:30-95`):

```math
\mathbf{y} = X\boldsymbol{\gamma} + \boldsymbol{\varepsilon},
\qquad
\boldsymbol{\gamma} \sim \mathcal{N}(\boldsymbol{\mu}_0,\ \Sigma_0),
\qquad
\Sigma_0 = 0.1\,I_K
```

Where:

- **y** is the vector of n individual fitted values of one parameter, such as each patient's fitted CL.
- X is the n × K design matrix. Entry X_ij is patient i's value of covariate j, read by `BayesCoefficient::get`.
- **γ** is the vector of K coefficients being estimated.
- **ε** is the residual, with variance σ².
- **μ**_0 is the published model's coefficients, used as the prior mean.
- Σ_0 is the prior covariance, and I_K is the K × K identity matrix.
- n is the number of cases and K the number of covariates for that parameter.

```math
\hat\sigma^2 = \max\!\left(\frac{\lVert \mathbf{y} - X\boldsymbol{\mu}_0 \rVert^2}{n - K},\ 10^{-6}\right)
```

Where σ̂² is the residual variance estimate, computed from the residuals of the prior-mean coefficients, and **y**, X, **μ**_0, n and K are as above.

```math
\Sigma = \left(\frac{X^\top X}{\hat\sigma^2} + \Sigma_0^{-1}\right)^{-1},
\qquad
\boldsymbol{\mu} = \Sigma\left(\frac{X^\top \mathbf{y}}{\hat\sigma^2} + \Sigma_0^{-1}\boldsymbol{\mu}_0\right),
\qquad
\mathrm{RSD}_j = \frac{\sqrt{\Sigma_{jj}}}{\mu_j}
```

Where:

- Σ is the posterior covariance of the coefficients, and Σ_jj its j-th diagonal entry.
- **μ** is the posterior mean, which becomes the local coefficients, and μ_j is its j-th entry.
- RSD_j is the relative standard deviation returned for coefficient j.

Behaviour the formulas do not show:

- Fitting throws unless n > K for every parameter (`populationfitting_regress.cpp:39-41`).
- σ̂² is estimated once. The loop is written to iterate, but it sets the previous value equal to the new one before the convergence check, so it always stops after one pass (`populationfitting_regress.cpp:74-81`).
- Σ_0 is 0.1 in absolute units whatever the coefficient's scale (`populationfitting_regress.cpp:46`). For Rodvold's CrCl slope of 0.0474, a prior SD of about 0.32 barely constrains the fit.
- The regression has no intercept unless the model declares a `CONSTANT` coefficient, which `get` evaluates as 1.
- The covariates `get` supports are `CRCL` (the latest CrCl, not a time-varying one), `SCR`, `ADJ_W`, `DOSING_W`, `AGE`, `TBW`, `CONSTANT` and `IS_CRITICALLY_ILL`. Any other name throws (`PK-Library/src/pharmacokinetics/model/bayescoefficient.cpp:24-47`).
- The regression treats each formula as purely linear in its coefficients. Branches outside the coefficients, such as Rodvold's ICU multiplier of 1.13 on Vdβ or its Tan 1990 volume for adults with CrCl below 10 mL/min, are not modelled.
- The regression fits individual fitted parameters, not measured levels, so it never checks serum-level predictions after the individual fits.
- On synthetic Rodvold 1988 data, the fit recovers the true coefficients within 10% only from 3,000 patients up. The 100, 1,000 and 2,000 patient cases are expected to miss (`PK-Library/test/populationfitting.test.cpp:102-166`). Established population methods such as FOCE and SAEM, as used by NONMEM and Monolix, estimate from the levels directly and are the standard alternative.

## Where local models are stored

Local models live in two tables in each institution's own schema.

| Table | Columns | ORM |
| --- | --- | --- |
| `models` | `ID`; `DRUG_ID`, the PK-Library drug name such as `Vancomycin`; `MODEL`, the published model it refits, such as `Rodvold 1988`; `SAMPLE_SIZE`; `DATE_FITTED` | `PreciseRx-Database/app/models/hospital/models.py` |
| `coefficients` | `MODEL_ID`, which cascades on delete; `PK`, the parameter such as `CL`; `COEFFICIENT`, such as `CRCL`; `VALUE` | `PreciseRx-Database/app/models/hospital/coefficients.py` |

Only the coefficient value is stored. The RSD the fit returns is dropped.

Database routes (service-relative paths; the frontend adds `database/<version>`, see `PreciseRx-Web/src/actions/AxiosRequestWrappers/Constants.ts:25-31`):

| Method | Path | Auth | What it does | Source |
| --- | --- | --- | --- | --- |
| POST | `/population/model` | User or admin role | Saves a model and its coefficients into the caller's institution schema. The body is `{ model: { drug, name, sample_size }, coefficients: [{ pk, coefficient, value }] }`, and `DATE_FITTED` is set to now. | `app/routes/dataaccess/save/post_population_model.py:9-26` |
| GET | `/population/local_models?drugName=` | User or admin role | Lists the institution's local models for a drug. | `app/routes/dataaccess/localpopulation.py:30-36` |
| GET | `/population/models?model=` | User or admin role | Lists local models that refit a given published model. | `app/routes/dataaccess/localpopulation.py:21-27` |
| GET | `/population/coefficients?model_id=` | User or admin role | Returns one local model's coefficients. | `app/routes/dataaccess/localpopulation.py:10-18` |
| POST | `/cases/load_case` | User or admin role | Returns the drug's local models as `drug.local_pop_models`. | `app/routes/dataaccess/cases.py:226-229` |

- Any user with the user role can save a local model for the whole institution. The save writes no audit row, because the handler sets no audit action (`PreciseRx-Database/app/middlewares/edithistory.py:76-92`).
- Engine and route names must match exactly. The frontend matches `MODEL` against the selected model's name, and Database matches `DRUG_ID` against the drug name.

## How the Local prior is applied

1. When the frontend loads models for a case, it also fetches `GET /population/local_models` for the drug (`PreciseRx-Web/src/actions/DrugActions.ts:175-190`, called from `src/actions/PKParametersActions.ts:418-432`).
2. The PK prior selector offers "Local Population (Local patient data based)" only when a local model exists for the currently selected published model (`src/components/User/PatientInformation/Models/PKPriorSelection.tsx:57-69`).
3. Choosing it selects the local model with the largest sample size and turns off model auto-select (`src/components/User/PatientInformation/Models/Models.tsx:360-368, 400-402`).
4. The frontend posts the drug, patient and settings to Main's `POST /pharmacokinetics/local-population`, with the local model's ID in `drug.selected_model.id` (`src/actions/PKParametersActions.ts:183-224, 277-288`).
5. Main fetches that model's coefficients from Database, computes the published-model PK as `theoretical`, computes the local PK with `calculate_pk_from_coefficients`, and returns `{ theoretical, derivedParams }` (`PreciseRx-Main/src/controllers/pharmacokinetics/post-local-population.js:26-60`).
6. The frontend stores the local PK as the prior, then runs the Bayesian fit on it as usual (`src/actions/PKParametersActions.ts:204-216, 287`).

Things that break silently:

- The stored coefficients replace the model's defaults entirely (`PK-Library/src/pharmacokinetics/model/bayescontainer.cpp:12-15`). A local model must include every coefficient the model's formulas read, or the engine throws on the missing key.
- Stored coefficient names must parse. `BayesCoefficient::from_string` accepts `CL`, `CRCL`, `SCR`, `ADJUSTED_WEIGHT`, `DOSING_WEIGHT`, `AGE`, `TRUE_BODY_WEIGHT`, `Q`, `NONRENAL` and `SEX`, and throws on anything else, including `CONSTANT` and `IS_CRITICALLY_ILL` (`bayescoefficient.cpp:68-80`).
- The binding catches engine exceptions and returns an empty object, logging only to stderr (`PK-Library/bindings/nodejs/pklibraryjs.cpp:719-743`). Main does not turn that into an HTTP error.

## How an institution gets a local model

Nothing in Web, Main, Analytics or Databridge calls `fit_population` or `POST /population/model`. Building a local model is a manual, offline step:

1. Extract the institution's cases for one drug and one published model: each case's patient, general-population prior PK and individual Bayesian fit. This data is PHI, so work only in an approved environment and prefer a de-identified extract.
2. Run `fit_population` with the PK-Library drug name and published model name.
3. Save the result with `POST /population/model`, authenticated as a user of that institution, because the route writes into the caller's schema. Use the exact PK-Library drug and model names.
4. Open a case for that drug and model and confirm the Local option appears and produces the expected prior.
