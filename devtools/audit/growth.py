"""Section 4 of the weekly audit: row counts against budget, and the change
since last week (spec section 11.4). truths.csv over 40 rows is flagged --
matches VEI-BUD-0005 in the linter, restated here so the audit report is
self-contained without cross-referencing a lint run."""
from ste100.csv_integrity import kind_of

TRUTHS_ROW_BUDGET = 40


def compute_growth(registry, previous_counts):
    rows = []
    for rel_path, sheet in sorted(registry.items()):
        count = len(sheet["rows"])
        prev = (previous_counts or {}).get(rel_path)
        delta = None if prev is None else count - prev
        entry = {"file": rel_path, "rows": count, "delta_since_last_week": delta}
        if kind_of(rel_path) == "truths" and count > TRUTHS_ROW_BUDGET:
            entry["over_budget"] = "{} rows, over the {}-row target".format(count, TRUTHS_ROW_BUDGET)
        rows.append(entry)
    current_counts = {rel_path: len(sheet["rows"]) for rel_path, sheet in registry.items()}
    return rows, current_counts
