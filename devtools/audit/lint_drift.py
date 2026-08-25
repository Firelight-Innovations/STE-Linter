"""Section 7 of the weekly audit: lint drift (spec section 11.7). Runs the
real linter (subprocess, not a re-implementation) over the whole project and
compares totals-by-test / totals-by-file against last week's snapshot. A
rising smell density means the standard is being ignored."""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LINTER = ROOT / "tools" / "ste_lint.py"


def run_lint_snapshot():
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(LINTER), "--format", "json", "--stats"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    data = json.loads(proc.stdout)
    by_test = Counter(f["test"] for f in data["findings"])
    by_file = Counter(f["file"] for f in data["findings"])
    return {
        "summary": data["summary"],
        "by_test": dict(by_test),
        "by_file": dict(by_file),
    }


def compute_lint_drift(previous_snapshot):
    current = run_lint_snapshot()
    drift = {"current": current, "previous": previous_snapshot, "delta": None}
    if previous_snapshot:
        prev_density = previous_snapshot.get("summary", {}).get("smell_density", 0.0)
        cur_density = current["summary"].get("smell_density", 0.0)
        drift["delta"] = {
            "smell_density_change": round(cur_density - prev_density, 4),
            "errors_change": current["summary"]["errors"] - previous_snapshot.get("summary", {}).get("errors", 0),
            "warnings_change": current["summary"]["warnings"] - previous_snapshot.get("summary", {}).get("warnings", 0),
        }
    return drift, current
