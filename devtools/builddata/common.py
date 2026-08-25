"""Shared paths and helpers for the src/ste100/data/*.json builders."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE = ROOT / "handoff" / "prose_lint_wordlists.json"
OUT_DIR = ROOT / "src" / "ste100" / "data"

# C6 (implementer decision, this build): the T1 wordlists flag "shall" as
# replaceable by "must|will". That conflicts with DEC-TEC-TOOL-003 / O3,
# which makes "shall" the mandatory keyword. Excluded from every T1 source list.
T1_EXCLUDE = {"shall"}


def id_list(prefix, items):
    """Assign stable, deterministic rule IDs to a word/phrase list (G2 taxonomy:
    VEI-<test>-<CATEGORY>-<seq4>). Sorted before numbering so a rerun with the
    same input produces byte-identical IDs (C4 determinism)."""
    return [{"id": f"{prefix}-{i:04d}", "pattern": p} for i, p in enumerate(sorted(set(items)), start=1)]


def load_source():
    with open(SOURCE, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")
