#!/usr/bin/env python3
"""weekly_audit.py -- Veistra weekly maintenance report (spec section 11).

Stdlib only (D1). Read-only: analyzes core/*.csv and every Markdown doc,
writes docs/audits/YYYY-MM-DD-audit.md, and never edits project content.

CLI entrypoint only; the eight report sections live in tools/audit/.
Usage: python -X utf8 tools/weekly_audit.py [--today YYYY-MM-DD]
"""
import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HTML_COMMENT_LINE_RE = re.compile(r"^\s*<!--.*-->\s*$", re.MULTILINE)

from audit.contradictions import find_contradiction_candidates
from audit.duplication import find_near_duplicates
from audit.growth import compute_growth
from audit.lint_drift import compute_lint_drift
from audit.orphans import find_orphans
from audit.report import render_report
from audit.stale_and_refs import find_broken_references, find_stale_rows
from audit.state import load_state, save_state
from audit.terminology_drift import find_terminology_drift
from lint.csv_integrity import kind_of, load_all_csvs
from lint.discovery import discover_files
from lint.engine import Engine
from lint.paths import DEFAULT_CONFIG, load_json, load_lint_data

ROOT = Path(__file__).resolve().parent.parent
AUDITS_DIR = ROOT / "docs" / "audits"


def main(argv=None):
    p = argparse.ArgumentParser(prog="weekly_audit.py", description="Veistra weekly maintenance report (stdlib only).")
    p.add_argument("--today", metavar="YYYY-MM-DD", default=None)
    args = p.parse_args(argv)

    try:
        today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else datetime.now(timezone.utc).date()
        config = load_json(DEFAULT_CONFIG)
        engine = Engine(config, load_lint_data())

        all_targets = discover_files([], config)
        csv_targets = [(rel, abs_) for rel, abs_ in all_targets if rel.endswith(".csv")]
        md_targets = [(rel, abs_) for rel, abs_ in all_targets if rel.endswith(".md")]
        registry = load_all_csvs(sorted(csv_targets))
        md_texts = {rel: abs_.read_text(encoding="utf-8") for rel, abs_ in md_targets}
        known_terms = [row.get("term", "") for rel_path, sheet in registry.items()
                       if kind_of(rel_path) == "terminology" for row in sheet["rows"]]

        prev_state = load_state() or {}

        stale = find_stale_rows(registry, today)
        broken_refs = find_broken_references(registry, today, engine)
        orphans = find_orphans(registry, md_texts)
        growth, current_counts = compute_growth(registry, prev_state.get("row_counts"))
        duplicates = find_near_duplicates(registry)
        contradictions = find_contradiction_candidates(registry)
        lint_drift = compute_lint_drift(prev_state.get("lint_snapshot"))
        # Profile-override comments (<!-- lint-profile: NAME -->) aren't prose;
        # stripped here only, so terminology drift doesn't treat that markup
        # as project vocabulary. Orphans/duplication keep the raw text -- they
        # need literal id references, which could legitimately sit in a comment.
        prose_only = {rel: HTML_COMMENT_LINE_RE.sub("", text) for rel, text in md_texts.items()}
        term_drift = find_terminology_drift(prose_only, known_terms)

        today_str = today.strftime("%Y-%m-%d")
        report = render_report(today_str, stale, broken_refs, orphans, growth, duplicates,
                                contradictions, lint_drift, term_drift)
        out_path = AUDITS_DIR / "{}-audit.md".format(today_str)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")

        save_state({"row_counts": current_counts, "lint_snapshot": lint_drift[1], "last_run": today_str})

        print("Wrote {}".format(out_path.relative_to(ROOT).as_posix()))
        print("stale={} broken_refs={} orphans={} duplicates={} contradictions={} terminology_drift={}".format(
            len(stale), len(broken_refs), len(orphans), len(duplicates), len(contradictions), len(term_drift)))
        return 0
    except Exception as e:
        print("tool failure: {}: {}".format(type(e).__name__, e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
