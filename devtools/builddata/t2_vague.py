"""T2 Unfalsifiable -- vague.json."""
from .common import id_list

VAGUE_QUANTIFICATION = [
    "some", "any", "allowable", "several", "many", "a lot of", "a few", "almost always",
    "very nearly", "nearly", "about", "close to", "almost", "approximate", "approximately",
    "numerous", "various", "multiple", "a number of", "up to",
]
VAGUE_ADJECTIVES = [
    "ancillary", "relevant", "routine", "common", "generic", "significant", "flexible",
    "expandable", "typical", "sufficient", "adequate", "appropriate", "efficient", "effective",
    "proficient", "reasonable", "customary", "bad", "good", "clear", "close", "easy", "far",
    "fast", "near", "recent", "slow", "strong", "suitable", "useful", "acceptable", "accurate",
    "essential", "normal", "timely", "large", "small", "rapid", "robust", "seamless", "intuitive",
]
GAMES_SPECIFIC = [
    "polished", "juicy", "satisfying", "fun", "engaging", "immersive", "snappy", "responsive",
    "tight", "punchy", "smooth", "feels good", "game feel",
]
SUBJECTIVE_UNVERIFIABLE = [
    "user-friendly", "easy to use", "cost-effective", "similar", "similarly", "usable",
    "ad hoc", "accommodate", "safe", "as {adjective} as possible",
]
NAMED_ACCEPTANCE_ID_PREFIXES = ["TRU-", "DEC-", "TL-", "TEST-", "REQ-"]


def build_vague():
    terms = id_list("STE-T2-VAG", VAGUE_QUANTIFICATION + VAGUE_ADJECTIVES + GAMES_SPECIFIC + SUBJECTIVE_UNVERIFIABLE)
    return {
        "schema_version": 1,
        "test": "T2",
        "name": "Unfalsifiable",
        "default_tier": "warning",
        "terms": terms,
        "suppression": {
            "rule": "Suppress a T2 finding when the sentence has a number with a unit, a named "
                    "acceptance-condition ID reference, or a named verification phrase (G4).",
            "id_prefixes": NAMED_ACCEPTANCE_ID_PREFIXES,
        },
        "notes": {"severity": "Warn in every profile (O1); design keeps T2 at warning explicitly (spec §7.4)."},
        "counts": {"terms": len(terms)},
    }
