"""Sections 1 (stale rows) and 2 (broken references, spec section 8.8) of the weekly audit."""
from datetime import datetime

from ste100.csv_integrity import check_csv_integrity, kind_of


def find_stale_rows(registry, today):
    """ACTIVE rows past review_by, sorted most-overdue first (section 11.1)."""
    stale = []
    for rel_path, sheet in registry.items():
        kind = kind_of(rel_path)
        if kind not in ("truths", "decisions"):
            continue
        id_col = "id" if "id" in sheet["header"] else "term"
        for row in sheet["rows"]:
            if row.get("status") != "ACTIVE":
                continue
            review_by = row.get("review_by", "")
            if not review_by:
                continue
            try:
                rb = datetime.strptime(review_by, "%Y-%m-%d").date()
            except ValueError:
                continue
            days_overdue = (today - rb).days
            if days_overdue > 0:
                stale.append({
                    "id": row.get(id_col, "?"), "file": rel_path, "review_by": review_by,
                    "days_overdue": days_overdue,
                })
    stale.sort(key=lambda r: -r["days_overdue"])
    return stale


def find_broken_references(registry, today, engine):
    """All spec section 8.8 integrity failures, across the whole registry (section 11.2)."""
    all_files = set(registry.keys())
    findings = check_csv_integrity(registry, today, engine, all_files)
    return [f.to_dict() for f in findings]
