"""Findings and the linted units (Markdown lines/sentences, CSV fields)."""
from .masking import iter_markdown_units, split_sentences


class Finding:
    __slots__ = ("file", "line", "column", "row_id", "field", "rule", "test", "severity",
                 "message", "excerpt", "suggestion", "source")

    def __init__(self, file, line, column, rule, test, severity, message, excerpt,
                 suggestion=None, source=None, row_id=None, field=None):
        self.file = file
        self.line = line
        self.column = column
        self.row_id = row_id
        self.field = field
        self.rule = rule
        self.test = test
        self.severity = severity
        self.message = message
        self.excerpt = excerpt
        self.suggestion = suggestion
        self.source = source

    def to_dict(self):
        d = {"file": self.file, "line": self.line, "column": self.column}
        if self.row_id is not None:
            d["row_id"] = self.row_id
        if self.field is not None:
            d["field"] = self.field
        d.update({
            "rule": self.rule, "test": self.test, "severity": self.severity,
            "message": self.message, "excerpt": self.excerpt,
        })
        if self.suggestion is not None:
            d["suggestion"] = self.suggestion
        if self.source is not None:
            d["source"] = self.source
        return d


def excerpt_around(text, start, end, radius=15):
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    prefix = "..." if lo > 0 else ""
    suffix = "..." if hi < len(text) else ""
    return prefix + text[lo:hi].strip() + suffix


class Unit:
    __slots__ = ("file", "line", "kind", "text", "col_offset", "profile", "row_id", "field",
                 "paragraph_id", "spans")

    def __init__(self, file, line, kind, text, col_offset, profile, row_id=None, field=None,
                 paragraph_id=None, spans=None):
        self.file = file
        self.line = line
        self.kind = kind
        self.text = text
        self.col_offset = col_offset
        self.profile = profile
        self.row_id = row_id
        self.field = field
        self.paragraph_id = paragraph_id
        # A sentence unit can span several physical lines, because the author
        # hard-wrapped it. spans maps an offset in self.text back to where that
        # character really is: each entry is (offset_in_text, lineno, col_base),
        # meaning that from offset_in_text onward the text came from lineno,
        # starting at 0-based column col_base. Units that occupy one line get
        # the single-entry default, which reproduces the old arithmetic exactly.
        self.spans = spans or ((0, line, col_offset),)

    def _span_at(self, offset):
        chosen = self.spans[0]
        for span in self.spans:
            if span[0] > offset:
                break
            chosen = span
        return chosen

    def line_at(self, offset):
        """1-based source line of the character at `offset` in self.text."""
        return self._span_at(offset)[1]

    def col_at(self, offset):
        """1-based source column of the character at `offset` in self.text."""
        span_start, _, col_base = self._span_at(offset)
        return col_base + (offset - span_start) + 1


def _spans_for(start, length, line_table):
    """Map a [start, start+length) slice of the joined buffer to source spans.

    line_table holds (buffer_offset, lineno, line_length) per physical line.
    """
    end = start + length
    spans = []
    for buf_offset, lineno, line_len in line_table:
        line_end = buf_offset + line_len
        if line_end <= start or buf_offset >= end:
            continue
        seg_start = max(buf_offset, start)
        spans.append((seg_start - start, lineno, seg_start - buf_offset))
    if not spans:  # a sentence of only separator whitespace; anchor it somewhere real
        spans.append((0, line_table[0][1], 0))
    return tuple(spans)


def build_markdown_units(rel_path, text, profile):
    """Build lint units, joining each paragraph before splitting it into sentences.

    iter_markdown_units() yields one physical line at a time. Splitting
    sentences inside each line separately meant a sentence the author
    hard-wrapped was analysed as two or more sentences: the T5 atomicity checks
    stopped seeing the real sentence, the word budget measured a fragment, and a
    five-sentence paragraph was reported as nine. The same prose then linted
    differently depending only on where the editor wrapped it. Joining the
    paragraph first makes the analysis independent of line breaks; spans carry
    each sentence's real line and column back to the report.
    """
    units = []
    pending = []            # [(lineno, masked)] for the paragraph being gathered
    pending_paragraph_id = None

    def flush():
        if not pending:
            return
        parts, line_table, cursor = [], [], 0
        for lineno, masked in pending:
            line_table.append((cursor, lineno, len(masked)))
            parts.append(masked)
            cursor += len(masked) + 1  # +1 for the joining space
        # A single space, not a newline: a Markdown line break already means a
        # space, and keeping unit.text free of newlines leaves every downstream
        # consumer (excerpts, word counts, regexes) working on one clean line.
        buffer = " ".join(parts)
        for start, sentence in split_sentences(buffer):
            spans = _spans_for(start, len(sentence), line_table)
            units.append(Unit(rel_path, spans[0][1], "sentence", sentence, spans[0][2],
                              profile, paragraph_id=pending_paragraph_id, spans=spans))
        del pending[:]

    for lineno, kind, masked, paragraph_id in iter_markdown_units(text):
        if kind == "fragment":
            flush()
            pending_paragraph_id = None
            units.append(Unit(rel_path, lineno, "fragment", masked, 0, profile))
            continue
        if paragraph_id != pending_paragraph_id:
            flush()
            pending_paragraph_id = paragraph_id
        pending.append((lineno, masked))
    flush()
    return units


def build_csv_units(rel_path, rows, header, profile):
    units = []
    id_col = "id" if "id" in header else ("term" if "term" in header else None)
    for rownum, row in enumerate(rows, start=2):  # header is row 1
        row_id = row.get(id_col) if id_col else "row{}".format(rownum)
        for field in header:
            value = row.get(field, "") or ""
            if not value:
                continue
            units.append(Unit(rel_path, rownum, "field", value, 0, profile, row_id=row_id, field=field))
    return units
