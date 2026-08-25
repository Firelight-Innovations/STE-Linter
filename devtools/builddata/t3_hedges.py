"""T3 Optional -- hedges.json (escape clauses, open-ended, optionality, infinitives, hedge list)."""
from .common import id_list

ESCAPE_CLAUSES = [
    "so far as possible", "as little as possible", "where possible", "as much as possible",
    "as far as possible", "if it should prove necessary", "if necessary", "to the extent necessary",
    "as appropriate", "as required", "as applicable", "to the extent practical", "if practicable",
    "where feasible", "wherever possible", "at the discretion of", "subject to",
]
OPEN_ENDED_CLAUSES = [
    "including but not limited to", "and so on", "and others", "the like", "among others",
    "etc.", "e.g.", "i.e.",
]
OPTIONALITY_PHRASES = [
    "in case", "if possible", "if appropriate", "if needed", "if required", "if practical",
    "as desired",
]
OPTIONALITY_SINGLE_MODALS = [
    "can", "may", "could", "might", "optionally", "possibly", "probably", "usually",
    "eventually", "preferably",
]
SUPERFLUOUS_INFINITIVES = [
    "to be designed to", "to be able to", "to be capable of", "to enable", "to allow",
    "be able to", "be capable of",
]

# This session: retext_intensify.hedges (161 entries) includes bare epistemic
# verbs ("read", "appear", "seem", ...) that also serve as ordinary imperative
# or copular verbs unrelated to hedging ("Read core/truths.csv"). A bare
# wordlist match on these flags correct, unhedged instructions. ste_lint.py
# (step 6) must require a collocate for this subset -- e.g. "reads as",
# "appears to" -- rather than matching the bare token. Listed here so the
# rule survives into the linter build.
AMBIGUOUS_HEDGE_VERBS_NEED_CONTEXT = ["read", "appear", "seem"]


def build_hedges(src):
    hedge_list = [w.lower() for w in src["retext_intensify.hedges"]["data"]]
    escape = id_list("STE-T3-ESC", ESCAPE_CLAUSES)
    open_ended = id_list("STE-T3-OPEN", OPEN_ENDED_CLAUSES)
    modal_phrases = id_list("STE-T3-MOD", OPTIONALITY_PHRASES + OPTIONALITY_SINGLE_MODALS)
    superfluous = id_list("STE-T3-SUP", SUPERFLUOUS_INFINITIVES)
    hedges = id_list("STE-T3-HDG", hedge_list)
    single_modal_set = set(OPTIONALITY_SINGLE_MODALS)
    for entry in modal_phrases:
        entry["kind"] = "single_modal" if entry["pattern"] in single_modal_set else "phrase"
    return {
        "schema_version": 1,
        "test": "T3",
        "name": "Optional",
        "default_tier": "error",
        "escape_clauses": escape,
        "open_ended_clauses": open_ended,
        "optionality": modal_phrases,
        "superfluous_infinitives": superfluous,
        "hedge_words": hedges,
        "ambiguous_hedge_verbs_need_context": AMBIGUOUS_HEDGE_VERBS_NEED_CONTEXT,
        "notes": {
            "severity": "Escape/open-ended phrases, optionality phrases, and superfluous infinitives block in every "
                        "profile (O1). Single modal verbs (kind=single_modal in 'optionality') are error in spec, "
                        "warning elsewhere (O1). Hedge words are error wherever T3 runs: core, csv, spec, design, "
                        "prose (O1). e.g./i.e./etc. are error in every profile except vision (K2).",
            "ambiguous_hedge_verbs": "See AMBIGUOUS_HEDGE_VERBS_NEED_CONTEXT: require a collocate (e.g. 'as', 'to be') "
                                      "before flagging, or these over-trigger on ordinary imperative/copular use.",
        },
        "counts": {"hedge_words": len(hedges), "escape_clauses": len(escape), "open_ended_clauses": len(open_ended),
                    "optionality": len(modal_phrases), "superfluous_infinitives": len(superfluous)},
    }
