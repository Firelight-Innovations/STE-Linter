"""Section 5 of the weekly audit: near-duplicate statements across files
(spec section 11.5). Token-set Jaccard similarity on content words, threshold
0.6, over every budget-tracked content field (the same fields spec section 9
budgets: truths.statement, decisions.decision/rationale, timeline.event/note)."""
from .textutil import content_words, jaccard

CONTENT_FIELDS = ("statement", "decision", "rationale", "event", "note")


def _collect_rows(registry):
    rows = []
    for rel_path, sheet in registry.items():
        id_col = "id" if "id" in sheet["header"] else "term"
        for row in sheet["rows"]:
            for field in CONTENT_FIELDS:
                text = row.get(field)
                if text:
                    rows.append({"id": row.get(id_col, "?"), "file": rel_path, "field": field, "text": text})
    return rows


def find_near_duplicates(registry, threshold=0.6):
    rows = _collect_rows(registry)
    tokens = [content_words(r["text"]) for r in rows]
    pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if rows[i]["id"] == rows[j]["id"] and rows[i]["file"] == rows[j]["file"]:
                continue
            score = jaccard(tokens[i], tokens[j])
            if score > threshold:
                pairs.append({
                    "a": {"id": rows[i]["id"], "file": rows[i]["file"], "field": rows[i]["field"], "text": rows[i]["text"]},
                    "b": {"id": rows[j]["id"], "file": rows[j]["file"], "field": rows[j]["field"], "text": rows[j]["text"]},
                    "similarity": round(score, 3),
                })
    pairs.sort(key=lambda p: -p["similarity"])
    return pairs
