---
name: ste100-lint
description: >-
  Lints and rewrites technical prose against ste100-linter's ASD-STE100-derived
  rule set (T1 replaceable words, T2 vague/unfalsifiable claims, T3 hedges and
  optionality, T4 dangling references, T5 non-atomic sentences, T6 filler and
  weasel words, structural rules like passive voice and TBD). Use whenever the
  user is writing or editing a README, spec, design doc, release notes, PR
  description, or any technical/documentation prose and wants it tightened or
  verified -- and whenever they explicitly ask to "lint", "check my writing",
  "run STE100", "simplify this", "make this clearer", "tighten this doc", or
  "make this more precise". Also use before presenting any Markdown or CSV
  deliverable in a repo that ships ste_lint.py, since a clean run (exit 0) is
  often a project requirement.
---

# ste100-lint

A stdlib-only Python linter for technical writing quality. It is not a style
checker for typos -- it finds specific, mechanically detectable smells:
replaceable jargon, unfalsifiable vague claims, optional/hedge language,
dangling pronoun and comparative references, non-atomic (run-on/multi-clause)
sentences, and zero-information filler. Six test families (T1-T6) plus
structural checks (S7) and CSV integrity checks.

## Running it

Primary form (once the packaging change lands):

```
ste100 <path> [path ...] [options]
```

Fallback, always available in this repo:

```
ste100 <path> [path ...] [options]
```

`-X utf8` matters on Windows: file reads are always UTF-8, but without this
flag Python's stdout encoding can fall back to the console's legacy code page
on older/unconfigured setups, which can mangle or crash on non-ASCII
characters in an excerpt line (smart quotes, em dashes, non-Latin terms).
Always include it on Windows; it is a no-op elsewhere.

Paths may be files or directories (directories are walked for `*.md` and
`*.csv`). With no path, it walks the whole project from the current directory.

Key flags:

| Flag | Effect |
|---|---|
| `--format json` | Structured output for programmatic handling (see below). |
| `--profile NAME` | Force a profile (`core`, `csv`, `spec`, `design`, `vision`, `prose`) instead of auto-detecting from the path. |
| `--explain RULE_ID` | Print the fixed explanation text for a rule ID. |
| `--fix` | Apply unambiguous T1 word substitutions in place. Narrow scope -- see below. |
| `--baseline PATH` | Suppress findings already present in a baseline JSON file. For adopting on an existing codebase. |
| `--stats` | Also print `review`-tier findings (normally hidden) and per-finding detail is otherwise the same. |
| `--today YYYY-MM-DD` | Override "now" for staleness checks. |
| `--config PATH` | Use a different rule config than the repo default `the active preset (src/ste100/presets/*.json)`. |

Exit codes: `0` clean (or only warning/review findings), `1` at least one
`error`-tier finding, `2` tool failure (bad config, missing file, etc.) --
distinguish `2` from `1` when deciding whether to retry vs. fix content.

## Reading the output

Text format, one line per finding:

```
file:line:col SEVERITY TEST RULE_ID -- message
    <excerpt>
```

CSV findings add a `[row_id:field]` tag before the severity. Real captured
example:

```
tests/corpus_dirty/dirty_t3.md:6:16 ERROR T3 STE-T3-MOD-0007 -- Optional (optionality): 'if possible'.
    Ship the patch if possible...
```

Severity tiers:

- **error** -- blocks. Causes exit code 1. T1, T3, T5, T6 default to error;
  some structural rules (TBD, `must` vs `shall`, undefined/deprecated terms)
  are also error.
- **warning** -- shown by default, does not block. T2 and T4 default to
  warning; so does passive voice and bare numbers.
- **review** -- advisory only, hidden unless `--stats` is passed. Never
  blocks. Universal quantifiers, directives, and some vision-profile
  demotions land here.

Severity for a given rule can shift by profile (see "False positives" below)
-- always check the actual SEVERITY word in the output rather than assuming
from the test family.

The summary line (`smell_density`, `ari_grade`, `passive_ratio`,
`budget_violations`) is a whole-run health signal, not a per-file gate --
useful for tracking a document or PR's trend but the file-by-file findings
are what you act on.

## `--format json`

Use this whenever you need to iterate over findings programmatically instead
of parsing text lines. Real captured shape:

```json
{
  "schema_version": 1,
  "summary": {"files": 1, "errors": 8, "warnings": 1, "review": 0, ...},
  "findings": [
    {
      "file": "tests/corpus_dirty/dirty_t3.md",
      "line": 4, "column": 13,
      "rule": "STE-T3-ESC-0002", "test": "T3", "severity": "error",
      "message": "Optional (escape clause): 'as appropriate'.",
      "excerpt": "Fix the bug as appropriate...",
      "source": "INCOSE R8"
    }
  ]
}
```

Every finding carries a `source` citing the style guidance it comes from
(INCOSE, NASA SEH, MIL-STD-961E, etc.) -- useful context when deciding
whether a finding is a genuine problem or a false positive for this prose.

## `--explain RULE_ID`

When a finding is unclear, resolve the rule ID to its canonical explanation
before guessing at intent:

```
$ ste100 --explain STE-T5-ANDOR-0001
STE-T5-ANDOR-0001: T5 Non-atomic: 'and/or' is always an error (MIL-STD-961E, NASA SEH).
```

For T1/T2/T3-hedge/T6 rule IDs (bulk word-list entries, not the small fixed
enumerations), `--explain` instead dumps the underlying `src/ste100/data/*.json`
entry (pattern, suggestion, alternates, source).

## What to do about findings -- rewrite strategy per test family

The point of this tool is rewriting, not satisfying a counter. Work
test-family by test-family; do not try to fix everything with one pass.

### T1 -- replaceable words

A simpler synonym exists. The finding message already gives it:
`Replaceable: 'utilize' -> 'use'`. Apply the suggestion directly unless it
changes meaning (rare -- these are near-synonyms by construction).

- Before: `We utilize the tool to delete the row.`
- After: `We use the tool to cut the row.`

### T2 -- unfalsifiable/vague claims

A word implies a comparison or acceptance condition with no number, unit, or
named condition attached (`small`, `far`, `many`, `appropriate` used as a
threshold). Fix by adding the missing number/unit/condition, or by cutting
the claim if it isn't actually load-bearing.

- Before: `Veistra ships small teams and small games.`
- After: `Veistra ships teams of 2-5 people building games under 50,000
  words.`

### T3 -- hedges, escape clauses, optionality

Words that make a statement non-mandatory or non-committal: hedges (`may`,
`possible`, `apparently`), escape clauses (`as appropriate`, `as needed`),
open-ended clauses (`etc.`), optionality phrases (`if possible`), superfluous
infinitives (`needs to be able to`). Fix by stating the actual rule plainly
-- decide what "appropriate" means and say that instead, or delete the hedge
and make the sentence a flat statement.

- Before: `Fix the bug as appropriate, using a mouse, keyboards, etc.`
- After: `Fix the bug. Accept input from a mouse or a keyboard.`
- Before: `Ship the patch if possible. The tool needs to be able to export.`
- After: `Ship the patch by Friday. The tool exports CSV.`

### T4 -- dangling references

A pronoun (`this`, `it`, `that`, `which`) or a comparative/superlative
(`faster`, `quicker than expected`) with no antecedent or baseline stated in
the same unit. Fix by naming the noun the pronoun stood for, and by stating
the comparison's baseline explicitly.

- Before: `This breaks the build. The new loader is faster.`
- After: `The missing header breaks the build. The new loader is 40% faster
  than the old loader.`
- Note: T4 checks per-sentence/per-unit, not whole-document context. A
  pronoun with a clear antecedent one sentence earlier in the same paragraph
  can still fire -- see "false positives" below before rewriting reflexively.

### T5 -- non-atomic sentences

A sentence packs more than one instruction or fact: `and/or`, a bare oblique
slash (`input/output`), too many commas/semicolons/colons (>3), or (in the
`spec` profile) more than one `shall`. Fix by splitting into separate
sentences, each with one subject and one action.

- Before: `Save and/or load the file, and configure the input/output
  device.`
- After: `Save the file. Load the file. Configure the input device.
  Configure the output device.`
- Before (run-on, 26 words, also trips T2/T3/T6 on `far`, `many`, `too`,
  `deliberately`, `easily`): `This single sentence deliberately runs on for
  far too many words in order to cross the twenty-word core profile
  easily.`
- After: `This sentence has 26 words. The core profile budget is 20 words.`

A finding like `STE-T5-SLASH-0001` will not fire on a genuine unit or
fraction (`50 km/h`, `1/2`) -- the slash exception is built into the check,
so if it does fire the slash really is standing in for "or".

### T6 -- zero-information filler

Intensifiers (`very`, `too`), weasel words (`many`, `very`), corporate
speak (`circle back`), AI-tell hedging openers (`It is important to note
that`), nominalizations (`perform an evaluation` instead of `evaluate`), and
machine artifacts (leftover citation markers like `oai_citation:1`). Fix by
deleting filler outright, replacing corporate speak with the direct verb, and
collapsing nominalizations into their verb.

- Before: `The fix is very stable. It is important to note that many
  players report issues.`
- After: `The fix is stable. Many players report issues.` (dropped `very`
  and the throat-clearing opener; kept `many` only if you can't name a
  number -- otherwise quantify it, see T2)
- Before: `The team will perform an evaluation of the new engine.`
- After: `The team will evaluate the new engine.`

### Structural (S7)

Passive voice, bare numbers with no unit, literal `tbd` (use `TBR` with a
best estimate instead), and `must` where the project's mandatory keyword is
`shall`. Fix by naming the actor (active voice), attaching a unit or `%` to
every bare number, and using the project's actual mandatory keyword.

- Before: `The file was written by the tool. Load time is 50 right now.`
- After: `The tool writes the file. Load time is 50 ms.`

## False positives -- suppress, don't mangle

A linter that trains blind compliance produces worse writing than no linter.
When a finding is wrong for the context, do not contort correct prose to
satisfy it. In order of preference:

1. **Re-read the finding's `source`.** If the rule is well-founded but
   mis-firing on this specific sentence (e.g. T4 firing on a pronoun whose
   antecedent is one clause earlier and genuinely unambiguous to a human
   reader), it may still be worth a light rewrite for clarity -- STE100's
   whole premise is that machine-checkable proxies for ambiguity are worth
   listening to even when a human wouldn't personally be confused.
2. **Use `--profile NAME`** when a whole file is the wrong genre for its
   auto-detected profile (e.g. a narrative vision doc getting `spec`-level
   EARS/shall enforcement it was never meant to satisfy). Profiles change
   which tests run and at what severity -- `vision`, for instance, only runs
   T1 and T6 and demotes hedges to `review`.
3. **Add a `<!-- lint-profile: NAME -->` comment as the file's first line**
   to pin a profile per-file without touching the CLI invocation, e.g. in a
   pre-commit hook or CI job that always calls `ste100` the same way. The
   profile named must exist in `the active preset (src/ste100/presets/*.json)`'s `profiles` map.
4. **Use `--baseline PATH`** when adopting the linter on a large existing
   body of prose you are not rewriting today -- see `docs/integrations.md`
   for the generate/consume workflow. This is for triage, not for
   permanently hiding a real problem.

Never invent a workaround like renaming a variable, adding a code span
around plain prose, or splitting a sentence in a way that changes its
meaning, purely to dodge a finding. If the rewrite would make the sentence
worse to read, the finding is probably a genuine profile mismatch --
suppress it structurally (options 2-4), don't fight it.

## `--fix`: real, narrow scope

`--fix` applies **only** unambiguous T1 word substitutions -- a T1 rule where
the underlying data has exactly one `alts` entry. It edits the file in place
and does not report what it changed (re-run without `--fix` to see remaining
findings). It does **not** touch T2-T6, structural, or CSV findings; those
always require a human rewrite.

Two things make its scope narrower than "fixes every T1 hit":

- **Ambiguous substitutions are skipped entirely.** `utilize -> use` has one
  alt and gets fixed. `delete -> cut` has two alts (`cut`, `drop`) and is
  left alone even though it still reports as a finding after `--fix` runs --
  confirmed by testing: `We utilize the tool. Do not delete the row.` becomes
  `We use the tool. Do not delete the row.` (`delete` untouched).
- **A line with any inline code span or link is skipped in its entirety**,
  even where the flagged word sits in plain prose outside the span --
  confirmed by testing against `` We utilize the tool `expect:...`. Do not
  delete the row `expect:...`. `` (no edits made at all, because both
  sentences share a line containing backtick spans). If a fixable word is
  stuck on a line with inline code, either accept the manual fix or reflow
  the prose onto its own line first.

Always re-lint after `--fix` -- it silently leaves ambiguous and
skipped-line cases as still-failing findings, which is correct behavior, not
a bug, but easy to miss if you assume `--fix` cleared everything T1 flagged.
