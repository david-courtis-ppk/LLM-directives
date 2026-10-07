# PK-Library testing and debugging

This guide covers building and running PK-Library's GoogleTest suite, writing tests, the `TESTING` macro, the VS Code setup, and stepping through the code on macOS and on Windows through WSL. Read it before you run or add C++ tests, or when a breakpoint will not bind.

Commands run from `src/packages/cpp/PK-Library` unless a step says otherwise.

## Prerequisites

- CMake 3.17 or newer (`CMakeLists.txt:1`), Ninja, ccache and a C++20 compiler. The Makefile always compiles through ccache (`Makefile:2-3`).
- On macOS, the Xcode Command Line Tools provide clang and `lldb`. Install the rest with `brew install cmake ninja ccache`.
- On Linux or WSL, install `build-essential`, `cmake`, `ninja-build`, `ccache` and `gdb` with `apt`.
- Network access on the first configure. CMake downloads GoogleTest at a pinned commit (`test/CMakeLists.txt:9-13`).

## Build and run

```sh
make build-test-cpp   # configure build/ with Ninja and compile the library and tests
make test-cpp         # run ./build/test/PKLibrary_tst
```

- `build-test-cpp` runs `cmake .. -G Ninja && ninja` inside `build/` (`Makefile:23-27`). `test-cpp` runs the binary (`Makefile:57-58`). CI runs the same two targets on every pull request to `main` (`.github/workflows/unit-test-workflow.yml`).
- CMake globs `*.cpp` under `src/` and `test/` with `CONFIGURE_DEPENDS` (`src/CMakeLists.txt:1`, `test/CMakeLists.txt:18`). New files join the build on the next `make build-test-cpp` without any list to edit.
- Every test file compiles into the single executable `build/test/PKLibrary_tst` (`test/CMakeLists.txt:25`).

`make test-cpp` takes no filter. Call the binary directly to pick tests, using GoogleTest's flags (see the [GoogleTest advanced guide](https://google.github.io/googletest/advanced.html#running-a-subset-of-the-tests)):

```sh
./build/test/PKLibrary_tst --gtest_list_tests
./build/test/PKLibrary_tst --gtest_filter='CefepimeAn2023.*'
./build/test/PKLibrary_tst --gtest_filter='BayesContainerTest.*-*Throws*'
./build/test/PKLibrary_tst --gtest_filter='DISABLED_CyclosporinePress2010.*' --gtest_also_run_disabled_tests
./build/test/PKLibrary_tst --gtest_filter='CefepimeAn2023.*' --gtest_break_on_failure
```

- A filter is `Suite.Test` with `*` wildcards. Separate patterns with `:`, and put the patterns to exclude after a `-`.
- Tests whose suite or name starts with `DISABLED_` are skipped unless you pass `--gtest_also_run_disabled_tests`.
- `--gtest_break_on_failure` stops a debugger at the first failing assertion.

The bindings have their own suites:

```sh
pnpm install                                              # once, for node-gyp and node-addon-api
make build-pk-library-js && make test-pk-library-js t='therapeutic_target'
make test-pk-library-python k='dosageregimen'
```

- The Node suite is Jest under `bindings/nodejs_test/`. `t` becomes Jest's `-t` filter (`Makefile:62-67`).
- The Python target builds `bindings/python/build` and runs pytest with `k` as its `-k` filter (`Makefile:29-41`). It needs `pytest` on your Python.
- To try a local binding build inside the running backend containers, use the umbrella's `make link-pk-library-js` (`PreciseRx-Web-PK/Makefile:163-183`).

## Writing tests

- Put the file in `test/`. Name it after what it tests: `model.test.cpp` for `model.cpp`, or the study class for a study model (`CefepimeAn2023.test.cpp`). Older files use other forms, such as `bayescontainertest.cpp` and `teicoplanin_kim_2024.test.cpp`.
- Include `"pch.h"` first. It defines `TESTING` and includes GoogleTest (`test/pch.h:8-10`). A library header included before it is parsed without `TESTING`.
- Name the suite after the class under test: `TEST(OneCompartment, ...)`, `TEST(CefepimeAn2023, ...)`, or a fixture such as `TEST_F(TeicoplaninKim2024Test, ...)`.
- Name the test after the behaviour. Older tests use `function___descriptor` with three underscores, for example `simulate_dosage_regimen___decay_time_added_to_time_reached_steady_state`. Newer tests use PascalCase, for example `CLMatchesDocumentation`. Either is accepted.
- Build patients with the helpers in `test/testdata.hpp`, such as `TestData::quick_patient(settings, weight, height, age, scr)`, `quick_dosage_history` and `quick_level_history`.
- For a study model, check each population parameter against a value computed by hand from the paper for one sample patient, with `ASSERT_NEAR`. `test/CefepimeAn2023.test.cpp` is the pattern to copy.
- Several suites loop over `Drug::all_supported_drugs()`, so a newly listed drug is exercised automatically (`test/bayescontainertest.cpp:45-225`, `test/steadystatetest.cpp:9-60`). Some of those loops skip named drugs, so check that yours is not excluded by mistake.

## The TESTING macro and FRIEND_TEST

- `test/pch.h:8` defines `TESTING`. Library headers use it to widen access for tests, for example `#ifdef TESTING` followed by `public:` in `model/linearmodel.h:82-84`, `model/onecompartment.h:108` and `model/twocompartment.h:243`.
- The `PKLibrary` library target is compiled without `TESTING`. The same class is therefore declared one way in the library and another way in the test binary. Use `TESTING` only to change access. Never add members, virtual functions or behaviour under it, or the two declarations will disagree about the class layout.
- `src/common/pkconstants.hpp:6-7` defines `FRIEND_TEST` without GoogleTest, so production headers can befriend one specific test (`model/model.hpp:436-442`, `model/bayescontainer.h:250-251`, `settings/casefilter.h:191-192`). The suite and test names in the macro must match the test exactly.

## VS Code

Open the umbrella `PreciseRx-Web-PK` as the workspace folder. Its committed `.vscode/settings.json` already points the tools at PK-Library:

- CMake Tools uses `src/packages/cpp/PK-Library` as the source directory and `src/packages/cpp/PK-Library/build` as the build directory (`cmake.sourceDirectory`, `cmake.buildDirectory`).
- C++ TestMate reads tests from `src/packages/cpp/PK-Library/build/test/PKLibrary_tst` (`testMate.cpp.test.advancedExecutables`).
- The C/C++ extension handles IntelliSense. The `compileCommands` path in `.vscode/c_cpp_properties.json` points at a `cpp/build` folder that no longer exists, so rely on CMake Tools as the configuration provider.

Install the C/C++ (`ms-vscode.cpptools`), CMake Tools (`ms-vscode.cmake-tools`) and C++ TestMate (`matepek.vscode-catch2-test-adapter`) extensions. On Windows, install them inside the WSL window, not on the Windows side.

After the first build, the Testing view lists every suite. Run or debug a single test from its context menu.

## Debug builds

`make build-test-cpp` configures without `CMAKE_BUILD_TYPE` (`Makefile:23-27`). A fresh `build/` therefore has no debug information, and breakpoints do not bind. Configure a Debug build once:

```sh
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Debug
cmake --build build --target PKLibrary_tst
```

In VS Code, run **CMake: Select Variant**, choose **Debug**, and let CMake Tools reconfigure. CMake stores the build type in `build/CMakeCache.txt`, so later `make build-test-cpp` runs in the same directory stay Debug. Delete `build/` to go back.

`make clean` does more than delete `build/`. It also removes `node_modules/`, `prebuilds/` and the Python build, clears ccache, prunes a Docker buildx cache, and runs `sudo rm -rf lib/benchmark` (`Makefile:69-79`).

## Debugging on macOS

Use `lldb` from the Command Line Tools:

```text
lldb -- ./build/test/PKLibrary_tst --gtest_filter='CefepimeAn2023.CLMatchesDocumentation'
(lldb) breakpoint set --file cefepime_an_2023.hpp --line 81
(lldb) run
(lldb) bt
```

If `/usr/local/include/gtest` exists, for example from `brew install googletest` on an Intel Mac, the test link fails with undefined `testing::internal::...` symbols. Apple clang searches `/usr/local/include` before the `-isystem` path of the GoogleTest that CMake downloads, so the tests compile against the wrong headers. Run `brew unlink googletest`, delete `build/`, and build again.

## Debugging on Linux and WSL

Use `gdb`:

```text
gdb --args ./build/test/PKLibrary_tst --gtest_filter='CefepimeAn2023.CLMatchesDocumentation'
(gdb) break cefepime_an_2023.hpp:81
(gdb) run
(gdb) bt
```

On Windows, open the umbrella from a WSL shell with `code .` so that VS Code runs in WSL, then install the extensions and `gdb` inside WSL.

## Launch configuration

The committed `.vscode/launch.json` has no configurations. Add one locally to start the test binary under the debugger from the Run and Debug view. The `cppdbg` type comes from the C/C++ extension (see the [VS Code launch.json reference](https://code.visualstudio.com/docs/cpp/launch-json-reference)):

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "PKLibrary_tst (gdb)",
            "type": "cppdbg",
            "request": "launch",
            "program": "${workspaceFolder}/src/packages/cpp/PK-Library/build/test/PKLibrary_tst",
            "args": ["--gtest_filter=CefepimeAn2023.*"],
            "cwd": "${workspaceFolder}/src/packages/cpp/PK-Library",
            "MIMode": "gdb",
            "miDebuggerPath": "/usr/bin/gdb",
            "setupCommands": [
                { "text": "-enable-pretty-printing", "ignoreFailures": true }
            ]
        },
        {
            "name": "PKLibrary_tst (lldb)",
            "type": "cppdbg",
            "request": "launch",
            "program": "${workspaceFolder}/src/packages/cpp/PK-Library/build/test/PKLibrary_tst",
            "args": ["--gtest_filter=CefepimeAn2023.*"],
            "cwd": "${workspaceFolder}/src/packages/cpp/PK-Library",
            "MIMode": "lldb"
        }
    ]
}
```

Rebuild with the Debug variant before you start a session. Otherwise the debugger launches the binary but skips every breakpoint.
