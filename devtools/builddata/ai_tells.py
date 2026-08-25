"""T6 Zero-information (AI tells) -- ai_tells.json."""
from .common import id_list


def build_ai_tells():
    hedging_openers = ["it is important to note that", "it's worth noting that", "it should be mentioned that", "keep in mind that"]
    conclusion_markers = ["in conclusion", "overall", "at the end of the day", "in summary"]
    contrastive_formulas = ["not just {x}, it's {y}", "not merely", "it's not about {x}, it's about {y}"]
    ai = id_list("STE-T6-AI", hedging_openers + conclusion_markers + contrastive_formulas)
    hedging_opener_set = set(hedging_openers)
    conclusion_marker_set = set(conclusion_markers)
    for entry in ai:
        if entry["pattern"] in hedging_opener_set:
            entry["kind"] = "hedging_opener"
        elif entry["pattern"] in conclusion_marker_set:
            entry["kind"] = "conclusion_marker"
        else:
            entry["kind"] = "contrastive_formula"
    artifacts = [
        {"id": "STE-T6-ARTIFACT-0001", "pattern": r":contentReference\[oaicite:\d+\]\{index=\d+\}"},
        {"id": "STE-T6-ARTIFACT-0002", "pattern": r"oai_citation:\d+"},
        {"id": "STE-T6-ARTIFACT-0003", "pattern": r"sandbox:/mnt/data/"},
    ]
    return {
        "schema_version": 1,
        "test": "T6",
        "name": "Zero-information (AI tells)",
        "default_tier": "error",
        "phrases": ai,
        "hedging_opener_action": "delete_phrase_keep_sentence",
        "conclusion_marker_condition": "documents under 1000 words",
        "machine_artifacts": {"rules": artifacts, "confidence": "high", "is_regex": True},
    }
