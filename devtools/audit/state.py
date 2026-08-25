"""Week-over-week state for the growth (spec section 11.4) and lint-drift
(section 11.7) audit sections. A single small JSON file, not version
history -- each run reads last week's snapshot, then overwrites it with
this week's numbers. First run on a project has no prior snapshot; sections
that need one say so explicitly rather than fabricating a zero baseline."""
import json
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "audits" / ".audit_state.json"


def load_state():
    if not STATE_PATH.exists():
        return None
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
