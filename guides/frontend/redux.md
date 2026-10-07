# Redux state in PreciseRx-Web

This guide explains how application state works in PreciseRx-Web today: the store, action types, thunks and the HTTP wrapper they call, reducers, selectors, the two store-wide resets, and the autosave middleware. Read it before you add state, an action or an API call. Paths are relative to the PreciseRx-Web root.

## The store

`src/store.ts` builds one store with Redux Toolkit's `configureStore`. The rest of the code does not use Redux Toolkit's `createSlice` or `createAsyncThunk`. Reducers are hand-written `switch` functions and async work is done in plain thunks.

- The store runs Redux Toolkit's default middleware with thunks on and the immutability and serializability checks off (`src/store.ts:47-55`). Nothing catches a mutated state object at runtime, so every reducer must return new objects.
- The autosave middleware runs after the default middleware (`src/store.ts:36`, `:53`). See [Autosave](#autosave).
- Redux DevTools is enabled in every environment except production (`src/store.ts:42-45`). Anyone with the browser extension can read the whole store, including case data, on staging and local builds.
- Components use the typed hooks `useAppSelector` and `useAppDispatch` from `src/store.ts:64-67`. `RootState` and `AppDispatch` are exported from the same file.

## Slices and the store-wide resets

`src/reducers/RootReducer.ts:32-51` combines 18 slices, one reducer file per slice, named after the slice (`patient` is `PatientReducer.ts`, `pk_parameters` is `PKParametersReducer.ts`, and so on).

`RootReducer` handles two actions before any slice sees them (`src/reducers/RootReducer.ts:62-105`):

- `USER_LOGOUT` resets every slice to its initial state.
- `NEW_PATIENT` starts a new patient case. It keeps the slices that do not belong to a case and resets the rest.

| On `NEW_PATIENT` | Slices |
| --- | --- |
| Kept unchanged | `advanced_analytics`, `model_analytics`, `profile`, `protocol_settings`, `settings` |
| Partly kept | `application` keeps everything except `database`, which holds the current case's identity and last-saved inputs. `pk_parameters` resets except `viewed_model_notes` and `auto_select_model`. |
| Reset | `aki_prediction`, `drug`, `external_platform`, `graphing`, `history`, `notes`, `patient`, `search`, `steadystate`, `therapeutic`, `therapeutic_analytics` |

When you add a slice, it is reset on `NEW_PATIENT` unless you add it to the kept list in `RootReducer.ts`. When you add a field to a kept slice, it survives a new case, so make sure that is what you want.

## Action types

- Declare every action type in `src/actions/Types.ts` as `export const NAME = 'NAME' as const;`.
- Put it under the comment header for its domain, such as `// Patient` or `// Application`. The file is grouped this way from top to bottom.
- `NEW_PATIENT` and `USER_LOGOUT` are declared there too (`src/actions/Types.ts:222`, `:34`).
- The files named `*ActionTypes.ts`, such as `src/actions/LoadActionTypes.ts`, hold TypeScript types for API responses. They do not declare action types.

## Thunks

Action creators live in `src/actions/<Domain>Actions.ts` and return a thunk, `(dispatch, getState) => ...`.

- A thunk that only changes state dispatches one action, as `updateScrHistory` does (`src/actions/PatientActions.ts:476-483`).
- A thunk that changes one item of an array reads the current array with `getState()`, builds the new array, and dispatches the whole array (`addScrEntry`, `src/actions/PatientActions.ts:492-501`).
- A thunk that calls the API builds a request config and calls `axiosRequestWrapper`, then dispatches from its success callback. `addNote` in `src/actions/NoteActions.ts:20-53` is a complete example:

```ts
export const addNote = (note: Record<string, any>) => (dispatch: AppDispatch) => {
    const data = { note: Note.ReduxToApi(note) };

    const requestConfig = {
        method: HttpMethod.PUT,
        server: Server.DATABASE,
        route: '/notes',
        wrapperConfig: { customErrorHandler: true },
    };

    const onSuccessCallback = (results: any) => new Promise((resolve) => {
        dispatch({ type: ADD_NOTE, payload: { note: { ...note, id: results.id } } });
        resolve(true);
    });
    const onFailureCallback = () => new Promise((resolve) => { resolve(false); });

    return axiosRequestWrapper(requestConfig, data, {}, onSuccessCallback, onFailureCallback)(dispatch);
};
```

## The HTTP wrapper

Every API call from a thunk goes through `axiosRequestWrapper(requestConfig, data, axiosConfig, onSuccess, onFailure)(dispatch)` in `src/actions/AxiosRequestWrappers/index.ts:144-260`.

- `requestConfig.server` picks the backend service: `Server.MAIN`, `DATABASE`, `DATABRIDGE`, `ANALYTICS` or `ML` (`src/actions/AxiosRequestWrappers/Constants.ts:17-23`).
- The URL is the environment's API host, then the service prefix, then the route (`index.ts:205`). The prefix is the service name followed by `VITE_SERVER_API_VERSION`, the blue-green lane `v1` or `v2` (`Constants.ts:25-31`).
- `data` is the request body. `axiosConfig` carries headers and query `params`.
- Every request sends cookies and an `Accept` header that asks for API `version=1.0`.
- The wrapper dispatches `SET_PENDING` before the request and `REMOVE_PENDING` after it (`index.ts:162-168`, `:247-255`). The `application` slice keeps these in `api_request.pending`, which is how the app knows a calculation is still running.

`requestConfig.wrapperConfig` turns behaviours on and off. Defaults are at `index.ts:25-31`.

| Flag | Default | What it does |
| --- | --- | --- |
| `retryRequest` | `true` | Retries a failed request up to 5 more times, 3 seconds apart (`Constants.ts:3`, `index.ts:173-187`). 7 actions turn it off. |
| `customErrorHandler` | `false` | Calls your `onFailure` with the error instead of the default handling. It also skips every retry (`index.ts:241-243`). About 34 actions turn it on. |
| `handleSessionErrors` | `true` | Sends a 401 to the global handler, which refreshes the session or logs the user out (`index.ts:226-239`). The sign-in, sign-up, password-reset and auth-status routes in `src/actions/AuthActions.ts` turn it off, because a 401 there means wrong credentials. |
| `cancelDuplicateRequests` | `false` | Aborts an in-flight request with the same method and route before sending a new one (`index.ts:199-203`). |
| `preventNetworkRace` | `false` | Calls `onSuccess` only for the latest request to a route, so a slow old response cannot overwrite a newer one (`index.ts:209-213`). The `/pharmacokinetics/*` calculations in `PatientActions.ts`, `/drug` in `DrugActions.ts` and `/search/case` in `LoadActions.ts` turn it on. |

Without `customErrorHandler`, a failed request is handled by `handleNetworkError` in `src/actions/AxiosRequestWrappers/AxiosErrorHandlers.ts:52-119`, and the wrapper's promise resolves to `null`. Callers must handle a `null` result.

| Failure | What happens |
| --- | --- |
| 401 with code `ExpiredTokenError` | Refreshes the tokens once per 10 seconds at most (`AxiosErrorHandlers.ts:35-40`), then retries the request. |
| Any other 401 | Records the HTTP status in the store and logs the user out. |
| 403 | Records the status and stops. The page stays on screen, so the backend's own checks are the real gate. |
| 500 or another status | Retries, then records the status after the last retry. |
| No response | Records a 500 status with the message `validation:connection_failed`. |

A recorded 500 status shows the connection-failed overlay over the whole app (`src/components/Application/PrecisePK.tsx:27-29`).

## Reducers

- Write a reducer as `export default function XReducer(state: XState = initialState, action: PayloadAction<any>): XState` with a `switch` on `action.type`. `src/reducers/NoteReducer.ts` is a short example.
- Wrap each `case` body in braces, return a new object, and end with `default: { return state; }`.
- Export `initialState` when another module needs it. `RootReducer` imports it from `ApplicationReducer` and `PKParametersReducer`.
- Older reducers document each case with a JSDoc `@event` tag. See [JSDoc](jsdoc.md).

## Selectors

- Put selectors in `src/selectors/<Slice>Selectors.ts` as named exports that take `RootState`.
- Use a plain function for a single path, such as `selectPatientAge` (`src/selectors/PatientSelectors.ts:19`).
- Use `createSelector` when a value is derived from several inputs, such as `selectIsPatientFormDirty` (`src/selectors/PatientSelectors.ts:36-60`).
- `import/prefer-default-export` flags a file with a single named export. A selector file with only one selector disables the rule with a comment, as `src/selectors/PkParametersSelectors.ts` does.

## Autosave

`src/middlewares/autosaveMiddleware.ts` runs after every action. It saves the open case five seconds after the user's last change to a case input.

1. It does nothing unless the effective general settings, `settings.settings_used.general_settings.autosave`, are set to `Enable` (`autosaveMiddleware.ts:86-91`).
2. It skips while a case is importing, while a save is running, after a failed save, while the case is invalid, and while `application.pause_autosave` is set (`autosaveMiddleware.ts:103-121`).
3. It compares the tracked inputs before and after the action, and against `application.database.last_saved_inputs` (`autosaveMiddleware.ts:123-149`). The tracked inputs are the state paths listed in `src/utils/SaveUtility.ts`. For history arrays, only complete entries count.
4. If unsaved changes exist, it schedules `saveCase(true)` after `AUTOSAVE_DELAY`, 5 seconds (`src/utils/SaveUtility.ts:18`). A new change restarts the timer.
5. `saveCase` sends `PATCH /patients/cases/save` to the Database service with only the changed paths (`src/actions/ApplicationActions.ts:216`, `:229-233`). A manual save, a new case, or a case not yet saved in UTC sends `PUT` with the whole case instead.
6. On success it records the saved inputs as the new `last_saved_inputs` (`ApplicationActions.ts:276`). Loading a case does the same through `updateLastSavedInputs` (`src/actions/LoadActions.ts:781`).

Call `pauseAutosave(true)` before a multi-step edit that passes through invalid states, and `pauseAutosave(false)` after it (`src/actions/ApplicationActions.ts:440-445`). `ScrHistory.tsx` does this around its editing dialog.

An action that resets `application.database` while the case slices still hold data makes autosave save that data as a new case. This caused duplicate cases on the EHR import page (BLITZ-3.6.0-1). `src/__tests__/ExternalPlatform/EhrImportPageRemountDuplicateCase.test.ts` shows the mechanism and the guards.

### When you add state

Work through these checks for every new field.

1. Add the action type to `src/actions/Types.ts`, the field to the slice's state type and `initialState`, and the handling to the reducer.
2. Decide what `NEW_PATIENT` should do with it. See [Slices and the store-wide resets](#slices-and-the-store-wide-resets).
3. If the field is a case input that must be saved, add its path to `REGULAR_INPUT_PATHS` (`src/utils/SaveUtility.ts:20-69`). Use `HISTORY_INPUT_PATHS` (`:71-76`) for an array of history entries with `entry.isComplete`. A path missing from these lists never triggers autosave and is never sent in a `PATCH`.
4. If the field holds local dates or times, add its path and converter to `LOCALIZED_PATHS_AND_CONVERTERS` (`SaveUtility.ts:79-90`), so it is sent in UTC.
5. If the Database service needs the whole parent object to save the field, add a prefix rule to `getSaveCaseOptionalBodyPaths` (`SaveUtility.ts:176`).
6. Check that the full `PUT` body in `saveCase` includes the field (`ApplicationActions.ts:229-249`). That body sends the whole `drug`, `history`, `patient`, `settings` and `therapeutic` slices, but only `fitting_settings` from `graphing` and only the fitted parameters and prior option from `pk_parameters`.
7. Confirm that the Database service accepts the field, and that loading a case restores it.
8. If the field is UI state and not a case input, keep it out of the tracked paths so it never triggers a save. If only one component needs it, keep it in component state instead of Redux.
9. Test fixtures preload whole slices, so a new field is missing from them. See [Testing](testing.md).

## Changing store state

These rules keep reducers small. They are how the current code changes the `patient` slice.

- Use one merge action per object instead of one action type per field. `UPDATE_PATIENT_INFO` spreads its payload into `patient` (`src/reducers/PatientReducer.ts:518-523`). `UPDATE_LAB_RESULTS` spreads its payload into `patient.lab_results` (`PatientReducer.ts:637-645`).
- Keep field setters as thin thunks that dispatch the merge action with the fields they change, as `changePID` and `changeGestationalAgeWeeks` do (`src/actions/PatientActions.ts:60-100`).
- Change arrays by computing the new array in the thunk and dispatching it through the merge action, not with separate add, update and delete cases. `addScrEntry` and `updateScrHistory` both go through `UPDATE_LAB_RESULTS`.
- Do not reshape existing slices, for example by nesting `patient.first_name` under a new object or moving `lab_results` into its own slice. Those paths are part of the autosave tracked inputs, the save request body, the Database API contract and every test fixture.
