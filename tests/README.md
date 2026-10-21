# tests

Run everything from the repository root:

```
python -m unittest discover -s tests
```

| Folder | What it covers |
|---|---|
| `core/` | The site's architecture rules (code stays language-neutral), the data source, and the site identity. |
| `version_history/` | Version history. `test_versioning.py` holds the general rules that apply to any language; each language that has version history adds one file, such as `test_python_versioning.py`. |
| `checkers/` | Tests that prove the per-language checkers in `scripts/check/` catch wrong data, by feeding them deliberately wrong data. |

## Running part of the suite

```
python -m unittest discover -s tests -p "test_python*.py"    # everything about one language
python -m unittest discover -s tests -p "test_identity.py"   # one file
cd tests && python -m unittest discover -s core               # one folder
cd tests && python -m unittest core.test_architecture         # one module
```

## Notes

- Each folder is a package (it has an `__init__.py`), which is why `unittest` finds the tests inside it. A new test folder needs one too.
- Do not name a test folder after a module in `renderer/` (for example `versioning`): test discovery puts `tests/` first on the import path, so the folder would hide the renderer module and break imports.
- The tests that run a whole language checker only run on the Python version that checker is written for (3.12, which CI uses) and are skipped on other versions.
