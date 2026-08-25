#!/usr/bin/env python3
"""Regression tests: line wrapping must not change the analysis.

A paragraph means the same thing whether the author hard-wrapped it at 60
columns or left it on one long line, so it must lint the same either way. That
invariant was broken and nothing caught it: sentence units were built from each
physical line, so a wrapped sentence was analysed as several fragments. The T5
atomicity checks stopped seeing the real sentence, the word budget measured a
fragment, and a five-sentence paragraph was reported as nine.

These tests pin the invariant, plus the column mapping that has to survive it --
--fix and the VS Code problemMatcher both navigate by line and column.

Usage: python -X utf8 tests/run_wrapping_tests.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
import textwrap
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINTER = ROOT / "ste_lint.py"

failures = []


def check(name, ok, detail=""):
    if ok:
        print("PASS {}".format(name))
    else:
        failures.append("{}{}".format(name, ": " + detail if detail else ""))


def findings_for(cwd, name, *args):
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(LINTER), "--format", "json", "--stats", *args, name],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(proc.stdout)["findings"]
    except (json.JSONDecodeError, KeyError):
        failures.append("non-JSON output for {}: {}".format(name, proc.stdout[:300]))
        return []


def write(path, body):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)


def rule_counts(findings):
    """Rules and how many of each -- position is compared separately."""
    return Counter(f["rule"] for f in findings)


tmp = Path(tempfile.mkdtemp(prefix="ste100-wrap-"))
try:
    # A single sentence carrying three 'shall' imperatives and four combinators.
    # Wrapped, its fragments individually look like harmless short sentences.
    SENTENCE = ("The system shall read the file and validate the header and parse the body "
                "and emit a report, and it shall log the result, and it shall exit cleanly.")

    write(tmp / "flat.md", "# T\n\n" + SENTENCE + "\n")
    write(tmp / "wrapped.md", "# T\n\n" + "\n".join(textwrap.wrap(SENTENCE, 28)) + "\n")

    flat = findings_for(tmp, "flat.md", "--profile", "spec")
    wrapped = findings_for(tmp, "wrapped.md", "--profile", "spec")

    check("the fixture actually trips the atomicity checks", len(flat) >= 6,
          "only {} findings on the unwrapped form".format(len(flat)))
    check("wrapping does not change which rules fire",
          rule_counts(flat) == rule_counts(wrapped),
          "flat={} wrapped={}".format(dict(rule_counts(flat)), dict(rule_counts(wrapped))))

    # The two findings most easily lost: both are whole-sentence judgements, so
    # they vanish entirely the moment a sentence is analysed as fragments.
    for rule, why in [("STE-T5-MULTI-0001", "multiple 'shall' imperatives"),
                      ("STE-BUD-0001", "the sentence word budget")]:
        check("{} still fires when wrapped ({})".format(rule, why),
              rule in rule_counts(wrapped),
              "rules seen: {}".format(sorted(rule_counts(wrapped))))

    # Fragments of a shall-statement must not be reported as non-requirements.
    for rule in ("STE-T5-NOSHAL-0001", "STE-T5-EARS-0001"):
        check("{} does not fire on wrapped fragments".format(rule),
              rule not in rule_counts(wrapped),
              "fired {} time(s)".format(rule_counts(wrapped).get(rule)))

    # Every reported position must land on the token it names. This is the part
    # that a naive "join the lines" fix gets wrong.
    lines = (tmp / "wrapped.md").read_text(encoding="utf-8").split("\n")
    misplaced = []
    for f in wrapped:
        if f["rule"] != "STE-T5-COMB-0001":
            continue
        got = lines[f["line"] - 1][f["column"] - 1:f["column"] - 1 + 3]
        if got != "and":
            misplaced.append("{}:{} -> {!r}".format(f["line"], f["column"], got))
    check("combinator findings point at the real 'and' across line breaks",
          not misplaced, "; ".join(misplaced))

    # The paragraph budget counts sentences, so it must not count line breaks.
    PARA = ("The tool reads the file. The parser builds a tree. The report prints results. "
            "The engine loads tables. The writer emits output.")
    write(tmp / "para_flat.md", "# T\n\n" + PARA + "\n")
    write(tmp / "para_wrapped.md", "# T\n\n" + "\n".join(textwrap.wrap(PARA, 24)) + "\n")

    budget_flat = [f for f in findings_for(tmp, "para_flat.md") if f["rule"] == "STE-BUD-0002"]
    budget_wrapped = [f for f in findings_for(tmp, "para_wrapped.md") if f["rule"] == "STE-BUD-0002"]
    check("a five-sentence paragraph is under budget on one line", not budget_flat,
          str(budget_flat))
    check("wrapping does not inflate the paragraph sentence count", not budget_wrapped,
          budget_wrapped[0]["message"] if budget_wrapped else "")

    # A wrapped list item is one item, not one item plus an orphan sentence.
    ITEM = ("The subsystem shall accept the request and record the outcome "
            "and it shall return a status code to the caller.")
    write(tmp / "list_flat.md", "# T\n\n- " + ITEM + "\n")
    write(tmp / "list_wrapped.md",
          "# T\n\n" + "\n".join(textwrap.wrap(ITEM, 30, initial_indent="- ",
                                             subsequent_indent="  ")) + "\n")

    list_flat = findings_for(tmp, "list_flat.md", "--profile", "spec")
    list_wrapped = findings_for(tmp, "list_wrapped.md", "--profile", "spec")
    check("the list fixture trips something", len(list_flat) >= 1,
          "{} findings".format(len(list_flat)))
    check("wrapping a list item does not change which rules fire",
          rule_counts(list_flat) == rule_counts(list_wrapped),
          "flat={} wrapped={}".format(dict(rule_counts(list_flat)),
                                      dict(rule_counts(list_wrapped))))

    # Separate paragraphs must stay separate: a blank line is a real boundary,
    # and joining across one would merge two sentences into a false run-on.
    write(tmp / "two_paras.md",
          "# T\n\nThe system shall read the file.\n\nThe system shall write the file.\n")
    two = findings_for(tmp, "two_paras.md", "--profile", "spec")
    check("a blank line still separates paragraphs",
          "STE-T5-MULTI-0001" not in rule_counts(two),
          "two one-shall paragraphs were merged into a multi-shall sentence")

    # A heading is not prose and must not be absorbed into the paragraph below it.
    write(tmp / "heading.md", "# The system shall start\n\nThe system shall stop.\n")
    heading = findings_for(tmp, "heading.md", "--profile", "spec")
    check("a heading is not joined to the paragraph after it",
          "STE-T5-MULTI-0001" not in rule_counts(heading),
          "heading text was merged into the following sentence")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

if failures:
    print("\nFAIL ({} issue(s)):".format(len(failures)))
    for f in failures:
        print(" - {}".format(f))
    sys.exit(1)
print("\nAll wrapping tests passed.")
