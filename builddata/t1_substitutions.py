"""T1 Replaceable -- substitutions.json."""
from .common import T1_EXCLUDE


def build_redhat_entries(data):
    """vale_redhat.simple_words: 107 pairs. Two malformed keys are skipped
    and logged: one has a quote character / unbalanced parens
    ('"approximate(?'), the other has balanced parens but is still a dead
    regex fragment ('objective(?! C?)') that would survive a naive
    quote/paren check and become an inert literal rule. Both classes are
    caught by a single '(?' artifact check (this session's tightening --
    the earlier build let the second one through as harmless-but-junk).
    27 replacements contain '|' alternation; first alternative is the
    suggestion, all kept as alts."""
    clean, skipped = [], []
    for k, v in data.items():
        if '"' in k or k.count("(") != k.count(")") or "(?" in k:
            skipped.append({"raw_key": k, "raw_value": v, "reason": "quote character, unbalanced parens, or regex artifact in key"})
            continue
        alts = [a.strip() for a in v.split("|")] if "|" in v else [v]
        clean.append({"pattern": k.lower(), "suggestion": alts[0], "alts": alts, "source": "vale_redhat.simple_words"})
    return clean, skipped


def build_merged99_entries(data):
    """MERGED.wordy_and_complex (876): filter to len(sources) >= 3 -> 99 entries."""
    clean = []
    for k, v in data.items():
        if len(v.get("sources", [])) >= 3:
            suggestions = v.get("suggestions") or [""]
            clean.append({"pattern": k.lower(), "suggestion": suggestions[0], "alts": suggestions, "source": "MERGED.wordy_and_complex"})
    return clean


def build_microsoft_entries(data):
    """vale_microsoft.wordiness (114): malformed across the board where the
    raw YAML line was split at the first ': '. Detect via unbalanced parens
    in the key, or a balanced-but-regex-bearing key ('(?' present). Both
    classes still carry regex artifacts after reconstruction; drop and log
    rather than guess a literal split (priority 3 of 4, partial loss OK)."""
    clean, dropped = [], []
    for k, v in data.items():
        if k.count("(") != k.count(")"):
            reconstructed = k + ": " + v
            dropped.append({"raw_key": k, "raw_value": v, "reconstructed": reconstructed, "reason": "reconstructed key:value still contains regex syntax"})
            continue
        if "(?" in k or "(?" in v:
            dropped.append({"raw_key": k, "raw_value": v, "reconstructed": None, "reason": "key contains unresolved regex artifact"})
            continue
        clean.append({"pattern": k.lower(), "suggestion": v, "alts": [v], "source": "vale_microsoft.wordiness"})
    return clean, dropped


def build_retext_simplify_entries(data):
    """retext_simplify (327): term -> {replace: [alts], omit_ok: bool}."""
    clean = []
    for k, v in data.items():
        replace = v.get("replace") or [""]
        clean.append({
            "pattern": k.lower(),
            "suggestion": replace[0],
            "alts": replace,
            "omit_ok": bool(v.get("omit_ok", False)),
            "source": "retext_simplify",
        })
    return clean


def build_substitutions(src):
    redhat, redhat_skipped = build_redhat_entries(src["vale_redhat.simple_words"]["data"])
    merged99 = build_merged99_entries(src["MERGED.wordy_and_complex"]["data"])
    microsoft, microsoft_dropped = build_microsoft_entries(src["vale_microsoft.wordiness"]["data"])
    retext = build_retext_simplify_entries(src["retext_simplify"]["data"])

    # Precedence: redhat > merged99 > microsoft > retext_simplify.
    # Dedupe by lowercase pattern, earlier tier wins.
    rules, excluded, seen = [], [], set()
    for tier in (redhat, merged99, microsoft, retext):
        for entry in sorted(tier, key=lambda e: e["pattern"]):
            pattern = entry["pattern"]
            if pattern in T1_EXCLUDE:
                excluded.append({**entry, "reason": "O3/DEC-TEC-TOOL-003: shall is the mandatory keyword, not slop"})
                continue
            if pattern in seen:
                continue
            seen.add(pattern)
            rules.append(entry)

    for i, rule in enumerate(rules, start=1):
        rule["id"] = f"VEI-T1-SUB-{i:04d}"

    return {
        "schema_version": 1,
        "test": "T1",
        "name": "Replaceable",
        "default_tier": "error",
        "rules": rules,
        "excluded": excluded,
        "skipped": redhat_skipped,
        "dropped_microsoft": microsoft_dropped,
        "counts": {
            "redhat_clean": len(redhat), "redhat_skipped": len(redhat_skipped),
            "merged99": len(merged99),
            "microsoft_clean": len(microsoft), "microsoft_dropped": len(microsoft_dropped),
            "retext_simplify": len(retext),
            "final_rules": len(rules), "excluded": len(excluded),
        },
    }
