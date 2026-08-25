"""T6 Zero-information -- filler.json."""
import re

from .common import id_list

ALWAYS_ERROR_INTENSIFIERS = [
    "very", "quite", "really", "actually", "basically", "essentially", "simply", "just",
    "literally", "totally", "completely", "absolutely", "definitely", "certainly", "clearly",
    "obviously", "significantly", "substantially", "extremely", "fairly", "rather", "somewhat",
    "virtually", "arguably",
]
WEASEL_WORDS_19 = [
    "clearly", "completely", "extremely", "fairly", "largely", "like", "many", "might", "most",
    "mostly", "probably", "quite", "rather", "really", "relatively", "several", "significantly",
    "very", "virtually",
]
OVERUSED_VOCABULARY = [
    "delve", "underscore", "seamlessly", "robust", "elevate", "bolster", "underpins", "synergy",
    "holistic", "paradigm", "cornerstone", "meticulous", "nuanced", "myriad", "plethora",
    "burgeoning", "ubiquitous", "granular", "actionable", "impactful", "empower", "proactive",
    "comprehensive", "unprecedented", "scalable", "versatile", "crucial", "vital",
    "state-of-the-art", "best-in-class", "unleash", "democratize", "landscape", "realm",
    "tapestry", "testament", "navigate", "foster", "leverage", "harness",
]
CORPORATE_SPEAK = [
    "at the end of the day", "back to the drawing board", "hit the ground running",
    "get the ball rolling", "low-hanging fruit", "thrown under the bus", "think outside the box",
    "let's touch base", "it's on my radar", "ping me", "i don't have the bandwidth", "no brainer",
    "par for the course", "bang for your buck", "synergy", "move the goal post",
    "apples to apples", "win-win", "circle back", "all hands on deck", "take this offline",
    "drill-down", "elephant in the room", "on my plate",
]
NOMINALIZATION_WEAK_VERBS = ["make", "perform", "conduct", "provide", "carry out", "undertake", "do", "give"]
NOMINALIZATION_SUFFIXES = ["tion", "ment", "ance", "ence", "ing"]


def build_filler(src):
    fillers_raw = [w.lower() for w in src["retext_intensify.fillers"]["data"]]
    intensifiers_raw = [w.lower() for w in src["MERGED.intensifiers_adverbs"]["data"].keys()]
    # One id_list call per prefix -- calling id_list twice with the same prefix
    # would restart numbering at 0001 and mint duplicate IDs, so overused
    # vocabulary (also zero-information) is folded into the same FILL batch.
    fill_all = id_list("VEI-T6-FILL", fillers_raw + intensifiers_raw + ALWAYS_ERROR_INTENSIFIERS + OVERUSED_VOCABULARY)
    overused_set = set(w.lower() for w in OVERUSED_VOCABULARY)
    fill = [e for e in fill_all if e["pattern"] not in overused_set]
    overused = [e for e in fill_all if e["pattern"] in overused_set]
    weasel = id_list("VEI-T6-WEASEL", WEASEL_WORDS_19)
    corp = id_list("VEI-T6-CORP", CORPORATE_SPEAK)
    weasel_and_hedge = src["MERGED.weasel_and_hedge"]["data"]
    weasel_skipped = [k for k in weasel_and_hedge if not re.search(r"[a-zA-Z]", k)]
    return {
        "schema_version": 1,
        "test": "T6",
        "name": "Zero-information",
        "default_tier": "error",
        "fillers_and_intensifiers": fill,
        "overused_vocabulary": overused,
        "weasel_words": weasel,
        "corporate_speak": corp,
        "nominalization": {"id": "VEI-T6-NOM-0001", "weak_verbs": NOMINALIZATION_WEAK_VERBS, "noun_suffixes": NOMINALIZATION_SUFFIXES},
        "generic_ly_adverb_detection": "review",  # C1: enumerated list above is error; generic -ly is review-tier
        "notes": {
            "weasel_cross_check": f"MERGED.weasel_and_hedge (280) used only as a cross-check; "
                                   f"{len(weasel_skipped)} punctuation-only junk keys skipped. "
                                   "The authoritative weasel list is the 19 words above (§8.6).",
        },
        "counts": {"fillers_and_intensifiers": len(fill), "weasel_words": len(weasel), "overused_vocabulary": len(overused)},
    }
