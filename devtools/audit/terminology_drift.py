"""Section 8 of the weekly audit: terminology drift (spec section 11.8).
Words appearing 5+ times across project prose that terminology.csv doesn't
define -- candidate technical names the glossary is missing. Stopwords and
short words are excluded, or every common English word would qualify."""
from collections import Counter

from .textutil import content_words

MIN_OCCURRENCES = 5


def find_terminology_drift(md_texts, known_terms):
    known = {t.lower() for t in known_terms}
    counts = Counter()
    for text in md_texts.values():
        counts.update(content_words(text))
    drift = [{"word": w, "count": c} for w, c in counts.items() if c >= MIN_OCCURRENCES and w not in known]
    drift.sort(key=lambda d: (-d["count"], d["word"]))
    return drift
