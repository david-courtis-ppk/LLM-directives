# PK-Library C++ style and comments

This guide describes the formatting, naming, error-handling and comment conventions that PK-Library's C++ code follows today. Read it before you write or review C++ in `src/packages/cpp/PK-Library`. Test naming lives in [testing-and-debugging.md](testing-and-debugging.md).

The code is C++20 with compiler extensions off (`CMakeLists.txt:4-6`). Much of it predates the current conventions, so the most reliable rule is to match the file you are editing.

## Formatting

`.clang-format` at the repo root defines the house layout. Nothing enforces it: no workflow or Makefile target runs clang-format, and the umbrella's VS Code settings turn format-on-save off for C++ (`PreciseRx-Web-PK/.vscode/settings.json`). The `src/pharmacokinetics/therapeutictarget/auc*` files were reformatted in the commit that added the config, so they show the intended result. Many older files still use spaces and long lines.

The committed file does not load in any clang-format release from 16 to 23. The first error each release reports is:

- clang-format 16 and 17: unknown key `AfterPlacementOperator` (`.clang-format:73`).
- clang-format 18 to 22: the final `---` line, which has no trailing newline (`.clang-format:115`). Removing it exposes further unknown keys, such as `BreakBeforeClosingParen` (`.clang-format:31`).
- clang-format 23: unknown key `BreakBeforeClosingParen` (`.clang-format:31`). It accepts every other key.

Until the file is fixed, apply its rules by hand. When you do run a formatter, format only the lines you changed (for example with `git clang-format`), because reformatting a whole legacy file buries the real change in the diff.

The rules that matter most:

- Indent with tabs, four columns wide, and continue wrapped lines by four columns (`.clang-format:84-89`).
- Keep lines within 80 columns (`.clang-format:83`).
- Attach `*`, `&` and `const` to the left: `const Patient& patient` (`.clang-format:25-27`).
- Put opening braces on the same line for classes, functions and control statements. Start `else`, `catch` and a do-while's `while` on a new line after the closing brace (`.clang-format:42-58`).
- When arguments wrap, put each group on its own indented line and the closing parenthesis on its own line (`AlignAfterOpenBracket: BlockIndent`, `.clang-format:16`).
- Short `if`/`else` bodies, loops, case labels and functions may stay on one line (`.clang-format:100-101`, `111-113`).
- Indent `case` labels and everything inside a namespace, and outdent access specifiers to the class's own column (`.clang-format:94`, `98`, `107`).
- Separate definitions with a blank line, and sort includes case-insensitively in regrouped blocks (`.clang-format:41`, `103-104`).

A function laid out this way looks like this (`src/drug/vancomycin.hpp:731-747`):

```cpp
    double default_interval(
        const Patient& patient, const BayesContainer& pk, const Route& route
    ) const override {
        if (pk.empty()) return -1;

        double t12 = this->model()->half_life(patient, pk).first;

        if (t12 < 8.0) return 8.0;
```

## Files

- Name files in lowercase. Older files run words together (`bayescontainer.h`, `onecompartment.cpp`). Newer ones use underscores (`linear_pk.h`, `onecompartment_general.h`, `study/cefepime/cefepime_an_2023.hpp`). Follow the other files in the folder.
- Write drug classes and study models as header-only `.hpp` files (`src/drug/*.hpp`, `src/pharmacokinetics/study/**/*.hpp`). Use a `.h` and `.cpp` pair for everything else. A few `.hpp` headers also have a `.cpp`, such as `model.hpp`, `pkconstants.hpp` and `pkexception.hpp`.
- Start every header with `#pragma once`. All but ten headers already do.
- Group long headers into sections with `#pragma region` and `#pragma endregion`, as `drug.hpp` and `model.hpp` do.

## Names

| Kind | Convention | Example |
| --- | --- | --- |
| Classes and structs | PascalCase | `BayesContainer`, `DosageRegimen` |
| Study model classes | Drug, first author and year in PascalCase | `CefepimeAn2023`, `VancomycinRodvold1988` |
| Functions and methods | snake_case | `population_values()`, `fitted_param_names()` |
| Variables and members | snake_case | `infusion_time`, `drug_settings` |
| Constants | UPPER_SNAKE_CASE, usually inside `PKConstants` | `PKConstants::Drug::Vancomycin::DOSAGE_INCREMENT_ADULT` |
| Enumerators | UPPER_SNAKE_CASE, usually in an `enum class` | `FullRoute::INTERMITTENT_IV_INJECTION`, `BayesParameter::Name::CL` |
| Macros | UPPER_SNAKE_CASE | `THROW_INVALID_ARGUMENT`, `TESTING` |

- Static factories are mixed. `Drug::init` and `SteadyStateTarget::build` are snake_case, while `DosageRegimen::NoDose` and `DosageRegimen::FixedDoses` are PascalCase. Follow the class you are editing.
- A leading underscore marks a few backing members that have a same-named accessor, such as `Drug::_model` behind `Drug::model()`.

## Constants and "not set" values

- Declare shared constants as `extern const` in `src/common/pkconstants.hpp` and define them in `pkconstants.cpp`, grouped by drug. Cefepime is a compact example (`pkconstants.hpp:1021-1043`, `pkconstants.cpp:1463-1484`). Drug names, model display names, source strings, dose increments and graph step sizes all live there.
- Keep a study's published coefficients inline in its formula function, next to the `Citation` that shows them to clinicians (for example `adalimumab_berends_2018.hpp:102-127`).
- Use `-1` to mean "not set" for doses, intervals, ranges and similar optional numbers. `DosageRegimen` initialises every field to `-1` (`src/pharmacokinetics/doseprediction/dosageregimen.h:43-54`), and `Drug::default_therapeutic_range` returns `{-1, -1}` when a drug has no default (`drug.cpp:417-419`).
- Units are plain `double`s. Each drug's `units()` declares its dose, volume, time and concentration units, and code converts with the factors on `UnitSettings`, such as `concentration_to_dose_correction()`.

## Errors

- Throw through the macros in `src/utils/logger.h:46-50`: `THROW_INVALID_ARGUMENT`, `THROW_OUT_OF_RANGE`, `THROW_RUNTIME_ERROR` and `THROW_PK_EXCEPTION`. The first three prefix the message with the file, line and function. The header says to always use them, although some `set_model()` overrides still `throw std::invalid_argument` directly (`src/drug/cefepime.hpp:117`).
- Use `THROW_PK_EXCEPTION(code, message)` only when the frontend must react to a specific failure. [error-codes.md](error-codes.md) lists the codes and how they reach JavaScript.

## Comments and Doxygen

Two comment styles coexist.

- **One-line `//` comments** above declarations are the norm. `drug.hpp` and `model.hpp` document almost every virtual function this way.
- **Doxygen blocks** appear in about 30 of the 364 files under `src/`, mostly in `src/settings/`, `src/warning/`, the therapeutic-target headers, `patient/labreport.h` and `patient/akiassessment.h`. `src/settings/infusion_time_protocol.h` is a clean example.

When a file already uses Doxygen, extend it in the same form:

```cpp
/**
 * @file file_name.h
 *
 * One to three sentences on what the file contains.
 */

/**
 * @class ClassName
 *
 * @brief One sentence on what the class is for.
 *
 * @details Longer explanation, only when the brief is not enough.
 */
class ClassName {
public:
    /**
     * @brief One sentence on what the function does.
     *
     * @param dose what the parameter means, with its unit
     * @param interval what the parameter means, with its unit
     *
     * @return what the function returns, and what -1 or an empty value means
     */
    std::optional<double> function_name(double dose, double interval) const;

    double member_name = -1; //!< What the member holds.
};
```

- Leave a blank comment line between the brief, the details, the parameters and the return value. Keep consecutive `@param` lines together.
- Use `@return`. The code uses it 126 times and `@retval` only 10 times.
- Document members with a trailing `//!<`. Doxygen ignores plain `//` comments.

The `Doxyfile` at the repo root is a Doxygen 1.8.17 template, and nothing runs it. Its `EXCLUDE_PATTERNS` contains `*/src/*` (`Doxyfile:936-941`), and those patterns are matched against absolute paths (`Doxyfile:933-934`). Inside the umbrella checkout every path contains `/src/`, so running `doxygen` there excludes every file. It would also write to `../../PreciseRx-Web-PK-cpp-doc` relative to the working directory (`Doxyfile:61`). See the [Doxygen manual](https://www.doxygen.nl/manual/index.html) for command syntax.
