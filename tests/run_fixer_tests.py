#!/usr/bin/env python3
"""Regression tests for --fix, which rewrites the user's source file in place.

The bar for --fix is higher than for reporting: a wrong finding wastes a
reader's time, but a wrong fix destroys their prose. These tests pin the
behaviours that keep it safe.

Usage: python -X utf8 tests/run_fixer_tests.py
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "ste_lint.py"

failures = []


def fix(text):
    """Run --fix over a throwaway copy of `text` and return the result."""
    tmp = Path(tempfile.mkdtemp(prefix="ste100-fixer-"))
    try:
        target = tmp / "doc.md"
        # write_text(newline=...) is 3.10+; this suite runs on 3.9 too.
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        subprocess.run([sys.executable, "-X", "utf8", str(LINTER), "--fix", str(target)],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        return target.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def expect(name, source, want_substrings, unwanted_substrings=()):
    got = fix(source)
    for want in want_substrings:
        if want not in got:
            failures.append("{}: expected {!r} in output, got:\n{}".format(name, want, got))
    for unwanted in unwanted_substrings:
        if unwanted in got:
            failures.append("{}: did not expect {!r} in output, got:\n{}".format(name, unwanted, got))
    if not failures:
        print("PASS {}".format(name))


# 14 T1 rules carry an empty suggestion, which means "delete this phrase".
# --fix used to apply them, producing " important that the operator selects
# the  of report." Deleting words changes the grammar around them, so it needs
# a human. The finding is still reported; only the auto-rewrite is withheld.
expect(
    "empty suggestions are never auto-applied",
    "# Report\n\nIt is important that the operator selects the type of report.\n",
    ["It is important that the operator selects the type of report."],
)

# The narrow, genuinely unambiguous case still works: exactly one alt, real text.
expect(
    "single-alt substitutions still apply",
    "# Guide\n\nWe utilize the tool to facilitate the process.\n",
    ["We use the tool", "to ease the process"],
    ["utilize", "facilitate"],
)

# A rule with more than one candidate replacement needs a human choice.
expect(
    "multi-alt substitutions are left alone",
    "# Guide\n\nDo not delete the row.\n",
    ["Do not delete the row."],
)

# The exceptions gate must hold through --fix too, or "pull request" would
# have been rewritten to "pull ask".
expect(
    "exceptions protect fixed compounds",
    "# Guide\n\nOpen a pull request for the change.\n",
    ["pull request"],
    ["pull ask"],
)

# Code spans are never rewritten.
expect(
    "code spans are untouched",
    "# Guide\n\nCall `utilize()` when needed.\n",
    ["`utilize()`"],
)

if failures:
    print("\nFAIL ({} issue(s)):".format(len(failures)))
    for f in failures:
        print(" - {}".format(f))
    sys.exit(1)
print("\nAll fixer tests passed.")
