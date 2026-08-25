#!/usr/bin/env python3
"""Regression tests for four config/engine bugs where the tool ignored its
own configuration:

  1. csv_integrity firing regardless of whether a CSV's resolved profile
     opts in via 'tests'.
  2. never_lint matching only at the repo root instead of by path segment.
  3. EARS checks hardcoded to the literal profile names 'spec'/'design'
     instead of consulting each profile's 'tests' list.
  4. severity_defaults being config that the engine never read.

Usage: python -X utf8 tests/run_config_tests.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
LINTER = ROOT / "ste_lint.py"

failures = []


def ok(name):
    # Only ever called by a test function after every one of its own checks
    # has passed (each failing check calls fail() and returns immediately),
    # so this can print unconditionally.
    print("PASS {}".format(name))


def fail(name, detail):
    failures.append("{}: {}".format(name, detail))


# A minimal but complete config -- every key the engine reads directly via
# cfg['key'] (see examples/config/lint_config.sample.json's own warning about
# this) must be present, or Engine.__init__ raises KeyError.
def base_config(**overrides):
    cfg = {
        "schema_version": 1,
        "profiles": {
            "prose": {"path_globs": ["**/*.md"], "tests": ["T1", "T2", "T3", "T4", "T5", "T6", "S7", "structural"],
                      "ari_target": None},
        },
        "profile_order": ["prose"],
        "profile_override_comment": "<!-- lint-profile: NAME -->",
        "never_lint": [],
        "severity_overrides": [],
        "universal_quantifiers": ["all"],
        "nasa_arm_directives": ["note"],
        "t4_pronouns": ["it"],
        "t4_comparative_irregulars": ["better"],
        "t4_comparative_min_stem_length": 4,
        "t4_comparative_exclusions": [],
        "t5_combinators": ["and"],
        "t5_punctuation_density_max": 3,
        "t5_punctuation_chars": [",", ";", ":"],
        "s7_units": ["ms"],
        "abbreviation_allowlist": [],
    }
    cfg.update(overrides)
    # cli.py does config["profiles"].get(profile, config["profiles"]["prose"]):
    # dict.get's default argument is evaluated unconditionally, so a config
    # must always carry a "prose" profile even when it will never be the
    # match -- same requirement examples/config/lint_config.sample.json
    # documents. Callers that override 'profiles' wholesale don't need to
    # remember this; patch a fallback in here instead.
    cfg["profiles"].setdefault("prose", {
        "path_globs": ["**/*.md"], "tests": ["T1", "T2", "T3", "T4", "T5", "T6", "S7", "structural"],
        "ari_target": None,
    })
    if "prose" not in cfg["profile_order"]:
        cfg["profile_order"] = list(cfg["profile_order"]) + ["prose"]
    return cfg


def run_lint(cwd, config, targets, today="2026-08-25"):
    """Write `config` to a temp file and run the CLI against `targets` inside `cwd`."""
    config_path = cwd / "ste100.config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    cmd = [sys.executable, "-X", "utf8", str(LINTER), "--config", str(config_path),
           "--root", str(cwd), "--format", "json", "--stats", "--today", today]
    cmd += [str(t) for t in targets]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AssertionError("non-JSON CLI output (stderr: {}): {}".format(proc.stderr, proc.stdout[:500]))


def rules_in(result):
    return {f["rule"] for f in result["findings"]}


# ---------------------------------------------------------------------------
# Bug 1: csv_integrity must respect the resolved profile's 'tests' list.
# ---------------------------------------------------------------------------

def test_csv_integrity_respects_profile():
    name = "csv_integrity respects profile tests"
    tmp = Path(tempfile.mkdtemp(prefix="ste100-cfg-"))
    try:
        csv_path = tmp / "truths.csv"
        csv_path.write_text(
            "id,statement,status,review_by,source_decision_id\n"
            "T-0001,Widget weighs 4 kg.,ACTIVE,2020-01-01,D-9999\n",
            encoding="utf-8")

        # csv_integrity NOT in tests -> STE-CSV-* must not fire, even though
        # source_decision_id is dangling and review_by is overdue.
        cfg_off = base_config(profiles={
            "csv": {"path_globs": ["*.csv"], "tests": ["budgets", "T1", "T3", "T6"], "ari_target": None},
            "prose": {"path_globs": ["**/*.md"], "tests": ["T1"], "ari_target": None},
        }, profile_order=["csv", "prose"])
        result = run_lint(tmp, cfg_off, [csv_path])
        csv_findings = [r for r in rules_in(result) if r.startswith("STE-CSV-")]
        if csv_findings:
            fail(name, "csv_integrity fired with 'csv_integrity' absent from profile tests: {}".format(csv_findings))
            return

        # csv_integrity IN tests -> the same file now produces STE-CSV-*.
        cfg_on = base_config(profiles={
            "csv": {"path_globs": ["*.csv"], "tests": ["budgets", "csv_integrity", "T1", "T3", "T6"], "ari_target": None},
            "prose": {"path_globs": ["**/*.md"], "tests": ["T1"], "ari_target": None},
        }, profile_order=["csv", "prose"])
        result = run_lint(tmp, cfg_on, [csv_path])
        csv_findings = [r for r in rules_in(result) if r.startswith("STE-CSV-")]
        if not csv_findings:
            fail(name, "csv_integrity did not fire with 'csv_integrity' present in profile tests")
            return
        ok(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_shipped_presets_csv_integrity():
    """The two shipped presets exercise both sides of the same bug directly:
    default's csv profile omits csv_integrity, veistra's includes it."""
    name = "shipped presets: default omits csv_integrity, veistra includes it"
    tmp = Path(tempfile.mkdtemp(prefix="ste100-cfg-"))
    try:
        csv_path = tmp / "truths.csv"
        csv_path.write_text(
            "id,statement,status,review_by,source_decision_id\n"
            "T-0001,Widget weighs 4 kg.,ACTIVE,2020-01-01,D-9999\n",
            encoding="utf-8")

        def run_preset(preset):
            cmd = [sys.executable, "-X", "utf8", str(LINTER), "--preset", preset,
                   "--root", str(tmp), "--format", "json", "--stats",
                   "--today", "2026-08-25", str(csv_path)]
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            return json.loads(proc.stdout)

        default_findings = [r for r in rules_in(run_preset("default")) if r.startswith("STE-CSV-")]
        veistra_findings = [r for r in rules_in(run_preset("veistra")) if r.startswith("STE-CSV-")]
        if default_findings:
            fail(name, "default preset leaked csv_integrity findings: {}".format(default_findings))
            return
        if not veistra_findings:
            fail(name, "veistra preset (which opts in) produced no csv_integrity findings")
            return
        ok(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Bug 2: never_lint segment matching.
# ---------------------------------------------------------------------------

def test_never_lint_segment_matching():
    from ste100.discovery import is_never_lint

    cases = [
        # (never_lint entries, path, expected)
        (["node_modules/"], "node_modules/x.md", True),
        (["node_modules/"], "packages/web/node_modules/x.md", True, "nested single-segment dir must be excluded anywhere"),
        (["build/"], "build.md", False, "a file merely named like the dir entry must not be excluded"),
        (["build/"], "packages/build.md", False, "same, nested"),
        (["build/"], "build/output.md", True),
        (["build/"], "packages/web/build/output.md", True),
        (["tests/corpus_dirty/"], "tests/corpus_dirty/x.md", True),
        (["tests/corpus_dirty/"], "other/tests/corpus_dirty/x.md", False, "multi-segment entry stays anchored to the root"),
        (["CHANGELOG.md"], "CHANGELOG.md", True),
        (["CHANGELOG.md"], "docs/CHANGELOG.md", False, "bare file entry is root-anchored"),
    ]
    name = "never_lint segment matching"
    all_pass = True
    for case in cases:
        entries, path, expected = case[0], case[1], case[2]
        detail = case[3] if len(case) > 3 else ""
        got = is_never_lint(path, {"never_lint": entries})
        if got != expected:
            all_pass = False
            fail(name, "is_never_lint({!r}, never_lint={!r}) = {}, want {} ({})".format(
                path, entries, got, expected, detail))
    if all_pass:
        ok(name)


def test_never_lint_end_to_end():
    """The same bug, exercised through the CLI's whole-project walk."""
    name = "never_lint nested exclusion end-to-end"
    tmp = Path(tempfile.mkdtemp(prefix="ste100-cfg-"))
    try:
        nested = tmp / "packages" / "web" / "node_modules" / "somepkg"
        nested.mkdir(parents=True)
        (nested / "README.md").write_text("# somepkg\n\nSome prose here.\n", encoding="utf-8")
        (tmp / "top.md").write_text("# Top\n\nSome prose here.\n", encoding="utf-8")

        cfg = base_config(never_lint=["node_modules/"])
        result = run_lint(tmp, cfg, [])  # empty targets -> whole-project walk
        files = {f["file"] for f in result["findings"]} | {"top.md"}  # top.md may be clean
        linted_count = result["summary"]["files"]
        if linted_count != 1:
            fail(name, "expected exactly 1 file linted (nested node_modules excluded), got {}".format(linted_count))
            return
        ok(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Bug 3: EARS checks must consult each profile's 'tests' list, not a literal
# profile-name comparison.
# ---------------------------------------------------------------------------

def test_ears_config_driven():
    name = "EARS checks are config-driven, not hardcoded to 'spec'/'design'"
    tmp = Path(tempfile.mkdtemp(prefix="ste100-cfg-"))
    try:
        req = tmp / "req.md"
        # Non-conforming EARS sentence (does not start with The/While/When/
        # Where/If) with exactly one 'shall', so it should trip S7-ARTICLE
        # (indefinite article 'a') and T5-EARS (template non-conformance).
        req.write_text("# Requirements\n\nA signal shall trigger the gadget.\n", encoding="utf-8")

        # A profile named 'requirements' (deliberately NOT 'spec' or
        # 'design') that opts into "ears" via its tests list.
        cfg = base_config(profiles={
            "requirements": {"path_globs": ["*.md"], "tests": ["T1", "T2", "T3", "T4", "T5", "T6", "S7", "structural", "ears"],
                              "ari_target": 12},
        }, profile_order=["requirements"])
        result = run_lint(tmp, cfg, [req])
        found = rules_in(result)
        if "STE-T5-EARS-0001" not in found:
            fail(name, "renamed profile with 'ears' in tests did not trigger STE-T5-EARS-0001; findings: {}".format(found))
            return
        if "STE-S7-ARTICLE-0001" not in found:
            fail(name, "renamed profile with 'ears' in tests did not trigger STE-S7-ARTICLE-0001; findings: {}".format(found))
            return

        # Same profile shape, but WITHOUT "ears" in tests -> must NOT fire.
        cfg_off = base_config(profiles={
            "requirements": {"path_globs": ["*.md"], "tests": ["T1", "T2", "T3", "T4", "T5", "T6", "S7", "structural"],
                              "ari_target": 12},
        }, profile_order=["requirements"])
        result = run_lint(tmp, cfg_off, [req])
        found = rules_in(result)
        if "STE-T5-EARS-0001" in found or "STE-S7-ARTICLE-0001" in found:
            fail(name, "EARS checks fired even though the profile did not opt in via 'tests': {}".format(found))
            return
        ok(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_ears_review_profile():
    """A profile that opts in via 'ears_review' (not 'ears') gets the
    template/article checks but not the stricter zero-shall/multi-shall
    checks -- mirrors the veistra preset's 'design' profile."""
    name = "'ears_review' enables EARS template checks, not zero/multi-shall"
    tmp = Path(tempfile.mkdtemp(prefix="ste100-cfg-"))
    try:
        no_shall = tmp / "no_shall.md"
        no_shall.write_text("# Design\n\nThe gadget looks nice.\n", encoding="utf-8")

        cfg = base_config(profiles={
            "blueprint": {"path_globs": ["*.md"], "tests": ["T1", "T2", "T3", "T4", "T5", "T6", "S7", "structural", "ears_review"],
                           "ari_target": 12},
        }, profile_order=["blueprint"])
        result = run_lint(tmp, cfg, [no_shall])
        found = rules_in(result)
        if "STE-T5-NOSHAL-0001" in found:
            fail(name, "zero-shall check fired for an 'ears_review'-only profile: {}".format(found))
            return
        ok(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# Bug 4: severity_defaults must actually drive the default severity tier.
# ---------------------------------------------------------------------------

def test_severity_defaults_wired():
    name = "severity_defaults drives the default severity tier"
    tmp = Path(tempfile.mkdtemp(prefix="ste100-cfg-"))
    try:
        doc = tmp / "doc.md"
        doc.write_text("# Doc\n\nThe queue holds 42 items before it drops the oldest one.\n", encoding="utf-8")

        # 'bare_number's call-site literal default is "warning". A profile
        # other than 'prose' is required so the prose error-tier cap in
        # Engine.severity() doesn't mask the result.
        docs_profile = {"path_globs": ["*.md"], "tests": ["T1", "T2", "T3", "T4", "T5", "T6", "S7", "structural"],
                         "ari_target": None}

        cfg_baseline = base_config(profiles={"docs": docs_profile}, profile_order=["docs"])
        result = run_lint(tmp, cfg_baseline, [doc])
        bare = [f for f in result["findings"] if f["rule"] == "STE-S7-BARENUM-0001"]
        if not bare or bare[0]["severity"] != "warning":
            fail(name, "expected baseline (no severity_defaults) bare_number severity 'warning', got {}".format(bare))
            return

        cfg_retuned = base_config(profiles={"docs": docs_profile}, profile_order=["docs"],
                                   severity_defaults={"bare_number": "error"})
        result = run_lint(tmp, cfg_retuned, [doc])
        bare = [f for f in result["findings"] if f["rule"] == "STE-S7-BARENUM-0001"]
        if not bare or bare[0]["severity"] != "error":
            fail(name, "severity_defaults.bare_number='error' did not change the finding's severity: {}".format(bare))
            return
        ok(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_severity_defaults_fallback_when_absent():
    """A rule absent from severity_defaults still falls back to the call
    site's own literal -- severity_defaults being present must not force
    every unlisted rule to some other value."""
    name = "severity_defaults falls back to the call-site literal when a rule is absent"
    tmp = Path(tempfile.mkdtemp(prefix="ste100-cfg-"))
    try:
        doc = tmp / "doc.md"
        doc.write_text("# Doc\n\nThe queue holds 42 items before it drops the oldest one.\n", encoding="utf-8")
        docs_profile = {"path_globs": ["*.md"], "tests": ["T1", "T2", "T3", "T4", "T5", "T6", "S7", "structural"],
                         "ari_target": None}
        # severity_defaults present, but doesn't mention bare_number.
        cfg = base_config(profiles={"docs": docs_profile}, profile_order=["docs"],
                           severity_defaults={"tbd": "error"})
        result = run_lint(tmp, cfg, [doc])
        bare = [f for f in result["findings"] if f["rule"] == "STE-S7-BARENUM-0001"]
        if not bare or bare[0]["severity"] != "warning":
            fail(name, "expected fallback to literal 'warning' for a rule absent from severity_defaults, got {}".format(bare))
            return
        ok(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    test_csv_integrity_respects_profile()
    test_shipped_presets_csv_integrity()
    test_never_lint_segment_matching()
    test_never_lint_end_to_end()
    test_ears_config_driven()
    test_ears_review_profile()
    test_severity_defaults_wired()
    test_severity_defaults_fallback_when_absent()

    print()
    if failures:
        print("FAIL ({} issue(s)):".format(len(failures)))
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("All config tests passed.")
    sys.exit(0)
