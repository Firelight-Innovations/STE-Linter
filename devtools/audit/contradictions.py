"""Section 6 of the weekly audit: contradiction candidates (spec section
11.6). ACTIVE row pairs sharing 3+ content words but differing on whether a
negation token is present. Advisory only -- never auto-resolved."""
from .textutil import NEGATIONS, content_words, tokenize

CONTENT_FIELDS = ("statement", "decision", "rationale", "event", "note")


def _collect_active_rows(registry):
    rows = []
    for rel_path, sheet in registry.items():
        id_col = "id" if "id" in sheet["header"] else "term"
        for row in sheet["rows"]:
            if row.get("status") != "ACTIVE":
                continue
            for field in CONTENT_FIELDS:
                text = row.get(field)
                if text:
                    rows.append({"id": row.get(id_col, "?"), "file": rel_path, "field": field, "text": text})
    return rows


def _has_negation(text):
    return any(w in NEGATIONS for w in tokenize(text))


def find_contradiction_candidates(registry, min_shared_words=3):
    rows = _collect_active_rows(registry)
    tokens = [set(content_words(r["text"])) for r in rows]
    negated = [_has_negation(r["text"]) for r in rows]
    pairs = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            if rows[i]["id"] == rows[j]["id"] and rows[i]["file"] == rows[j]["file"]:
                continue
            shared = tokens[i] & tokens[j]
            if len(shared) >= min_shared_words and negated[i] != negated[j]:
                pairs.append({
                    "a": {"id": rows[i]["id"], "file": rows[i]["file"], "text": rows[i]["text"]},
                    "b": {"id": rows[j]["id"], "file": rows[j]["file"], "text": rows[j]["text"]},
                    "shared_words": sorted(shared),
                })
    return pairs
