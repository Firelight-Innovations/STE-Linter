#!/usr/bin/env python3
"""Regression tests for the T1 suggestion/ban collision pass.

Four checks, all must pass:

  1. audit/collision_audit.py reports zero collisions -- no T1 rule hands the
     writer a replacement that an error-tier table bans (whole string, each
     pipe-separated branch, and each word of a multi-word replacement), and
     no rule reintroduces `must` (O3 / DEC-TEC-TOOL-003: `shall` is the
     mandatory keyword).
  2. tests/corpus_suggestions/new_suggestions.md -- zero error-tier findings.
     Every replacement the changed rules now hand out appears in that file,
     so a writer who takes the advice of the tool stays clean.
  3. tests/corpus_suggestions/old_suggestions.md -- every prose line still
     raises at least one error-tier finding. The words that were removed are
     still banned; the pass changed the advice, not the ban tables.
  4. tests/corpus_suggestions/t1_exceptions.md -- the `exceptions` field of a
     T1 rule suppresses the finding when the preceding word makes a fixed
     compound ("pull request", "the interface"), and does not suppress the
     plain replaceable use.

Usage: python -X utf8 tests/run_suggestion_tests.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "audit"))

LINTER = ROOT / "ste_lint.py"
FIXTURES = ROOT / "tests" / "corpus_suggestions"
NEW_MD = FIXTURES / "new_suggestions.md"
OLD_MD = FIXTURES / "old_suggestions.md"
EXC_MD = FIXTURES / "t1_exceptions.md"

# Rules whose suggestion/alts this pass rewrote. Ids only -- the expected
# values are read live from lint_data/substitutions.json, so the fixture
# coverage check follows any later edit to these rules.
CHANGED_RULE_IDS = [
    "STE-T1-SUB-0007", "STE-T1-SUB-0009", "STE-T1-SUB-0027", "STE-T1-SUB-0031",
    "STE-T1-SUB-0037", "STE-T1-SUB-0040", "STE-T1-SUB-0042", "STE-T1-SUB-0061",
    "STE-T1-SUB-0070", "STE-T1-SUB-0074", "STE-T1-SUB-0086", "STE-T1-SUB-0097",
    "STE-T1-SUB-0107", "STE-T1-SUB-0116", "STE-T1-SUB-0117", "STE-T1-SUB-0121",
    "STE-T1-SUB-0124", "STE-T1-SUB-0126", "STE-T1-SUB-0134", "STE-T1-SUB-0136",
    "STE-T1-SUB-0139", "STE-T1-SUB-0140", "STE-T1-SUB-0142", "STE-T1-SUB-0143",
    "STE-T1-SUB-0150", "STE-T1-SUB-0157", "STE-T1-SUB-0162", "STE-T1-SUB-0177",
    "STE-T1-SUB-0183", "STE-T1-SUB-0184", "STE-T1-SUB-0185", "STE-T1-SUB-0188",
    "STE-T1-SUB-0189", "STE-T1-SUB-0190", "STE-T1-SUB-0191", "STE-T1-SUB-0195",
    "STE-T1-SUB-0197", "STE-T1-SUB-0209", "STE-T1-SUB-0212", "STE-T1-SUB-0219",
    "STE-T1-SUB-0220", "STE-T1-SUB-0232", "STE-T1-SUB-0233", "STE-T1-SUB-0234",
    "STE-T1-SUB-0237", "STE-T1-SUB-0255", "STE-T1-SUB-0268", "STE-T1-SUB-0276",
    "STE-T1-SUB-0297", "STE-T1-SUB-0299", "STE-T1-SUB-0303", "STE-T1-SUB-0304",
    "STE-T1-SUB-0305", "STE-T1-SUB-0306", "STE-T1-SUB-0313", "STE-T1-SUB-0315",
    "STE-T1-SUB-0316", "STE-T1-SUB-0317", "STE-T1-SUB-0323", "STE-T1-SUB-0324",
    "STE-T1-SUB-0327", "STE-T1-SUB-0329", "STE-T1-SUB-0335", "STE-T1-SUB-0340",
    "STE-T1-SUB-0344", "STE-T1-SUB-0347", "STE-T1-SUB-0352", "STE-T1-SUB-0353",
    "STE-T1-SUB-0368", "STE-T1-SUB-0375", "STE-T1-SUB-0376", "STE-T1-SUB-0377",
    "STE-T1-SUB-0393", "STE-T1-SUB-0405", "STE-T1-SUB-0419", "STE-T1-SUB-0421",
    "STE-T1-SUB-0422",
]

# t1_exceptions.md, keyed by line number: rule id that must fire (or None).
EXCEPTION_LINES = {
    10: None,                 # "pull request"    -- exception, silent
    11: None,                 # "merge request"   -- exception, silent
    12: None,                 # "API request"     -- exception, silent
    13: "STE-T1-SUB-0383",    # "Operators request a new key" -- verb, fires
    14: None,                 # "The interface"   -- noun, silent
    15: "STE-T1-SUB-0320",    # "Vendors interface with" -- verb, fires
}

failures = []


def lint(paths):
    cmd = [sys.executable, "-X", "utf8", str(LINTER), "--format", "json"]
    cmd += [str(p) for p in paths]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(proc.stdout)["findings"]
    except (json.JSONDecodeError, KeyError):
        failures.append("lint invocation produced non-JSON output: {}".format(proc.stdout[:500]))
        return []


def errors_by_line(findings, rel_name):
    out = {}
    for f in findings:
        if f["severity"] == "error" and f["file"].endswith(rel_name):
            out.setdefault(f["line"], []).append(f["rule"])
    return out


def check_audit():
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(ROOT / "devtools" / "collision_audit.py")],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        failures.append("collision audit is not clean:\n{}".format(proc.stdout))
    else:
        first = proc.stdout.split("\n")[0]
        print("PASS collision audit: {}".format(first))


def replacements_of(rule):
    out = []
    for value in [rule["suggestion"]] + list(rule.get("alts") or []):
        if "|" in value:
            out.extend(p.strip() for p in value.split("|"))
        else:
            out.append(value)
    return [v for v in out if v]


def check_new_fixture():
    findings = lint([NEW_MD])
    bad = errors_by_line(findings, "new_suggestions.md")
    if bad:
        for line in sorted(bad):
            failures.append("new_suggestions.md:{} raises {} -- the advice of the tool is not clean".format(line, bad[line]))
    else:
        print("PASS new_suggestions.md: 0 error-tier findings")

    with open(ROOT / "src" / "ste100" / "data" / "substitutions.json", encoding="utf-8") as fh:
        rules = {r["id"]: r for r in json.load(fh)["rules"]}
    text = NEW_MD.read_text(encoding="utf-8").lower()
    missing = []
    covered = 0
    for rid in CHANGED_RULE_IDS:
        rule = rules.get(rid)
        if rule is None:
            failures.append("changed rule {} no longer exists in substitutions.json".format(rid))
            continue
        for value in replacements_of(rule):
            covered += 1
            if not re.search(r"(?<![a-z0-9]){}(?![a-z0-9])".format(re.escape(value.lower())), text):
                missing.append("{} ({!r})".format(rid, value))
    if missing:
        failures.append("new_suggestions.md does not exercise: {}".format(", ".join(sorted(set(missing)))))
    else:
        print("PASS new_suggestions.md coverage: {} replacements over {} changed rules".format(covered, len(CHANGED_RULE_IDS)))


def check_old_fixture():
    findings = lint([OLD_MD])
    by_line = errors_by_line(findings, "old_suggestions.md")
    lines = OLD_MD.read_text(encoding="utf-8").split("\n")
    # Prose lines start after the header block (the first blank line that
    # follows the explanatory paragraph). Everything from the first sentence
    # line onward is a one-word-per-line ban probe.
    start = next(i for i, l in enumerate(lines, start=1) if l.startswith("The run took about"))
    silent = [i for i in range(start, len(lines) + 1)
              if i - 1 < len(lines) and lines[i - 1].strip() and i not in by_line]
    if silent:
        failures.append("old_suggestions.md lines no longer flagged: {}".format(silent))
    else:
        print("PASS old_suggestions.md: {} lines all still flagged".format(len(lines) - start + 1 - lines[start - 1:].count("")))


def check_exceptions_fixture():
    findings = lint([EXC_MD])
    by_line = errors_by_line(findings, "t1_exceptions.md")
    ok = True
    for line, expected in EXCEPTION_LINES.items():
        got = by_line.get(line, [])
        if expected is None and got:
            failures.append("t1_exceptions.md:{} should be silent, raised {}".format(line, got))
            ok = False
        elif expected is not None and expected not in got:
            failures.append("t1_exceptions.md:{} should raise {}, raised {}".format(line, expected, got))
            ok = False
    if ok:
        print("PASS t1_exceptions.md: exceptions gate suppresses compounds, keeps plain uses")


if __name__ == "__main__":
    check_audit()
    check_new_fixture()
    check_old_fixture()
    check_exceptions_fixture()

    print()
    if failures:
        print("FAIL ({} issue(s)):".format(len(failures)))
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("All suggestion tests passed.")
    sys.exit(0)
