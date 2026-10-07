# Guides

Engineering guides for PrecisePK. Each one covers a single job and says when to read it. The rules behind each convention are cited as `path:line` in the repository that defines them.

## Index

| Guide | Covers | Read it when you |
| --- | --- | --- |
| [onboarding.md](onboarding.md) | What PrecisePK is, the repositories, the stack, how work is tracked | Are new, or need the big picture |
| [environment/setup-macos.md](environment/setup-macos.md) | Tools, AWS SSO, GitHub token, first run of the stack and the frontend | Set up a Mac |
| [environment/setup-windows.md](environment/setup-windows.md) | WSL2, Docker Desktop, Windows-only fixes | Set up a Windows machine |
| [environment/make-commands.md](environment/make-commands.md) | Every make target in use, per repository | Need a command to start, link, test or clean something |
| [git/branching.md](git/branching.md) | Branch names, release flow, porting fixes, frontend lane branches, cross-repo branches | Create a branch, cut a release, or port a fix |
| [git/pull-requests.md](git/pull-requests.md) | Titles, squash commits, the template, checks, merge rules, review | Open or review a pull request |
| [git/github-packages.md](git/github-packages.md) | `@preciserx` packages, token scopes, `.npmrc`, Docker build secret, publishing | Install private packages or publish one |
| [platform/ci-cd.md](platform/ci-cd.md) | Pull request checks, Amplify, Jenkins image builds, package publishing, Jenkins servers | Ship something or debug a pipeline |
| [platform/licensing.md](platform/licensing.md) | License names and expiry, institution schemas, site and user types, drug packages, feature flags | Touch access, licenses or drug availability |
| [frontend/react.md](frontend/react.md) | Component layout, props, hooks, Chakra UI, translations, Datadog masking | Write or review a component |
| [frontend/redux.md](frontend/redux.md) | Store, action types, thunks, the HTTP wrapper, reducers, selectors, autosave | Add state, an action or an API call |
| [frontend/testing.md](frontend/testing.md) | Vitest, the custom render, store fixtures, MSW mocks, test conventions | Write or debug a frontend test |
| [frontend/eslint.md](frontend/eslint.md) | The ESLint config, running it, the rules that shape the code | Lint your changes |
| [frontend/jsdoc.md](frontend/jsdoc.md) | JSDoc conventions actually used | Document a file or function |
| [pk-library/primer.md](pk-library/primer.md) | Layers, the Drug → model type → study hierarchy, request flow | Start work in PK-Library |
| [pk-library/cpp-style.md](pk-library/cpp-style.md) | Formatting, names, constants, errors, comments | Write or review C++ |
| [pk-library/testing-and-debugging.md](pk-library/testing-and-debugging.md) | GoogleTest, the `TESTING` macro, VS Code, debugging on macOS and WSL | Test or debug the engine |
| [pk-library/models.md](pk-library/models.md) | The one- and two-compartment equations the engine evaluates | Need the maths behind a prediction |
| [pk-library/adding-a-drug.md](pk-library/adding-a-drug.md) | Every change needed for a new drug or study model | Add a drug or a model |
| [pk-library/error-codes.md](pk-library/error-codes.md) | Internal error codes and how they reach JavaScript | Handle or raise an engine error |
| [pk-library/local-population.md](pk-library/local-population.md) | Institution-specific population models | Work on the Local prior |
| [pk-library/drugs/vancomycin.md](pk-library/drugs/vancomycin.md) | Vancomycin settings, model selection, Rodvold 1988, Goti 2018 | Change vancomycin behaviour |
| [pk-library/drugs/carboplatin.md](pk-library/drugs/carboplatin.md) | Carboplatin and the Lindauer 2010 model | Change carboplatin behaviour |
| [pk-library/drugs/teicoplanin.md](pk-library/drugs/teicoplanin.md) | Teicoplanin models and the Trough Range target | Change teicoplanin behaviour |
| [database/testing.md](database/testing.md) | Running and writing PreciseRx-Database tests safely | Touch the Database service. Its suite drops local databases. |

For how the whole system fits together, see the [Codebase Atlas](https://claude.ai/artifact/NDxuSDmUDz114P8W9j6pht).

## Writing and updating guides

Update a guide in the same task as any change that makes it wrong. Follow these rules for every guide:

1. **Pure documentation.** Describe the current state. Don't include notes on how the guide was produced, migration banners, "last verified" lines, disclaimers or provenance marks.
2. **Only what is non-obvious and true.** Leave out general knowledge a competent engineer already has, and link to official documentation instead of re-teaching public tools. Leave out meeting schedules and people's names; refer to roles and channels.
3. **Trace before writing.** Read the code before describing it. Cite the config or code that defines each convention as `path:line`. When the code and older documentation disagree, the code wins.
4. **Human-reader style.**
   - Open with one or two sentences on what the guide covers and when to read it.
   - Gloss internal shorthand on first use.
   - Put one idea in each sentence, and use the active voice.
   - Write list items as complete, actionable sentences.
   - Use tables to compare three or more things, and fenced code blocks for commands.
5. **Maths.** Put a "where" list under every equation. Give each letter one meaning within a guide.
6. **No secrets or identifiers.** Leave out passwords, tokens, keys, account ids, IP addresses and internal hostnames. Say where a secret is stored instead.
7. **Format.** Use GitHub-flavoured Markdown with spaced table pipes (`| --- |`), and no HTML or emoji. Keep each guide as short as its content allows.

When you add a guide, add it to the index above, and to the task table in `style.md` if agents should read it before a task.
