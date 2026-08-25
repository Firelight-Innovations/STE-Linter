# Contributing to STE100-Linter

Thanks for looking at this. STE100-Linter is a small, stdlib-only Python tool, so the setup cost is low and most fixes are testable in minutes.

## Setup

There is nothing to install beyond Python itself.

```
git clone https://github.com/Firelight-Innovations/STE100-Linter.git
cd STE100-Linter
python -X utf8 ste_lint.py --help
```

CI tests Python 3.9, 3.11, and 3.13 on Linux, macOS, and Windows. Use `python -X utf8` on every platform -- it forces UTF-8 I/O regardless of the OS locale, which matters on Windows in particular.

## The stdlib-only rule, and why it's a hard rule

STE100-Linter does not take on third-party runtime dependencies. Ever. This carries over from the internal Veistra project this tool was extracted from, where it's decision D1, and it stays a hard rule here for concrete reasons:

- **No supply-chain surface.** This tool reads arbitrary files a caller points it at (including in CI pipelines and pre-commit hooks). A dependency tree is an attack surface this tool doesn't need.
- **No install friction.** `git clone` and run. No `pip install -r requirements.txt`, no lockfile drift, no "works on my machine" from a resolver picking a different version.
- **No version-matrix explosion.** The CI matrix is already 3 OSes x 3 Python versions. Runtime dependencies would multiply that.

A PR that adds an `import` of anything outside the standard library (or a `pyproject.toml`/`setup.cfg` dependency) will be asked to remove it, no matter how small. If you think a dependency is genuinely unavoidable, open an issue to discuss it before writing the code.

The one exception is packaging/dev tooling that never ships to an end user's environment (for example `build` for producing a release artifact in CI) -- that's not a runtime dependency of `ste100` itself.

## Running the tests

Two independent suites. Both must pass before you open a PR; CI runs both across the full OS/Python matrix (the corpus suite is required to pass on every cell; the stress suite's performance check is tracked as a known-flaky non-blocking job -- see below).

```
python -X utf8 tests/run_corpus_tests.py
python -X utf8 tests/run_stress_tests.py
```

`run_corpus_tests.py` prints `All corpus tests passed.` and exits 0 on success. It checks, in order:

1. Every file in `tests/corpus_clean/` produces zero errors and zero warnings.
2. Every file in `tests/corpus_dirty/` fires the rule(s) named in its inline `` `expect:RULE_ID` `` annotations (Markdown), plus every entry in `tests/corpus_dirty/csv_findings_manifest.json` (for CSV-integrity and budget findings, which have no line to attach an inline annotation to).
3. Every fixed rule ID in `lint/rule_ids.py` is exercised at least once by something in `tests/corpus_dirty/` (two documented exceptions are noted in the harness itself: `STE-CSV-0009` aliases to `STE-BUD-0003`, and `STE-BUD-0004` is exercised by a direct `Engine` call instead of a fixture, because it's keyed to exact real project paths).
4. Determinism: running the whole project twice produces byte-identical output apart from the `run_at` timestamp.

`run_stress_tests.py` throws adversarial/malformed CSV at the CSV-integrity checker (must degrade to findings or a clean tool-failure message, never an unhandled traceback) and times a 200-file lint run against a 2-second budget. That budget check is currently known to fail on some hardware (~4s observed) after a path-resolution fix that made file discovery actually work standalone -- see the CI workflow comments in `.github/workflows/ci.yml` for how that's handled (a separate, non-blocking job, not a widened budget and not deletion).

## How the rule data works

Findings come from two places:

- **Fixed rules** (`lint/rule_ids.py`): T4 (pronoun/comparative ambiguity), T5 (non-atomic-sentence structure: multiple `shall`, `and/or`, punctuation density, EARS conformance), the `S7-*` structural checks (bare numbers, articles, passive voice, `tbd`, abbreviations, terminology, `must` vs `shall`), CSV-integrity checks (`STE-CSV-*`), and word/sentence/paragraph budgets (`STE-BUD-*`). These are small, closed enumerations, hand-assigned directly in the source.
- **Bulk word/phrase lists** (`lint_data/*.json`): T1 substitutions (424 entries as of this writing -- "use a plainer word"), T2 vague/unfalsifiable terms, T3 hedges (escape clauses, open-ended clauses, optionality phrases, superfluous infinitives), and T6 filler/intensifiers/weasel words/corporate speak/nominalizations/AI-tell phrases. Each entry carries a stable `STE-<test>-<CATEGORY>-<seq4>` ID (see `lint_config.json`'s `rule_id_taxonomy`), assigned by sorting the word list and numbering from 1 so a rebuild from the same input is byte-identical.

`ste_lint.py` loads `lint_data/*.json` straight off disk at `lint/paths.py:LINT_DATA_DIR` (the repo root's `lint_data/`, not something generated at install time) -- so for day-to-day use, those JSON files **are** the rule data; you don't need to regenerate them to change what the linter catches.

**Known gap, please read before relying on it:** `build_lint_data.py` (which is supposed to regenerate `lint_data/*.json` from a source word-list file) and `lint_data/budgets.json`'s whole-file-budget targets still reference paths from the original Veistra monorepo this tool was extracted from (`handoff/prose_lint_wordlists.json`, `core/00-READ-FIRST.md`, `core/writing-standard.md`, `truths.csv`, `decisions-*.csv`, `timeline.csv`, `terminology.csv`) that don't exist in this standalone repo. Running `python -X utf8 build_lint_data.py` here fails with `FileNotFoundError` today. Until someone fixes that, **edit the `lint_data/*.json` files by hand** for word-list changes (see below) rather than trying to run the generator.

## Proposing a new rule

Two very different kinds of change, and they get very different scrutiny:

**Adding a word/phrase to an existing list (T1/T2/T3/T6)** -- the common case. Low risk if you also supply a counterexample.

1. Open `lint_data/<the right file>.json` and add your entry to the appropriate array (for example a T1 substitution needs `pattern`, `suggestion`, `alts`, and a `source`; see the existing entries for the shape).
2. Give it the next sequential ID in that category -- do not reuse or skip numbers, and do not renumber existing entries (that breaks anyone with a saved baseline referencing the old IDs, since `--baseline` matches on file/rule/message).
3. Add at least one example sentence to `tests/corpus_dirty/` (in the file for that test, for example `dirty_t1.md`) with an `` `expect:YOUR-NEW-ID` `` annotation, and, if the term is plausibly ambiguous, a counterexample in `tests/corpus_clean/` that should *not* fire.
4. Run both test suites. `run_corpus_tests.py`'s rule-ID-coverage check will fail if your new ID isn't exercised.

**New check logic** (new Python in `lint/checks_*.py` or `lint/engine.py`) -- higher bar. Open an issue first (use the "New rule / word-list addition" issue template) describing the ASD-STE100 rule, or other cited source (NASA SEH, MIL-STD-961E, INCOSE, etc. -- see the `source` fields already in `lint_data/*.json` and `severity_overrides` in `lint_config.json`), that the check implements, plus example sentences it should and shouldn't flag. New fixed rule IDs go in `lint/rule_ids.py` next to the existing `T4_*`/`T5_*`/`S7_*` constants, with an `EXPLAIN_TEXT` entry.

In both cases: false positives are the recurring failure mode for a lexical linter. A rule that catches real problems but also flags common, correct usage will get reverted, so a counterexample is not optional -- it's the thing that gets a rule accepted.

## Commit and PR conventions

- Commit messages: short imperative summary line, blank line, body explaining *why* if the change isn't self-evident from the diff. Look at `git log` for the existing style.
- One logical change per PR. A rule addition and an unrelated refactor should be two PRs.
- Fill out the PR template -- it checks both test suites, plus (for rule changes) that you added corpus examples and cited a source.
- Use the issue templates: "Bug report" for tool bugs, "False positive" for a rule firing (or not firing) incorrectly on valid text, "New rule / word-list addition" for proposing new coverage.

## License

By contributing, you agree that your contributions are licensed under the Apache License, Version 2.0 (see `LICENSE`), consistent with section 5 of that license ("Submission of Contributions").
