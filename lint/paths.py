"""Project paths, schema version, and JSON/data loading."""
import json
from pathlib import Path

# lint/paths.py -> lint/ -> repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "lint_config.json"
LINT_DATA_DIR = REPO_ROOT / "lint_data"

# The directory whose tree is walked (and against which finding paths are made
# relative) when no explicit target is given. Standalone, that is the user's
# current working directory, not the linter's own install location.
ROOT = Path.cwd()
SCHEMA_VERSION = 1

LINT_DATA_NAMES = ["substitutions", "hedges", "vague", "filler", "ai_tells",
                   "pos_heuristics", "budgets"]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_lint_data():
    return {n: load_json(LINT_DATA_DIR / f"{n}.json") for n in LINT_DATA_NAMES}
