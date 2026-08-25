"""Shared text normalization for duplication/contradiction/terminology-drift
sections. Stdlib only (D1) -- no NLP dependency, just a stopword list and a
tokenizer, which is enough for the coarse signals these sections need."""
import re

STOPWORDS = frozenset("""
a an the this that these those is are was were be been being have has had
do does did will would shall should may might must can could to of in on
at by for with without from into onto over under about as and or but if
then than so not no nor it its they them their he she his her we our you
your i me my all any some each every either neither one two first last
per via using use used new same other such only also more most very just
""".split())

NEGATIONS = frozenset(["not", "no", "never", "none", "cannot", "n't", "without"])


def tokenize(text):
    return re.findall(r"[a-z][a-z'-]*", text.lower())


def content_words(text):
    return [w for w in tokenize(text) if w not in STOPWORDS and len(w) > 2]


def jaccard(a, b):
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
