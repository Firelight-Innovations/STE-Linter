#!/usr/bin/env python3
"""Test harness for ste_lint.py (spec section 12.1-12.2, 12.7).

Three checks, all must pass:
  1. corpus_clean/*  -> zero errors AND zero warnings (linted together).
  2. corpus_dirty/*   -> every inline `expect:RULE_ID` annotation (Markdown)
     and every tools/tests/corpus_dirty/csv_findings_manifest.json entry
     (CSV-integrity/budget findings, which have no line to annotate) fires.
  3. Determinism (C4) -> same input twice -> identical output minus run_at.

Plus a coverage check: every fixed rule ID in tools/lint/rule_ids.py must
appear at least once across the corpus_dirty expectations/manifest, except
VEI-CSV-0009 (aliased to VEI-BUD-0003, see rule_ids.py) and VEI-BUD-0004
(whole-file budget: keyed to exact real project paths, so it's exercised
by a direct engine call below instead of a fixture file).

Scope note: bulk word-list rule IDs (T1 substitutions, T2 vague terms, T3
hedges, T4 pronouns, T6 fillers/weasels/corp-speak/ai-tells -- ~1130 IDs
total) are covered by category via dirty_t1..t6.md (2+ examples each), not
individually. Testing each of 1130 IDs with its own fixture line isn't a
useful bar; the regex/lookup machinery is shared per category, so a handful
of examples per category exercises the same code path as all of them.

Usage: python -X utf8 tools/tests/run_corpus_tests.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
LINTER = TOOLS / "ste_lint.py"
CLEAN_DIR = TOOLS / "tests" / "corpus_clean"
DIRTY_DIR = TOOLS / "tests" / "corpus_dirty"
MANIFEST = DIRTY_DIR / "csv_findings_manifest.json"
EXPECT_RE = re.compile(r"`expect:([A-Za-z0-9\-]+)`")

failures = []


def run_lint(paths, today=None, stats=True):
    cmd = [sys.executable, "-X", "utf8", str(LINTER), "--format", "json"]
    if stats:
        cmd.append("--stats")
    if today:
        cmd += ["--today", today]
    cmd += [str(p) for p in paths]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        failures.append("lint invocation produced non-JSON output: {}".format(proc.stdout[:500]))
        return {"findings": []}


def check_corpus_clean():
    files = sorted(CLEAN_DIR.rglob("*.md")) + sorted(CLEAN_DIR.rglob("*.csv"))
    result = run_lint(files)
    bad = [f for f in result["findings"] if f["severity"] in ("error", "warning")]
    if bad:
        for f in bad:
            failures.append("corpus_clean not clean: {}:{} {} {}".format(f["file"], f["line"], f["rule"], f["severity"]))
    else:
        print("PASS corpus_clean: {} files, 0 errors, 0 warnings".format(len(files)))


def collect_expectations():
    expectations = []
    for md in sorted(DIRTY_DIR.rglob("*.md")):
        rel = md.relative_to(ROOT).as_posix()
        for i, line in enumerate(md.read_text(encoding="utf-8").split("\n"), start=1):
            for rule in EXPECT_RE.findall(line):
                expectations.append((rel, i, rule))
    return expectations


def check_corpus_dirty():
    all_files = sorted(DIRTY_DIR.rglob("*.md")) + sorted(DIRTY_DIR.rglob("*.csv"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = run_lint(all_files, today=manifest["today"])
    found = {(f["file"], f["line"], f["rule"]) for f in result["findings"]}
    found_by_row = {(f["file"], f.get("row_id"), f["rule"]) for f in result["findings"]}

    expectations = collect_expectations()
    seen_rules = set()
    for rel, line, rule in expectations:
        seen_rules.add(rule)
        if (rel, line, rule) not in found:
            failures.append("expected {}:{} {} not found".format(rel, line, rule))
    if not any("expected" in f for f in failures):
        print("PASS corpus_dirty inline expectations: {} annotations".format(len(expectations)))

    manifest_bad = 0
    for e in manifest["entries"]:
        seen_rules.add(e["rule"])
        if (e["file"], e["row_id"], e["rule"]) not in found_by_row:
            failures.append("manifest entry not found: {} row_id={} {}".format(e["file"], e["row_id"], e["rule"]))
            manifest_bad += 1
    if not manifest_bad:
        print("PASS csv_findings_manifest: {} entries".format(len(manifest["entries"])))
    return seen_rules


def check_rule_id_coverage(seen_rules):
    from lint import rule_ids as r
    required = {getattr(r, n) for n in dir(r) if n.endswith("_ID") and not n.startswith("_")}
    required |= set(r.CSV_CHECK_IDS.values())
    required -= {r.CSV_CHECK_IDS[9], r.BUD_WHOLE_FILE_ID}  # documented exclusions, see module docstring
    missing = required - seen_rules
    if missing:
        failures.append("rule IDs with no corpus_dirty coverage: {}".format(sorted(missing)))
    else:
        print("PASS rule ID coverage: {} fixed IDs all exercised".format(len(required)))


def check_whole_file_budget_direct():
    from lint.engine import Engine
    from lint.paths import DEFAULT_CONFIG, load_json, load_lint_data

    engine = Engine(load_json(DEFAULT_CONFIG), load_lint_data())
    for target, over_budget_words in (("core/00-READ-FIRST.md", 601), ("core/writing-standard.md", 1201)):
        findings = []
        engine.check_whole_file_budget(target, "word " * over_budget_words, findings)
        if not findings or findings[0].rule != "VEI-BUD-0004":
            failures.append("VEI-BUD-0004 did not fire for synthetic {}-word {}".format(over_budget_words, target))
    if not any("VEI-BUD-0004" in f for f in failures):
        print("PASS VEI-BUD-0004 (whole-file budget, direct engine call)")


def check_determinism():
    a = run_lint([], stats=True)
    b = run_lint([], stats=True)
    a.pop("run_at", None)
    b.pop("run_at", None)
    if a != b:
        failures.append("determinism (spec C4): two runs over the whole project produced different output")
    else:
        print("PASS determinism: whole-project run is byte-identical minus run_at")


if __name__ == "__main__":
    check_corpus_clean()
    seen = check_corpus_dirty()
    check_rule_id_coverage(seen)
    check_whole_file_budget_direct()
    check_determinism()

    print()
    if failures:
        print("FAIL ({} issue(s)):".format(len(failures)))
        for f in failures:
            print(" -", f)
        sys.exit(1)
    print("All corpus tests passed.")
    sys.exit(0)
