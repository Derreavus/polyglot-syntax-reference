# scripts

Everything here is run from the command line. Scripts find the repository from their own location, so it does not matter which directory you run them from.

| Folder | What it is for | May it name a language? |
|---|---|---|
| `validate/` | Checks on the built site and the data: links, HTML structure, content lint, and parity with the legacy pages. Run `python renderer/build_site.py` first, because most of them read `dist/`. | No |
| `check/` | Per-language checkers that compare the version-history data and its examples with the real language. | Yes, by design |
| `content/` | Tools that change the data, such as the one-time legacy importer. | No |
| `dev/` | Local helpers, such as `serve_staging.py`, which builds and serves the site. | No |
| `lib/` | Helpers shared by the other scripts (`language_registry.py`). | No |

"No" is enforced: `tests/core/test_architecture.py` fails if a script in `validate/` or `lib/` names a language, so the site keeps taking everything about a language from `data/site_data.json`.

## What CI runs

```
python -m unittest discover -s tests
python renderer/build_site.py
python scripts/validate/validate_staging_parity.py
python scripts/validate/validate_syntax_html.py
python scripts/validate/validate_links.py
python scripts/validate/validate_html_smoke.py
python scripts/check/check_python_examples.py --strict
rustup toolchain install 1.75.0 1.95.0 --profile minimal --no-self-update
python scripts/check/check_rust_examples.py --strict --rustc "rustup run 1.75.0 rustc"
python scripts/check/check_rust_examples.py --strict --rustc "rustup run 1.95.0 rustc"
# .NET SDKs 8 and 10 (actions/setup-dotnet) and Mono (sudo apt-get install -y mono-devel), then:
python scripts/check/check_csharp_examples.py --strict
# in the separate C++ job, after bash scripts/ci/setup_cpp_toolchains.sh:
python scripts/check/check_cpp_examples.py --strict
```

## The per-language checkers

- `check/check_python_examples.py` compares the Python data with a real Python 3.12 interpreter. On any other Python it skips its probes with a notice; `--strict` (what CI uses) fails instead.
- `check/check_rust_examples.py` compiles the Rust examples and small feature probes with a real Rust compiler, and adapts to whichever compiler it is given (`--rustc "<command>"`, default `rustc`). Features newer than the compiler must fail to compile; features it has must compile. It also compiles edition probes (code that builds in one edition and not the next). CI runs it on an old and a new toolchain (1.75.0 and 1.95.0), so each run checks the data in both directions. A missing compiler is skipped with a notice, or an error with `--strict`.
- `check/check_cpp_examples.py` compares the C++ data with real GCC and Clang toolchains (probe code in `check/cpp_probe_data.py`). Each toolchain configuration is a compiler plus the standard library it is paired with: GCC N with its own libstdc++ (9 to 16), Clang N with libc++ N (14 to 23). It checks that every version is marked "Verified here" exactly when a configuration exists for it; that each GCC and Clang event at a verified version is the first version whose feature-test macro (`__cpp_*` or, for the 207 library features with a macro, `__cpp_lib_*` with a minimum value where a macro first existed for another feature) or probe supports the feature (the 57 library features with no macro use probes, `LIBRARY_PROBES`) (and carries the "Documented by the vendor" note when the evidence does not confirm it); that language, header and library probes compile at their own standard and fail at the one before, and library macros are defined at their own standard and not at the one before, on a strict configuration, unless listed as leakage; and that Clang with libc++ and GCC with libstdc++ behave as recorded when a facility is removed. MSVC cannot run here, so none of its versions is verified. `scripts/ci/setup_cpp_toolchains.sh` builds the layout the checker discovers (apt packages, libc++ headers unpacked per version under `/opt/libcxx`, and conda-forge environments under `/opt`). `--strict` turns a missing configuration into an error; options: `--envs-root`, `--libcxx-root`, `--jobs`.
- `check/check_csharp_examples.py` compiles small probes with the Roslyn compiler from a .NET SDK (probe code is in `check/csharp_probe_data.py`). For each C# language event the probe must compile at that `-langversion` and fail one version earlier. For each .NET Framework event it must compile against Mono's reference assemblies for that release and fail against the previous one, and for each .NET API it must exist in the .NET 10 reference pack (and in the .NET 8 pack only up to .NET 8). It also compiles the runtime-dependent language features against .NET Framework 4.5 to 4.8, netstandard 2.1, .NET 8 and .NET 10 and requires the data's compatibility notes to say exactly what those results say, and it reads the default C# version of net8.0 and net10.0 from a real SDK build. `--strict` (what CI uses) turns a missing SDK, reference pack or Mono into an error; without it the checker skips with a notice. Options: `--dotnet`, `--mono`, `--jobs`.
- `check/check_js_examples.js` parses the JavaScript examples in the edition they belong to. Install its parser once with `npm install --no-save acorn`.

Each new language that gets version history gets its own checker here, and a matching test in `tests/checkers/`.
