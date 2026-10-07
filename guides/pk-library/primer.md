# PK-Library primer

This guide explains how PK-Library is put together: its layers, the Drug, model type and study hierarchy, how prior parameters are stored, and how a call from a Node service reaches the C++ code. Read it before you change anything in `src/packages/cpp/PK-Library`, or when you need to find where a calculation lives.

PK-Library is the C++20 dosing engine behind PrecisePK. For one patient and one drug it estimates population pharmacokinetic (PK) parameters from a published study, fits them to measured drug levels, simulates concentration over time, and searches for a dose regimen that hits a target. Main, Analytics and Databridge load it in-process as the Node addon `@preciserx/pk-library-js`. All three pin version 1.6.1 (`PreciseRx-Main/package.json:23`). A pybind11 Python binding lives in `bindings/python/`.

Related guides: [models.md](models.md) covers the maths, [adding-a-drug.md](adding-a-drug.md) the extension points, [error-codes.md](error-codes.md) the failure paths, and [testing-and-debugging.md](testing-and-debugging.md) the build.

## Layers

All paths are relative to `src/packages/cpp/PK-Library`.

| Layer | Folder | What it owns |
| --- | --- | --- |
| Drug | `src/drug/` | One class per drug. Each class lists routes, targets per route, patient factors, units, dose rounding, fitting defaults and infusion-time rules, and picks the study model for a patient. |
| Model type | `src/pharmacokinetics/model/` | The abstract model structures (`Model`, `LinearModel`, `OneCompartment`, `TwoCompartment`, `ThreeCompartment`, `NonLinear`, `NonLinearTwoCompartment`), the numerical simulators, and the parameter containers. |
| Study | `src/pharmacokinetics/study/` | One concrete model per published study. It turns patient covariates into prior values and spreads, and supplies the study's metadata and citations. |
| Closed-form maths | `src/pharmacokinetics/math/` | `LinearPK`, the eigendecomposition solver for N-compartment IV dosing. |
| Fitting | `src/pharmacokinetics/bayesianfitting/` | The Bayesian fit (a hand-written Levenberg-Marquardt optimizer), its loss functions, and population regression. |
| Histories and graphs | `src/pharmacokinetics/graphicanalysis/` | Dose, level and dialysis histories, the concentration graph, level prediction and `FittingSettings`. |
| Steady state | `src/pharmacokinetics/steadystate/` | Steady-state metrics and forecast graphs. |
| Dose prediction | `src/pharmacokinetics/doseprediction/` | `DosageRegimen` (a proposed regimen, with rounding) and `Nomogram`. |
| Targets | `src/pharmacokinetics/therapeutictarget/` | One class per target type, such as AUC24, trough, peak and time above MIC (minimum inhibitory concentration). |
| Patient | `src/patient/`, `src/formulas/` | Body composition, lab report, drug factors and covariates, and the BSA, CrCl (creatinine clearance), eGFR, IBW, LBM and FFM formulas. |
| Settings | `src/settings/` | Institution formula choices and the four protocols: peak time, max dose, default target input and infusion time. |
| Shared | `src/common/`, `src/utils/`, `src/warning/` | `PKConstants`, `PKException`, `Citation`, date handling, units, logging and warnings. |
| Bindings | `bindings/nodejs/`, `bindings/nodejs-v2/`, `bindings/python/` | The Node addon (`pklibraryjs`), the Node `Settings` class, and the Python module. |

Every computed value that a clinician sees carries a `Citation` (`src/common/citation.h:8-15`): a KaTeX formula, the variables used and the sources. That is why most model functions return `std::pair<double, Citation>` rather than a bare `double`.

## Drug, model type and study

Three class families cooperate for every calculation.

- **The drug** (`class Vancomycin : public Drug`) knows everything that does not depend on the study. `Drug::init(name)` is the factory that maps a drug name to its class (`src/drug/drug.cpp:42-77`).
- **The model type** (`class TwoCompartment : public LinearModel`) implements the maths shared by every model with that structure: closed-form concentrations, dose-from-target formulas and the compartment layout used by the simulator.
- **The study** (`class VancomycinRodvold1988`) is the concrete leaf. It implements the "study-specific" functions declared in `model.hpp:248-434`, such as `model_name()`, `fitted_param_names()`, `population_values()` and `derived_parameters()`. It also implements the structural parameters that its model type leaves pure virtual, such as `vc()` and `k21()` for `TwoCompartment` (`twocompartment.h:102-129`).

Some drugs add an intermediate layer between the model type and the study. For example, the vancomycin chain is `VancomycinRodvold1988 : VancomycinTDMS : VancomycinTwoCompartment : TwoCompartment : LinearModel : Model`, and every aminoglycoside uses `AminoglycosideTDMS : OneCompartmentGeneral`. TDMS is the name of the single legacy model that most older drugs use (`PKConstants::Drug::Model::TDMS`).

The drug owns its model as a raw pointer.

- `Drug::_model` starts as `nullptr` (`drug.hpp:39`). `Drug::model()` throws a `runtime_error` until a model is set (`drug.cpp:99-106`).
- `drug->determine_model(patient, name, route)` picks the study. Drugs with several models usually return `name` when it is not empty and otherwise auto-select one for the patient. Single-model drugs always return their one model. `PKConstants::Drug::Model::DEFAULT` is the empty string.
- `drug->set_model(name)` allocates the study with `new`, and `~Drug()` deletes it (`drug.cpp:83-85`). The overrides do not delete a previous model, so call `set_model` once per `Drug` object.
- Each study keeps a `const Drug*` back to its drug (`model.hpp:45`), so model code can read drug settings such as units.

The Node binding always runs the same three steps, which is the pattern to copy in tests (`bindings/nodejs/unraveler.cpp:267-276`):

```cpp
auto drug = Drug::init(store_drug.name);

std::string input_model_name = reset_model ? PKConstants::Drug::Model::DEFAULT : store_drug.model;
std::string model_name = drug->determine_model(patient, input_model_name, store_drug.selected_route);
drug->set_model(model_name);
```

## BayesParameter and BayesContainer

A `BayesParameter` is `{val, sd, citation}` (`src/pharmacokinetics/model/bayesparameter.h:8-12`).

`sd` is a relative standard deviation, that is, a coefficient of variation, even though the header comment calls it "the standard deviation". The code treats it that way everywhere:

- The normal-scale prior penalty divides by `max(sd * val, 0.01 * val)` (`src/pharmacokinetics/bayesianfitting/param_loss_v1.1.cpp:39`).
- The log-normal penalty, used for nonlinear models, divides the log difference by `sd` directly (`param_loss_v1.1.cpp:29-34`).
- `therapeutic_target` builds the prior variance as `pow(sd * val, 2)` (`bindings/nodejs/pklibraryjs.cpp:2372`).
- Studies store the paper's between-subject variability straight into `sd`, for example `0.491` for adalimumab clearance (`study/adalimumab/adalimumab_berends_2018.hpp:114-126`).

A `BayesContainer` holds the parameters for one patient (`src/pharmacokinetics/model/bayescontainer.h:237-248`):

- `f_map` holds bioavailability (F) per route.
- `others_map` holds every other fitted parameter, keyed by `BayesParameter::Name`.
- The `*_datetime_adjust`, `*_treatment_time_adjust`, `*_infusion_adjust` and `*_cycle_adjust` maps hold time-varying multipliers. For example, clearance changes when the patient has several CrCl entries.

`BayesContainer(drug, patient)` calls the study's `population_values()` to build the prior (`bayescontainer.cpp:6-16`). `IndividualFitting::fit()` returns a `FittingSession` whose `post` member is the fitted container (`bayesianfitting.h:131`). Only F and the parameters named in `fitted_param_names()` live in the container. Everything else is derived on demand from them, for example `k10 = CL / Vc` (clearance divided by central volume).

Any time-varying adjustment turns off the closed-form concentration path, so every prediction for that patient is simulated numerically (`model.cpp:730-745`). [models.md](models.md) describes both paths.

## How a request reaches C++

Every exported function is synchronous. A slow fit blocks the calling service's event loop for its whole duration.

1. A service calls a function on the addon. For example, Main's recommendation route calls `pklibraryjs.therapeutic_target(patient, drug, settings, pk, input, covariance, clinicalContext, graphicAnalysis)` (`PreciseRx-Main/src/controllers/drug/therapeutic-target/post-recommendation.js:47-56`).
2. `index.js` loads the matching prebuilt binary with `node-gyp-build` (`index.js:6`).
3. `InitAll` maps each JavaScript name to a C++ function (`bindings/nodejs/pklibraryjs.h:408-491`). A few names differ from the C++ name. For example, `supported_drugs` calls `all_supported_drugs`, and `therapeutic_target_v2` is an alias of `therapeutic_target`.
4. The C++ function reads its positional arguments into plain `Store::` structs (`bindings/nodejs/storeobjects.cpp`). This is where JavaScript field names become C++ names. For example, `fitting_settings.standard_error` becomes `FittingSettings::assay_error` (`storeobjects.cpp:470-474`).
5. `Unravel::` functions turn the structs into domain objects: `Settings`, `Patient`, `Drug` with its study model, `BayesContainer` and `GraphicAnalysis` (`bindings/nodejs/unraveler.cpp`).
6. The function runs the calculation, such as `IndividualFitting::fit`, `DosageRegimen` or `SteadyState`.
7. `Reravel::` functions convert the results back into JavaScript objects (`bindings/nodejs/reraveler.cpp`).
8. If anything throws, the function catches it, prints the message to stderr and returns an empty value. [error-codes.md](error-codes.md) lists the exceptions.

The newer `bindings/nodejs-v2/settings/` code wraps `Settings` as a real JavaScript class (`SettingsWrap`) and uses the typed `Parser::` and `Serializer::` helpers in `bindings/nodejs/parser/` and `bindings/nodejs/serializer/`. The rest of the API still goes through `Store`, `Unravel` and `Reravel`.

## Where to look

| To change or understand | Start in |
| --- | --- |
| A drug's routes, targets, units, rounding or model selection | `src/drug/<drug>.hpp`, then [adding-a-drug.md](adding-a-drug.md) |
| A study's population formulas | `src/pharmacokinetics/study/<drug>/<study>.hpp` |
| Closed-form concentration and dose formulas | `model/onecompartment.cpp`, `model/twocompartment.cpp`, `model/linearmodel.cpp`, `math/linear_pk.cpp` |
| Numerical simulation | `Model::simulate` (`model.cpp:770-801`) and `model/pksimulator_euler.cpp` |
| Dose search when no formula applies | `Model::target_binary_search` (`model.cpp:335-422`) |
| Bayesian fitting | `bayesianfitting/individualfitting.cpp`, `bayesianfitting.cpp`, `level_loss_v1.0.cpp`, `param_loss_v1.1.cpp` |
| Rounding and the infusion-time loop | `doseprediction/dosageregimen.cpp` |
| Institution protocols | `src/settings/` |
| Drug names, model names, increments and graph step sizes | `src/common/pkconstants.hpp` (declarations) and `pkconstants.cpp` (values) |
| Exceptions and logging | `src/common/pkexception.*`, `src/utils/logger.h` |
| Every exported JavaScript function | `bindings/nodejs/pklibraryjs.h` |

For a narrative walk-through of one study (vancomycin, Rodvold 1988) and of the fit's objective function, see the atlas sections [Worked example: Rodvold 1988](https://claude.ai/artifact/NDxuSDmUDz114P8W9j6pht#pk-rodvold) and [How a fit works](https://claude.ai/artifact/NDxuSDmUDz114P8W9j6pht#pk-fit).
