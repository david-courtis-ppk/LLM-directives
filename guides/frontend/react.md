# React components in PreciseRx-Web

This guide covers how components are written in PreciseRx-Web: file layout, props, hooks, styling with Chakra UI, translations, and masking patient data from Datadog. Read it before you add or review a component. Paths are relative to the PreciseRx-Web root, and `.eslintrc` lines are cited where a rule enforces the convention.

## File layout

Components live under `src/components/<Area>/`, one component per `.tsx` file.

| Folder | Holds |
| --- | --- |
| `User/` | The clinical workflow: patient home and search, patient information, Drug Monitoring, steady-state analysis, notes, user settings. |
| `Admin/` | Institution settings, dosing protocols, edit history, patient database. |
| `Analytics/` | Model Analytics and Advanced Analytics. |
| `IAM/` | User account administration. |
| `ExternalPlatform/` | The EHR and Sentri7 import wizard. |
| `Login/`, `Application/` | Sign-in, the app shell, error pages. |
| `Shared/` | Reusable pieces such as `CustomTable`, `Badge`, `Citation` and the settings panels. Check here before writing a new table or input. |

- Put a constant shared by sibling components in a constants file next to them, named `<Feature>Constants.ts` or `Constants.ts`. For example, `src/components/User/DrugMonitoring/SerumLevelGraph/SerumLevelGraphConstants.ts`.
- Put shared types in a `Types.ts` beside the components, as in `src/components/IAM/Types.ts`.
- Put a hook used by one feature next to it as `useX.ts` or `useX.tsx`, for example `src/components/Admin/InstitutionSettings/ProtocolSettingsManager/useTabs.tsx`. Put app-wide hooks and the route guards `withAuth` and `withRole` in `src/hooks/`.
- Import app code by absolute path, such as `components/Shared/Badge`, `actions/PatientActions` or `store`. The aliases are defined in `tsconfig.app.json:3-20`.
- Write components in `.tsx` files. `react/jsx-filename-extension` allows JSX only in `.tsx` and `.ts` files (`.eslintrc:161-169`), and `src/` has no `.js` files.

## Functional components

New components are functional components written as arrow functions (`.eslintrc:177-183`), with a default export at the end of the file. `src/components/User/PatientHome/Search/UnableToLoadCaseModal.tsx` and `src/components/IAM/UserAccounts/EditUserStatus/EditUserStatus.tsx` are good small and medium examples.

```tsx
type EditUserStatusProps = {
    account?: Account;
    handleCloseOverlay: () => void;
    overlayType: EditUserStatusType;
};

const EditUserStatus = ({
    account = DEFAULT_ACCOUNT,
    handleCloseOverlay,
    overlayType,
}: EditUserStatusProps) => {
    const { t } = useTranslation();
    const dispatch = useAppDispatch();
    // ...
};

export default EditUserStatus;
```

### Props

- Declare props as a `type <Component>Props = { ... }` above the component. About 360 component files use `type` and only 4 use `interface`.
- Destructure props, either in the parameter list or on the first line of the body. `react/destructuring-assignment` requires it (`.eslintrc:170-176`).
- Give every optional prop a default in the destructuring, as `account = DEFAULT_ACCOUNT` does above. `react/require-default-props` asks for default arguments, not `defaultProps` (`.eslintrc:213-218`).
- Do not add PropTypes. TypeScript checks props, and `react/prop-types` is off (`.eslintrc:211`). A few older files still import `prop-types`.
- Name callback props after what they handle, such as `handleOnClose` or `onRoleChange`.
- Put each JSX prop on its own line (`.eslintrc:195-201`) and sort props alphabetically (`.eslintrc:203`).
- Import types with `import type` (`.eslintrc:290`).

### Hooks

- Read the store with `useAppSelector` and dispatch with `useAppDispatch`, both exported from `src/store.ts:64-67`. They carry the app's `RootState` and thunk types. Plain `useSelector` and `useDispatch` are not used.
- Use a selector from `src/selectors/` when the same state path is read in more than one place, as in `src/selectors/PatientSelectors.ts`. An inline selector is fine for a one-off read, as in `src/components/IAM/UserAccounts/EditUserAttributes/AccountInfoList.tsx:51`.
- Await a thunk when you need its result, as in `await dispatch(enableAccount(username, sub, userPoolId))`. Thunks that call the API return a promise. See [Redux](redux.md) for what they resolve to.
- Follow the rules of hooks and keep effect dependency lists complete. `plugin:react-hooks/recommended` is enabled (`.eslintrc:11`).

## Class components

About 40 files still define class components, for example `src/components/User/PatientInformation/LabResults/ScrHistory/ScrHistory.tsx`. They are legacy code. Do not write new ones. Edit an existing class component in its current style, and convert one to a function only as its own scoped task.

A class component follows this pattern:

- It reads the store through `connect(mapStateToProps, mapActionsToProps)` and types the result with `ConnectedProps<typeof connector>` (`ScrHistory.tsx:71-97`).
- It gets `t` from the `withTranslation()` HOC and routing from `withRouter()` in `src/hooks/withRouter.tsx`, because react-router 6 has no `withRouter` of its own. The export composes them: `export default withRouter()(withTranslation()(connector(ScrHistory)))` (`ScrHistory.tsx:813`).
- It binds its methods in the constructor (`ScrHistory.tsx:140-159`).
- It orders members as static methods, then lifecycle methods, then everything else, then `render` (`.eslintrc:219-258`).

All 572 `react/destructuring-assignment` warnings in `src/` come from 34 of these class component files, because their methods read `this.props` directly.

## Styling with Chakra UI

The app uses Chakra UI 2.8. `src/index.tsx:20-24` mounts `ChakraProvider` with the `precisepkTheme` theme.

- Build layouts from Chakra components and style props, not new CSS files. Only a handful of components still import a `.css` file.
- Use the shared text styles from `src/styles/textStyles.ts` through the `textStyle` prop, as in `textStyle="helper-text"`.
- Change the look of a Chakra component for the whole app in `src/styles/components/`, then register it in `src/styles/theme.ts:33-63`. Colors live in `src/styles/colors.ts`.
- Use Chakra's `useToast` for notifications, `react-icons` for icons and `react-spinners` for loading indicators, as the existing components do.
- See the [Chakra UI v2 documentation](https://v2.chakra-ui.com/docs/components) for component APIs.

## Translations

Every string a user sees goes through react-i18next.

- In a functional component, call `const { t } = useTranslation();` and prefix each key with its namespace, as in `t('patient_case_management:headers.failed_to_load_case')`. This `namespace:key` form is used about 2,000 times in `src/components/`.
- A class component gets `t` from `withTranslation()` instead.
- A namespace is one JSON file, `public/locales/<language>/<namespace>.json`, loaded over HTTP (`src/i18n.ts:35-37`). The default namespace is `common` (`src/i18n.ts:40-41`).
- To add a namespace, create `public/locales/en/<namespace>.json` and add its name to the `namespaces` list in `src/utils/i18nextUtility.ts`. `PrecisePKWrapper` loads that list when the app starts (`src/components/Application/PrecisePKWrapper.tsx:51`). If the EHR import wizard uses it, add it to `epNamespaces` in the same file too.
- English has 71 namespaces. Spanish, Korean, Thai and Chinese have 54 each, and a missing file falls back to English (`fallbackLng: 'en'`, `src/i18n.ts:26`).
- Tests render translation keys, not English text. See [Testing](testing.md).

## Masking patient data from Datadog

Datadog RUM (real user monitoring) records every session outside development, including a session replay (`src/utils/DatadogRumUtility.ts:13-35`). The default privacy level is `mask-user-input` (`DatadogRumUtility.ts:19`). That masks form inputs only. Any other text the page renders is recorded as shown.

- Add `data-dd-privacy="mask"` to every element that renders PHI (protected health information), such as a patient name, patient ID, birth date or note text. `src/components/User/PatientHome/ActiveCaseSnapshot.tsx:207` and `:233` are examples.
- In a `CustomTable`, every cell is masked unless its column sets `dataDDPrivacy` (`src/components/Shared/CustomTable/TableContent.tsx:46-48`). Set `dataDDPrivacy: 'mask-user-input'` only on columns that hold no PHI. In `src/components/Admin/EditHistory/EditHistory.tsx:138-191`, only the action and site columns do.
- Pass a `dataDDPrivacy` prop through reusable components that render PHI, as `src/components/User/UserSidebar/SummaryItem.tsx:69-74` does.
- Datadog names a click action after the clicked element's text. It honours the mask in those names only when `enablePrivacyForActionName: true` is passed to `datadogRum.init` (RX-3684, the fix for patient names leaking into click action names). Check that `initializeDatadogRum` sets it on the branch you work on.
- Never put PHI in `datadogRum.addAction` or `datadogRum.addError` payloads. Privacy attributes apply to recorded page content, not to data you send yourself.
- See Datadog's [browser privacy options](https://docs.datadoghq.com/real_user_monitoring/session_replay/browser/privacy_options/) for what each level masks.
