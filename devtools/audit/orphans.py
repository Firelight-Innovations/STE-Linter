"""Section 3 of the weekly audit: ACTIVE decisions no document references."""
from ste100.csv_integrity import kind_of


def find_orphans(registry, md_texts):
    """A decision is an orphan candidate when its id string appears nowhere
    except its own row: not in any Markdown doc, and not in any other CSV
    row's fields (supersedes/superseded_by/linked_truth_ids/source_decision_id
    all count as a reference; the id column itself does not, or every row
    would trivially 'reference' itself)."""
    haystack_parts = list(md_texts.values())
    for rel_path, sheet in registry.items():
        id_col = "id" if "id" in sheet["header"] else "term"
        for row in sheet["rows"]:
            for field, value in row.items():
                if field != id_col and value:
                    haystack_parts.append(value)
    haystack = "\n".join(haystack_parts)

    orphans = []
    for rel_path, sheet in registry.items():
        if kind_of(rel_path) != "decisions":
            continue
        id_col = "id" if "id" in sheet["header"] else "term"
        for row in sheet["rows"]:
            if row.get("status") != "ACTIVE":
                continue
            rid = row.get(id_col)
            if rid and rid not in haystack:
                orphans.append({"id": rid, "file": rel_path, "decision": row.get("decision", "")})
    return orphans
