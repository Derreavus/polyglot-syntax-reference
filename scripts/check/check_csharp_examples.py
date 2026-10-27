#!/usr/bin/env python3
"""Check the C# version-history data against the real C# compiler (Roslyn) and reference assemblies.

Language-specific, like check_rust_examples.py. It reads the C#, .NET and .NET Framework features from
data/site_data.json and compiles small snippets with the Roslyn compiler that ships in a .NET SDK. Standard
library only. The snippets live in csharp_probe_data.py.

1. Language versions. For every C# language event with a probe, the snippet must compile at the event's
   -langversion and FAIL at the previous one, which confirms the data's version is neither too early nor too late.
2. .NET Framework. For every Framework event with a probe, the snippet must compile against the reference assemblies
   of that release and fail against the previous release's (4.5 is compared with 4.0). The reference assemblies
   come from Mono's `<version>-api` directories.
3. .NET APIs. For every .NET event with an API probe, the type or member must exist in the .NET 10 reference pack, and
   in the .NET 8 pack only for releases up to .NET 8. The packs available cannot tell earlier releases apart.
4. Compatibility. The language features that need library or runtime support are compiled at the newest
   -langversion against .NET Framework 4.5 to 4.8, netstandard 2.1, .NET 8 and .NET 10. The data's compatibility notes
   must be exactly what those results say, and a feature that compiles everywhere must have no such note.
5. Default language versions. A real SDK build reports the compiler's default C# version for net8.0 and net10.0, which
   must match the note on those .NET releases.
6. Coverage. Every event on the three tracks must have a probe or an entry in NOT_PROBEABLE with the reason, and every
   probe must belong to an event in the data, so a new feature cannot ship unchecked and a stale probe cannot linger.

The probes establish what compiles. The release in which a library API first shipped rests on Microsoft's
documentation and the dotnet-api-docs history, gathered when the data was written.

Run from the repo root:
    python3 scripts/check/check_csharp_examples.py            # SDK on PATH; skipped if missing
    python3 scripts/check/check_csharp_examples.py --strict   # a missing SDK, pack or Mono is an error
    python3 scripts/check/check_csharp_examples.py --mono /usr/lib/mono --jobs 4

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

from csharp_probe_data import (  # noqa: E402
    COMPAT_PROBES, FRAMEWORK_PROBES, LANGUAGE_PROBES, NOT_PROBEABLE, POLYFILL_FOR, POLYFILLS, RUNTIME_API_PROBES,
)
from load_data import load_data  # noqa: E402

LANGUAGE = "csharp"
CSHARP, DOTNET, NETFX = "csharp", "dotnet", "netfx"
FRAMEWORK_TARGETS = ["4.5", "4.6.2", "4.7", "4.7.1", "4.7.2", "4.8"]
COMPAT_PREFIX = "Needs library or runtime support."
POLYFILL_TYPES = {
    "records+init": "System.Runtime.CompilerServices.IsExternalInit",
    "module-initializer": "System.Runtime.CompilerServices.ModuleInitializerAttribute",
    "required": "RequiredMemberAttribute, CompilerFeatureRequiredAttribute and SetsRequiredMembersAttribute",
}
# Mono's directory for .NET Framework 4.0, the release before the first one the data covers.
FRAMEWORK_BEFORE_FIRST = "4.0"
FRAMEWORK_ORDER = ["4.0", "4.5", "4.5.1", "4.5.2", "4.6", "4.6.1", "4.6.2", "4.7", "4.7.1", "4.7.2", "4.8"]


class Toolchain:
    """Where the compiler and reference assemblies are. Any part may be missing; checks that need it are skipped or fail under --strict."""

    def __init__(self, csc: list[str], supported: list[str], packs: dict[str, list[str] | None], mono: Path | None, dotnet: str):
        self.csc, self.supported, self.packs, self.mono, self.dotnet = csc, supported, packs, mono, dotnet

    def mono_refs(self, version: str) -> list[str] | None:
        if self.mono is None:
            return None
        base = self.mono / f"{version}-api"
        if not base.is_dir():
            return None
        return [f"-r:{f}" for f in sorted(glob.glob(str(base / "*.dll"))) + sorted(glob.glob(str(base / "Facades" / "*.dll")))]


# ---------------------------------------------------------------- discovery

def parse_sdk_list(text: str) -> tuple[str, str] | None:
    """Pick the highest SDK from `dotnet --list-sdks` output: '10.0.113 [/usr/lib/dotnet/sdk]' -> ('10.0.113', '/usr/lib/dotnet/sdk')."""
    found = []
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\.(\d+)\.(\d+)\S*\s+\[(.+)\]\s*$", line)
        if m:
            found.append(((int(m[1]), int(m[2]), int(m[3])), line.split()[0], m[4]))
    if not found:
        return None
    _, version, base = max(found)
    return version, base


def parse_langversions(text: str) -> list[str]:
    """The numbered values from `csc -langversion:?` in order, without default, latest, preview and latestmajor."""
    out = []
    for line in text.splitlines():
        token = line.split()[0] if line.split() else ""
        if re.fullmatch(r"\d+(\.\d+)?", token):
            out.append(token)
    return out


def latest_pack(root: str, pack: str, major: int, subdir: str) -> list[str] | None:
    dirs = sorted(glob.glob(f"{root}/packs/{pack}/{major}.*/ref/{subdir}"))
    if not dirs:
        return None
    return [f"-r:{f}" for f in sorted(glob.glob(dirs[-1] + "/*.dll"))]


def discover(dotnet: str | None, mono: str | None) -> Toolchain | None:
    exe = dotnet or shutil.which("dotnet")
    if not exe:
        return None
    try:
        sdks = subprocess.run([exe, "--list-sdks"], capture_output=True, text=True)
    except OSError:
        return None
    picked = parse_sdk_list(sdks.stdout)
    if not picked:
        return None
    version, base = picked
    csc_dll = Path(base) / version / "Roslyn" / "bincore" / "csc.dll"
    if not csc_dll.is_file():
        return None
    csc = [exe, str(csc_dll), "-nologo", "-noconfig", "-nostdlib+", "-nullable:disable"]
    supported = parse_langversions(subprocess.run([*csc, "-langversion:?"], capture_output=True, text=True).stdout)
    root = str(Path(base).parent)
    packs = {
        "net8.0": latest_pack(root, "Microsoft.NETCore.App.Ref", 8, "net8.0"),
        "net10.0": latest_pack(root, "Microsoft.NETCore.App.Ref", 10, "net10.0"),
        "netstandard2.1": latest_pack(root, "NETStandard.Library.Ref", 2, "netstandard2.1") or latest_pack(root, "NETStandard.Library.Ref", 2, "ref/netstandard2.1"),
    }
    mono_dir = Path(mono) if mono else next((Path(p) for p in ("/usr/lib/mono", "/usr/local/lib/mono") if Path(p).is_dir()), None)
    return Toolchain(csc, supported, packs, mono_dir, exe)


# ---------------------------------------------------------------- compiler

def compile_snippet(tc: Toolchain, refs: list[str], code: str, langversion: str, flags: tuple[str, ...] = ()) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "snippet.cs"
        src.write_text(code + "\n", encoding="utf-8")
        cmd = [*tc.csc, f"-langversion:{langversion}", "-t:exe" if "exe" in flags else "-t:library", f"-out:{tmp}/snippet.dll",
               "-nowarn:CS0168,CS0219,CS0169,CS0649,CS8632"]
        if "unsafe" in flags:
            cmd.append("-unsafe")
        result = subprocess.run([*cmd, *refs, str(src)], capture_output=True, text=True, timeout=300)
        output = result.stdout + result.stderr
        if "warnfail" in flags and "CS8371" in output:
            return False, "warning CS8371: field-targeted attributes on auto-properties are not supported in this language version"
        lines = [line for line in output.splitlines() if "error" in line]
        return result.returncode == 0, (lines[0] if lines else "")


def error_code(message: str) -> str:
    m = re.search(r"error (CS\d+)", message)
    return m.group(1) if m else ""


def langversion(version_id: str) -> str:
    """'cs7.3' -> '7.3'; C# 1 to 6 are named by their major number only."""
    ver = version_id.removeprefix("cs")
    major = int(ver.split(".")[0])
    return ver[:-2] if ver.endswith(".0") and major < 7 else ver


def previous_langversion(lv: str, supported: list[str]) -> str | None:
    if lv not in supported:
        return None
    i = supported.index(lv)
    return supported[i - 1] if i else None


def framework_version(version_id: str) -> str:
    return version_id.removeprefix("fx")


def previous_framework(version: str) -> str | None:
    i = FRAMEWORK_ORDER.index(version) if version in FRAMEWORK_ORDER else -1
    return FRAMEWORK_ORDER[i - 1] if i > 0 else None


def dotnet_major(version_id: str) -> int:
    """'net9.0' -> 9; every '.NET Core' release counts as before .NET 8."""
    return int(version_id.removeprefix("net").split(".")[0]) if version_id.startswith("net") else 0


# ---------------------------------------------------------------- compatibility notes

def expected_compat_note(row: dict[str, tuple[bool, str]], polyfill_slug: str | None, polyfill_ok: bool) -> str | None:
    """The note the data must carry for a language feature, from compile results per target; None when it compiles everywhere."""
    if all(ok for ok, _ in row.values()):
        return None
    fw = {t: row[f"net{t}"] for t in FRAMEWORK_TARGETS}
    fw_ok = [t for t in FRAMEWORK_TARGETS if fw[t][0]]
    code = next((error_code(fw[t][1]) for t in FRAMEWORK_TARGETS if not fw[t][0] and error_code(fw[t][1])), "")
    parts = []
    if not fw_ok:
        parts.append(f"It does not compile against any .NET Framework 4.5 to 4.8 reference assembly ({code})")
    else:
        parts.append(f"It compiles against .NET Framework from {fw_ok[0]} but not before ({code})")
    ns_ok, ns_err = row["netstandard2.1"]
    parts.append("netstandard 2.1 " + ("accepts it" if ns_ok else f"rejects it ({error_code(ns_err)})"))
    modern = [t for t in ("net8.0", "net10.0") if row[t][0]]
    parts.append(".NET 8 and .NET 10 accept it" if len(modern) == 2 else "check .NET 8 and .NET 10 results")
    text = f"{COMPAT_PREFIX} " + "; ".join(parts) + "."
    if polyfill_slug and polyfill_ok:
        text += f" Defining {POLYFILL_TYPES[polyfill_slug]} in your own code makes it compile there; this was checked at compile time only."
    return text


# ---------------------------------------------------------------- the checks

class Report:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.counts: dict[str, int] = {}
        self.skipped: list[str] = []

    def count(self, name: str, n: int = 1) -> None:
        self.counts[name] = self.counts.get(name, 0) + n

    def problem(self, message: str) -> None:
        self.problems.append(message)


def events_of(data: dict, track: str) -> list[tuple[str, str, str]]:
    """(feature slug, event version id, event kind) for every event on a track."""
    return [(f["slug"], e["version"], e["kind"]) for f in data["features"] if f["language"] == LANGUAGE for e in f["history"].get(track, [])]


def check_coverage(data: dict, report: Report) -> None:
    in_data = set()
    for track in (CSHARP, DOTNET, NETFX):
        keys = {f"{slug}@{version}" for slug, version, _ in events_of(data, track)}
        in_data |= keys
        probes = {CSHARP: LANGUAGE_PROBES, DOTNET: RUNTIME_API_PROBES, NETFX: FRAMEWORK_PROBES}[track]
        for key in sorted(keys):
            if key not in probes and key not in NOT_PROBEABLE:
                report.problem(f"{track} event {key} has no probe and no NOT_PROBEABLE reason")
        report.count(f"{track} events", len(keys))
    for table, name in ((LANGUAGE_PROBES, "LANGUAGE_PROBES"), (FRAMEWORK_PROBES, "FRAMEWORK_PROBES"), (RUNTIME_API_PROBES, "RUNTIME_API_PROBES"),
                        (NOT_PROBEABLE, "NOT_PROBEABLE")):
        for key in table:
            if key not in in_data:
                report.problem(f"{name} has {key}, which is not an event in the data")
    for key in NOT_PROBEABLE:
        if key in LANGUAGE_PROBES or key in FRAMEWORK_PROBES or key in RUNTIME_API_PROBES:
            report.problem(f"{key} has both a probe and a NOT_PROBEABLE reason")


def check_language(tc: Toolchain, data: dict, report: Report, pool: ThreadPoolExecutor) -> None:
    jobs = []
    for slug, version, kind in events_of(data, CSHARP):
        key = f"{slug}@{version}"
        if key not in LANGUAGE_PROBES:
            continue
        code, flags = LANGUAGE_PROBES[key]
        lv = langversion(version)
        if lv not in tc.supported:
            report.skipped.append(f"{key}: the compiler does not know -langversion {lv}")
            continue
        prev = previous_langversion(lv, tc.supported)
        jobs.append((key, kind, lv, prev, pool.submit(compile_snippet, tc, [*tc.packs["net10.0"]], code, lv, flags),
                     pool.submit(compile_snippet, tc, [*tc.packs["net10.0"]], code, prev, flags) if prev else None))
    for key, kind, lv, prev, now, before in jobs:
        ok, err = now.result()
        report.count("language probes")
        if not ok:
            report.problem(f"{key}: does not compile at -langversion {lv}: {err}")
        if before is not None:
            bok, _ = before.result()
            if bok:
                report.problem(f"{key}: also compiles at -langversion {prev}, so {lv} is too late (or the feature is not gated by -langversion)")


def check_framework(tc: Toolchain, data: dict, report: Report, pool: ThreadPoolExecutor, strict: bool) -> None:
    jobs = []
    for slug, version, kind in events_of(data, NETFX):
        key = f"{slug}@{version}"
        if key not in FRAMEWORK_PROBES:
            continue
        v = framework_version(version)
        prev = previous_framework(v)
        refs, prev_refs = tc.mono_refs(v), tc.mono_refs(prev) if prev else None
        if refs is None or prev_refs is None:
            (report.problem if strict else report.skipped.append)(f"{key}: Mono reference assemblies for {v} or {prev} not found")
            continue
        code = FRAMEWORK_PROBES[key]
        jobs.append((key, v, prev, pool.submit(compile_snippet, tc, refs, code, "7.3"), pool.submit(compile_snippet, tc, prev_refs, code, "7.3")))
    for key, v, prev, now, before in jobs:
        ok, err = now.result()
        report.count("framework probes")
        if not ok:
            report.problem(f"{key}: does not compile against the {v} reference assemblies: {err}")
        if before.result()[0]:
            report.problem(f"{key}: also compiles against {prev}, so {v} is too late")


def check_runtime_apis(tc: Toolchain, data: dict, report: Report, pool: ThreadPoolExecutor, strict: bool) -> None:
    n8, n10 = tc.packs.get("net8.0"), tc.packs.get("net10.0")
    if n8 is None or n10 is None:
        msg = "the .NET 8 or .NET 10 reference pack is missing, so the .NET API probes were not run"
        report.problem(msg) if strict else report.skipped.append(msg)
        return
    jobs = []
    for slug, version, kind in events_of(data, DOTNET):
        key = f"{slug}@{version}"
        if key not in RUNTIME_API_PROBES:
            continue
        code = RUNTIME_API_PROBES[key]
        jobs.append((key, dotnet_major(version), pool.submit(compile_snippet, tc, n10, code, "latest"), pool.submit(compile_snippet, tc, n8, code, "latest")))
    for key, major, on10, on8 in jobs:
        report.count("API probes")
        ok10, err10 = on10.result()
        ok8, err8 = on8.result()
        if not ok10:
            report.problem(f"{key}: not in the .NET 10 reference pack: {err10}")
        if major <= 8 and not ok8:
            report.problem(f"{key}: expected in the .NET 8 reference pack but missing: {err8}")
        if major >= 9 and ok8:
            report.problem(f"{key}: already in the .NET 8 reference pack, so listing it at .NET {major} is too late")


def check_compat(tc: Toolchain, data: dict, report: Report, pool: ThreadPoolExecutor, strict: bool) -> None:
    targets: dict[str, list[str] | None] = {f"net{t}": tc.mono_refs(t) for t in FRAMEWORK_TARGETS}
    targets.update({"netstandard2.1": tc.packs.get("netstandard2.1"), "net8.0": tc.packs.get("net8.0"), "net10.0": tc.packs.get("net10.0")})
    missing = [t for t, refs in targets.items() if refs is None]
    if missing:
        msg = f"reference assemblies missing for {', '.join(missing)}, so the compatibility notes were not checked"
        report.problem(msg) if strict else report.skipped.append(msg)
        return
    futures = {slug: {t: pool.submit(compile_snippet, tc, refs, code, "latest") for t, refs in targets.items()} for slug, code in COMPAT_PROBES.items()}
    poly = {name: {t: pool.submit(compile_snippet, tc, targets[t], code, "latest") for t in ("net4.8", "netstandard2.1")} for name, code in POLYFILLS.items()}
    features = {f["slug"]: f for f in data["features"] if f["language"] == LANGUAGE}
    for slug, per_target in futures.items():
        row = {t: fut.result() for t, fut in per_target.items()}
        pname = POLYFILL_FOR.get(slug)
        pok = bool(pname) and all(fut.result()[0] for fut in poly[pname].values())
        expected = expected_compat_note(row, pname, pok)
        events = features[slug]["history"][CSHARP]
        notes = [e.get("note", "") for e in events if COMPAT_PREFIX in e.get("note", "")]
        report.count("compatibility checks")
        if expected is None:
            if notes:
                report.problem(f"{slug}: compiles against every target, but the data has a compatibility note")
        elif notes != [expected] or events[0].get("note") != expected:
            report.problem(f"{slug}: compatibility note differs from the compile results.\n    expected: {expected}\n    in data:  {events[0].get('note')}")
    # features outside the checked list must not carry the note
    for slug, feature in features.items():
        if slug not in COMPAT_PROBES and any(COMPAT_PREFIX in e.get("note", "") for e in feature["history"].get(CSHARP, [])):
            report.problem(f"{slug}: has a compatibility note but no compat probe to back it")


def default_csharp_version(tc: Toolchain, tfm: str) -> str | None:
    """The language version the SDK picks by default for a target framework, read from a real build."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "p.csproj").write_text(
            f'<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>{tfm}</TargetFramework><OutputType>Library</OutputType>'
            "<NuGetAudit>false</NuGetAudit></PropertyGroup></Project>", encoding="utf-8")
        (Path(tmp) / "a.cs").write_text("#error version\n", encoding="utf-8")
        env = {**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1", "DOTNET_NOLOGO": "1"}
        result = subprocess.run([tc.dotnet, "build"], cwd=tmp, capture_output=True, text=True, env=env, timeout=600)
        m = re.search(r"Language version: (\d+(?:\.\d+)?)", result.stdout + result.stderr)
        return m.group(1) if m else None


def check_defaults(tc: Toolchain, data: dict, report: Report, strict: bool) -> None:
    versions = {v["id"]: v for v in data["versions"] if v["language"] == LANGUAGE and v["track"] == DOTNET}
    for tfm, version_id in (("net8.0", "net8.0"), ("net10.0", "net10.0")):
        if tc.packs.get(tfm) is None:
            msg = f"the {tfm} reference pack is missing, so its default C# version was not checked"
            report.problem(msg) if strict else report.skipped.append(msg)
            continue
        found = default_csharp_version(tc, tfm)
        report.count("default-version builds")
        note = versions[version_id].get("note", "")
        if found is None:
            report.problem(f"{tfm}: the SDK build did not report a language version")
        elif f"Default C# version: {found.removesuffix('.0')}." not in note and f"Default C# version: {found}." not in note:
            report.problem(f"{tfm}: the SDK defaults to C# {found} but the data says {note!r}")


def run(tc: Toolchain, data: dict, strict: bool, jobs: int) -> Report:
    report = Report()
    check_coverage(data, report)
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        if tc.packs.get("net10.0") is None:
            report.problem("the .NET 10 reference pack is missing, so nothing could be compiled") if strict else report.skipped.append("the .NET 10 reference pack is missing")
        else:
            check_language(tc, data, report, pool)
        check_framework(tc, data, report, pool, strict)
        check_runtime_apis(tc, data, report, pool, strict)
        check_compat(tc, data, report, pool, strict)
    check_defaults(tc, data, report, strict)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--strict", action="store_true", help="a missing SDK, reference pack or Mono is an error")
    parser.add_argument("--dotnet", help="path to the dotnet executable")
    parser.add_argument("--mono", help="directory that holds Mono's <version>-api directories (default /usr/lib/mono)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    args = parser.parse_args(argv)
    tc = discover(args.dotnet, args.mono)
    if tc is None:
        print(f"{'FAIL' if args.strict else 'SKIP'} csharp examples: no .NET SDK with Roslyn found" + (" (--strict)" if args.strict else ""))
        return 1 if args.strict else 0
    report = run(tc, load_data(), args.strict, args.jobs)
    for name, n in report.counts.items():
        print(f"     {name}: {n}")
    for line in report.skipped:
        print(f"SKIP {line}")
    if report.problems:
        for problem in report.problems:
            print(f"FAIL {problem}")
        print(f"FAIL csharp examples: {len(report.problems)} problem(s)")
        return 1
    print("OK   csharp examples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
