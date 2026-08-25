#!/usr/bin/env python3
"""Build tools/lint_data/*.json from handoff/prose_lint_wordlists.json and the
spec-text-only lists documented in docs/handoffs/2026-08-09-implementation-handoff.md section 6.

Run with: python -X utf8 tools/build_lint_data.py
Deterministic: same input, same output, byte for byte (no clock, no random).

CLI entrypoint only; the per-test builders live in tools/builddata/.
"""
import sys
from pathlib import Path as _P

sys.path.insert(0, str(_P(__file__).resolve().parent.parent / "src"))

from builddata.ai_tells import build_ai_tells
from builddata.common import OUT_DIR, load_source, write_json
from builddata.misc_data import build_budgets, build_pos_heuristics
from builddata.t1_substitutions import build_substitutions
from builddata.t2_vague import build_vague
from builddata.t3_hedges import build_hedges
from builddata.t6_filler import build_filler


def main():
    src = load_source()

    outputs = {
        "substitutions.json": build_substitutions(src),
        "hedges.json": build_hedges(src),
        "vague.json": build_vague(),
        "filler.json": build_filler(src),
        "ai_tells.json": build_ai_tells(),
        "pos_heuristics.json": build_pos_heuristics(),
        "budgets.json": build_budgets(),
    }

    for name, obj in outputs.items():
        write_json(OUT_DIR / name, obj)
        print(f"wrote {name}")

    sub = outputs["substitutions.json"]
    print("\n--- substitutions.json build report ---")
    for k, v in sub["counts"].items():
        print(f"  {k}: {v}")
    if sub["skipped"]:
        print("  redhat skipped:", [s["raw_key"] for s in sub["skipped"]])
    if sub["dropped_microsoft"]:
        print("  microsoft dropped:", [s["raw_key"] for s in sub["dropped_microsoft"]])
    if sub["excluded"]:
        print("  excluded (policy):", [e["pattern"] for e in sub["excluded"]])


if __name__ == "__main__":
    main()
