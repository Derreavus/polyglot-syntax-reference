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
```

## The per-language checkers

- `check/check_python_examples.py` compares the Python data with a real Python 3.12 interpreter. On any other Python it skips its probes with a notice; `--strict` (what CI uses) fails instead.
- `check/check_js_examples.js` parses the JavaScript examples in the edition they belong to. Install its parser once with `npm install --no-save acorn`.

Each new language that gets version history gets its own checker here, and a matching test in `tests/checkers/`.
