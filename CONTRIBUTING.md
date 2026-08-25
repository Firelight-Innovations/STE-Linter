# Contributing to STE100-Linter

Thanks for looking at this. STE100-Linter is a small, stdlib-only Python tool, so the setup cost is low and most fixes are testable in minutes.

If you only have five minutes, the section below is the whole onboarding. The rest of this document is reference material you can read when you need it.

## Contents

- [Get started in five minutes](#get-started-in-five-minutes)
- [The test suite](#the-test-suite)
- [The stdlib-only rule, and why it is a hard rule](#the-stdlib-only-rule-and-why-it-is-a-hard-rule)
- [The supported-Python story](#the-supported-python-story)
- [How the rule data is structured](#how-the-rule-data-is-structured)
- [How rule IDs are assigned](#how-rule-ids-are-assigned)
- [The three kinds of contribution](#the-three-kinds-of-contribution)
- [Coding standards](#coding-standards)
- [Commit and PR conventions](#commit-and-pr-conventions)
- [Running CI's checks locally](#running-cis-checks-locally)
- [What happens after you open a PR](#what-happens-after-you-open-a-pr)
- [License](#license)

## Get started in five minutes

There is nothing to install beyond Python 3.9 or later. No virtualenv, no `pip install -r requirements.txt`, no build step. The linter is standard library only, and that is a hard project constraint rather than a temporary state.

```bash
git clone https://github.com/Firelight-Innovations/STE100-Linter.git
cd STE100-Linter
python -X utf8 ste_lint.py --help
```

`ste_lint.py` is a compatibility shim at the repo root. It puts `src/` on `sys.path` and calls the same entry point as the installed console script, so a bare checkout runs the real linter. The `ste100` command that the README shows exists only after you install the package; from a source checkout, use `python -X utf8 ste_lint.py` everywhere the docs say `ste100`. `PYTHONPATH=src python -X utf8 -m ste100` works too.

Pass `-X utf8` on every platform. It forces UTF-8 I/O regardless of the OS locale, which matters on Windows in particular.

Run the tests to confirm the checkout is healthy:

```bash
python -X utf8 tests/run_corpus_tests.py
```

That prints a handful of `PASS` lines and then `All corpus tests passed.`

Now make a change and watch the output move. Lint a file that is deliberately full of violations:

```bash
python -X utf8 ste_lint.py tests/corpus_dirty/dirty_t1.md
```

Every T1 finding you see comes from one entry in `src/ste100/data/substitutions.json`, read off disk at startup. Edit an entry's `suggestion` field, re-run the same command, and the new text appears in the output. No rebuild, no reinstall. That loop -- edit the JSON, re-run the linter, re-run the suites -- is most of what contributing to this project looks like.

## The test suite

There are eight harnesses under `tests/`. Each is a plain Python script with no test framework behind it. Each prints `PASS` lines as it goes and one success line at the end.

| Harness | What it guards | Success line |
| --- | --- | --- |
| `tests/run_corpus_tests.py` | The clean corpus stays silent, the dirty corpus fires the expected rule IDs, every fixed rule ID is exercised, and a whole-project run is deterministic. | `All corpus tests passed.` |
| `tests/run_suggestion_tests.py` | No T1 rule suggests a replacement that another error-tier table bans, and the `exceptions` gate still suppresses fixed compounds. | `All suggestion tests passed.` |
| `tests/run_fixer_tests.py` | `--fix` applies only unambiguous single-alternative substitutions, never deletes words, and never touches code spans. | `All fixer tests passed.` |
| `tests/run_baseline_tests.py` | `--baseline` suppresses known findings while a genuinely new violation still surfaces and still exits 1. | `All baseline tests passed.` |
| `tests/run_config_tests.py` | The engine honours its own configuration: `never_lint` matching, config-driven EARS checks, and `severity_defaults`. | `All config tests passed.` |
| `tests/run_default_preset_tests.py` | The default preset stays quiet on good, natural documentation, so a new user's first run is not a wall of errors. | `All default-preset tests passed.` |
| `tests/run_helve_tests.py` | The HELVE-ADE JSON-RPC server, driven as a real subprocess. The assertion that matters most is stdout purity, since a stray `print()` anywhere in the package corrupts the protocol stream. | `All HELVE integration tests passed.` |
| `tests/run_stress_tests.py` | Adversarial and malformed CSV degrade to findings or a clean tool-failure message, never an unhandled traceback. Also times a 200-file lint run against a 2-second budget. | `All stress tests passed.` |

Run them all before you open a PR:

```bash
python -X utf8 tests/run_corpus_tests.py
python -X utf8 tests/run_suggestion_tests.py
python -X utf8 tests/run_fixer_tests.py
python -X utf8 tests/run_baseline_tests.py
python -X utf8 tests/run_config_tests.py
python -X utf8 tests/run_default_preset_tests.py
python -X utf8 tests/run_helve_tests.py
python -X utf8 tests/run_stress_tests.py
```

CI runs every one of them on each cell of a 3-OS by 3-Python matrix. All eight are blocking.

### Why CI checks the success line as well as the exit code

For seven of the eight harnesses, `.github/workflows/ci.yml` captures stdout and asserts on two things: the exit code is 0, and the output carries the harness's exact success line.

The second assertion exists because of a real failure. The corpus-clean check once exited 0 while doing nothing at all: file discovery resolved to the wrong root, found zero files, and the loop over "every clean file" ran zero times. A green tick meant nothing. Asserting on the success line does not fully close that hole, but together with the counts each harness prints (`12 files`, `35 annotations`, `28 fixed IDs`) it makes a silently empty run visible.

`run_stress_tests.py` is asserted on its exit code only. If you add a harness, follow the seven-step pattern and give it a distinct success line.

### The two non-blocking things in CI

The `dogfood` job lints this repo's own Markdown and is `continue-on-error: true` on purpose. The shipped rule tables were calibrated for strict specification writing, and community-health prose legitimately uses words the stricter profiles reject. A failure there posts a warning annotation instead of blocking the merge. Read its output; do not contort your prose to silence it.

The `packaging` job builds a wheel, installs it, and runs `ste100` from an unrelated directory. It is blocking. It catches the one class of bug the eight harnesses cannot see: a packaging mistake that leaves the rule tables or presets out of the wheel. Every harness above runs from a source checkout, where those files are simply present.

## The stdlib-only rule, and why it is a hard rule

STE100-Linter does not take on third-party runtime dependencies. Ever. This carries over from the internal project this tool was extracted from, where it is decision D1, and it stays a hard rule here for concrete reasons:

- **No supply-chain surface.** This tool reads arbitrary files a caller points it at, including in CI pipelines and pre-commit hooks. A dependency tree is an attack surface this tool does not need.
- **No install friction.** Clone and run. No lockfile drift, no "works on my machine" from a resolver picking a different version.
- **No version-matrix explosion.** The CI matrix is already three operating systems by three Python versions. Runtime dependencies would multiply that.

A PR that adds an `import` of anything outside the standard library, or a dependency in `pyproject.toml`, will be asked to remove it, no matter how small. If you think a dependency is genuinely unavoidable, open an issue to discuss it before writing the code.

The exception is packaging and development tooling that never ships to an end user's environment. `hatchling` builds the wheel and `build` drives that in the release workflow; neither is a runtime dependency of `ste100`.

## The supported-Python story

`pyproject.toml` declares `requires-python = ">=3.9"`. CI tests 3.9, 3.11, and 3.13 on Linux, macOS, and Windows.

To check that a change stays 3.9-compatible, parse every module at that feature version:

```bash
python -X utf8 -c "
import ast, pathlib, sys
bad = 0
for p in sorted(pathlib.Path('src').rglob('*.py')):
    try:
        ast.parse(p.read_text(encoding='utf-8'), filename=str(p), feature_version=(3, 9))
    except SyntaxError as e:
        bad += 1
        print('FAIL', p, e)
print('checked', len(list(pathlib.Path('src').rglob('*.py'))), 'files,', bad, 'failures')
sys.exit(1 if bad else 0)
"
```

Also grep for standard-library names that arrived after 3.9:

```bash
grep -rnE '\b(tomllib|datetime\.UTC|graphlib)\b' src/
```

**The trap:** `feature_version=(3, 9)` catches new *syntax*. It does not catch a method that gained a new *keyword argument* in a later version, because the argument is syntactically valid at any feature version. That is not hypothetical. `Path.write_text(newline=...)` is 3.10 and later. It passed the AST check, shipped, and then made `--fix` raise `TypeError` on 3.9 across all three operating systems until the 3.9 leg of the matrix caught it.

The AST check is a fast pre-flight, not a proof. The 3.9 matrix leg is the real guard. Keep it, and when you call into the standard library, check the "Changed in version" notes in the Python docs for the method you are using.

## How the rule data is structured

Findings come from two places.

**Fixed rules** live in `src/ste100/rule_ids.py`: T4 pronoun and comparative ambiguity, T5 non-atomic sentence structure, the `S7-*` structural checks, CSV-integrity checks (`STE-CSV-*`), and word, sentence, and paragraph budgets (`STE-BUD-*`). These are small, closed enumerations, hand-assigned as module-level constants alongside an `EXPLAIN_TEXT` entry that `--explain` prints.

**Bulk word and phrase lists** live in `src/ste100/data/*.json`:

| File | Contents |
| --- | --- |
| `substitutions.json` | 424 T1 rules -- "use a plainer word" -- plus small `excluded`, `skipped`, and `dropped_microsoft` arrays that record deliberate omissions. |
| `vague.json` | 84 T2 vague and unfalsifiable terms. |
| `hedges.json` | T3 escape clauses, open-ended clauses, optionality phrases, superfluous infinitives, and 144 hedge words. |
| `filler.json` | T6 fillers and intensifiers, overused vocabulary, weasel words, and corporate speak. |
| `ai_tells.json` | T6 phrases that mark generated prose. |
| `pos_heuristics.json` | Part-of-speech heuristics the lexical checks use for disambiguation. |
| `budgets.json` | Word budgets per CSV field, per sentence, and per whole file. |

`src/ste100/paths.py` loads these off disk at `LINT_DATA_DIR` on every run. They are not generated at install time and there is no compiled form. For day-to-day work, these JSON files **are** the rule data.

### `devtools/build_lint_data.py` cannot be run

`devtools/build_lint_data.py` was the generator that produced `src/ste100/data/*.json` from a source word-list file. That source file, `handoff/prose_lint_wordlists.json`, is not in this repository and is not going to be. Running the generator here fails with `FileNotFoundError` on that path. Verified as of this writing.

Two consequences, both of which matter:

1. **Edit the JSON tables directly.** They are the source of truth. Hand-edit them the way you would any other checked-in data file.
2. **Do not try to fix the generator by re-running it.** The tables have been hand-edited since the extraction -- the T1 suggestion-collision pass documented in `docs/changelogs/t1-suggestion-collisions.md` rewrote suggestions across dozens of rules. A regeneration from a reconstructed word list would silently discard that work. If you want to restore the generator, that is a design discussion for an issue first.

`src/ste100/data/budgets.json` has a related wrinkle. Its whole-file budget targets still name paths from the monorepo this tool came from (`core/00-READ-FIRST.md`, `core/writing-standard.md`), which do not exist in a normal project. The check is inert unless a project happens to have files at those paths.

## How rule IDs are assigned

Every rule ID has the shape `STE-<test>-<CATEGORY>-<seq4>`, for example `STE-T1-SUB-0104`. The taxonomy is declared in each preset under `rule_id_taxonomy`, which lists the valid categories per test: `SUB` for T1, `VAG` for T2, `ESC`/`OPEN`/`MOD`/`SUP`/`HDG` for T3, `PRO`/`COMP` for T4, and so on.

For bulk lists, the four-digit sequence comes from sorting the word list and numbering from 0001. That is what made a rebuild from the same input produce the same bytes, back when rebuilds were possible. For fixed rules, the sequence is written by hand in `src/ste100/rule_ids.py`.

**Rule IDs are stable from v0.1.0 onward.** People pin them in `--baseline` files and in `severity_overrides` in their config. Renumbering an existing entry breaks both silently: a baseline stops suppressing the finding it was recorded for, and an override stops applying.

In practice this means three rules:

- Add new entries with the next unused sequence number in that category.
- Never reuse a retired number.
- Never renumber existing entries, even to close a gap. A gap is fine. A gap is cheaper than a broken baseline.

One deliberate exception shows the shape of the problem. `T4_COMPARATIVE_GENERIC_ID` is `STE-T4-COMP-9999` rather than a low number, because the irregular-comparative list auto-numbers upward from 0001 and a hardcoded `0011` once collided with a real word's ID. 9999 stays clear of that list at any plausible size.

## The three kinds of contribution

These have genuinely different bars, so they are worth separating.

### 1. False-positive report

This is the single most useful contribution to a linter. A rule that catches real problems but also flags common, correct usage is worse than no rule, because it teaches people to ignore the tool. You do not need to write any code to report one.

Use the **False positive** issue template and fill in all four fields:

- **The exact sentence** that was flagged, copied verbatim. Do not paraphrase. The checks are lexical and regex-driven, so a changed word can change whether a rule fires.
- **The rule ID** from the finding. Run `python -X utf8 ste_lint.py --explain STE-T3-ESC-0012` to see what that rule is meant to catch and which source it cites.
- **The profile** the file was linted under: one of `spec`, `reference`, `csv`, `docs`, `prose` under the default preset. Say so if you passed `--profile` explicitly.
- **What the correct behaviour would be.** Silence? A lower tier? A different rule? These lead to different fixes, and the answer is not always obvious from the sentence alone.

A maintainer turns a good report into a fixture in `tests/corpus_clean/`, which is the permanent guard against the same false positive returning.

### 2. New or changed rule

Three things are required, and a rule without them will be sent back.

**A citation to a real source.** Every rule in this project cites where it comes from: ASD-STE100 itself, the INCOSE requirements guide, the NASA Systems Engineering Handbook, MIL-STD-961E, the EARS templates, or Femmer et al. on requirements smells. Look at the `source` field on existing entries in `src/ste100/data/*.json` for the form. "This reads better to me" is not a source.

**A corpus fixture.** Add at least one example to the right file in `tests/corpus_dirty/` -- `dirty_t1.md`, `dirty_t3.md`, and so on -- with an inline `` `expect:YOUR-RULE-ID` `` annotation. If the term is plausibly ambiguous, also add a counterexample to `tests/corpus_clean/` that must *not* fire. The counterexample is not optional politeness. It is the thing that gets a rule accepted.

For a new fixed rule ID, `run_corpus_tests.py` fails loudly if the ID is never exercised by anything in `tests/corpus_dirty/`. That check is why the coverage line reads `28 fixed IDs all exercised` rather than a number you have to trust.

**Evidence it does not collide with an existing suggestion.** A T1 rule tells the writer to replace one word with another. If the replacement is itself banned -- as a T1 pattern, a T3 hedge, or a T6 filler term -- then following the tool's advice creates a new violation. `devtools/collision_audit.py` finds exactly that:

```bash
python -X utf8 devtools/collision_audit.py
```

It reports four things and exits 1 if any of the first three are non-empty: whole-string collisions, word-level collisions inside multi-word replacements, uses of `must` as a replacement (`shall` is the mandatory keyword here), and, as a lower-priority advisory that does not fail, replacements that land on a T2 vague term. Its module docstring still gives the old `audit/collision_audit.py` path; run it from `devtools/`.

You do not have to remember to run it. `run_suggestion_tests.py` invokes it as a subprocess and fails if it is not clean. Running it directly is just faster feedback while you iterate.

For a word-list addition, that is the whole procedure: add the entry with the next sequential ID, add the fixture, run the suites. For new check *logic* in `src/ste100/checks_*.py` or `src/ste100/engine.py`, open an issue first using the **New rule / word-list addition** template. Describe the source rule, and give example sentences it should and should not flag. New fixed IDs go in `src/ste100/rule_ids.py` beside the existing constants, with an `EXPLAIN_TEXT` entry.

### 3. Code change

Extend the suite that covers the surface you touched. The mapping is direct: `--fix` behaviour belongs in `run_fixer_tests.py`, config handling in `run_config_tests.py`, the JSON-RPC server in `run_helve_tests.py`, CSV robustness in `run_stress_tests.py`. If your change has no natural home in any of the eight, say so in the PR and explain why.

Then confirm you added no runtime dependency. This is the one review comment guaranteed to appear otherwise.

## Coding standards

These describe what the code already does. Match it rather than importing conventions from elsewhere.

**No type annotations.** There are none anywhere in `src/ste100/`, and nothing imports `typing`. Signatures are bare. Do not add annotations to a module that has none; a partially annotated codebase is worse than a consistently unannotated one.

**`.format()`, not f-strings, for messages.** Finding messages and user-facing output use `"Replaceable: '{}' -> '{}'.".format(...)` throughout. There are 62 `.format()` calls across the package. F-strings appear only in `paths.py` and `rule_ids.py`, and only for short path and ID construction. F-strings are fine on 3.9, so this is a style convention rather than a compatibility constraint -- but it is the convention, and mixed styles in one file read badly.

**Docstrings explain the module's job; comments explain *why*.** Every module opens with a one-line docstring and, where it helps, a short paragraph. Comments inside functions cite the reason the code is shaped that way, often naming the bug that motivated it. From `rule_ids.py`:

```python
# Out-of-band on purpose: t4_comp_irregular_ids auto-numbers from 0001 up
# through however many words are in t4_comparative_irregulars (12 today,
# STE-T4-COMP-0001..0012). A hardcoded low number here previously collided
# with an irregular word's real ID (0011 was also "worse"). 9999 stays clear
# of that list at any plausible size.
```

That is the house style. A comment restating the code is noise; a comment recording why an obvious-looking alternative was rejected is the thing that stops someone undoing the fix in six months. When you fix a bug, leave the reason behind in a comment.

**Module layout under `src/ste100/`.** Modules are small and single-purpose; the largest is 363 lines and the median is under 120. Checks are grouped by what they examine, not by test number: `checks_lexical.py` (T1, T3, T6 word lookups), `checks_atomicity.py` (T5 sentence structure), `checks_reference.py` (T4 dangling references), `csv_integrity.py`. Each exposes a mixin class -- `LexicalChecksMixin` and its siblings -- that `Engine` in `engine.py` composes. Supporting modules stay separate: `paths.py` for config and data loading, `discovery.py` for file walking and profile detection, `masking.py` for hiding code spans from the checks, `units.py` for the `Finding` type and excerpting, `report.py` for output formatting, `fixer.py` for `--fix`, `explain.py` for `--explain`, `cli.py` for argument parsing, `helve.py` for the JSON-RPC server.

New check logic belongs in the existing `checks_*.py` module that matches what it inspects. Add a new module only when the thing genuinely does not fit one.

**Naming.** `snake_case` for functions and variables, `CapWords` for classes, `UPPER_SNAKE` for module-level constants and compiled regexes (`PROFILE_COMMENT_RE`). A leading underscore marks a private helper (`_seq_ids`, `_build_indexes`, `_PRECEDING_WORD_RE`).

**Line length.** `pyproject.toml` sets Ruff's `line-length = 120` but puts `E501` in the ignore list, so long lines are not an error. In practice most code sits under 100 columns, with about 21 lines over 120 -- mostly the single-line `EXPLAIN_TEXT` strings, which are more readable unwrapped than split. Prose in comments and docstrings wraps at roughly 72 to 79 columns. Aim for under 100 for code and do not fight the formatter over a table of literals.

**Ruff configuration.** `pyproject.toml` selects `E`, `F`, `W`, `I`, `UP`, `B`, `C4`, `SIM` with `target-version = "py39"`. Ruff is not installed by CI and not required to contribute. If you happen to have it, `ruff check src/ tests/ devtools/` is a reasonable pre-flight.

## Commit and PR conventions

**Commits.** Short imperative summary line, blank line, then a body explaining *why* when the diff does not make it obvious. `git log --oneline` shows the existing style: "Stop --baseline from swallowing new violations", "Fix --fix crashing on Python 3.9", "Read each file once, fixing the 200-file performance budget". No conventional-commit prefixes, no ticket numbers in the subject.

**Pull requests.** One logical change each. A rule addition and an unrelated refactor are two PRs. Fill in the template; its checklist is the same set of gates a reviewer would apply by hand.

**Issues.** Use the templates. "Bug report" for the tool itself misbehaving -- a crash, a wrong exit code, bad file discovery. "False positive" for a rule firing, or failing to fire, on text that is actually fine. "New rule / word-list addition" for proposing new coverage. Usage questions and open-ended proposals go to Discussions; see [SUPPORT.md](SUPPORT.md).

## Running CI's checks locally

You can reproduce almost everything CI does without leaving your checkout.

Run the eight harnesses as listed above. That is the `test` job, minus the matrix.

Reproduce the dogfood job, remembering it is advisory:

```bash
python -X utf8 ste_lint.py .
```

Reproduce the packaging job, which is the one place a build backend is involved:

```bash
python -m pip install --upgrade build
python -m build --wheel
python -m pip install dist/*.whl
cd /tmp && ste100 --version && ste100 --explain STE-T5-ANDOR-0001
```

Do that in a scratch virtualenv rather than your system Python. It is worth running once if you touched `pyproject.toml`, `src/ste100/data/`, or `src/ste100/presets/`, since those are the paths where a wheel can end up missing files it needs. For any other change, the eight harnesses are enough.

What you cannot reproduce locally is the matrix itself: three operating systems and three Python versions, including the 3.9 leg that catches keyword-argument regressions. Open the PR and let CI do it.

## What happens after you open a PR

This project has one maintainer, so honest expectations are better than a service-level promise nobody can keep.

CI starts on its own and runs three jobs: `test` across nine matrix cells, `packaging` on Linux and Windows, and the non-blocking `dogfood` job. Expect the full run to finish in a few minutes. A red `test` or `packaging` job needs fixing before review; a red `dogfood` job is information, not a blocker.

Review is by the maintainer, via `.github/CODEOWNERS`. Turnaround is usually days rather than hours, and can be longer during a busy stretch. If a week goes by with no response, a comment on the PR is welcome and will not be read as impatience.

Small, well-scoped changes with a fixture merge quickly. A word-list addition with a corpus example and a source citation is close to a rubber stamp. A new check with novel logic will get a real design conversation, which is why the templates ask you to open an issue for that case first -- it is much cheaper to discuss the rule before you have written it.

Merged changes go into `CHANGELOG.md` under `## [Unreleased]`, and land in the next tagged release.

## License

By contributing, you agree that your contributions are licensed under the Apache License, Version 2.0 (see `LICENSE`), consistent with section 5 of that license, "Submission of Contributions". There is no separate contributor licence agreement to sign.
