# PK-Library error codes and failure paths

This guide lists the internal error codes PK-Library defines, what raises each one, and what a JavaScript caller receives when the engine fails. Read it when you add a failure the frontend must react to, or when a service gets an empty result back from `@preciserx/pk-library-js`.

Paths are relative to `src/packages/cpp/PK-Library` unless they name another repository.

## PKException codes

`PKException` (`src/common/pkexception.hpp:16-41`) carries a numeric `code` and a `message`. Throw it with `THROW_PK_EXCEPTION(code, message)` (`src/utils/logger.h:50`). The numbers have no meaning beyond identity. The binding sends the name, not the number.

| Code | Name | Raised by |
| --- | --- | --- |
| 1000 | `ERR_GENERIC` | Nothing throws it. `PKException::code_to_string` returns this name for any code it does not list (`pkexception.cpp:3-16`). |
| 5001 | `ERR_CALCULATED_INFUSION_TIME_EXCEEDED_INTERVAL` | The infusion-time search in `therapeutic_target` (`bindings/nodejs/pklibraryjs.cpp:2355-2357`) and in `DosageRegimen`'s constructor (`src/pharmacokinetics/doseprediction/dosageregimen.cpp:64-67`). Both raise it when the infusion time grows past the requested interval before it satisfies the infusion rule. |
| 6001 | `ERR_INVALID_PK` | `therapeutic_target` when the prior or fitted half-life is at least a quarter of the drug's graphing window, which is 60 days for most drugs (`pklibraryjs.cpp:2289-2294`). Drugs that use multi-dose loading, such as teicoplanin, skip this check. `NonLinearTwoCompartment::decay_time` raises it when a level would take longer than the graphing window to decay (`src/pharmacokinetics/model/nonlineartwocompartment.cpp:125-126`); voriconazole is the only such model. `therapeutic_assessment` raises it when the fit is empty or there is no dose history (`pklibraryjs.cpp:2805-2808`). |
| 6002 | `ERR_INVALID_COVARIATES` | Nothing. The only test that expects it is disabled (`test/drugfactors.test.cpp:77-96`). |
| 6003 | `ERR_INVALID_MEASUREMENTS` | Nothing. |
| 6004 | `ERR_INVALID_PKCONTAINER` | Nothing. `code_to_string` has no case for it, so it would reach JavaScript as `ERR_GENERIC`. |

The half-life check's message says that steady state cannot be reached with a reasonable regimen. The steady-state simulation and the dose search both run inside the graphing window, so a half-life that long cannot settle within it.

`THROW_PK_EXCEPTION` builds a message with the file, line and function, then throws the original text without it (`logger.h:154-157`). JavaScript therefore receives only the plain message.

To add a code, add the enumerator in `pkexception.hpp`, add its case to `code_to_string` in `pkexception.cpp`, and handle the name in each caller that must react to it.

## What JavaScript receives

Every exported function except `route_information` wraps its body in `try` and `catch(...)`. The catch prints the message to the service's stderr in ANSI colour (`printException`, `pklibraryjs.cpp:49-52`, and `Logger::printError`, `src/utils/logger.cpp:91-95`). It does not reach the service's logger. The function then returns an empty value of its return type.

| Function | Result on failure |
| --- | --- |
| Most functions that return an object, such as `fit_and_plot`, `fit`, `plot`, `steady_state` and `dosage_regimen` | `{}` |
| Functions that return an array, such as `supported_drugs` and `drug_routes` | `[]` |
| Functions that return a number, such as `predict_level` | `-1` (`pklibraryjs.cpp:1655-1658`) |
| `therapeutic_target` and `recalculate_therapeutic_target` (and their `_v2` aliases) | `{err: {code, message}}` for a `PKException`, where `code` is the name such as `"ERR_INVALID_PK"`. Any other exception returns `{}` (`pklibraryjs.cpp:2409-2415`, `2519-2525`, `bindings/nodejs/reraveler.cpp:1554-1562`). |
| `therapeutic_assessment` | `{}`, even when it raised `ERR_INVALID_PK`, because it has only `catch(...)` (`pklibraryjs.cpp:2826-2830`) |
| `route_information(drug, route)` | No result: the Node process aborts. The function has no `try`, and node-addon-api 8.8 turns only `Napi::Error` into a JavaScript exception unless `NODE_ADDON_API_CPP_EXCEPTIONS_ALL` is defined (`node_modules/node-addon-api/napi-inl.h:87-116`). An unknown drug or route name therefore ends the process with `libc++abi: terminating due to uncaught exception` and exit status 134 (`pklibraryjs.cpp:3148-3156`). Version 1.6.1 has the same code. Its only caller, Databridge, cannot trigger this today. It passes only supported drug names (`PreciseRx-Databridge/src/model/redux/redux-dosage-history.js:531-533`), and it first maps each imported route onto one of the drug's routes (`:34-46`, `:407-411`), before the call at `:357-360`. Any new caller must validate its input the same way, or the function needs a `try`. |
| `new Settings(value)` | A JavaScript `TypeError` when `value` is not an object (`bindings/nodejs-v2/settings/settings.cpp:125-127`). Values it cannot parse become entries in the instance's `parse_warnings` instead of errors. |

A caller cannot tell "no result" from "failed" except by the shape of the response, so check for an empty object before reading fields. When you add an exported function, wrap its body in `try` and `catch(...)` like the others, so that a C++ exception cannot abort the calling service.

### How the services handle it

- Main's recommendation route maps `ERR_CALCULATED_INFUSION_TIME_EXCEEDED_INTERVAL` to `InfusionTimeExceededIntervalError` and `ERR_INVALID_PK` to `InvalidPKParametersError`, both HTTP 400. Any other code becomes `InternalError`, HTTP 500 (`PreciseRx-Main/src/controllers/drug/therapeutic-target/post-recommendation.js:58-68`).
- Both 400 error classes send a fixed message and drop the engine's text (`PreciseRx-Main/src/utils/errors/bad_request_errors/`). The class in `InvalidPKParametersError.js` is declared with the name `InfusionTimeExceededIntervalError` (`InvalidPKParametersError.js:10`), although its error code is correct.
- Main's recalculate route returns the engine result with HTTP 200 whatever it contains, including an `err` object (`PreciseRx-Main/src/controllers/drug/therapeutic-target/post-recalculate.js:59-71`).
- Analytics treats an empty or `err` result from `therapeutic_target` as "no regimen" (`PreciseRx-Analytics/src/controllers/therapeutic-status/get-patient-summary.js:116-129`).
- The frontend shows both 400 codes with the same network-error indicator (`PreciseRx-Web/src/actions/TherapeuticActions.ts:224-240`).

## Fitting status codes

A Bayesian fit reports its outcome through `FittingSession::Status`, not through an exception (`src/pharmacokinetics/bayesianfitting/bayesianfitting.h:74-80`). `fit_and_plot` returns it as the string `fitting_session.status` (`bindings/nodejs/reraveler.cpp:1457-1463`).

| Status | Meaning |
| --- | --- |
| `SUCCESS` | The optimizer finished. It also reports `SUCCESS` when it stops at the iteration cap of 1000 without converging (`bayesianfitting.cpp:238`, `332`). |
| `NOT_FITTED` | There is nothing to fit. With a dose history, the fit needs two levels before the first dose or one after it. Without one, it needs two levels (`individualfitting.cpp:26-49`). |
| `ERR_EMPTY_PRIOR` | The prior `BayesContainer` is empty (`individualfitting.cpp:50-51`). |
| `ERR_TIMEOUT_EXCEEDED` | The fit ran past 20 seconds of wall-clock time (`bayesianfitting.cpp:206`, `240-241`). |

Every status except `SUCCESS` leaves the fitted parameters empty (`bayesianfitting.h:116-127`).

## Failures that raise nothing

Two inputs are corrected silently instead of failing:

- Invalid institution settings are replaced by the defaults, including the CrCl formula. Only a yellow stderr line records it (`bindings/nodejs/unraveler.cpp:28-32`).
- A weight or height unit other than exactly `kg`, `lb`, `cm` or `in` makes the binding rebuild the patient with `kg` and `cm` and the same numbers. A weight of 180 sent as `lbs` becomes 180 kg (`unraveler.cpp:40-50`).
