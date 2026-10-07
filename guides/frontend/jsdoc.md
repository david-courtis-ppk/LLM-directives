# JSDoc comments in PreciseRx-Web

This guide covers the JSDoc comment conventions PreciseRx-Web's code actually uses: file headers, component and function comments, and the Redux tags. Read it before you document a new file or edit the comments of an old one. Paths are relative to the PreciseRx-Web root.

## No generated documentation

JSDoc comments are read in the source and in editor hovers. Nothing generates HTML documentation from them.

- The `docs` script runs `jsdoc -c jsdoc.json` (`package.json:68`), but `jsdoc.json` was deleted in RX-2430 (March 2024). `pnpm run docs` fails with "Cannot parse the config file jsdoc.json".
- The better-docs template is not installed.
- The deleted configuration only matched `.js` files, and `src/` now has none.
- `pnpm docs` without `run` is pnpm's own command for opening a package's web page, not this script.

The better-docs tags that grouped the generated pages, such as `@category` and `@subcategory`, now only help a reader find their way.

## General style

- Start with a description of one to three sentences that says what the thing is for.
- Leave a blank ` *` line between the description and the tags, and between groups of tags.
- Order the tags as `@param`, then `@property`, then `@returns`.
- Indent the continuation of a long tag line further than the tag, as `src/reducers/PatientReducer.ts:234-235` does.
- Point to external documentation with `@see` and a URL, as `src/store.ts:33-34` does.
- Leave the type out of `@param` and `@returns` in TypeScript, and write `@param name Description`. TypeScript already declares the type, and code written in 2026 follows this form (`src/components/IAM/UserAccounts/EditUserAttributes/AccountInfoList.tsx:34-42`). Older files write `{Object}` or `{Void}` types. Leave those as they are unless you are rewriting the comment anyway.

## File headers

About half the files in `src/` open with a `@fileoverview` block before the imports.

```ts
/**
 * @fileoverview Handles account creation by taking in emails, validating them, and sending them to Cognito.
 * Accounts are created and results (success/failure) are displayed to the user.
 */
```

- Describe the file's purpose in one to three sentences, as `src/components/IAM/UserAccounts/CreateAccounts/InviteEmail/InviteEmail.tsx:1-4` does.
- Put the text on the tag's line or indented on the next line. Both forms are common.
- In a test file, use the header to say what behaviour the test pins down and why (`src/__tests__/components/User/DrugMonitoring/MultipleDosageEntries.test.tsx:1-9`).
- Write `@fileoverview`, not `@filedescription`. Only `src/__mocks__/server.ts` and `handlers.ts` use `@filedescription`, which is not a [JSDoc tag](https://jsdoc.app/tags-file).

## Components and functions

- For a functional component, write a description and one `@param` per prop above the component, as `AccountInfoList.tsx:34-42` does.
- Older functional components start the block with `@class ComponentName`, then list props as `@param` and `useState` values as `@property` (`src/components/User/PatientHome/TherapeuticStatus/TherapeuticStatus.tsx:43`). Keep that form when you edit those files. New components do not use `@class`.
- For a function inside a component or module, write a description, a `@param` per argument and a `@returns` when it returns a value (`AccountInfoList.tsx:55-61`).
- For a selector, a `@returns` line describing the value is enough (`src/selectors/PkParametersSelectors.ts`).
- In a class component, document the constructor with `@constructs ClassName` and its props (`src/components/Analytics/GraphComponents/SingleGraph.tsx:77-84`). Document a module-level constant with `@memberof ComponentName` and `@constant {type} NAME` (`src/components/User/PatientInformation/LabResults/ScrHistory/ScrHistory.tsx:41-55`).
- Mark code that is kept but no longer used with `@deprecated`.

## Redux files

Nine action files, nine reducers, `src/store.ts` and `src/utils/StoreUtils.ts` carry a Redux file header. Keep it when you edit those files.

```ts
/**
 * @fileoverview
 *      PatientReducer handles all dispatched actions that will modify the "patient" state tree.
 * @module PatientReducer
 * @category Redux
 * @subcategory Reducer
 */
```

- Set `@module` to the file name, `@category` to `Redux`, and `@subcategory` to `Actions` or `Reducer` (`src/reducers/PatientReducer.ts:1-7`, `src/actions/PatientActions.ts:1-7`). `src/store.ts:1-7` uses `@module Redux` and `@subcategory Store`.
- Document `initialState` with `@constant {Object} initialState`, then one `@property` per field, using dotted paths for nested fields (`src/reducers/PatientReducer.ts:173-243`).
- Give each `case` of a reducer's `switch` a short description of what it does and an `@event ACTION_TYPE` tag (`src/reducers/PatientReducer.ts:373-377`). `DrugReducer.ts`, `PKParametersReducer.ts` and `PatientReducer.ts` follow this. Add an `@event` block when you add a case to one of them.
