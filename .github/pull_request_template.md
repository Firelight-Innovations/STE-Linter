## What this changes and why

<!-- One or two sentences. Link the issue this closes, if any. -->

## Testing

<!-- Both suites are required to pass locally before review; CI re-runs them across the OS/Python matrix. -->

- [ ] `python -X utf8 tests/run_corpus_tests.py` passes (prints "All corpus tests passed.")
- [ ] `python -X utf8 tests/run_stress_tests.py` passes (the 200-file performance check is a known flaky/slow check on some hardware -- note if it failed only on that check, and paste the timing)
- [ ] If this adds or changes a rule: I added at least one example to `tests/corpus_dirty/` (should flag) and, if relevant, `tests/corpus_clean/` (should not flag)
- [ ] If this adds a rule ID: it's covered by the corpus coverage check (`run_corpus_tests.py` fails loudly if a fixed rule ID in `src/ste100/rule_ids.py` is never exercised)

## Checklist

- [ ] No new runtime dependencies (stdlib only -- this project's hard constraint)
- [ ] Rule/severity changes reference the ASD-STE100 rule or other cited source (NASA SEH, MIL-STD-961E, INCOSE, etc.), not just personal preference
- [ ] Updated `CHANGELOG.md` under `## [Unreleased]`
- [ ] Docs updated if behavior, flags, or the rule set changed
