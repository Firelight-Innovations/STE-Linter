#!/usr/bin/env python3
"""Stress tests for ste_lint.py: spec section 12.5 (referential-integrity
fuzzing) and section 12.6 (200-file performance budget).

Generates throwaway fixtures under a TemporaryDirectory (never committed --
corpus_dirty/decisions_dirty.csv already covers the curated cycle/dangling/
duplicate cases with asserted findings; this script's job is to throw
messier, less-curated input at the tool and confirm it degrades safely:
findings or a clean tool-failure message, never an unhandled traceback).

Usage: python -X utf8 tools/tests/run_stress_tests.py
"""
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "ste_lint.py"
failures = []


def run(args, cwd=None):
    return subprocess.run([sys.executable, "-X", "utf8", str(LINTER)] + args,
                           cwd=cwd or ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def looks_like_traceback(text):
    return "Traceback (most recent call last)" in text


# ---- 12.5: referential-integrity fuzzing -----------------------------------

FUZZ_CSVS = {
    "empty_file.csv": "",
    "header_only.csv": "id,date,decision,rationale,status,supersedes,superseded_by,owner,review_by,scope,linked_truth_ids\n",
    "self_cycle.csv": (
        "id,date,decision,rationale,status,supersedes,superseded_by,owner,review_by,scope,linked_truth_ids\n"
        "DEC-FUZZ-001,2026-01-01,Self referencing decision,Self referencing rationale,ACTIVE,DEC-FUZZ-001,,owner,2027-01-01,scope,\n"
    ),
    "long_cycle.csv": "id,date,decision,rationale,status,supersedes,superseded_by,owner,review_by,scope,linked_truth_ids\n" + "".join(
        "DEC-FUZZ-{0:03d},2026-01-01,Chain decision {0},Chain rationale {0},ACTIVE,DEC-FUZZ-{1:03d},,owner,2027-01-01,scope,\n".format(i, (i % 20) + 1)
        for i in range(1, 21)
    ),
    "embedded_commas_quotes.csv": (
        'id,date,decision,rationale,status,supersedes,superseded_by,owner,review_by,scope,linked_truth_ids\n'
        'DEC-FUZZ-050,2026-01-01,"Decision, with a comma and ""quotes"" inside",Rationale here,ACTIVE,,,owner,2027-01-01,scope,\n'
    ),
    "ragged_rows.csv": (
        "id,date,decision,rationale,status,supersedes,superseded_by,owner,review_by,scope,linked_truth_ids\n"
        "DEC-FUZZ-060,2026-01-01,Too few columns\n"
        "DEC-FUZZ-061,2026-01-01,Too many columns,rationale,ACTIVE,,,owner,2027-01-01,scope,,extra,extra2\n"
    ),
    "empty_ids.csv": (
        "id,date,decision,rationale,status,supersedes,superseded_by,owner,review_by,scope,linked_truth_ids\n"
        ",2026-01-01,No id at all,rationale,ACTIVE,,,owner,2027-01-01,scope,\n"
    ),
    "duplicate_ids_x5.csv": "id,date,decision,rationale,status,supersedes,superseded_by,owner,review_by,scope,linked_truth_ids\n" + "".join(
        "DEC-FUZZ-DUP,2026-01-01,Duplicate number {0},rationale,ACTIVE,,,owner,2027-01-01,scope,\n".format(i)
        for i in range(5)
    ),
}


def check_csv_fuzzing():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for name, content in FUZZ_CSVS.items():
            (tmp_path / name).write_text(content, encoding="utf-8")
        (tmp_path / "invalid_encoding.csv").write_bytes(b"id,decision\n\xff\xfe\x00\xff not valid utf-8 at all\n")

        for name in list(FUZZ_CSVS) + ["invalid_encoding.csv"]:
            proc = run([str(tmp_path / name)])
            if looks_like_traceback(proc.stdout) or looks_like_traceback(proc.stderr):
                failures.append("{}: unhandled traceback (exit {})".format(name, proc.returncode))
            elif proc.returncode not in (0, 1, 2):
                failures.append("{}: unexpected exit code {}".format(name, proc.returncode))
            elif proc.returncode == 2 and "tool failure" not in proc.stderr:
                failures.append("{}: exit 2 without a 'tool failure' message".format(name))
    if not failures:
        print("PASS CSV fuzzing: {} adversarial files, no crashes".format(len(FUZZ_CSVS) + 1))


# ---- 12.6: performance -------------------------------------------------

def check_performance(target_files=200, budget_seconds=2.0):
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for i in range(target_files):
            (tmp_path / "gen_{:04d}.md".format(i)).write_text(
                "# Generated File {0}\n\nThe system saves progress every five minutes.\n"
                "Players start a new run from the hub.\n".format(i),
                encoding="utf-8",
            )
        start = time.perf_counter()
        proc = run([str(tmp_path)])
        elapsed = time.perf_counter() - start
        if proc.returncode not in (0, 1):
            failures.append("performance run: unexpected exit code {}, stderr: {}".format(proc.returncode, proc.stderr[:300]))
        if elapsed > budget_seconds:
            failures.append("performance: {} files took {:.2f}s, over the {:.0f}s budget".format(target_files, elapsed, budget_seconds))
        else:
            print("PASS performance: {} files in {:.2f}s (budget {:.0f}s)".format(target_files, elapsed, budget_seconds))


if __name__ == "__main__":
    check_csv_fuzzing()
    check_performance()

    print()
    if failures:
        print("FAIL ({} issue(s)):".format(len(failures)))
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("All stress tests passed.")
    sys.exit(0)
