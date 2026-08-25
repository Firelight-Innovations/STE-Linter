## What this changes and why

<!-- One or two sentences. Link the issue this closes, if any. -->

## Testing

<!--
All eight harnesses are required to pass locally before review; CI re-runs
them across the 3-OS by 3-Python matrix. Each prints a distinct success line
that CI greps for, because a harness once exited 0 without running any checks.
See CONTRIBUTING.md, "The test suite".
-->

- [ ] `python -X utf8 tests/run_corpus_tests.py` -- "All corpus tests passed."
- [ ] `python -X utf8 tests/run_suggestion_tests.py` -- "All suggestion tests passed."
- [ ] `python -X utf8 tests/run_fixer_tests.py` -- "All fixer tests passed."
- [ ] `python -X utf8 tests/run_baseline_tests.py` -- "All baseline tests passed."
- [ ] `python -X utf8 tests/run_config_tests.py` -- "All config tests passed."
- [ ] `python -X utf8 tests/run_default_preset_tests.py` -- "All default-preset tests passed."
- [ ] `python -X utf8 tests/run_helve_tests.py` -- "All HELVE integration tests passed."
- [ ] `python -X utf8 tests/run_stress_tests.py` -- "All stress tests passed." (includes a 200-file, 2-second performance budget; paste the timing if it failed only on that check)
- [ ] If this adds or changes a rule: I added at least one example to `tests/corpus_dirty/` (should flag) and, if the term is plausibly ambiguous, a counterexample in `tests/corpus_clean/` (should not flag)
- [ ] If this adds a rule ID: it is covered by the corpus coverage check (`run_corpus_tests.py` fails loudly if a fixed rule ID in `src/ste100/rule_ids.py` is never exercised)
- [ ] If this changes a T1 suggestion: `python -X utf8 devtools/collision_audit.py` is clean

## Checklist

- [ ] No new runtime dependencies (stdlib only -- this project's hard constraint)
- [ ] Rule and severity changes cite the ASD-STE100 rule or another source already used here (NASA SEH, MIL-STD-961E, INCOSE, Femmer et al.), not personal preference
- [ ] Rule IDs added, never renumbered or reused (people pin them in baselines and config overrides)
- [ ] Updated `CHANGELOG.md` under `## [Unreleased]`
- [ ] Docs updated if behavior, flags, or the rule set changed
