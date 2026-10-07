# Style

Conventions for PreciseRx repositories. Each rule comes from a guide in `/Users/david/git/LLM-directives/guides/`, which gives the detail and the `path:line` behind it. In other repositories, follow that repository's own conventions.

## Read the guide first

| Before you | Read |
| --- | --- |
| Set up a machine or run the stack | `guides/environment/setup-macos.md` or `setup-windows.md`, and `make-commands.md` |
| Create a branch, open a PR, or port a fix to a release | `guides/git/branching.md`, `guides/git/pull-requests.md` |
| Install or publish `@preciserx` packages | `guides/git/github-packages.md` |
| Change CI, image builds or publishing | `guides/platform/ci-cd.md` |
| Write a frontend component, state, test, lint fix or JSDoc | the matching file in `guides/frontend/` |
| Work in PK-Library, add a drug or model, or touch the maths | `guides/pk-library/` (start with `primer.md`) |
| Change licensing, drug packages or the Local prior | `guides/platform/licensing.md`, `guides/pk-library/local-population.md` |
| Run PreciseRx-Database tests | `guides/database/testing.md`. The suite drops and recreates local databases. |

## PreciseRx repositories

- Use pnpm 11 on Node 24 or newer. Never use npm or yarn.
- Name branches `feature/rx-####` or `bugfix/rx-####`, with the Jira key in lowercase. A fix to a cut release needs a PR into `stable/vX.Y.Z` and a counterpart into `main`.
- Title a PR as a sentence-case summary followed by the key, as in `Refresh on whichever token expires sooner (RX-3625)`. Fill in the sections of `.github/pull_request_template.md`, and write them for a reader outside the workstream.
- Merges are squash-only. The subject on `main` is the PR title, or the commit subject of a single-commit PR. Branch commit messages are copied into the body. See `guides/git/pull-requests.md` for the format.
- Never let PHI reach logs, URLs or telemetry payloads.
- In the umbrella, sync submodules with `make checkout-all <branch>`, never `git submodule update`.

## PreciseRx-Web

- Write new components as arrow-function components with a default export. Declare props as `type XProps`, destructure them with defaults for optional props, and don't add PropTypes. Don't write new class components.
- Read the store with `useAppSelector` and dispatch with `useAppDispatch`. Put a selector used in more than one place in `src/selectors/`.
- Style with Chakra UI props and the shared text styles, not new CSS files.
- Send user-facing strings through `t('namespace:key')`. Register a new namespace in `src/utils/i18nextUtility.ts`.
- Put `data-dd-privacy="mask"` on elements that render PHI. Never put PHI in `datadogRum.addAction` or `addError`.
- Format with 4-space indents, Stroustrup braces, a 120-column limit, one JSX prop per line and sorted props. Check your files with `pnpm exec eslint <files> --max-warnings 0`, because the `only-warn` plugin otherwise exits 0. Don't run Prettier.
- Declare action types in `src/actions/Types.ts`. Call the API only through `axiosRequestWrapper` in a thunk, and handle its `null` result. Reducers are hand-written `switch` functions that must return new objects, because the immutability check is off.
- When you add a saved case input, add its path to `src/utils/SaveUtility.ts`, and decide how `NEW_PATIENT` treats it.
- Put tests under `src/__tests__/`, mirroring the source path. Import `render` from `utils/tests/TestsUtility` and build MSW handler URLs from `serverApiPaths`. Translations render as keys in tests. Assert on keys. Drive the UI with `userEvent`.
- Open files with a `@fileoverview` comment. In TypeScript, write `@param name Description` without a type.

## PK-Library (C++20)

- Apply `.clang-format` by hand, because the committed file doesn't load in current clang-format releases: tabs four wide, 80 columns, `const T& x`, opening braces on the same line, `else` on a new line.
- Name types in PascalCase and functions and variables in snake_case. Put constants in UPPER_SNAKE_CASE inside `PKConstants`. Name study models `DrugAuthorYear`.
- Write drug classes and study models as header-only `.hpp` files that start with `#pragma once`.
- Throw through the `THROW_*` macros. Use `-1` for "not set".
- Comment with one-line `//` above declarations. Use Doxygen only where the file already does.
- `binding.gyp` lists sources by hand. A new `.cpp` file must be added there as well as picked up by CMake.

## Writing for people

Learnt from David's line-by-line RX-3699 reviews. The rules cover text a person reads: comments, doc blocks, test names, translation strings, commit messages, PR descriptions and replies to David.

Write for a reader outside the workstream. A sentence earns its place by answering a question that reader has. When a sentence answers no question, cut it. When the reader has to decode it first, rewrite it.

Absolutes belong in hard rules, such as "Never let PHI reach logs". In descriptions they overclaim.

### Say what it is for, in the reader's terms

A true statement the reader cannot connect to the feature is noise. Name the result it produces or the caller it serves.

```txt
Bad:  Gives the chi-square tail, which has no closed form.
Bad:  Used because the chi-square tail is Q at half arguments, and computing Q directly keeps small p-values accurate.
Good: Gives the chi-square tail for fit p-values.
```

### State the exception, not the default

A reader applies a statement to the whole set and assumes the obvious count. Leave out "every", "each", "all", "one", "a single" and "exactly" when they state the default reading, and drop "the" before general plurals. Keep a quantifier when it changes the meaning, as with all versus some, and write it as "all Xs are Y". Do not use "every" as a universal quantifier.

```txt
Bad:  Graph bar for each dose, in hours from the graph start.
Good: Graph bars for doses, in hours from graph start.

Bad:  Rates the case under every other model for the route.
Good: Rates the case under other models for the route.

Bad:  Flags levels more than 2× from the population prediction. Works with one level.
Good: Flags levels more than 2× from the population prediction.

Good: Empty when all levels are flagged.
Good: Needs more counted levels than fitted parameters to detect a poor fit.
```

The last two keep their quantifier or limit because the reader would assume otherwise.

### Cut disclaimers and negatives

A clause saying what something does not do, or a definition the reader did not need, is bloat. Ask "why would the reader care?". Keep a negative when the reader has to act on it: a `@returns` that can be null, or a clinician needing to know a preview leaves dosing unchanged.

```txt
Bad:  Population prior of another model for this patient, without storing it.
Good: Population prior of another model for this patient.

Bad:  Marks borderline entries. The rating uses the overall thresholds.
Good: Marks borderline entries.

Bad:  @param model Model to fit instead of the selected one.
Good: @param model Model to fit. Defaults to the selected one.

Good: @returns The view, or null if the response has no graph.
Good: Previews the fit in the Fit tab. Dosing uses the model's prior.
```

### No implication chains or contrasts

Avoid "X, so Y", "X, which Y", "X, which means Y", "X, therefore Y", "X, because Y" and "Not X, but Y". State the action and its purpose, split cause and effect into two sentences, or say what the thing is.

```txt
Bad:  One request at a time. A choice made meanwhile runs next, so dragging a slider sends at most two requests.
Good: Queue the latest choice behind the running request to limit engine load while a slider is dragged.

Bad:  Levels with under 5% of the latest level's weight barely move the fit, so the rating ignores them.
Good: Ignore levels with under 5% of the latest level's weight. They barely move the fit.

Bad:  Should rate Good by curve match, because the curve passes through a single level
Good: Should rate Good by curve match, with the curve passing through the level

Bad:  Ratings are not computed in the engine, but in the frontend.
Good: Keep ratings, thresholds and change windows in the frontend.
```

### Clear beats short

A terse line the reader has to decode fails them as much as padding does. Name things the reader knows, and say what a term refers to on first use.

```txt
Bad:  Engine-sourced per-level evidence; no reversal.
Good: Read the predicted level, measurement SD and time weight of a level from the engine's fitting session.
```

### No labels, stock openers or staging

Do not prefix lines with invented categories such as "Numerical:". Do not open with "Used because", "This function", "Note that", "Helper to", "This commit introduces", "We now" or "Let's". Start with the verb or noun that carries the meaning. Skip AI prose such as "robust", "seamless" and "It's worth noting".

```txt
Bad:  Numerical: gives the 1/Γ(a) factor in `gammaQ` in log space, because Γ(a) overflows a double above a ≈ 171.
Good: Log to prevent numerical overflow.
```

### Never hide a limit behind a result

A clinician acts on what a rating or number says. Text that turns a blind spot into a result, or plays down a clinical value, misleads them.

```txt
Bad:  With one level, the curve passes through it and the rating is Good.
Good: Needs more counted levels than fitted parameters to detect a poor fit.

Bad:  This approximation is more than good enough for visual display purposes.
Good: Error below 2e-10, far below the 0.001 resolution of the displayed p.
```

When the text is right and the behaviour is wrong, such as a green Good shown for a fit the method cannot judge, raise the behaviour with David.

### Keep user-facing text true when settings change

A translation string must hold for any value a setting can take.

```txt
Bad:  How much we should consider this level in the goodness of fit. Older levels are weighted lower. Outliers are capped at an SD of 3.
Good: How much the level counts toward the fit rating. Older levels count less.
```

The cap is a setting, and the cap setting's tooltip describes it.

### Check the whole diff before handing it over

Before calling work ready, check comments, doc blocks, test names, translation strings and the commit message against these rules. When David flags one line, fix the same fault across the diff before replying. A first pass can search for banned words and chains, then read what the search cannot catch: disclaimers, hidden limits and wording that needs decoding.

```sh
grep -rn -i -E "((^\s*(\*|//)|it\(').*(\b(every|each|only|always|never|concrete|alone)\b|, so |, which |which means|therefore|, because))" <changed files>
grep -n -i -E "\b(every|each|only|always|never|concrete|alone)\b|, so |, which |which means|therefore| rather than |, because" public/locales/en/<namespace>.json
```

## Comments and doc blocks

`guides/frontend/jsdoc.md` sets the JSDoc tag format. These rules set the content.

### Default to no comment

Write an inline comment for a reason the code cannot show: a constraint, an invariant or a gotcha. When editing code, add no comment that describes the edit or restates the line below.

```ts
// Bad: these restate their line.
// Shows the Fit tab in development, or when VITE_ENABLE_MODEL_FIT is true.
const FLAG_COLOR = '#E53E3E'; // red.500
// 80% of the Serum Level Graph's size.
const SCALE = 0.8;
// Approximates Q by a series when x < a + 1, stopping once terms change the sum by under 1e-14.

// Good: gotchas the code does not show.
// Redraw the axes after renders. D3 draws into the axis groups outside React.
// Infinity approximation
let c = 1 / FPMIN;
```

### The shape of a doc block

Line 1 names the thing: its scientific or plain name, the method, and the accuracy or limit. Line 2 gives its reason, in a few words. Then the tags. David's own example is the model:

```ts
/**
 * Natural log of the gamma function, ln Γ(x), by the Lanczos approximation. Error below 2e-10 for x > 0.
 * Log to prevent numerical overflow.
 *
 * @param x Positive real.
 * @returns ln Γ(x).
 */
```

Exported and module-level functions, and functions inside components, get a block with a `@param` per argument and a `@returns` when they return a value. Keep the lines short.

```ts
/**
 * Rating from the share of counted weight carried by flagged levels.
 *
 * @param levels Levels.
 * @param verdicts Verdict per level.
 * @returns Good with no flags, Poor when flags carry at least half the weight, otherwise Moderate.
 */
```

### Put the explanation where the reader meets the code

Say "approximation" above the loop that approximates. Explain a branch at the branch.

```ts
// Series approximation, which converges fast for x < a + 1.
if (x < a + 1) { ... }
// Continued fraction approximation (modified Lentz method) for the remaining x.
```

### Magic values and maths

Give a literal a comment when its name and use leave its purpose unclear. Cite the source of copied numerical code once, near the top, for reviewers to check the constants against.

```ts
// 2.506628274631 is √(2π).
// `logGamma`, `gammaQ` and `erfc` follow Press et al., Numerical Recipes in C, 2nd ed. (1992), sections 6.1 and 6.2.
```

For a statistical function, the reason line names the equation it serves. A reviewer's first question is whether the function is machinery or a modelling choice.

```ts
 * Chi-square survival function, P(χ²_dof ≥ x) = Q(dof / 2, x / 2). `dof` need not be an integer.
 * Plausibility p and curve match overall p.
```

### A comment that warns about coupling is a design bug

When a comment has to say "mirrors X in another repository, change both", remove the duplication. RX-3699 first shipped a frontend `recoverPrediction` that solved the engine's residual backwards for the predicted level. The fix was for the engine to return the prediction.

## Code structure

Also from the RX-3699 reviews.

- **The engine returns facts, the frontend interprets them.** Predictions, SDs, weights, objectives and the scale used come from PK-Library. Ratings, thresholds and labels stay in the frontend, where they can change without an engine release. The frontend does not reverse, re-derive or copy an engine formula.
- **Reuse existing types.** Before declaring an interface, search `src/types/pklibrary/`, the reducers and `src/types/database/`. Derive a narrower type with `Pick`, or export the existing type.

  ```ts
  // Bad
  interface FittingSettingsLike { standard_error: number; fixed_error: number; ... }
  // Good
  fittingSettings: Pick<DefaultFittingSettingsResponse, 'objective_function'>;
  ```

- **Keep feature logic in the feature folder.** `src/utils/` holds helpers used across the app. Move a helper there once a second feature needs it.
- **Name files as their folder does.** In `components/User/DrugMonitoring/`, non-hook `.ts` files are PascalCase (`FitEvidence.ts`, `SerumLevelGraphUtilities.ts`). Hooks stay `useThing.ts`.
- **Check import case after a rename.** macOS ignores case. A stale `./fitView` import then works locally and fails on Linux CI. After renaming, check imports against the exact file names.
- **Type-check with `tsconfig.app.json`.** `tsc -p tsconfig.json` checks nothing in PreciseRx-Web. Run `pnpm exec tsc -p tsconfig.app.json --noEmit` with `pnpm exec eslint <files> --max-warnings 0`.
- **Check for a library before hand-writing maths.** `simple-statistics` is already a dependency. It has `gammaln` and `errorFunction`, and lacks a continuous chi-square tail.

## Commits for review

For now, write branch commits in this form, without a conventional-commit prefix such as `feat(scope):`. Add Claude as co-author.

```txt
Implement the data layer for the Fit tab.

- Fit the case with a previewed prior or another model.
- Suggest another model for the route when it rates higher than the selected one.
- Hold the Fit tab's settings in a context shared by the tab and the graph settings modal.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
```

- The subject is one plain sentence saying what the commit does, ending with a full stop.
- Use 3 or 4 bullets that frame the change for a reader. Leave out file lists, helper names and test counts.
- Add a brief note for an implementation that is unusual or hard to follow.
- Put a release dependency in its own bullet, as in "Needs the fitting session fields added to PK-Library in RX-3699."

```txt
Bad: a bullet per file or function.
- Add `fitCaseWith`, which fits the case with a previewed prior or another model.
- Add `useModelFit`, which combines the case's fit, the prior preview, the rating, the change windows and the model suggestion.
- Add `useModelSuggestion`, which rates the case under the other models for the route.
- Send one preview request at a time.
- Add `FitView`, which builds the Fit tab's data.
- Hold the Fit tab's settings in a context.
```

Shaping the commits:

- A commit is worth reviewing on its own. Fold a 10-line change into the commit that first uses it.
- Order commits by dependency: calculations, then data, then UI. A commit type-checks and passes its tests without the ones after it.
- Split where a part can be deleted and the app still works, such as a graph or a settings panel. A split by layer inside one feature, such as UI without its tooltips, leaves a state nobody ran.
- Put release dependencies in the PR description. A frontend that needs new engine fields ships after the `@preciserx/pk-library-js` bump in Main.

## Replying to David

- **Answer first, in one sentence.** For "What's this?" about `let c = 1 / FPMIN;`, start with "It's the starting value for the modified Lentz method", then the detail.
- **Answer the question asked.** "Does this matter?" gets yes or no, then why. "Why should I care?" gets the consequence.
- **Separate machinery from modelling choices.** Say which one a function is, and name the equation it serves: "Plausibility p = P(χ²_N ≥ J_min)".
- **Read his shorthand literally.** "Gives the chi-square tail for x" meant "replace x with a word".
- **A question is a question.** When David asks "should we…?" or "why…?", answer and recommend. Change code when he says to.
- **Check before agreeing.** Before saying a rule or fix makes sense, apply it to the diff and look for cases it misses. When unsure what he means, ask. Saying "that makes sense" and then breaking the rule is worse than asking.

## Documentation

- The guides and the Codebase Atlas are pure documentation. Their rules are in `guides/README.md` and `atlas/README.md`.
