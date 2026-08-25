#!/usr/bin/env python3
"""Regression test for the default preset's out-of-box experience.

Dogfooding this repo's own docs (README/CONTRIBUTING/SECURITY/CODE_OF_CONDUCT/
docs/**) against `--preset default` found a wall of error-tier findings on
perfectly ordinary technical writing -- see CHANGELOG.md for the 2026-08
retune this test guards. The fix lives entirely in
src/ste100/presets/default.json: a new 'docs' profile (README.md,
CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md, docs/**, examples/**) with
severity_overrides that keep hedge_word/T6/open_ended_clause at 'review'
instead of 'error' for that profile, while T1 stays at its normal 'error'
tier because it is mostly defensible advice even on casual prose.

This test lints tests/corpus_default/ -- a small fixture of natural,
correctly-written technical documentation (a README.md and a docs/guide.md)
that a competent maintainer would not consider defective -- and asserts the
default preset reports zero error-tier findings on it. If a future change to
default.json (or the engine) makes this fixture start erroring, that is the
out-of-box-experience regression this test exists to catch.

Usage: python -X utf8 tests/run_default_preset_tests.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "ste_lint.py"
FIXTURE_DIR = ROOT / "tests" / "corpus_default"

failures = []


def run_lint():
    # --root points at the fixture directory itself, so relative paths come
    # out as e.g. "README.md" / "docs/guide.md" -- the exact shape the
    # 'docs' profile's path_globs in default.json match against. Pointing
    # --root at the repo root instead would report paths as
    # "tests/corpus_default/README.md", which matches no profile glob and
    # would silently fall back to the (deliberately stricter) 'prose'
    # profile, defeating the point of this test.
    cmd = [
        sys.executable, "-X", "utf8", str(LINTER),
        "--preset", "default",
        "--root", str(FIXTURE_DIR),
        "--stats", "--format", "json",
        str(FIXTURE_DIR),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        failures.append("lint invocation produced non-JSON output (stderr: {}): {}".format(
            proc.stderr[:500], proc.stdout[:500]))
        return None


def check_zero_errors():
    result = run_lint()
    if result is None:
        return
    summary = result["summary"]
    error_findings = [f for f in result["findings"] if f["severity"] == "error"]
    if summary["files"] < 2:
        failures.append("expected at least 2 fixture files under {}, found {}".format(
            FIXTURE_DIR, summary["files"]))
    if error_findings:
        for f in error_findings:
            failures.append("{}:{} {} {} -- {}".format(
                f["file"], f["line"], f["severity"].upper(), f["rule"], f["message"]))
        failures.append("expected 0 error-tier findings on natural doc prose, got {}".format(
            summary["errors"]))
    else:
        print("PASS corpus_default: {} files, 0 error-tier findings ({} warnings, {} review)".format(
            summary["files"], summary["warnings"], summary["review"]))


if __name__ == "__main__":
    check_zero_errors()

    print()
    if failures:
        print("FAIL ({} issue(s)):".format(len(failures)))
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("All default-preset tests passed.")
    sys.exit(0)
