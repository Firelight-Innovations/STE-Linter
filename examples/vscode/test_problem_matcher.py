"""Validate the VS Code problemMatcher regex in tasks.json against real
ste_lint.py text output. Not part of the linter -- a one-off verification
script kept here so the regex can be re-checked if report.py's format
changes. Run: python examples/vscode/test_problem_matcher.py
"""
import re
import subprocess
import sys

PATTERN = (
    r"^(.*):(\d+):(\d+)(?:\s+\[[^\]]+\])?\s+"
    r"(ERROR|WARNING|REVIEW)\s+(\S+)\s+(\S+)\s+--\s+(.*)$"
)

CASES = [
    # (line, expect_match, expected groups or None)
    (
        "tests/corpus_dirty/dirty_t3.md:6:16 ERROR T3 STE-T3-MOD-0007 -- Optional (optionality): 'if possible'.",
        True,
    ),
    (
        "tests/corpus_dirty/dirty_t4.md:4:1 WARNING T4 STE-T4-PRO-0022 -- Referentially open: pronoun 'This' with no clear antecedent in this unit.",
        True,
    ),
    (
        "tests/corpus_dirty/decisions_dirty.csv:0:1 [DEC-DIRTY-001:superseded_by] ERROR csv_integrity STE-CSV-0001 -- CSV integrity: status=SUPERSEDED needs a resolving superseded_by.",
        True,
    ),
    (
        "tests/corpus_dirty/dirty_t6.md:8:40 WARNING structural STE-S7-PASSIVE-0001 -- Structural: passive voice.",
        True,
    ),
    # excerpt / summary lines must NOT match
    ("    Ship the patch if possible...", False),
    ("Veistra lint: 1 files, 2 errors, 0 warnings, 0 review", False),
    ("smell_density=0.6667 ari_grade=2.5 passive_ratio=0.0 budget_violations=0", False),
]


def run_real_output():
    """Run the linter on a real dirty fixture and feed every line through
    the pattern, printing what matches so this can be eyeballed too."""
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "ste_lint.py", "tests/corpus_dirty/dirty_t3.md"],
        capture_output=True, text=True,
    )
    rx = re.compile(PATTERN)
    print("--- live linter output run through the pattern ---")
    for line in proc.stdout.splitlines():
        m = rx.match(line)
        tag = "MATCH " + str(m.groups()) if m else "no-match"
        print(f"{tag} :: {line}")


def main():
    rx = re.compile(PATTERN)
    failures = 0
    for line, should_match in CASES:
        m = rx.match(line)
        ok = bool(m) == should_match
        status = "OK" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"[{status}] match={bool(m)} expected={should_match} :: {line[:90]}")
        if m:
            print(f"       file={m.group(1)!r} line={m.group(2)} col={m.group(3)} "
                  f"severity={m.group(4)} test={m.group(5)} rule={m.group(6)} "
                  f"message={m.group(7)!r}")
    run_real_output()
    if failures:
        print(f"\n{failures} case(s) FAILED")
        return 1
    print("\nAll cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
