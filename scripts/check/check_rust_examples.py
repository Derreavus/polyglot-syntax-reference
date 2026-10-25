#!/usr/bin/env python3
"""Check the Rust version-history data against a real Rust compiler.

Language-specific, like check_python_examples.py. It reads the Rust features from data/site_data.json and
compiles code with whatever rustc it is given, so it can run on any toolchain. Standard library only.

It adapts to the compiler's version M (read from `rustc --version`), so a single run on one toolchain is
checked in both directions, and CI runs it on an old and a new toolchain:

1. Examples. For every feature with a before/after example, the "before" snippet must compile in its
   edition. The "after" snippet must compile when the feature already exists in rustc 1.M, and must FAIL to
   compile when the data says the feature is newer than that, which confirms the data's version is not too
   early.
2. Probes. A tiny program per feature that compiles if the feature is available. The result is compared
   with what the site itself says about that feature in 1.M (renderer/versioning.py lifecycle_state, using
   the nearest listed release at or before 1.M). Deprecated features are checked by denying the
   `deprecated` lint, which must then reject them.
3. Edition probes. Code that compiles in one edition and fails in the next. The probe must agree with the
   data: the edition track has an event for that feature at the edition where the behaviour differs.
4. Coverage. Every Rust feature must have an example, a probe, an edition probe, or an entry in
   NOT_PROBEABLE with the reason, so a new feature cannot ship unchecked.

The probes establish availability at the toolchains they run on. The exact release in which something was
stabilised rests on Rust's own release notes, gathered when the data was written.

Run from the repo root:
    python3 scripts/check/check_rust_examples.py                                  # rustc on PATH; skipped if missing
    python3 scripts/check/check_rust_examples.py --strict                         # a missing rustc is an error
    python3 scripts/check/check_rust_examples.py --strict --rustc "rustup run 1.75.0 rustc"

Exit code 0 = OK, 1 = problems found.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "renderer"))

from load_data import load_data  # noqa: E402
from versioning import features_for, lifecycle_state, version_orders, versions_for  # noqa: E402

LANGUAGE = "rust"
RELEASES, EDITIONS = "rust", "edition"
EDITION_MIN_RUSTC = {"2015": 0, "2018": 31, "2021": 56, "2024": 85}  # the first rustc that accepts each edition

# (legacy edition, modern edition) for each example, because some "before" code only exists in 2015 or 2018.
EXAMPLE_EDITIONS = {
    "question-mark": ("2015", "2021"), "try-macro": ("2015", "2021"), "impl-trait": ("2015", "2021"),
    "bare-trait-objects": ("2015", "2021"), "ellipsis-range-patterns": ("2015", "2021"),
    "nll": ("2015", "2021"), "anonymous-trait-params": ("2015", "2018"),
    "let-chains": ("2021", "2024"), "if-let-guards": ("2021", "2024"),
    "unsafe-extern": ("2021", "2024"), "unsafe-attributes": ("2021", "2024"),
}
DEFAULT_EXAMPLE_EDITIONS = ("2021", "2021")


class Probe(NamedTuple):
    code: str
    edition: str = "2021"
    crate: str = "lib"
    flags: tuple[str, ...] = ()
    deprecation: bool = False  # compiled with -D deprecated, which must reject the code once it is deprecated


def P(code: str, edition: str = "2021", crate: str = "lib", flags: tuple[str, ...] = (), deprecation: bool = False) -> Probe:
    return Probe(code, edition, crate, flags, deprecation)


DENY_DEPRECATED = ("-D", "deprecated")
DENY_UNKNOWN_LINTS = ("-D", "unknown_lints")

# Availability probes: the code compiles when the feature exists in the compiler (a deprecated feature still does).
PROBES: dict[str, list[Probe]] = {
    "question-mark": [P('pub fn f() -> Result<(), std::num::ParseIntError> { "1".parse::<i32>()?; Ok(()) }')],
    "try-macro": [P('pub fn f() -> Result<u8, std::num::ParseIntError> { Ok(try!("1".parse::<u8>())) }', "2015"),
                  P('pub fn f() -> Result<u8, std::num::ParseIntError> { Ok(try!("1".parse::<u8>())) }', "2015", flags=DENY_DEPRECATED, deprecation=True)],
    "impl-trait": [P("pub fn f() -> impl Iterator<Item = u8> { 0..3u8 }")],
    "dyn-trait": [P("pub fn f(_: &dyn std::fmt::Debug) {}")],
    "bare-trait-objects": [P("pub fn f(_: &std::fmt::Debug) {}", "2015"),
                           P("pub fn f(_: &std::fmt::Debug) {}", "2018", flags=("-D", "bare_trait_objects"), deprecation=True)],
    "inclusive-ranges": [P("pub fn f() { for _ in 1..=3 {} }")],
    "ellipsis-range-patterns": [P("pub fn f(c: char) -> bool { match c { 'a'...'z' => true, _ => false } }", "2015")],
    "const-fn": [P("pub const fn f() -> u8 { 1 }")],
    "async-await": [P("pub async fn f() {}", "2018")],
    "gats": [P("pub trait T { type A<'a> where Self: 'a; }")],
    "let-else": [P("pub fn f(x: Option<u8>) -> u8 { let Some(y) = x else { return 0 }; y }")],
    "const-generics": [P("pub fn f<const N: usize>(_: [u8; N]) {}")],
    "slice-patterns": [P("pub fn f(v: &[u8]) { if let [first, ..] = v { let _ = first; } }")],
    "inline-format-args": [P('pub fn f(x: u8) -> String { format!("{x}") }')],
    "inline-const": [P("pub fn f() -> u8 { const { 1 } }")],
    "exclusive-range-patterns": [P("pub fn f(x: u8) -> bool { match x { 0..5 => true, _ => false } }")],
    "async-fn-in-traits": [P("pub trait T { async fn f(&self); }")],
    "precise-capturing": [P("pub fn f<'a>(x: &'a u8) -> impl Sized + use<'a> { x }")],
    "raw-borrow": [P("pub fn f(x: &u8) -> *const u8 { &raw const *x }")],
    "c-string-literals": [P('pub fn f() -> &\'static std::ffi::CStr { c"x" }')],
    "trait-upcasting": [P("pub trait A {} pub trait B: A {} pub fn f(x: &dyn B) -> &dyn A { x }")],
    "async-closures": [P("pub fn f() { let _c = async || {}; }")],
    "let-chains": [P("pub fn f(a: Option<u8>) -> bool { if let Some(x) = a && x > 0 { true } else { false } }", "2024")],
    "if-let-guards": [P("pub fn f(a: Option<u8>) -> u8 { match a { Some(x) if let Ok(y) = u8::try_from(x) => y, _ => 0 } }", "2024")],
    "nll": [P("pub fn f() { let mut v = vec![1u8]; let a = &v[0]; let _ = *a; v.push(2); }")],
    "associated-consts": [P("pub struct S; impl S { pub const X: u8 = 1; }")],
    "procedural-macros": [P("extern crate proc_macro; use proc_macro::TokenStream; #[proc_macro] pub fn m(i: TokenStream) -> TokenStream { i }", crate="proc-macro")],
    "u128": [P("pub fn f() -> u128 { 1 }")],
    "main-return-values": [P("fn main() -> Result<(), String> { Ok(()) }", crate="bin")],
    "derive-default-enum": [P("#[derive(Default)] pub enum E { #[default] A }")],
    "unsafe-op-in-unsafe-fn": [P("#![deny(unsafe_op_in_unsafe_fn)] pub unsafe fn f(p: *const u8) -> u8 { unsafe { *p } }", flags=DENY_UNKNOWN_LINTS)],
    "static-mut-references": [P("#![deny(static_mut_refs)] pub fn f() {}", flags=DENY_UNKNOWN_LINTS)],
    "unsafe-extern": [P('unsafe extern "C" { pub safe fn abs(x: i32) -> i32; }')],
    "unsafe-attributes": [P('#[unsafe(no_mangle)] pub extern "C" fn f() {}')],
    "thread-scope": [P("pub fn f() { std::thread::scope(|_| {}); }")],
    "lazy-statics": [P("pub static X: std::sync::OnceLock<u8> = std::sync::OnceLock::new();")],
    "maybe-uninit": [P("pub fn f() { let _ = std::mem::MaybeUninit::<u8>::uninit(); }")],
    "mem-uninitialized": [P("pub fn f() -> u8 { unsafe { std::mem::uninitialized() } }"),
                          P("pub fn f() -> u8 { unsafe { std::mem::uninitialized() } }", flags=DENY_DEPRECATED, deprecation=True)],
    "nonzero": [P("pub fn f() { let _ = std::num::NonZeroU8::new(1); }")],
    "array-into-iter": [P("pub fn f() { for _ in [1u8, 2] {} }")],
    "core-error": [P("pub fn f(_: &dyn core::error::Error) {}")],
    "error-description": [P("pub fn f(e: &dyn std::error::Error) { let _ = e.description(); }"),
                          P("pub fn f(e: &dyn std::error::Error) { let _ = e.description(); }", flags=DENY_DEPRECATED, deprecation=True)],
    "trim-left-right": [P("pub fn f(s: &str) -> &str { s.trim_left() }"),
                        P("pub fn f(s: &str) -> &str { s.trim_left() }", flags=DENY_DEPRECATED, deprecation=True)],
    "atomic-compare-and-swap": [
        P("use std::sync::atomic::{AtomicUsize, Ordering}; pub fn f(a: &AtomicUsize) { let _ = a.compare_and_swap(0, 1, Ordering::SeqCst); }"),
        P("use std::sync::atomic::{AtomicUsize, Ordering}; pub fn f(a: &AtomicUsize) { let _ = a.compare_and_swap(0, 1, Ordering::SeqCst); }", flags=DENY_DEPRECATED, deprecation=True)],
    "anonymous-trait-params": [P("pub trait T { fn f(&self, u8); }", "2015"),
                               P("pub trait T { fn f(&self, u8); }", "2015", flags=("-D", "anonymous_parameters"), deprecation=True)],
    "box-slice-into-iter": [P("pub fn f(b: Box<[u8]>) { for _ in b {} }")],
}


class EditionProbe(NamedTuple):
    code: str
    ok_in: str
    fails_in: str
    min_rustc: int = 0  # the first rustc that can tell the editions apart for this code


# Code that compiles in one edition and fails in the other. The newer of the two editions must have an event
# in the data's edition track for the feature.
EDITION_PROBES: dict[str, list[EditionProbe]] = {
    "bare-trait-objects": [EditionProbe("pub fn f(_: &std::fmt::Debug) {}", "2018", "2021")],
    "ellipsis-range-patterns": [EditionProbe("pub fn f(c: char) -> bool { match c { 'a'...'z' => true, _ => false } }", "2018", "2021")],
    "anonymous-trait-params": [EditionProbe("pub trait T { fn f(&self, u8); }", "2015", "2018")],
    "reserved-keywords": [EditionProbe("pub fn async() {}", "2015", "2018"),
                          EditionProbe("pub fn r#gen() {} pub fn g() { gen(); }", "2021", "2024", 85)],
    "module-paths": [EditionProbe("pub mod a { pub fn g() {} } pub fn f() { ::a::g(); }", "2015", "2018")],
    "array-into-iter": [EditionProbe("pub fn f() { let a = [1u8]; let _: u8 = a.into_iter().next().unwrap(); }", "2021", "2018")],
    "disjoint-closure-capture": [EditionProbe(
        "pub struct S { pub a: String, pub b: String } pub fn f(s: &mut S) { let c = || drop(&s.a); s.b.push('x'); c(); }", "2021", "2018")],
    "or-patterns-in-macros": [EditionProbe(
        "macro_rules! m { ($p:pat) => { match 1u8 { $p => {} _ => {} } } } pub fn f() { m!(1 | 2); }", "2021", "2018")],
    "prelude-additions": [EditionProbe("pub fn f() { let _ = u8::try_from(1u32); }", "2021", "2018"),
                          EditionProbe("pub fn f<T: Future>() {}", "2024", "2021", 85)],
    "panic-macro-consistency": [EditionProbe('pub fn f() { panic!("{}"); }', "2018", "2021")],
    "reserved-prefixes": [EditionProbe('macro_rules! m { ($($t:tt)*) => {} } pub fn f() { m!(a"x"); }', "2018", "2021")],
    "c-string-literals": [EditionProbe('pub fn f() -> &\'static std::ffi::CStr { c"x" }', "2021", "2018", 77)],
    "let-chains": [EditionProbe("pub fn f(a: Option<u8>) -> bool { if let Some(x) = a && x > 0 { true } else { false } }", "2024", "2021", 88)],
    "unsafe-extern": [EditionProbe('extern "C" { pub fn abs(x: i32) -> i32; }', "2021", "2024", 85)],
    "unsafe-attributes": [EditionProbe('#[no_mangle] pub extern "C" fn f() {}', "2021", "2024", 85)],
    "static-mut-references": [EditionProbe("static mut X: u8 = 0; pub fn f() { unsafe { let _ = &X; } }", "2021", "2024", 85)],
    "newly-unsafe-functions": [EditionProbe('pub fn f() { std::env::set_var("A", "b"); }', "2021", "2024", 85)],
    "macro-fragment-specifiers": [EditionProbe("macro_rules! m { ($e:expr) => {} } pub fn f() { m!(_); }", "2024", "2021", 85)],
    "rpit-lifetime-capture": [EditionProbe("pub fn f<'a>(x: &'a u8) -> impl Sized { x }", "2024", "2021", 85)],
    "tail-expression-temporary-scope": [EditionProbe(
        'pub fn f() -> usize { let c = std::cell::RefCell::new(""); c.borrow().len() }', "2024", "2021", 85)],
    "match-ergonomics-reservations": [EditionProbe("pub fn f(v: &Option<u8>) { match v { Some(ref x) => { let _ = x; } None => {} } }", "2021", "2024", 85)],
    "box-slice-into-iter": [EditionProbe("pub fn f(b: Box<[u8]>) { let _: u8 = b.into_iter().next().unwrap(); }", "2024", "2021", 85)],
}

# Features that rustc cannot check by compiling, with the reason.
NOT_PROBEABLE = {
    "cargo-add": "a Cargo command, not something rustc compiles",
    "workspace-inheritance": "Cargo manifest behaviour, not something rustc compiles",
    "sparse-registry": "Cargo registry protocol, not something rustc compiles",
    "cargo-lints-table": "Cargo manifest behaviour, not something rustc compiles",
    "cargo-resolver": "Cargo dependency resolution, not something rustc compiles",
    "if-let-temporary-scope": "a drop-order difference with no compile-time signal",
}


# ---------------------------------------------------------------- compiler

def compile_snippet(rustc: list[str], code: str, edition: str, crate: str = "lib", flags: tuple[str, ...] = ()) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "snippet.rs"
        src.write_text(code + "\n", encoding="utf-8")
        cmd = [*rustc, "--crate-type", crate, "--emit=metadata", "--edition", edition, "-A", "warnings", *flags, "--out-dir", tmp, str(src)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        lines = result.stderr.strip().splitlines()
        return result.returncode == 0, (lines[0] if lines else "")


def rustc_minor(rustc: list[str]) -> int | None:
    try:
        out = subprocess.run([*rustc, "--version"], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"rustc 1\.(\d+)\.", out)
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------- helpers

def minor_of(version_id: str) -> int:
    match = re.fullmatch(r"rust-1\.(\d+)", version_id)
    if not match:
        raise ValueError(f"unexpected release id {version_id!r}")
    return int(match.group(1))


def rust_added(feature: dict) -> int | None:
    for event in feature["history"].get(RELEASES, []):
        if event["kind"] == "added":
            return minor_of(event["version"])
    return None


def usable_edition(edition: str, minor: int) -> bool:
    return minor >= EDITION_MIN_RUSTC[edition]


# ---------------------------------------------------------------- checks

def check_examples(rustc: list[str], minor: int, features: list[dict], problems: list[str]) -> dict[str, int]:
    stats = dict(legacy=0, modern_ok=0, modern_fails_as_newer=0, skipped=0)
    for f in features:
        migration = f.get("migration")
        if not migration:
            continue
        slug = f["slug"]
        legacy_ed, modern_ed = EXAMPLE_EDITIONS.get(slug, DEFAULT_EXAMPLE_EDITIONS)
        added = rust_added(f)
        if added is None:
            added = 0
        if usable_edition(legacy_ed, minor):
            ok, msg = compile_snippet(rustc, migration["legacy"], legacy_ed)
            stats["legacy"] += 1
            if not ok:
                problems.append(f"{slug}: the 'before' snippet does not compile on edition {legacy_ed}: {msg[:120]}")
        edition = modern_ed if usable_edition(modern_ed, minor) else "2021"
        ok, msg = compile_snippet(rustc, migration["modern"], edition)
        if added <= minor:
            if ok:
                stats["modern_ok"] += 1
            elif usable_edition(modern_ed, minor):
                problems.append(f"{slug}: the 'after' snippet does not compile on rustc 1.{minor} although the feature arrived in 1.{added}: {msg[:120]}")
            else:
                stats["skipped"] += 1  # needs an edition this compiler does not have
        elif ok:
            problems.append(f"{slug}: the data says this arrived in 1.{added}, but the 'after' snippet compiles on rustc 1.{minor}")
        else:
            stats["modern_fails_as_newer"] += 1
    return stats


def check_probes(rustc: list[str], minor: int, data: dict, features: list[dict], problems: list[str]) -> dict[str, int]:
    stats = dict(available=0, deprecation=0, newer=0)
    versions = versions_for(data, LANGUAGE, RELEASES)
    orders = version_orders(versions)
    listed = [v for v in versions if minor_of(v["id"]) <= minor]
    at = orders[listed[-1]["id"]] if listed else 0
    for f in features:
        probes = PROBES.get(f["slug"])
        if not probes:
            continue
        state = lifecycle_state(f, RELEASES, orders, at)
        if state == "not-yet":
            stats["newer"] += 1
        for probe in probes:
            edition = probe.edition if usable_edition(probe.edition, minor) else "2021"
            ok, msg = compile_snippet(rustc, probe.code, edition, probe.crate, probe.flags)
            if probe.deprecation:
                stats["deprecation"] += 1
                expected_ok = state != "deprecated"
                if ok != expected_ok:
                    problems.append(f"{f['slug']}: the data says {state} in rustc 1.{minor}, but denying deprecations "
                                    f"{'accepted' if ok else 'rejected'} the code ({msg[:90]})")
                continue
            stats["available"] += 1
            expected_ok = state in ("available", "deprecated")
            if ok != expected_ok:
                actual = "compiles" if ok else f"does not compile ({msg[:90]})"
                problems.append(f"{f['slug']}: the data says {state} in rustc 1.{minor}, but the probe {actual}")
    return stats


def check_edition_probes(rustc: list[str], minor: int, features: list[dict], problems: list[str]) -> dict[str, int]:
    stats = dict(checked=0, skipped_old_compiler=0)
    by_slug = {f["slug"]: f for f in features}
    for slug, probes in EDITION_PROBES.items():
        feature = by_slug.get(slug)
        if feature is None:
            continue  # reported by the coverage check
        edition_versions = {e["version"] for e in feature["history"].get(EDITIONS, [])}
        for probe in probes:
            older, newer = sorted((probe.ok_in, probe.fails_in))
            if f"ed{newer}" not in edition_versions:
                problems.append(f"{slug}: the probe differs between editions {older} and {newer}, "
                                f"but the data has no edition event at {newer}")
            if minor < probe.min_rustc or not usable_edition(newer, minor):
                stats["skipped_old_compiler"] += 1
                continue
            stats["checked"] += 1
            ok, msg = compile_snippet(rustc, probe.code, probe.ok_in)
            if not ok:
                problems.append(f"{slug}: the edition probe should compile on {probe.ok_in} but does not: {msg[:110]}")
            ok, _msg = compile_snippet(rustc, probe.code, probe.fails_in)
            if ok:
                problems.append(f"{slug}: the edition probe should fail on {probe.fails_in} but compiles")
    return stats


def check_coverage(features: list[dict], problems: list[str]) -> None:
    slugs = {f["slug"] for f in features}
    known = set(PROBES) | set(EDITION_PROBES) | set(NOT_PROBEABLE) | set(EXAMPLE_EDITIONS)
    for slug in sorted(known - slugs):
        problems.append(f"{slug}: has a probe, example setting or exemption here but is not a feature of the Rust track")
    for slug in sorted((set(PROBES) | set(EDITION_PROBES)) & set(NOT_PROBEABLE)):
        problems.append(f"{slug}: is both probed and listed as not probeable")
    for f in features:
        slug = f["slug"]
        if not (f.get("migration") or slug in PROBES or slug in EDITION_PROBES or slug in NOT_PROBEABLE):
            problems.append(f"{slug}: nothing checks this feature; add an example, a probe, an edition probe or a NOT_PROBEABLE entry")


def main() -> int:
    args = sys.argv[1:]
    strict = "--strict" in args
    command = "rustc"
    if "--rustc" in args:
        command = args[args.index("--rustc") + 1]
    rustc = shlex.split(command)

    data = load_data()
    features = features_for(data, LANGUAGE, RELEASES) + [
        f for f in features_for(data, LANGUAGE, EDITIONS) if f["slug"] not in {g["slug"] for g in features_for(data, LANGUAGE, RELEASES)}]
    if not features:
        print("FAIL rust examples: the data has no Rust features")
        return 1

    problems: list[str] = []
    check_coverage(features, problems)

    minor = rustc_minor(rustc)
    if minor is None:
        message = f"no working compiler for `{command}`"
        if strict:
            print(f"FAIL rust examples: {message} (--strict)")
            return 1
        print(f"SKIP rust examples: {message}; coverage was checked, nothing was compiled")
        return 1 if problems else 0

    examples = check_examples(rustc, minor, features, problems)
    probes = check_probes(rustc, minor, data, features, problems)
    editions = check_edition_probes(rustc, minor, features, problems)

    if problems:
        print(f"FAIL rust examples (rustc 1.{minor}):")
        for problem in problems:
            print(f"  - {problem}")
        print(f"\n{len(problems)} problem(s) found")
        return 1

    print(f"OK   rust examples on rustc 1.{minor} ({len(features)} features)")
    print(f"     examples: {examples['legacy']} 'before' compile, {examples['modern_ok']} 'after' compile, "
          f"{examples['modern_fails_as_newer']} 'after' fail as newer than 1.{minor}, {examples['skipped']} skipped (edition too new)")
    print(f"     probes: {probes['available']} availability and {probes['deprecation']} deprecation checks against the site's own state; "
          f"{probes['newer']} features newer than 1.{minor} confirmed absent")
    print(f"     edition probes: {editions['checked']} compiled in both editions, {editions['skipped_old_compiler']} skipped (compiler too old)")
    print(f"     not probeable: {len(NOT_PROBEABLE)} ({', '.join(NOT_PROBEABLE)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
