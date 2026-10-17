#!/usr/bin/env python3
"""Check the Python version-history data against Python itself.

Language-specific, like check_js_examples.js. It reads every feature of the Python track from
data/site_data.json and checks three things. Standard library only.

1. Examples. Every before/after snippet is parsed.
   - The "after" snippet must parse as current Python. Syntax added after the running interpreter is
     the exception: its parser must reject it, which confirms the data's version is not too early.
   - For syntax features added in 3.4 to 3.12, ast.parse(feature_version=...) must accept the snippet
     in the version that added the feature. When the parser also rejects it in the version before, the
     feature is counted as confirmed. The parser cannot tell every grammar change apart, so the rest
     are counted as not distinguishable, which is not a problem.
   - The "before" snippet must parse too, except for Python 2 syntax removed in 3.0, which must raise
     SyntaxError in Python 3.

2. Probes. Library features, behaviour changes and removals cannot be checked by parsing, so each is
   probed against the running interpreter. An "exists" probe is compared with what the site itself says
   about that feature in Python 3.12 (renderer/versioning.py lifecycle_state), so the data and the
   interpreter have to agree. That includes features the data says arrive after 3.12, which must be
   absent, and syntax that arrives after 3.12, which the parser must reject. A "holds" probe must be
   true. The probes establish the state in Python 3.12 only; earlier dates rest on the What's New
   evidence gathered when the data was written. Probes are written for Python 3.12 only.
   On any other Python they are skipped with a notice, or fail with --strict (CI uses --strict, so a CI
   Python upgrade cannot quietly switch the probes off).

3. Coverage. Every Python feature must be covered by a parse check or a probe, or be newer than the
   probed interpreter. A new feature in the data therefore cannot ship unchecked: add a probe to PROBES
   (or, for a syntax feature without a before/after example, a snippet to SYNTAX_EXAMPLES). A feature
   that really cannot be probed goes in NOT_PROBEABLE, with the reason.

Run from the repo root:
    python3 scripts/check_python_examples.py            # probes are skipped on a Python other than 3.12
    python3 scripts/check_python_examples.py --strict   # a different Python is an error

Exit code 0 = OK, 1 = problems found.
"""

from __future__ import annotations

import ast
import builtins
import importlib
import importlib.util
import inspect
import io
import keyword
import re
import subprocess
import sys
import sysconfig
import tempfile
import types
import warnings
from pathlib import Path
from typing import Callable, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "renderer"))

from load_data import load_data  # noqa: E402
from versioning import features_for, lifecycle_state, version_orders, versions_for  # noqa: E402

LANGUAGE = "python"
TRACK = "python"
PROBED = (3, 12)  # the interpreter the probes are written for
PROBED_ID = "py3.12"
MIN_FEATURE_VERSION = 4  # ast.parse(feature_version=(3, n)) accepts n from 4

# Syntax features that have no before/after example in the data still need a snippet to parse.
SYNTAX_EXAMPLES = {
    "function-annotations": "def scale(value: float, factor: float = 2.0) -> float:\n    return value * factor\n",
    "async-generators": "async def ticks(n):\n    for i in range(n):\n        yield i\n\nasync def collect(n):\n    return [i async for i in ticks(n)]\n",
    "positional-only-parameters": "def clamp(value, low, high, /):\n    return max(low, min(value, high))\n",
    "structural-pattern-matching": "def describe(point):\n    match point:\n        case (0, 0):\n            return \"origin\"\n        case (x, y):\n            return f\"({x}, {y})\"\n        case _:\n            return \"unknown\"\n",
    "exception-groups": "try:\n    risky()\nexcept* ValueError as group:\n    handle(group)\n",
    "template-strings": "name = \"world\"\ngreeting = t\"Hello {name}\"\n",
}


# ---------------------------------------------------------------- probes

class Probe(NamedTuple):
    kind: str  # "exists": compared with the site's state in 3.12. "holds": must be true.
    label: str
    run: Callable[[], bool]


def E(label: str, run: Callable[[], bool]) -> Probe:
    return Probe("exists", label, run)


def H(label: str, run: Callable[[], bool]) -> Probe:
    return Probe("holds", label, run)


def ebuiltin(name: str) -> Probe:
    return E(f"builtin {name}", lambda: hasattr(builtins, name))


def eattr(module: str, dotted: str) -> Probe:
    def run() -> bool:
        try:
            obj = importlib.import_module(module)
            for part in dotted.split("."):
                obj = getattr(obj, part)
            return True
        except (ImportError, AttributeError):
            return False

    return E(f"{module}.{dotted}", run)


def stdlib_module_exists(name: str) -> bool:
    # sys.stdlib_module_names ignores third-party shims that would make "import distutils" succeed.
    if name.split(".")[0] not in sys.stdlib_module_names:
        return False
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def emodule(name: str) -> Probe:
    return E(f"module {name}", lambda: stdlib_module_exists(name))


def run_in_temp_package(files: dict[str, str], statement: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmp:
        for rel, text in files.items():
            path = Path(tmp) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        code = "import sys; sys.path.insert(0, sys.argv[1]); " + statement
        return subprocess.run([sys.executable, "-I", "-c", code, tmp], capture_output=True, text=True, timeout=60)


def h_true_division() -> bool:
    return 7 / 2 == 3.5 and 7 // 2 == 3


def h_classic_classes() -> bool:
    class Point:
        pass

    return object in Point.__mro__


def h_text_and_bytes() -> bool:
    try:
        "a" + b"a"  # type: ignore[operator]
    except TypeError:
        return isinstance("", str) and isinstance(b"", bytes) and not isinstance("", bytes)
    return False


def h_stdlib_renames() -> bool:
    names = sys.stdlib_module_names
    return {"configparser", "queue", "urllib"} <= names and not ({"ConfigParser", "Queue", "urllib2"} & names)


def h_print_function() -> bool:
    out = io.StringIO()
    print("a", "b", sep="-", end="!", file=out, flush=True)
    return out.getvalue() == "a-b!"


def h_exec_function() -> bool:
    namespace: dict[str, int] = {}
    exec("x = 1", namespace)
    return namespace.get("x") == 1


def h_async_keywords() -> bool:
    return keyword.iskeyword("async") and keyword.iskeyword("await")


def h_fstring_same_quotes() -> bool:  # PEP 701, Python 3.12
    ast.parse('f"{"a" + "b"}"')
    return True


def h_dict_order() -> bool:
    return list({3: 1, 1: 2, 2: 3}) == [3, 1, 2]


def h_module_getattr() -> bool:
    module = types.ModuleType("probe")
    module.__getattr__ = lambda name: 42  # type: ignore[attr-defined]
    return module.anything == 42  # type: ignore[attr-defined]


def h_dict_union() -> bool:
    return ({"a": 1} | {"b": 2}) == {"a": 1, "b": 2}


def h_builtin_generics() -> bool:
    return list[int].__origin__ is list


def h_zip_strict() -> bool:
    try:
        list(zip([1], [1, 2], strict=True))
    except ValueError:
        return True
    return False


def h_collections_abc() -> bool:
    import collections.abc

    return hasattr(collections.abc, "Mapping")


def h_asyncio_loop_parameter() -> bool:
    import asyncio

    return "loop" in inspect.signature(asyncio.sleep).parameters


def h_default_encoding() -> bool:
    return inspect.signature(open).parameters["encoding"].default is None


def h_cmp_to_key() -> bool:
    import functools

    return callable(functools.cmp_to_key)


def h_annotations_deferred() -> bool:  # Python 3.14: an undefined name in an annotation is not evaluated
    # dont_inherit: without it the code would pick up this file's own "from __future__ import annotations"
    code = compile("def f(x: Undefined) -> Undefined2: ...", "<probe>", "exec", flags=0, dont_inherit=True)
    try:
        exec(code, {})
    except NameError:
        return False
    return True


def h_free_threaded_marker() -> bool:  # the config variable exists in 3.13 and later, set to 1 only for free-threaded builds
    return sysconfig.get_config_var("Py_GIL_DISABLED") is not None


def h_implicit_relative_imports() -> bool:
    files = {"pkg/__init__.py": "", "pkg/helpers.py": "VALUE = 1\n", "pkg/user.py": "import helpers\n"}
    result = run_in_temp_package(files, "import pkg.user")
    return result.returncode != 0 and "ModuleNotFoundError" in result.stderr


def h_namespace_packages() -> bool:
    result = run_in_temp_package({"nspkg/mod.py": "VALUE = 1\n"}, "import nspkg.mod")
    return result.returncode == 0


PROBES: dict[str, list[Probe]] = {
    # Python 2 features that Python 3.0 removed or changed
    "dict-has-key": [E("dict.has_key()", lambda: hasattr({}, "has_key"))],
    "xrange": [ebuiltin("xrange")],
    "raw-input": [ebuiltin("raw_input")],
    "dict-iter-methods": [E(f"dict.{name}()", lambda name=name: hasattr({}, name)) for name in ("iteritems", "iterkeys", "itervalues")],
    "unicode-type": [ebuiltin("unicode")],
    "true-division": [H("7 / 2 is 3.5 and 7 // 2 is 3", h_true_division)],
    "classic-classes": [H("a class with no bases inherits from object", h_classic_classes)],
    "cmp-and-ordering": [ebuiltin("cmp"), H("functools.cmp_to_key() exists", h_cmp_to_key)],
    "implicit-relative-imports": [H("import sibling inside a package raises ModuleNotFoundError", h_implicit_relative_imports)],
    "stdlib-renames": [H("the new module names exist and the old ones do not", h_stdlib_renames)],
    "exec-statement": [H("exec() is a function", h_exec_function)],
    "print-function": [H("print() takes sep, end, file and flush", h_print_function)],
    "text-and-bytes": [H("str and bytes are separate types that do not mix", h_text_and_bytes)],
    # additions
    "ordereddict": [eattr("collections", "OrderedDict")],
    "concurrent-futures": [emodule("concurrent.futures")],
    "lru-cache": [eattr("functools", "lru_cache")],
    "venv": [emodule("venv")],
    "namespace-packages": [H("a directory without __init__.py imports as a package", h_namespace_packages)],
    "unittest-mock": [emodule("unittest.mock")],
    "asyncio-module": [emodule("asyncio")],
    "pathlib": [emodule("pathlib")],
    "enum-module": [emodule("enum")],
    "async-await": [H("async and await are keywords", h_async_keywords)],
    "type-hints-module": [emodule("typing")],
    "os-scandir": [eattr("os", "scandir")],
    "subprocess-run": [eattr("subprocess", "run")],
    "typing-collection-aliases": [eattr("typing", "List"), eattr("typing", "Dict")],
    "f-strings": [H("the same quote type can be reused inside the braces (PEP 701)", h_fstring_same_quotes)],
    "secrets-module": [emodule("secrets")],
    "dict-insertion-order": [H("dictionaries keep insertion order", h_dict_order)],
    "dataclasses-module": [emodule("dataclasses")],
    "postponed-annotations": [eattr("__future__", "annotations")],
    "breakpoint-function": [ebuiltin("breakpoint")],
    "module-getattr": [H("a module-level __getattr__ is used", h_module_getattr)],
    "contextvars-module": [emodule("contextvars")],
    "typing-protocols": [eattr("typing", name) for name in ("Protocol", "TypedDict", "Literal", "Final")],
    "cached-property": [eattr("functools", "cached_property")],
    "dict-union": [H("dict | dict merges", h_dict_union)],
    "removeprefix-suffix": [E(f"str.{name}()", lambda name=name: hasattr(str, name)) for name in ("removeprefix", "removesuffix")],
    "builtin-generics": [H("list[int] works without importing typing", h_builtin_generics)],
    "zoneinfo-module": [emodule("zoneinfo")],
    "zip-strict": [H("zip(strict=True) raises ValueError for unequal lengths", h_zip_strict)],
    "exception-notes": [E("BaseException.add_note()", lambda: hasattr(BaseException, "add_note"))],
    "tomllib-module": [emodule("tomllib")],
    "asyncio-taskgroup": [eattr("asyncio", "TaskGroup")],
    "typing-self": [eattr("typing", "Self")],
    "override-decorator": [eattr("typing", "override")],
    "itertools-batched": [eattr("itertools", "batched")],
    "default-text-encoding": [H("open() has an encoding argument that defaults to None, the platform default", h_default_encoding)],
    # deprecations and removals
    "time-clock": [eattr("time", "clock")],
    "collections-abc-aliases": [eattr("collections", "Mapping"), H("collections.abc.Mapping exists", h_collections_abc)],
    # a restricted removal: the probe checks one representative function
    "asyncio-loop-parameter": [E("asyncio.sleep() takes a loop argument", h_asyncio_loop_parameter)],
    "asyncio-coroutine-decorator": [eattr("asyncio", "coroutine")],
    "getargspec": [eattr("inspect", "getargspec")],
    "distutils": [emodule("distutils")],
    "imp-module": [emodule("imp")],
    "asyncore-asynchat-smtpd": [emodule(name) for name in ("asyncore", "asynchat", "smtpd")],
    "unittest-assert-aliases": [eattr("unittest", "TestCase.assertEquals"), eattr("unittest", "TestCase.assert_")],
    "ssl-wrap-socket": [eattr("ssl", "wrap_socket")],
    "dead-batteries": [emodule(name) for name in ("cgi", "crypt", "telnetlib", "pipes")],
    "datetime-utcnow": [eattr("datetime", "datetime.utcnow"), eattr("datetime", "datetime.utcfromtimestamp")],
    # features newer than 3.12: the probes must find them absent
    "free-threaded-build": [E("the Py_GIL_DISABLED build variable", h_free_threaded_marker)],
    "warnings-deprecated": [eattr("warnings", "deprecated")],
    "deferred-annotations": [E("annotations are not evaluated when a function is defined", h_annotations_deferred)],
    "compression-zstd": [emodule("compression.zstd")],
    "frozendict": [ebuiltin("frozendict")],
    "sentinel": [ebuiltin("sentinel")],
    "profiling-sampling": [emodule("profiling.sampling")],
}

# Features that cannot be probed, with the reason. Syntax features are covered by parsing instead.
NOT_PROBEABLE = {
    "experimental-jit": "a build-time option with no marker that a Python 3.12 probe could look for",
}


# ---------------------------------------------------------------- helpers

def running_version() -> tuple[int, int]:
    return sys.version_info[:2]


def version_tuple(version_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"py(\d+)(?:\.(\d+))?", version_id)
    if not match:
        raise ValueError(f"unexpected version id {version_id!r}")
    return int(match.group(1)), int(match.group(2) or 0)


def event_version(feature: dict, kind: str) -> tuple[int, int] | None:
    for event in feature["history"][TRACK]:
        if event["kind"] == kind:
            return version_tuple(event["version"])
    return None


def parse_error(code: str, feature_version: tuple[int, int] | None = None) -> str | None:
    try:
        if feature_version:
            ast.parse(code, feature_version=feature_version)
        else:
            ast.parse(code)
    except SyntaxError as error:
        return f"{error.msg} (line {error.lineno})"
    return None


def short(code: str) -> str:
    first = code.strip().splitlines()[0]
    return first if len(first) <= 60 else first[:57] + "..."


# ---------------------------------------------------------------- checks

def check_examples(features: list[dict], running: tuple[int, int], problems: list[str]) -> dict[str, int]:
    stats = dict(snippets=0, skipped_newer=0, confirmed=0, not_distinguishable=0, py2_syntax=0)
    for feature in features:
        slug, category = feature["slug"], feature["category"]
        added, removed = event_version(feature, "added"), event_version(feature, "removed")
        migration = feature.get("migration")
        modern = migration["modern"] if migration else SYNTAX_EXAMPLES.get(slug)
        py2_syntax = category == "syntax" and removed == (3, 0)

        if migration:
            error = parse_error(migration["legacy"])
            if py2_syntax and error is None:
                problems.append(f"{slug}: the 'before' snippet is Python 2 syntax but parses in Python 3: {short(migration['legacy'])}")
            elif py2_syntax:
                stats["py2_syntax"] += 1
            elif error:
                problems.append(f"{slug}: the 'before' snippet does not parse: {error}: {short(migration['legacy'])}")

        if modern is None:
            continue
        stats["snippets"] += 1
        error = parse_error(modern)
        if added > running and category == "syntax":
            if error:
                stats["skipped_newer"] += 1  # rejected, as it should be: this interpreter is too old for it
            else:
                problems.append(f"{slug}: the data says Python {added[0]}.{added[1]} added this syntax, but the snippet parses in Python {running[0]}.{running[1]}")
            continue
        if error and added > running:
            stats["skipped_newer"] += 1
            continue
        if error:
            problems.append(f"{slug}: the 'after' snippet does not parse: {error}: {short(modern)}")
            continue
        if added > running:
            continue  # parses even here, but the grammar rule below needs the version that added it
        if category == "syntax" and added[0] == 3 and MIN_FEATURE_VERSION <= added[1] <= running[1]:
            error = parse_error(modern, added)
            if error:
                problems.append(f"{slug}: the 'after' snippet is rejected as Python {added[0]}.{added[1]} syntax: {error}")
            elif added[1] - 1 >= MIN_FEATURE_VERSION:
                before = parse_error(modern, (added[0], added[1] - 1))
                stats["confirmed" if before else "not_distinguishable"] += 1
    return stats


def check_probes(features: list[dict], data: dict, problems: list[str]) -> dict[str, int]:
    stats = dict(exists=0, holds=0, newer=0)
    orders = version_orders(versions_for(data, LANGUAGE, TRACK))
    at = orders[PROBED_ID]
    for feature in features:
        slug = feature["slug"]
        probes = PROBES.get(slug, [])
        state = lifecycle_state(feature, TRACK, orders, at)
        if state == "not-yet":
            stats["newer"] += 1
        for probe in probes:
            if state == "not-yet" and probe.kind == "holds":
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    result = bool(probe.run())
                except Exception as error:  # a probe that crashes is a finding, not a crash of the checker
                    problems.append(f"{slug}: probe '{probe.label}' raised {type(error).__name__}: {error}")
                    continue
            stats[probe.kind] += 1
            if probe.kind == "holds":
                if not result:
                    problems.append(f"{slug}: expected to hold in Python 3.12 but does not: {probe.label}")
                continue
            expected = state in ("available", "deprecated")
            if result != expected:
                actual = "exists" if result else "does not exist"
                problems.append(f"{slug}: the data says {state} in Python 3.12, but {probe.label} {actual}")
    return stats


def check_coverage(features: list[dict], problems: list[str]) -> None:
    slugs = {f["slug"] for f in features}
    for slug in sorted((set(PROBES) | set(SYNTAX_EXAMPLES) | set(NOT_PROBEABLE)) - slugs):
        problems.append(f"{slug}: has a probe, example or exemption here but is not a feature of the Python track")
    for slug in sorted(set(PROBES) & set(NOT_PROBEABLE)):
        problems.append(f"{slug}: is both probed and listed as not probeable")
    for feature in features:
        slug = feature["slug"]
        has_snippet = bool(feature.get("migration")) or slug in SYNTAX_EXAMPLES
        if feature["category"] == "syntax":
            if not has_snippet:
                problems.append(f"{slug}: a syntax feature with no before/after example; add one to the data or to SYNTAX_EXAMPLES")
        elif slug not in PROBES and slug not in NOT_PROBEABLE:
            problems.append(f"{slug}: no probe; add one to PROBES so the data is checked against Python")


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    data = load_data()
    features = features_for(data, LANGUAGE, TRACK)
    if not features:
        print("FAIL python examples: the data has no Python features")
        return 1

    running = running_version()
    problems: list[str] = []
    notes: list[str] = []

    examples = check_examples(features, running, problems)
    check_coverage(features, problems)

    probes = None
    if running == PROBED:
        probes = check_probes(features, data, problems)
    else:
        message = f"probes are written for Python {PROBED[0]}.{PROBED[1]}, this is Python {running[0]}.{running[1]}"
        if strict:
            problems.append(message + " (--strict)")
        else:
            notes.append(message + ", so they were skipped (CI runs them)")

    if problems:
        print("FAIL python examples:")
        for problem in problems:
            print(f"  - {problem}")
        print(f"\n{len(problems)} problem(s) found")
        return 1

    print(f"OK   python examples ({len(features)} features, {examples['snippets']} snippets)")
    print(f"     parsed: {examples['snippets'] - examples['skipped_newer']}, rejected as newer than Python {running[0]}.{running[1]}: {examples['skipped_newer']}")
    print(f"     syntax confirmed new in its version by the parser: {examples['confirmed']}, not distinguishable by it: {examples['not_distinguishable']}")
    print(f"     Python 2 syntax confirmed as SyntaxError: {examples['py2_syntax']}")
    if probes is not None:
        print(f"     probes passed: {probes['exists'] + probes['holds']} ({probes['exists']} exist-or-absent checks against the site's own state, {probes['holds']} behaviour checks)")
        print(f"     features newer than Python 3.12, found absent as the data says: {probes['newer']}")
        if NOT_PROBEABLE:
            print(f"     not probeable: {len(NOT_PROBEABLE)} ({', '.join(NOT_PROBEABLE)})")
    for note in notes:
        print(f"     note: {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
