# Frontend tests in PreciseRx-Web

This guide covers how to write and run PreciseRx-Web's tests with Vitest, Testing Library and MSW (Mock Service Worker): the global setup, the custom `render`, preloaded store fixtures, API mocks, and the conventions the existing tests follow. Read it before you add a test or debug a failing one. Paths are relative to the PreciseRx-Web root.

## Running tests

`pnpm test` runs Vitest with `VITE_ENVIRONMENT=development` (`package.json:67`). In an interactive terminal it starts in watch mode. CI runs the same command on every pull request after `pnpm build`.

```sh
pnpm test                                   # watch mode
pnpm test --run                             # run everything once
pnpm test --run src/__tests__/components/User/DrugMonitoring/MultipleDosageEntries.test.tsx
pnpm test --run src/__tests__/components/User/DrugMonitoring/MultipleDosageEntries.test.tsx -t "rejects 91 days"
```

- `-t` runs only the tests whose name matches the pattern. The other tests in the file are reported as skipped.
- `pnpm build` also type-checks the tests, because `tsc -b` includes all of `src/` (`tsconfig.app.json:47-48`). A test that runs but does not type-check still fails CI.

## Configuration

The Vitest settings live in the `test` block of `vite.config.ts:88-101`.

- Tests run in jsdom with Vitest's globals, so `describe`, `it`, `expect` and `vi` need no import (`vite.config.ts:89-90`).
- Each test may take up to 15 seconds (`vite.config.ts:93`), because tests that drive Chakra components with `userEvent` are slow on CI runners.
- Log lines containing the keywords in `SILENT_KEYWORDS` are dropped (`vite.config.ts:9-18`, `:100`). They include Redux Toolkit's slow-check warnings and jsdom's "navigation not implemented" error.

`src/setupTests.ts` runs before every test file:

- It adds the jest-dom matchers such as `toBeInTheDocument` (`setupTests.ts:8-13`).
- It works around a crash in `@zag-js/focus-visible` that makes the first Chakra `Checkbox` or `Menu` in a file render empty on Linux CI (`setupTests.ts:15-48`).
- It sets the time zone to `America/Los_Angeles`, so date and time conversion tests give the same result on every machine (`setupTests.ts:51`).
- It stubs `scrollIntoView`, `window.scrollTo` and `matchMedia`, which jsdom lacks (`setupTests.ts:57-73`).
- It starts the MSW server before all tests and closes it after (`setupTests.ts:75-81`, `:97-100`).
- After each test it unmounts rendered components, calls `vi.resetAllMocks()`, and removes handlers added with `server.use()` (`setupTests.ts:83-95`). Call `mockReturnValue` or `mockImplementation` inside the test or a `beforeEach`, because a call made at module level is undone after the first test.

## Rendering components

Import `render`, `screen`, `waitFor` and the rest of Testing Library from `utils/tests/TestsUtility`, not from `@testing-library/react`. Its `render` (`src/utils/tests/TestsUtility.tsx:45-72`) wraps the component in what the app provides. That is a Redux `Provider` with a store built from `RootReducer`, an `I18nextProvider` with the test i18n instance, a `BrowserRouter`, and the app's `ErrorBoundary`.

`render` takes these options besides Testing Library's own.

| Option | Default | Use it to |
| --- | --- | --- |
| `preloadedState` | none | Start the store from a fixture, usually a mock store. |
| `store` | a new store from `RootReducer` and `preloadedState` | Pass a store you built, for example to dispatch actions and read state around the render. |
| `route` | `/` | Set the URL before the component mounts. |

- The default store uses Redux Toolkit's default middleware. It does not include the autosave middleware, so autosave never runs in a component test.
- `TestsUtility.tsx` mocks react-router's `useBlocker` (`TestsUtility.tsx:12-22`). The app uses a data router, but the test wrapper uses `BrowserRouter`, where `useBlocker` would throw.
- Wrap a component that must sit inside a Chakra `ModalContent` with `src/utils/tests/TestModalWrapper.tsx`.
- Chakra modals render in a portal outside the render container. Query them through `screen` or `document`, not `container` (`src/__tests__/components/User/DrugMonitoring/MultipleDosageEntries.test.tsx:69-70`).

### Translations render as keys

The test i18n instance (`src/utils/tests/i18nForTests.ts`) loads no translation files. `t('iam:buttons.update_and_close')` renders `buttons.update_and_close`, the key without its namespace. Assert on that key, as in `screen.getByRole('button', { name: 'buttons.update_and_close' })` (`src/__tests__/IAM/Overlays/EditUserAttributes.test.tsx:116`).

## Store fixtures

`src/__mocks__/mock_stores/` holds JSON snapshots of the whole store for realistic cases.

| Fixture | Case |
| --- | --- |
| `vancomycin_case_1.json` | A vancomycin case. Most component tests use it. |
| `tacrolimus_case_1.json` | A tacrolimus case, for covariates and lab measurements. |
| `sentri7_import_case_1.json`, `sentri7_import_case_2.json` | Cases imported from Sentri7. |
| `therapeutic_insights_1.json` | Only the `advanced_analytics` and `external_platform` slices, for the Therapeutic Insights settings test. |

- Change what a test needs by spreading the fixture, as `dayDrugState` does in `MultipleDosageEntries.test.tsx:38-54`. Do not edit a shared fixture for one test.
- A preloaded slice replaces that slice's `initialState` completely. A field you add to a reducer's `initialState` is therefore missing from every test that preloads a fixture. Add it to the fixtures, or spread it in where a test depends on it.
- A slice missing from the fixture starts from its `initialState`. None of the fixtures has `protocol_settings`, for example.

## Mocking the API

`src/__mocks__/server.ts` creates one MSW server from the handlers in `src/__mocks__/handlers.ts`. See the [MSW documentation](https://mswjs.io/docs/) for the `http` and `HttpResponse` APIs.

- Build every handler URL from `http://localhost/` and `serverApiPaths`, as in `` `http://localhost/${serverApiPaths[Server.MAIN]}/iam/users` ``. Tests run with `VITE_ENVIRONMENT=development`, which sends requests to `http://localhost/`. The lane segment comes from `VITE_SERVER_API_VERSION`, which CI does not set, so a hard-coded `v1` would not match there.
- Add a handler to `handlers.ts` only when many tests need the same response.
- Override a response for one test with `server.use(...)` inside that test (`EditUserAttributes.test.tsx:123-131`). `setupTests.ts` removes it afterwards.
- Capture request bodies in a `server.use` handler to assert on what the app sent (`src/__tests__/ExternalPlatform/EhrImportPageRemountDuplicateCase.test.ts:66-85`).
- `server.listen()` is called without an `onUnhandledRequest` option (`setupTests.ts:80`). MSW then prints a warning for a request with no handler and sends it to the real network, where it fails, or reaches your local backend if the umbrella stack is running on port 80. Add a handler for every call the test depends on.
- `redux-mock-store` and `axios-mock-adapter` are installed, but no test uses them. Use a real store and MSW instead.

## Where tests live and what they look like

All tests live under `src/__tests__/` and end in `.test.ts` or `.test.tsx`.

- New tests mirror the source path, for example `src/__tests__/components/User/DrugMonitoring/MultipleDosageEntries.test.tsx` for `src/components/User/DrugMonitoring/DosageHistory/MultipleDosageEntries.tsx`, or `src/__tests__/reducers/PatientReducer.test.ts`. Older tests are grouped by feature, such as `src/__tests__/Login/`.
- Put constants shared by a folder's tests in a `Constants.ts` beside them, as in `src/__tests__/IAM/Overlays/Constants.ts`.
- Start from `src/__tests__/TestTemplate`. It has no extension, so Vitest never runs it.

Follow these conventions from the existing tests:

- Name the top-level `describe` after the component, as `describe('<EditUserAttributes />', ...)`, and group behaviours in nested `describe` blocks.
- Use `it` with a sentence that states the behaviour, such as `it('Should call callbacks on successful role update', ...)`.
- Write a `setupComponent` helper that renders the component with its fixture and returns `userEvent.setup()`, as the template does.
- Drive the UI with `@testing-library/user-event`, not `fireEvent`. Only one test file still uses `fireEvent`.
- Mock a module with `vi.mock`, and create the spies it needs with `vi.hoisted`, as `EditUserAttributes.test.tsx:12-17` does for Chakra's `useToast`.
- Start a test file with a `@fileoverview` comment that explains what behaviour it pins down and why, especially for a regression test (`MultipleDosageEntries.test.tsx:1-9`).

## Testing below the component

Test behaviour through the rendered component first. Test a unit directly when its logic is complex enough to deserve its own cases.

- Call a reducer directly, and get its initial state with `PatientReducer(undefined, { type: '@@INIT' } as any)` (`src/__tests__/reducers/PatientReducer.test.ts:18`).
- Test a model converter in `src/models/` directly, as the files under `src/__tests__/models/pklibraryjs/` do.
- To test autosave or a thunk against the real middleware, build a store with `configureStore`, `RootReducer` and `autosaveMiddleware`, as `EhrImportPageRemountDuplicateCase.test.ts:35-63` does.
- Import `'store'` before the middleware in such a test (`EhrImportPageRemountDuplicateCase.test.ts:11-14`). The store, the autosave middleware and the actions import each other, and entering that cycle through the middleware leaves it undefined.
