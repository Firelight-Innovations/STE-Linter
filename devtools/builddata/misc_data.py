"""pos_heuristics.json (spec section 2.5) and budgets.json (spec section 9)."""


def build_pos_heuristics():
    return {
        "schema_version": 1,
        "purpose": "Positional heuristic table approximating part-of-speech without a tagger (D1 rules out a dependency).",
        "heuristics": [
            {"rule": "preceded_by", "tokens": ["the", "a", "an", "this", "each"], "pos": "noun", "confidence": "high"},
            {"rule": "preceded_by_possessive_or_adjective_followed_by_verb", "pos": "noun", "confidence": "medium"},
            {"rule": "sentence_initial_in_procedure_profile", "pos": "verb_imperative", "confidence": "high", "note": "C3: the 'procedure' profile row is dropped per spec defect resolution; six profiles only."},
            {"rule": "preceded_by", "tokens": ["to"], "pos": "verb_infinitive", "confidence": "high"},
            {"rule": "preceded_by", "tokens": ["shall", "must", "will"], "pos": "verb", "confidence": "high"},
            {"rule": "followed_by_noun_no_determiner", "pos": "adjective", "confidence": "medium"},
            {"rule": "no_match", "pos": "unknown", "confidence": None, "severity_cap": "review"},
        ],
    }


def build_budgets():
    return {
        "schema_version": 1,
        "csv_field_budgets": [
            {"target": "truths.csv:statement", "words": 15, "tier": "error"},
            {"target": "decisions-*.csv:decision", "words": 25, "tier": "error"},
            {"target": "decisions-*.csv:rationale", "words": 25, "tier": "error"},
            {"target": "decisions-*.csv:scope", "words": 10, "tier": "error"},
            {"target": "timeline.csv:event", "words": 15, "tier": "error"},
            {"target": "timeline.csv:note", "words": 20, "tier": "error"},
            {"target": "terminology.csv:definition", "words": 20, "tier": "error"},
        ],
        "sentence_budgets": [
            {"profile": "core", "words": 20, "tier": "error"},
            {"profile": "spec", "words": 25, "tier": "error"},
            {"profile": "design", "words": 25, "tier": "error"},
            {"profile": "prose", "words": 30, "tier": "warning"},
            {"profile": "vision", "words": 30, "tier": "warning"},
        ],
        "paragraph_budget": {"sentences": 6, "tier": "warning", "applies_to": "all profiles"},
        "whole_file_budgets": [
            {"target": "core/00-READ-FIRST.md", "words": 600, "tier": "error"},
            {"target": "core/writing-standard.md", "words": 1200, "tier": "error"},
        ],
        "truths_csv_row_budget": {"rows": 40, "tier": "warning", "note": "escalates in weekly audit"},
    }
