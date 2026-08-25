#!/usr/bin/env python3
"""Audit: T1 substitution suggestions that collide with error-tier ban lists.

A T1 rule tells the writer to replace `pattern` with `suggestion`/`alts`.
If the replacement word is itself banned (as a T1 pattern, a T3 hedge, or a
T6 filler/weasel/corporate term), following the tool's advice creates a new
violation. This script reports every such collision.

Run from the repo root:  python -X utf8 audit/collision_audit.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEDGE_KEYS = (
    "escape_clauses",
    "open_ended_clauses",
    "optionality",
    "superfluous_infinitives",
    "hedge_words",
)
FILLER_KEYS = (
    "fillers_and_intensifiers",
    "overused_vocabulary",
    "weasel_words",
    "corporate_speak",
)


def load(name):
    with open(os.path.join(ROOT, "lint_data", name), encoding="utf-8") as fh:
        return json.load(fh)


def collect():
    """Return (sub_rules, error_tier_words, vague_words)."""
    subs = load("substitutions.json")["rules"]
    sub_patterns = {r["pattern"].lower() for r in subs}

    hedges = load("hedges.json")
    hedge_patterns = set()
    for key in HEDGE_KEYS:
        hedge_patterns |= {e["pattern"].lower() for e in hedges[key]}

    filler = load("filler.json")
    filler_patterns = set()
    for key in FILLER_KEYS:
        filler_patterns |= {e["pattern"].lower() for e in filler[key]}

    error_tier_words = sub_patterns | hedge_patterns | filler_patterns

    vague = load("vague.json")
    vague_words = set()
    for key, val in vague.items():
        if isinstance(val, list):
            for e in val:
                if isinstance(e, dict) and "pattern" in e:
                    vague_words.add(e["pattern"].lower())
                elif isinstance(e, str):
                    vague_words.add(e.lower())
    return subs, error_tier_words, vague_words


def replacements(rule):
    """Every word a writer could take away from this rule as the replacement.

    Some values are pipe-separated menus ("also | besides"); each branch is a
    replacement in its own right, so each branch is audited separately.
    """
    out = []
    for value in [rule["suggestion"]] + list(rule.get("alts") or []):
        out.append(value)
        if "|" in value:
            out.extend(part.strip() for part in value.split("|"))
    seen = set()
    unique = []
    for v in out:
        if v and v.lower() not in seen:
            seen.add(v.lower())
            unique.append(v)
    return unique


def tokens(value):
    """The individual words of a multi-word replacement."""
    if " " not in value.strip():
        return []
    return [w for w in re.split(r"[^A-Za-z0-9'-]+", value.lower()) if w]


def main():
    subs, error_tier_words, vague_words = collect()

    collisions = []
    for r in subs:
        for alt in replacements(r):
            if alt.lower() in error_tier_words:
                collisions.append((r["pattern"], alt, r["id"]))

    # Deeper pass: a multi-word replacement is just as broken when one of its
    # WORDS is banned -- the ban tables match on word boundaries, so advising
    # "so that" walks the writer into the T6 filler rule for "so".
    word_collisions = []
    for r in subs:
        for alt in replacements(r):
            for tok in tokens(alt):
                if tok in error_tier_words:
                    word_collisions.append((r["pattern"], alt, tok, r["id"]))

    print(len(collisions), "collisions found")
    for c in collisions:
        print(c)

    print()
    print(len(word_collisions), "word-level collisions inside multi-word replacements")
    for c in word_collisions:
        print(c)

    # Secondary, lower-priority signal: replacements that land on a T2 vague term.
    soft = []
    for r in subs:
        for alt in replacements(r):
            if alt.lower() not in error_tier_words and alt.lower() in vague_words:
                soft.append((r["pattern"], alt, r["id"]))
    print()
    print(len(soft), "soft (T2 vague-tier) collisions")
    for c in soft:
        print(c)

    # `must` is forbidden as a suggestion per O3 / DEC-TEC-TOOL-003.
    musts = [
        (r["pattern"], alt, r["id"])
        for r in subs
        for alt in replacements(r)
        if alt.lower() == "must"
    ]
    print()
    print(len(musts), "uses of 'must' as a replacement")
    for m in musts:
        print(m)

    return 1 if (collisions or word_collisions or musts) else 0


if __name__ == "__main__":
    sys.exit(main())
