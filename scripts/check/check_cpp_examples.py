#!/usr/bin/env python3
"""Check the C++ version-history data against real compilers.

Language-specific, like check_rust_examples.py. It reads the C++ features from data/site_data.json and compiles small
probes with the toolchain configurations listed in CONFIGS. Standard library only. The probes are in cpp_probe_data.py.

A *configuration* is a compiler together with the standard library it is paired with and the flags that make the pairing
explicit: GCC N uses its own libstdc++, and Clang N uses libc++ N (never the system's libstdc++, which only a matching GCC can
read). Which configurations exist on a machine is discovered, so the checker works with whatever is installed:
    GCC 9 to 14 and Clang 14 to 20   apt packages g++-N, clang++-N, and libc++ headers unpacked to <libcxx-root>/N
    GCC 15, 16 and Clang 21 to 23     conda-forge environments <envs-root>/gcc15 ... <envs-root>/clang23
scripts/ci/setup_cpp_toolchains.sh builds exactly that layout. MSVC cannot run here, so none of its versions is verified.

What it checks:
1. Version markers. A GCC or Clang version in the data is marked "Verified here" exactly when this checker has a configuration for it.
2. Implementation events. For every GCC and Clang event at a verified version, the first configuration whose feature-test macro or
   probe supports the feature must be that version. An event the evidence confirms must not carry the "Documented by the vendor"
   note, and one it does not confirm must carry it, so the markers in the data stay honest in both directions.
3. Standard boundaries. Library features (one per __cpp_lib_* macro) must have their macro defined at their own standard and not at the one before on a strict
   configuration, unless listed in LIBRARY_LEAKAGE. A language or header probe must compile at its own standard and fail at the one before on at least one strict
   configuration, unless it is listed in STANDARD_LEAKAGE (compilers accept it early, or none implements it yet).
4. Lifecycle. For each removed facility, Clang with libc++ and GCC with libstdc++ must behave as recorded in the data at the
   standard that removed it (rejects, still accepts, or changes meaning).
5. Coverage. Every header and lifecycle feature in the data has a probe table entry, and every table entry belongs to a feature.

The standard's own text (Annex C, Annex D, the header tables) and the vendors' documentation are not re-read here; the data cites them.

Run from the repo root:
    python3 scripts/check/check_cpp_examples.py             # checks whatever configurations are found
    python3 scripts/check/check_cpp_examples.py --strict    # a missing configuration is an error

Exit code 0 = OK, 1 = problems found.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "renderer"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cpp_probe_data import HEADER_PROBES, LANGUAGE_EVIDENCE, LIBRARY_EVIDENCE, LIBRARY_LEAKAGE, LIFECYCLE_PROBES, STANDARD_LEAKAGE  # noqa: E402
from load_data import load_data  # noqa: E402

LANGUAGE = "cpp"
GCC_VERSIONS = list(range(9, 17))
CLANG_VERSIONS = list(range(14, 24))
STD_NAMES = {"03": ["c++03"], "11": ["c++11"], "14": ["c++14"], "17": ["c++17"], "20": ["c++20", "c++2a"], "23": ["c++23", "c++2b"], "26": ["c++26", "c++2c"]}
PREVIOUS = {"11": "03", "14": "11", "17": "14", "20": "17", "23": "20", "26": "23"}
DOCUMENTED = "Documented by the vendor; no probe here confirmed this feature at this version."
STRICT_CONFIGS = (("gcc", 16), ("clang", 23))


class Config:
    def __init__(self, track: str, version: int, cxx: list[str], flags: list[str], stdlib: str):
        self.track, self.version, self.cxx, self.flags, self.stdlib = track, version, cxx, flags, stdlib
        self._std: dict = {}
        self._macros: dict[str, int] | None = None

    def key(self) -> str:
        return f"{self.track}{self.version}"

    def std_flag(self, std: str) -> str | None:
        if std not in self._std:
            self._std[std] = next((n for n in STD_NAMES[std] if self._accepts(n)), None)
        return self._std[std]

    def _accepts(self, name: str) -> bool:
        r = subprocess.run([*self.cxx, f"-std={name}", *self.flags, "-dM", "-E", "-x", "c++", "-"], input="", capture_output=True, text=True)
        return r.returncode == 0

    def newest_std(self) -> str | None:
        for std in ("26", "23", "20", "17"):
            if self.std_flag(std): return std
        return None

    def lib_macros(self, std: str | None = None) -> dict[str, int] | None:
        """The __cpp_lib_* macros that <version> defines at a standard (default: the newest the configuration knows), as name -> value."""
        std = std or self.newest_std() or "17"
        key = ("lib", std)
        if key not in self._std:
            flag = self.std_flag(std)
            if flag is None:
                self._std[key] = None
            else:
                out = subprocess.run([*self.cxx, f"-std={flag}", *self.flags, "-dM", "-E", "-x", "c++", "-"], input="#include <version>\n", capture_output=True, text=True).stdout
                self._std[key] = {m: int(v) for m, v in re.findall(r"#define __cpp_lib_(\w+) (\d+)", out)}
        return self._std[key]

    def macros(self) -> dict[str, int]:
        if self._macros is None:
            std = self.std_flag(self.newest_std() or "17")
            out = subprocess.run([*self.cxx, f"-std={std}", *self.flags, "-dM", "-E", "-x", "c++", "-"], input="", capture_output=True, text=True).stdout
            self._macros = {m.group(1): int(m.group(2)) for m in re.finditer(r"#define (__cpp_\w+) (\d+)L?", out)}
        return self._macros


def discover(envs_root: str = "/opt", libcxx_root: str = "/opt/libcxx") -> dict[tuple[str, int], Config]:
    found: dict[tuple[str, int], Config] = {}
    for v in GCC_VERSIONS:
        exe = shutil.which(f"g++-{v}") if v <= 14 else next(iter(glob.glob(f"{envs_root}/gcc{v}/bin/*-g++")), None)
        if exe: found[("gcc", v)] = Config("gcc", v, [exe], [], f"libstdc++ {v}")
    for v in CLANG_VERSIONS:
        if v <= 20:
            exe, hdr = shutil.which(f"clang++-{v}"), Path(libcxx_root) / str(v) / "usr" / "lib" / f"llvm-{v}" / "include" / "c++" / "v1"
            extra: list[str] = []
        else:
            exe, hdr = f"{envs_root}/clang{v}/bin/clang++", Path(envs_root) / f"clang{v}" / "include" / "c++" / "v1"
            gcc_dirs = glob.glob(f"{envs_root}/clang{v}/lib/gcc/x86_64-conda-linux-gnu/*")
            extra = [f"--gcc-install-dir={gcc_dirs[0]}"] if gcc_dirs else []
            if not Path(exe).exists(): exe = None
        if exe and hdr.is_dir():
            found[("clang", v)] = Config("clang", v, [exe], ["-stdlib=libc++", "-nostdinc++", "-isystem", str(hdr), *extra], f"libc++ {v}")
    return found


_cache: dict[tuple, bool | None] = {}


def compiles(cfg: Config, std: str, code: str) -> bool | None:
    """True/False for the probe at that standard, None when the configuration has no such -std."""
    key = (cfg.key(), std, code)
    if key not in _cache:
        flag = cfg.std_flag(std)
        if flag is None:
            _cache[key] = None
        else:
            with tempfile.TemporaryDirectory() as tmp:
                src = Path(tmp) / "probe.cpp"
                src.write_text(code + "\n", encoding="utf-8")
                r = subprocess.run([*cfg.cxx, f"-std={flag}", "-pedantic-errors", "-fsyntax-only", *cfg.flags, str(src)], capture_output=True, text=True, timeout=300)
                _cache[key] = r.returncode == 0
    return _cache[key]


def macro_ok(cfg: Config, spec: str) -> bool:
    name, _, value = spec.partition(">=")
    return cfg.macros().get(name, 0) >= int(re.match(r"\d+", value or "0").group())


class Report:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.skipped: list[str] = []
        self.counts: dict[str, int] = {}

    def count(self, name: str, n: int = 1) -> None:
        self.counts[name] = self.counts.get(name, 0) + n

    def problem(self, text: str) -> None:
        self.problems.append(text)


def features(data: dict) -> dict[str, dict]:
    return {f["slug"]: f for f in data["features"] if f["language"] == LANGUAGE}


def version_ids(data: dict, track: str) -> dict[str, dict]:
    return {v["id"]: v for v in data["versions"] if v["language"] == LANGUAGE and v["track"] == track}


def major(version_id: str, track: str) -> int:
    return int(re.match(r"\d+", version_id.removeprefix(track)).group())


# ---------------------------------------------------------------- 1. version markers (data only)
def check_markers(data: dict, report: Report) -> None:
    verified = {"gcc": set(GCC_VERSIONS), "clang": set(CLANG_VERSIONS), "msvc": set()}
    for track, ok in verified.items():
        for vid, v in version_ids(data, track).items():
            report.count("version markers")
            says = v.get("note", "").startswith("Verified here")
            should = track != "msvc" and major(vid, track) in ok
            if says != should:
                report.problem(f"{track} {vid}: marked {'verified' if says else 'not verified'} but the checker {'has' if should else 'has no'} configuration for it")


# ---------------------------------------------------------------- 2. implementation events
def evidence_first(slug: str, track: str, cfgs: dict, versions: list[int]) -> tuple[set[int], bool]:
    """Versions at which the macro or the probe first supports the feature, and whether every needed configuration was found."""
    found = set(); complete = True
    if slug.startswith("lib-"):
        name, low = LIBRARY_EVIDENCE[slug]["macro"].removeprefix("__cpp_lib_"), LIBRARY_EVIDENCE[slug].get("min_value", 1)
        tests = [lambda cfg, name=name, low=low: cfg.lib_macros().get(name, 0) >= low]
    elif slug.startswith("header-"):
        std, code = HEADER_PROBES[slug]
        tests = [lambda cfg, std=std, code=code: compiles(cfg, std, code)]
    else:
        ev = LANGUAGE_EVIDENCE[slug]
        tests = []
        if ev["macros"]: tests.append(lambda cfg, ev=ev: all(macro_ok(cfg, m) for m in ev["macros"]))
        if ev["probe"]: tests.append(lambda cfg, ev=ev: compiles(cfg, ev["std"], ev["probe"]))
    for test in tests:
        for v in versions:
            cfg = cfgs.get((track, v))
            if cfg is None: complete = False; continue
            if test(cfg):
                found.add(v); break
    return found, complete


def check_events(data: dict, cfgs: dict, report: Report, strict: bool) -> None:
    feats = features(data)
    for track, versions in (("gcc", GCC_VERSIONS), ("clang", CLANG_VERSIONS)):
        for slug, feat in feats.items():
            for e in feat["history"].get(track, []):
                v = major(e["version"], track)
                if v not in versions: continue
                has_note = DOCUMENTED in e.get("note", "")
                known = LIBRARY_EVIDENCE if slug.startswith("lib-") else HEADER_PROBES if slug.startswith("header-") else LANGUAGE_EVIDENCE
                if slug not in known:
                    if not has_note: report.problem(f"{track} {e['version']} {slug}: no evidence table entry, so the event must carry the documented-only note")
                    continue
                found, complete = evidence_first(slug, track, cfgs, versions)
                if not complete:
                    (report.problem if strict else report.skipped.append)(f"{track} {e['version']} {slug}: a configuration needed for this event was not found")
                    continue
                report.count("implementation events")
                matches = v in found
                if matches and has_note: report.problem(f"{track} {e['version']} {slug}: the evidence confirms this version but the event says it is documented only")
                if not matches and not has_note: report.problem(f"{track} {e['version']} {slug}: the evidence first supports {sorted(found) or 'nothing'} but the event does not say it is documented only")


# ---------------------------------------------------------------- 3. standard boundaries
def check_boundaries(data: dict, cfgs: dict, report: Report, strict: bool) -> None:
    strict_cfgs = [cfgs[k] for k in STRICT_CONFIGS if k in cfgs]
    if not strict_cfgs:
        (report.problem if strict else report.skipped.append)("GCC 16 and Clang 23 are both missing, so no standard boundary was checked")
        return
    feats = features(data)
    items = [(s, ev["std"], ev["probe"]) for s, ev in LANGUAGE_EVIDENCE.items() if ev["probe"]] + [(s, std, code) for s, (std, code) in HEADER_PROBES.items()]
    for slug, std, code in items:
        if slug not in feats: continue
        report.count("standard boundaries")
        want = f"cpp{std}"
        got = [e["version"] for e in feats[slug]["history"]["cpp"] if e["kind"] == "added"]
        if got != [want]: report.problem(f"{slug}: the data adds it in {got} but its probe belongs to C++{std}")
        prev = PREVIOUS[std]
        results = [(compiles(c, std, code), compiles(c, prev, code)) for c in strict_cfgs]
        confirmed = any(a and not b for a, b in results)
        if slug in STANDARD_LEAKAGE:
            if confirmed: report.problem(f"{slug}: listed as leaking, but a strict configuration does confirm its boundary")
        elif not confirmed:
            report.problem(f"{slug}: no strict configuration compiles it at C++{std} and rejects it at C++{prev}: {results}")
    for slug in STANDARD_LEAKAGE:
        if slug not in feats: report.problem(f"STANDARD_LEAKAGE has {slug}, which is not a feature in the data")


def check_library_boundaries(data: dict, cfgs: dict, report: Report, strict: bool) -> None:
    strict_cfgs = [cfgs[k] for k in STRICT_CONFIGS if k in cfgs]
    if not strict_cfgs:
        (report.problem if strict else report.skipped.append)("GCC 16 and Clang 23 are both missing, so no library boundary was checked")
        return
    feats = features(data)
    for slug, ev in LIBRARY_EVIDENCE.items():
        if slug not in feats: report.problem(f"LIBRARY_EVIDENCE has {slug}, which is not a feature in the data"); continue
        report.count("library boundaries")
        name, std, low = ev["macro"].removeprefix("__cpp_lib_"), ev["std"], ev.get("min_value", 1)
        got = [e["version"] for e in feats[slug]["history"]["cpp"] if e["kind"] == "added"]
        if got != [f"cpp{std}"]: report.problem(f"{slug}: the data adds it in {got} but its macro evidence belongs to C++{std}")
        prev = PREVIOUS[std]
        results = []
        for c in strict_cfgs:
            a, b = c.lib_macros(std), c.lib_macros(prev)
            results.append((a is not None and a.get(name, 0) >= low, b is not None and b.get(name, 0) < low))
        confirmed = any(a and b for a, b in results)
        if slug in LIBRARY_LEAKAGE:
            if confirmed: report.problem(f"{slug}: listed as leaking, but a strict configuration does confirm its boundary")
        elif not confirmed:
            report.problem(f"{slug}: no strict configuration defines {ev['macro']} at C++{std} and not at C++{prev}: {results}")
    for slug in LIBRARY_LEAKAGE:
        if slug not in LIBRARY_EVIDENCE: report.problem(f"LIBRARY_LEAKAGE has {slug}, which is not in LIBRARY_EVIDENCE")


# ---------------------------------------------------------------- 4. lifecycle
def behaviour(cfg: Config, probe: dict) -> str:
    std = probe["removed"]; before = PREVIOUS[std]
    b, a = compiles(cfg, before, probe["code"]), compiles(cfg, std, probe["code"])
    if probe["inverse"]: return "changes" if (not b and a) else "ok-both" if (b and a) else "unclear"
    return "rejects" if (b and not a) else "accepts" if (b and a) else "unclear"


def check_lifecycle(data: dict, cfgs: dict, report: Report, strict: bool) -> None:
    feats = features(data)
    for slug, probe in LIFECYCLE_PROBES.items():
        if slug not in feats: report.problem(f"LIFECYCLE_PROBES has {slug}, which is not a feature in the data"); continue
        if not probe["removed"] or not probe["impl"]: continue
        for track, version, key in (("clang", 23, "libcxx"), ("gcc", 16, "libstdcxx")):
            cfg = cfgs.get((track, version))
            if cfg is None:
                (report.problem if strict else report.skipped.append)(f"{slug}: {track} {version} not found, so its removal behaviour was not checked"); continue
            report.count("lifecycle behaviours")
            got = behaviour(cfg, probe)
            if got != probe["impl"][key]: report.problem(f"{slug}: {track} {version} {got} at C++{probe['removed']}, the data records {probe['impl'][key]}")


# ---------------------------------------------------------------- 5. coverage
def check_coverage(data: dict, report: Report) -> None:
    feats = features(data)
    for slug in feats:
        if slug.startswith("header-") and slug not in HEADER_PROBES: report.problem(f"header feature {slug} has no probe")
    for slug in HEADER_PROBES:
        if slug not in feats: report.problem(f"HEADER_PROBES has {slug}, which is not a feature in the data")
    for slug in LANGUAGE_EVIDENCE:
        if slug not in feats: report.problem(f"LANGUAGE_EVIDENCE has {slug}, which is not a feature in the data")
    for slug in feats:
        if slug.startswith("lib-") and slug not in LIBRARY_EVIDENCE: report.problem(f"library feature {slug} has no evidence entry")
    for slug in LIBRARY_EVIDENCE:
        if slug not in feats: report.problem(f"LIBRARY_EVIDENCE has {slug}, which is not a feature in the data")
    report.count("probe table entries", len(HEADER_PROBES) + len(LANGUAGE_EVIDENCE) + len(LIFECYCLE_PROBES) + len(LIBRARY_EVIDENCE))


def run(data: dict, cfgs: dict, strict: bool, jobs: int) -> Report:
    report = Report()
    check_markers(data, report)
    check_coverage(data, report)
    missing = [f"{t}{v}" for t, vs in (("gcc", GCC_VERSIONS), ("clang", CLANG_VERSIONS)) for v in vs if (t, v) not in cfgs]
    if missing:
        (report.problem if strict else report.skipped.append)(f"configurations not found: {', '.join(missing)}")
    with ThreadPoolExecutor(max_workers=jobs) as pool:   # warm the macro and -std caches in parallel
        list(pool.map(lambda c: c.macros(), list(cfgs.values())))
    check_events(data, cfgs, report, strict)
    check_boundaries(data, cfgs, report, strict)
    check_library_boundaries(data, cfgs, report, strict)
    check_lifecycle(data, cfgs, report, strict)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--strict", action="store_true", help="a missing configuration is an error")
    parser.add_argument("--envs-root", default="/opt", help="where the conda environments gcc15, gcc16, clang21 to clang23 are")
    parser.add_argument("--libcxx-root", default="/opt/libcxx", help="where libc++ headers are unpacked, one directory per version")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    args = parser.parse_args(argv)
    cfgs = discover(args.envs_root, args.libcxx_root)
    if not cfgs:
        print(f"{'FAIL' if args.strict else 'SKIP'} cpp examples: no C++ toolchain configuration found" + (" (--strict)" if args.strict else ""))
        return 1 if args.strict else 0
    report = run(load_data(), cfgs, args.strict, args.jobs)
    print(f"     configurations found: {len(cfgs)} of {len(GCC_VERSIONS) + len(CLANG_VERSIONS)}")
    for name, n in report.counts.items(): print(f"     {name}: {n}")
    for line in report.skipped: print(f"SKIP {line}")
    if report.problems:
        for p in report.problems: print(f"FAIL {p}")
        print(f"FAIL cpp examples: {len(report.problems)} problem(s)")
        return 1
    print("OK   cpp examples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
