# ESLint in PreciseRx-Web

This guide covers PreciseRx-Web's ESLint configuration, how to run it locally, the rules that shape the code, and how to set up an editor. Read it before you open a pull request or when a lint warning puzzles you. Paths are relative to the PreciseRx-Web root.

## What is configured

The configuration is `.eslintrc`, a JSON file with comments, read by ESLint 8.57.

- It extends `airbnb`, `plugin:@typescript-eslint/recommended`, `plugin:import/typescript` and `plugin:react-hooks/recommended` (`.eslintrc:7-12`). See the [Airbnb React style guide](https://airbnb.io/javascript/react/) for the base rules.
- It parses TypeScript with `@typescript-eslint/parser` (`.eslintrc:16`).
- It loads the `only-warn` plugin (`.eslintrc:26`), which reports every rule as a warning. See [The only-warn caveat](#the-only-warn-caveat).
- It declares the browser and Jest environments and the Vitest global `vi` (`.eslintrc:2-15`).
- It resolves absolute imports such as `components/Shared/Badge` from `src/` (`.eslintrc:293-301`).

## Nothing runs ESLint for you

- `package.json` has no lint script.
- The pull request workflow, `.github/workflows/build-and-test-workflow.yml`, installs, builds and tests, but does not lint.
- The Vite dev server does not lint. Its only checker plugin runs TypeScript (`vite.config.ts:72-78`).

TypeScript is the check that actually fails a build. `pnpm build` runs `tsc -b` with `strict`, `noUnusedLocals` and `noUnusedParameters` on (`tsconfig.app.json:41-43`). ESLint is advisory, and running it on your changes is up to you.

## Running it

Run ESLint from the PreciseRx-Web root through pnpm, which uses the version in `node_modules`.

```sh
# Lint the files your branch changed, which is the useful everyday check.
pnpm exec eslint $(git diff --name-only --diff-filter=d main...HEAD -- '*.ts' '*.tsx')

# Lint and auto-fix one file.
pnpm exec eslint --fix src/components/User/PatientHome/PatientHome.tsx

# Lint the whole tree. This takes over a minute.
pnpm exec eslint src
```

- `pnpm exec eslint src` picks up `.ts` and `.tsx` files without an `--ext` flag, because the TypeScript preset declares overrides for those files.
- Add `--cache` to speed up repeat runs. The cache file `.eslintcache` is already gitignored.
- `npx eslint` works too, but `pnpm exec` is the form that matches the repository's package manager.

## The only-warn caveat

The `only-warn` plugin turns every error into a warning. That includes rules `.eslintrc` sets to `"error"`, such as `camelcase` (`.eslintrc:34-42`) and `@typescript-eslint/no-unused-vars` (`.eslintrc:291`), and everything the presets set to error.

- ESLint therefore exits with status 0 no matter what it finds.
- To make a run fail on any finding, add `--max-warnings 0`. Use it on the files you changed, not on `src/`.
- The whole tree currently reports about 6,400 warnings and no errors. Most are `@typescript-eslint/no-explicit-any` and `max-len`. Do not try to clear them outside a scoped task.

## Rules that shape the code

`--fix` corrects the formatting rules in this table, except `max-len`.

| Rule | Setting | What it means when you write code |
| --- | --- | --- |
| `indent`, `react/jsx-indent`, `react/jsx-indent-props` | 4 spaces, `case` indented once (`.eslintrc:69-75`, `:187-194`) | Indent with four spaces everywhere, including JSX. |
| `brace-style` | `stroustrup` (`.eslintrc:30-33`) | Put `else`, `catch` and `finally` on a new line after the closing brace. |
| `max-len` | 120 characters, URLs ignored (`.eslintrc:88-95`) | Wrap lines at 120 characters. |
| `operator-linebreak` | `&&` and `\|\|` after, `?` and `:` before (`.eslintrc:141-152`) | End a wrapped line with `&&` or `\|\|`. Start the continuation line of a ternary with `?` or `:`. |
| `react/jsx-max-props-per-line` | 1, always (`.eslintrc:195-201`) | Put each JSX prop on its own line. |
| `react/jsx-sort-props` | on (`.eslintrc:203`) | Sort JSX props alphabetically. |
| `react/function-component-definition` | arrow functions (`.eslintrc:177-183`) | Write components as `const Name = (props) => { ... }`. |
| `react/require-default-props` | default arguments (`.eslintrc:213-218`) | Give optional props a default in the parameter list, not `defaultProps`. |
| `react/prop-types`, `react/react-in-jsx-scope` | off (`.eslintrc:211-212`) | Type props with TypeScript, and do not import React just for JSX. |
| `react/destructuring-assignment` | always (`.eslintrc:170-176`) | Destructure props and state before use. |
| `camelcase` | identifiers only, not properties (`.eslintrc:34-42`) | Keep snake_case store keys, but rename them when you destructure, as in `last_saved_inputs: savedInputs` (`src/middlewares/autosaveMiddleware.ts:49`). |
| `@typescript-eslint/consistent-type-imports` | on (`.eslintrc:290`) | Import types with `import type`. |
| `@typescript-eslint/no-unused-vars` | replaces the base rule (`.eslintrc:129`, `:291`) | Remove unused variables and imports. |
| `import/extensions` | never for `.ts`, `.tsx`, `.js`, `.jsx` (`.eslintrc:59-68`) | Import modules without their file extension. |
| `import/prefer-default-export` | on, from `airbnb` | Export a single-export module as default, or disable the rule with a comment as `src/selectors/PkParametersSelectors.ts` does. |
| `react-hooks/rules-of-hooks`, `react-hooks/exhaustive-deps` | on, from `plugin:react-hooks/recommended` (`.eslintrc:11`) | Call hooks unconditionally and list every dependency of an effect. |

Two rules are switched off on purpose. `no-undef` is off because TypeScript already reports undefined names (`.eslintrc:103`). `no-duplicate-imports` is off in favour of `consistent-type-imports` (`.eslintrc:105`), so a module can have one `import type` line and one value import from the same package, as `src/store.ts:8-9` does.

All 572 `react/destructuring-assignment` warnings come from class components, whose methods read `this.props` directly. Functional components in `src/` have none.

## Editor setup

- In VS Code, install the [ESLint extension](https://marketplace.visualstudio.com/items?itemName=dbaeumer.vscode-eslint). With ESLint 8.57 it reads `.eslintrc` by default.
- To fix on save, add `"editor.codeActionsOnSave": { "source.fixAll.eslint": "explicit" }` to your user settings. The repository ignores `.vscode/`, so there are no shared workspace settings.
- To fix a file on demand, run "ESLint: Fix all auto-fixable Problems" from the Command Palette.
- Do not format this repository with Prettier. Prettier 3 is installed, but the repository has no Prettier configuration, so it applies its defaults of double quotes and two-space indentation. Those contradict the single quotes and four-space indentation that the ESLint configuration requires.
