# Adding a drug or a study model to PK-Library

This guide lists every change needed to add a new drug, or a new published study model to an existing drug, and documents the dosing defaults a drug class controls. Read it before you start either task. [primer.md](primer.md) explains the Drug, model type and study classes that these steps extend.

Paths are relative to `src/packages/cpp/PK-Library` unless they name another repository.

## Add a study model

Do this for each published model, including the first model of a new drug.

1. **Pick the model type.** Derive from `OneCompartment`, `TwoCompartment` or `ThreeCompartment` for linear models, or from `NonLinear` or `NonLinearTwoCompartment` for Michaelis-Menten elimination. `OneCompartmentGeneral` is a shortcut for one-compartment models that fit only CL and Vd: it supplies `fitted_param_names()`, `population_values()`, `derived_parameters()` and `ke()`, and the study implements `cl(patient, coefficients, datetime)` and `vd(patient, coefficients)` (`model/onecompartment_general.h:4-27`). `AminoglycosideTDMS` uses it.
2. **Add the constants.** Declare the display name and the citation string as `extern const char * const` under `PKConstants::Drug::<Drug>::Model` and `::Source` in `src/common/pkconstants.hpp`. Define them in `pkconstants.cpp`. The Cefepime block is the pattern (`pkconstants.hpp:1021-1043`, `pkconstants.cpp:1463-1484`). The display name, such as `"An 2023"`, is what the frontend shows and what callers pass as `selected_model.model_name`.
3. **Write the class.** Create a header-only `src/pharmacokinetics/study/<drug>/<drug>_<author>_<year>.hpp` holding `class <Drug><Author><Year>`, with a constructor that forwards the drug pointer, for example `CefepimeAn2023(const Drug* drug) : TwoCompartment(drug) {}`.
4. **Implement the study functions.** Every study provides the following.
   - `model_name()` returns the constant from step 2.
   - `fitted_param_names()` lists the parameters the fit may move. `population_values()` must put exactly one `BayesParameter` in `others_map` for each of them (`model.hpp:253-265`).
   - `population_values(patient, routes, coefficients)` fills `f_map` with F for every route and `others_map` with each fitted parameter as `{value, relative SD, Citation}`. The second field is a coefficient of variation, not an absolute SD (see [primer.md](primer.md#bayesparameter-and-bayescontainer)).
   - `derived_parameters()` returns the non-fitted values shown to clinicians, such as $k_e$ and half-life.
   - The structural functions that the model type leaves pure virtual: `cl()`, `vd()` and `ke()` for one-compartment models (`onecompartment.h:87-93`), or `vc()`, `vp()`, `Q()`, `k10()`, `k12()`, `k21()`, `alpha()` and `beta()` for two-compartment models (`twocompartment.h:102-129`). Two-compartment studies usually return `alpha_from_microconstants()` and `beta_from_microconstants()`.
   - `f()`, `ka()`, `time_lag()` and `salt()` for any non-IV route, and whenever F or the salt fraction is not 1.
   - The metadata the model picker shows: `model_study_summary()`, `model_age_range()`, `model_weight_range()`, `model_population_title()`, `model_population_value()` and `model_sources()`.
   - Optionally, `can_fit()` returning true and `coefficients()`, which let an institution refit the population coefficients on its own patients (`model.hpp:335-338`). Four vancomycin models do this, for example `study/vancomycin/vancomycinrodvold1988.hpp:151`.
5. **Handle time-varying clearance when the study depends on renal function.** Record the ratio of clearance at each CrCl entry to the latest clearance in `others_datetime_adjust`, as `study/cefepime/cefepime_an_2023.hpp:55-60` does. Any adjustment switches that patient to numerical simulation (see [models.md](models.md#how-the-engine-chooses-a-method)).
6. **Register the model in its drug class.** Include the header in `src/drug/<drug>.hpp`, then update four functions: `models()`, `models_for_patient()` (which models the picker offers for this patient), `determine_model()` (which model auto-selection picks when the name is empty) and `set_model()` (which name builds which class). `src/drug/cefepime.hpp:38-119` shows all four.
7. **Update `binding.gyp` if you created a folder.** The Node build compiles a hand-maintained source list. A header in an existing study folder needs nothing. A new folder under `study/` needs an `include_dirs` entry (`binding.gyp:157-194`), and any new `.cpp` file needs a `sources` entry (`binding.gyp:5-155`). CMake and the Python binding glob the tree, so they need no change (`src/CMakeLists.txt:1-9`, `bindings/python/CMakeLists.txt:21`).
8. **Test it.** Add `test/<Drug><Author><Year>.test.cpp` that checks each population parameter against a value worked out by hand from the paper for a sample patient. See [testing-and-debugging.md](testing-and-debugging.md#writing-tests).

Main can hide a model from some institutions. `ModelWhitelists` in `PreciseRx-Main/src/feature-whitelist.js:14-27` maps a model name to the institutions allowed to use it and a fallback model for everyone else. It is empty today.

## Add a drug

1. **Add the drug constants** under `PKConstants::Drug::<Drug>` in `pkconstants.hpp` and `pkconstants.cpp`: `NAME`, the model and source names, and any dosing constants such as `DOSAGE_INCREMENT`. `NAME` is the string every API call uses to identify the drug.
2. **Write the drug class** as `src/drug/<drug>.hpp`, holding `class <Drug> : public Drug`. It must implement the pure virtual functions in `src/drug/drug.hpp`:
   - `name()`, `set_model(std::string)` and `determine_model(patient, model_name, route)`. `determine_model` must return `model_name` when it is not empty, and must also handle an empty `route`.
   - `routes()` and `targets(route)`.
   - `assay_error()`, `sem()` and `time_weight(patient)`, the default fitting settings. The fixed error `sem()` is in the drug's concentration unit.
3. **Override what differs from the defaults.** The usual overrides are:
   - `models()` and `models_for_patient()`, when the drug has more than the single `TDMS` model.
   - `drug_can_be_used(body_comp)`, to limit the drug by age. Adalimumab is adults only (`adalimumab.hpp:48-53`).
   - `units(age)`, when doses or concentrations are not in mg and mg/L.
   - `all_drug_specific_factors()`, `required_covariates()` and `required_lab_measurements()`, for the patient inputs the models read.
   - `route_information(route)`, for single-dose or continuous-rate routes and nomogram support.
   - The dosing defaults in the next section.
   - `warning_metadata()`, `toxicology_info()`, `therapeutic_min()` and `therapeutic_max()`, for warnings and the displayed ranges.
   - `graphing_max_time()` and `graphing_dt()`, for drugs with very long half-lives, as infliximab and adalimumab do.
4. **Register the drug** in `src/drug/drug.cpp`. Include the header, add a branch to `Drug::init` (`drug.cpp:42-77`), and add the name to `Drug::all_supported_drugs()` (`drug.cpp:176-207`). A drug missing from that list still initialises, but no catalogue call returns it.
5. **Add any new enum values.** A new route needs a `FullRoute` value and its strings in `src/drug/routes.h` and `routes.cpp`. A new patient flag needs a `DrugFactor::Name` in `src/patient/drugfactor.h`, and a new covariate needs an entry in `src/patient/covariate.h` and `covariate.cpp`. Adalimumab's first commit shows the route and drug-factor changes (`git show --stat 4e46f670`).
6. **Add the study models** with the steps above.
7. **Run the whole suite.** Several suites loop over `Drug::all_supported_drugs()`, so they exercise the new drug's routes and targets immediately (`test/steadystatetest.cpp:9-60`).

Changes outside PK-Library:

- Publish a new `@preciserx/pk-library-js` version and bump it in Main, Analytics and Databridge. All three pin `1.6.1` today (`PreciseRx-Main/package.json:23`).
- Main limits new drugs to listed institutions in each environment through `DrugWhitelists` (`PreciseRx-Main/src/feature-whitelist.js:39-73`). Add the drug there if it should launch to a subset of customers.
- The frontend keeps drug-name constants for drug-specific screens in `PreciseRx-Web/src/models/pklibraryjs/Drug/constants.ts`. Search the frontend for an existing drug's constant to find the behaviour you may need to extend.

## Dosing defaults a drug controls

Each value below is a virtual function on `Drug` with a default in `src/drug/drug.cpp`. The drug class overrides it.

| Function | Default | What reads it |
| --- | --- | --- |
| `dosage_increment(patient, route)` | 5 (`drug.cpp:339-341`) | Rounding in `DosageRegimen::round()`, and the UI dose stepper through `drug_information` (`bindings/nodejs/pklibraryjs.cpp:300`) |
| `standard_dosages(patient, route)` | None (`drug.cpp:345-347`) | Rounding snaps to these values instead of multiples of the increment |
| `dosage_bounds(patient, route)` | One increment up to no limit (`drug.cpp:351-353`) | The UI dose stepper |
| `dose_rounding_enabled(patient, route)` | Age 18 or over (`drug.cpp:356-358`) | Whether `round()` uses increments at all |
| `dosage_rounding_options(patient, route, dose)` | The increment multiples below and above the dose, never below one increment (`drug.cpp:360-368`) | `round()` |
| `recommended_infusion_time_default(route, dose)` | 1 h intermittent IV, 24 h continuous IV, none otherwise (`drug.cpp:449-462`) | The infusion-time rules below |
| `recommended_infusion_times(body_comp)` | None (`drug.cpp:328`) | Infusion-time options in `drug_information`, and the nomogram |
| `recommended_intervals(body_comp, route)` | None (`drug.cpp:334`) | Interval options in `drug_information` |
| `recommended_intervals(patient, pk)` | None (`drug.cpp:336`) | The nomogram's interval columns (`nomogram.cpp:24`) |
| `default_interval(patient, pk, route)` | Not set (`drug.cpp:464-466`) | `therapeutic_target`, only for single-dose routes (`pklibraryjs.cpp:2392-2398`) |
| `default_therapeutic_range(target)` | Not set (`drug.cpp:417-419`) | `default_therapeutic_target_ranges` (`pklibraryjs.cpp:2965-2987`) |
| `requires_loading_dose()` | True (`drug.cpp:376-378`) | When false, regimens drop their loading dose (`dosageregimen.cpp:319-327`) and the dose search skips it (`model.cpp:375-379`) |

Two of these hooks do less than their names suggest.

- `default_interval` only affects single-dose routes, which exist only for carboplatin (all routes) and methotrexate (intermittent IV, oral and IM). The overrides in other drugs, including vancomycin's half-life rule (`vancomycin.hpp:731-747`) and the aminoglycosides' 24 hours, have no effect today.
- `default_infusion_time()` has no callers. Busulfan, carboplatin, infliximab and meropenem override it, but nothing reads the result.

### Rounding

`DosageRegimen::round()` (`src/pharmacokinetics/doseprediction/dosageregimen.cpp:181-284`) runs after the target calculation when the caller asks for rounding. `therapeutic_target` asks for it on every route except continuous-rate routes (`bindings/nodejs/pklibraryjs.cpp:2324`).

1. A continuous rate above 1 is rounded to the nearest whole number and nothing else changes.
2. When `dose_rounding_enabled` is true, the engine tries the maintenance dose rounded down and rounded up, and keeps whichever lands closer to the target (`SteadyStateTarget::closer_to_target`). For each candidate it also compares rounding the loading dose up, rounding it down and dropping it, by how far the first trough lands from the steady-state trough. The comparison loop never updates its running minimum, so it keeps the last option that beats the round-up option rather than the best of the three (`dosageregimen.cpp:243-248`).
3. When rounding is disabled, doses for patients under one year are truncated to one decimal place, and other doses are rounded to the nearest whole number.
4. A loading dose equal to the maintenance dose is removed.
5. Trough-range targets (teicoplanin) use their own rounding instead. See [models.md](models.md#matrix-solution-for-short-courses).

Increments are in the drug's dose unit from `units(age)`:

| Drug | Increment | Where |
| --- | --- | --- |
| Every drug not listed below | 5 | `drug.cpp:339-341` |
| Vancomycin | 250 mg from age 18, 5 mg under 18 | `pkconstants.cpp:117-118`, `vancomycin.hpp:825-829` |
| Piperacillin | 0.005 g from age 18, 5 mg under 18 | `pkconstants.cpp:1172-1173`, `piperacillin.hpp:55-59` |
| Busulfan | 1 mg | `pkconstants.cpp:1224` |
| Tacrolimus, methotrexate, cyclosporine | 0.5 | `pkconstants.cpp:1245`, `1282`, `1338` |
| Meropenem | 250 mg | `pkconstants.cpp:1387` |
| Teicoplanin | 100 mg | `pkconstants.cpp:1406` |
| Linezolid | 200 mg IV, 600 mg tablets, 100 mg suspension | `pkconstants.cpp:1427-1429`, `linezolid.hpp:199-210` |
| Cefepime | 500 mg, snapping to 500, 1000 or 2000 mg vials | `pkconstants.cpp:1466-1468`, `cefepime.hpp:175-207` |
| Adalimumab | 40 mg | `pkconstants.cpp:1489` |

Because `dose_rounding_enabled` defaults to age 18 or over, the pediatric increments above are reported to the UI but do not round the recommended dose unless a drug overrides that function. No drug does today.

### Infusion time

The recommended infusion time for a dose comes from two sources, in order (`drug.cpp:440-447`).

1. **The institution's infusion-time protocol**, when one matches the case. `InfusionTimeProtocol::get` picks the protocol whose filter scores highest for the patient, drug and route (`src/settings/infusion_time_protocol.cpp:127-145`). Within it, rules are sorted by dose, and the first rule whose comparison (`gt`, `lt`, `gte`, `lte`, `eq` or `ne` against the rule's dose) holds wins. If none holds, the lowest-dose rule applies (`infusion_time_protocol.cpp:86-106`).
2. **The drug's `recommended_infusion_time_default`.** Vancomycin uses 1 hour plus 0.25 hour for each started 250 mg above 1000 mg, on intermittent and continuous IV (`vancomycin.hpp:782-800`). Meropenem always uses 0.5 hour (`meropenem.hpp:202-204`).

When a therapeutic-target request does not fix the infusion time, `therapeutic_target` searches for one (`bindings/nodejs/pklibraryjs.cpp:2340-2364`).

1. It starts at 0.5 hour and calculates the regimen.
2. It adds 0.25 hour while the infusion time is shorter than the recommendation for the larger of the maintenance and loading doses, for at most 200 rounds.
3. If the infusion time passes the requested interval, it raises `ERR_CALCULATED_INFUSION_TIME_EXCEEDED_INTERVAL` (5001).

`DosageRegimen`'s constructor runs the same loop when called with `auto_calculate_infusion_time` (`dosageregimen.cpp:16-17`, `53-70`). The Node binding never sets it, and the Python binding turns it on by default (`bindings/python/src/pharmacokinetics/doseprediction/dosageregimen.cpp:37`). The infusion ranges in a drug's `warning_metadata()` only raise warnings. They never change the recommended time.

### Default target values

- Most therapeutic-target inputs start blank. The exceptions are MIC, day of treatment and treatment cycle, which start at 1 (`src/pharmacokinetics/therapeutictarget/target_input.cpp:110-121`).
- An institution's default-target-input protocol replaces these defaults whenever it matches the case with a value above 0, unless the settings disable the protocol (`steadystatetarget.cpp:261-275`).
- `default_therapeutic_range(target)` supplies per-drug ranges for the target picker. Only amikacin, vancomycin and busulfan override it (`amikacin.hpp:112-128`, `vancomycin.hpp:997-1017`, `busulfan.hpp:305-327`).
