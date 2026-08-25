"""--fix: apply unambiguous T1 substitutions in place.

"Unambiguous" is deliberately narrow. --fix rewrites a writer's source file,
so it only ever applies a rule that has exactly one candidate replacement and
that replacement is real text. Anything needing human judgement is reported as
a finding and left alone.
"""
from .masking import FENCE_RE, mask_line


def apply_fix(abs_path, engine):
    text = abs_path.read_text(encoding="utf-8")
    if not engine.t1_regex:
        return 0

    def repl(m):
        rule = engine.t1_rules.get(m.group(1).lower())
        if not rule or len(rule.get("alts", [])) != 1:
            return m.group(0)  # ambiguous (multiple alts) -- never auto-fix
        exceptions = rule.get("exceptions")
        if exceptions:
            prev = engine.preceding_word(m.string, m.start())
            if prev and prev in {e.lower() for e in exceptions}:
                return m.group(0)  # fixed compound -- not the replaceable use
        suggestion = rule["suggestion"]
        # 14 rules carry an empty suggestion, meaning "delete this phrase".
        # Deleting words changes the grammar of the surrounding sentence, and
        # applying that blind corrupts prose: "It is important that the
        # operator selects the type of report." became " important that the
        # operator selects the  of report." Report those, never auto-apply.
        if not suggestion.strip():
            return m.group(0)
        if m.group(1)[0].isupper():
            suggestion = suggestion[:1].upper() + suggestion[1:]
        return suggestion

    # Only fix outside fenced/inline code -- reuse the masked-line scan to
    # decide which lines are eligible, but write back against the real text.
    lines = text.split("\n")
    in_fence = False
    changed = False
    for i, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        masked = mask_line(line)
        if masked != line:
            continue  # line has inline code/links; skip to avoid corrupting spans
        new_line = engine.t1_regex.sub(repl, line)
        if new_line != line:
            lines[i] = new_line
            changed = True
    if changed:
        # Not Path.write_text(newline=...): that keyword arrived in 3.10, and
        # this package supports 3.9, where it raises TypeError. Newlines stay
        # pinned so --fix never silently rewrites a file's line endings.
        with open(abs_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines))
    return 1 if changed else 0
