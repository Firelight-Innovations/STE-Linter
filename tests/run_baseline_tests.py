#!/usr/bin/env python3
"""Regression tests for --baseline.

--baseline exists so an existing codebase can adopt the linter without fixing
everything first: snapshot today's findings, then enforce only on new writing.
That promise is only kept if a NEW violation still surfaces, which is the
property these tests pin.

Usage: python -X utf8 tests/run_baseline_tests.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "ste_lint.py"

failures = []


def run(cwd, *args):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(LINTER), *args],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")
    return proc


def errors_in(cwd, *args):
    proc = run(cwd, "--format", "json", *args)
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        failures.append("non-JSON output: {}".format(proc.stdout[:300]))
        return []
    return [f for f in report["findings"] if f["severity"] == "error"]


def check(name, ok, detail=""):
    if ok:
        print("PASS {}".format(name))
    else:
        failures.append("{}{}".format(name, ": " + detail if detail else ""))


tmp = Path(tempfile.mkdtemp(prefix="ste100-baseline-"))
try:
    docs = tmp / "docs"
    docs.mkdir()
    target = docs / "guide.md"
    with open(target, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Guide\n\nWe utilize the tool to facilitate the process.\n")

    before = errors_in(tmp, "docs/")
    check("fixture produces findings to baseline", len(before) >= 2,
          "got {}".format(len(before)))

    baseline = tmp / "base.json"
    proc = run(tmp, "--format", "json", "docs/")
    with open(baseline, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(proc.stdout)

    after = errors_in(tmp, "--baseline", "base.json", "docs/")
    check("baselined findings are suppressed", after == [],
          "{} still reported".format(len(after)))

    proc = run(tmp, "--baseline", "base.json", "docs/")
    check("suppressed run exits 0", proc.returncode == 0,
          "exit {}".format(proc.returncode))

    # The regression that motivated this suite. Matching a baseline entry by
    # presence alone meant a file that already had one 'utilize' swallowed
    # every later 'utilize' added to it, so new violations went unreported.
    with open(target, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\nWe utilize the new module.\n")

    new = errors_in(tmp, "--baseline", "base.json", "docs/")
    check("a NEW instance of an already-baselined rule still surfaces",
          any("utilize" in f["message"] for f in new),
          "reported {} errors: {}".format(len(new), [f["message"] for f in new]))
    check("only the new instance surfaces, not the baselined one",
          len(new) == 1, "got {}".format(len(new)))

    proc = run(tmp, "--baseline", "base.json", "docs/")
    check("a new violation makes the run exit 1", proc.returncode == 1,
          "exit {}".format(proc.returncode))

    # An unreadable or malformed baseline is a tool failure (exit 2), not a
    # silent pass -- otherwise a typo'd path quietly disables enforcement.
    proc = run(tmp, "--baseline", "does-not-exist.json", "docs/")
    check("a missing baseline file is a tool failure", proc.returncode == 2,
          "exit {}".format(proc.returncode))
finally:
    shutil.rmtree(tmp, ignore_errors=True)

if failures:
    print("\nFAIL ({} issue(s)):".format(len(failures)))
    for f in failures:
        print(" - {}".format(f))
    sys.exit(1)
print("\nAll baseline tests passed.")
