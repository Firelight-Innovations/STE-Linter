# Configuring the linter

The linter reads one JSON config file. Two presets ship inside the package, in
`src/ste100/presets/`:

- **`default`** -- the generic config for any project. Start here.
- **`veistra`** -- a byte-for-byte copy of the original private-monorepo config, kept so that
  project's behaviour (its document-control profiles, its CSV-registry schema, its
  `never_lint` list) stays reproducible. Use it if you are that project, or if you want a
  fully worked example with every feature turned on, including CSV-integrity checking.

```
ste100 --preset default [PATH ...]
ste100 --config path/to/my-config.json [PATH ...]
```

With no flags, config resolves in this order, first match winning:

1. `--config <path>`
2. `--preset <name>`
3. `ste100.json` or `.ste100.json`, found by walking up from the target
4. the shipped `default` preset

## The profile system

Every file that gets linted is assigned a **profile**, which controls which tests run against
it and what its word/ARI budgets are. Detection, verified against
`src/ste100/discovery.py:detect_profile()`, resolves in this exact order:

1. **`--profile NAME`** on the command line -- overrides everything, for every targeted file.
2. **An inline comment** on the file's first line: `<!-- lint-profile: NAME -->`. Only honored
   if `NAME` is a profile that actually exists in the config (`config["profiles"]`) -- an
   unknown name is silently ignored and detection falls through to the next step.
3. **`profile_order` glob match.** The config's `profile_order` list is walked in order; for
   each profile name in it, each of that profile's `path_globs` entries is tested against the
   file's path (relative to the current working directory, forward slashes) with Python's
   `fnmatch.fnmatch()`. First match wins.
4. **`prose`**, unconditionally, if nothing above matched.

### `fnmatch` gotchas that shaped this preset's globs

`path_globs` are matched with `fnmatch.fnmatch()`, not a real glob library, and not
gitignore-style patterns. Three behaviors are easy to get wrong when writing your own globs, all
verified by directly testing `fnmatch.fnmatch()`:

- **`*` matches `/` too.** Unlike shell globs, `fnmatch` does not treat `/` specially, so
  `core/*.md` matches `core/x.md` **and** `core/deeply/nested/x.md`. A pattern like
  `*requirements*/**` matches `requirements/x.md`, `docs/requirements/x.md`, and (because it's a
  substring match) `myrequirements/x.md` too -- broad by design, but worth knowing.
- **`**/` requires a literal separator before it can match.** `**/*.md` does **not** match a
  root-level `README.md` -- there's no `/` character in that path for the pattern to consume.
  This is why `the default preset`'s `prose` profile lists `path_globs: ["**/*.md"]` but that
  is genuinely inert: `detect_profile()` falls back to `prose` unconditionally at the end
  regardless of whether `prose`'s own globs match, so it doesn't matter that a bare `**/*.md`
  glob would miss root files. If you add a *new*, non-fallback profile and want it to match
  both a root-level file and nested ones, use a single leading `*` (e.g. `*spec*/**`), not a
  leading `**/`.
- **Case sensitivity depends on the OS you run the tool on**, because `fnmatch.fnmatch()`
  normalizes case via `os.path.normcase` -- case-insensitive on Windows, case-sensitive
  everywhere else. `*requirements*.md` matches `REQUIREMENTS.md` on Windows but not on Linux/
  macOS. `the default preset`'s globs use lowercase and a few common all-caps root filenames
  (`REQUIREMENTS.md`, `SPEC.md`, `REFERENCE.md`, `API.md`) explicitly for this reason -- add
  your own casing variants if your project's convention differs.

### How `never_lint` matches

`src/ste100/discovery.py:is_never_lint()` matches on **path segments**, and the entry's shape
decides how far it reaches:

- A **single-segment** entry such as `node_modules/` excludes a directory of that name
  *anywhere* in the tree -- both a root-level `node_modules/` and a nested
  `packages/foo/node_modules/`.
- A **multi-segment** entry such as `tests/corpus_dirty/` is anchored at the root, so it
  excludes only that specific path.

Matching is on whole segments, so a `build/` entry excludes the `build/` directory without
touching a file named `build.md`.

Earlier versions tested a raw string prefix, so `node_modules/` excluded only a root-level
directory and a monorepo's nested `packages/*/node_modules/` was walked and linted. If you
added explicit nested entries to work around that, they are now redundant.

Also note: `never_lint` only governs automatic discovery (a directory walk, or a whole-project
scan with no path arguments). A file you name explicitly on the command line is always linted,
even if it matches a `never_lint` prefix -- this is intentional, so the test suite can point the
tool at its own deliberately-dirty fixtures.

## Profiles in `the default preset`, and why

The original config had five profiles wired to one company's document tree: `core`
(`core/*.md`), `csv`, `spec` (`docs/spec/**`), `design` (`docs/design/**`), `vision`
(`docs/vision/**`), and `prose` as fallback. None of the first four generalize -- they assume a
specific document-control taxonomy no other project has.

`the default preset` collapses this into four profiles chosen around what any technical
writer actually has: general prose/docs, formal requirements/specs, and
reference/API docs -- plus CSV, since the tool has real (if partly private-schema) CSV support.

- **`prose`** -- the fallback, and what general documentation gets. Kept exactly as
  permissive as the original: T1/T3/T6 (replaceable words, optionality, zero-information) stay
  at `error`; everything else is capped to `review` by the profile-wide cap in
  `Engine.severity()` (see `docs/rules.md`). This is deliberately the safest profile to run
  against a whole existing repo for the first time -- it will not fail CI on prose-quality
  nitpicks, only on the three checks that are almost never false positives.
- **`spec`** -- formal requirements and specifications: shall-statements, EARS templates,
  atomicity enforcement. The name is conventional, not load-bearing: EARS,
  indefinite-article and zero-`shall` checks fire for whichever profiles list `ears` (or
  `ears_review`) in their `tests`, so you can name your own profile `requirements` and it
  will still get them. The zero-`shall` and multi-`shall` checks need `ears`; the
  indefinite-article and EARS-template checks accept either `ears` or `ears_review`.
- **`reference`** -- reference/API documentation: parameter tables, enumerations, code samples.
  Runs the same test set as `spec` minus EARS (reference material is not made of
  shall-statements).
- **`csv`** -- generic CSV cell linting (T1/T3/T6 word-level checks plus per-field word
  budgets), with `csv_integrity` deliberately left out of `tests` (see below).

There is no analog of the original `design` or `vision` profiles. `design` (SME-facing design
docs, EARS at `review` instead of `error`) and `vision` (aspirational docs, only T1/T6 checked)
both encode editorial policy specific to that project's document-control process, not a
generally-applicable document type -- a project that wants that distinction can add a profile
for it in a custom config using `spec`/`prose` as a starting point.

### Should the generic `csv` profile run `csv_integrity`? No.

`csv_integrity` (`STE-CSV-0001`..`STE-CSV-0010`) validates a bespoke registry schema --
`truths.csv` / `decisions-*.csv` / `timeline.csv` / `terminology.csv` with specific columns like
`superseded_by`, `linked_truth_ids`, `review_by` -- that is Veistra's own document-control
process, not something any other project has. Running it by default against an arbitrary CSV
would either find nothing (the common case: `kind_of()` in `src/ste100/csv_integrity.py` only
recognizes those four literal filenames, so an unrelated CSV is mostly invisible to it) or,
worse, produce a confusing false positive if a generic CSV happens to have a `review_by` column
with past dates (the one check inside `csv_integrity.py` that isn't gated by filename kind).
Neither outcome is useful to a new user, so `the default preset`'s `csv` profile omits it.

**What generic CSV linting is left, and why it's worth keeping:** T1 (replaceable words), T3
(optionality/hedges), T6 (zero-information), and CSV field word budgets, run cell-by-cell
against every column of every row (see `src/ste100/units.py:build_csv_units()`). This still catches
real problems -- a spreadsheet of feature descriptions or a decision log full of "we should
probably utilize a faster approach" benefits from the same wordiness/hedge/filler checking as
prose does, without requiring any particular column schema. It's a strict subset of the checks
that already ran on Markdown, applied to CSV cells instead of sentences, so keeping it on by
default costs nothing and finds real issues.

**Important caveat, verified by running the tool:** turning off `csv_integrity` in a profile's
`tests` list is currently cosmetic, not a real gate -- `ste_lint.py`'s `main()` calls
`check_csv_integrity()` unconditionally for every discovered `.csv` file, without checking any
profile's `tests` list at all. Confirmed: running `the default preset` (whose `csv` profile
excludes `csv_integrity`) against a dirty `decisions-*.csv` fixture still produced `STE-CSV-*`
findings.

### `never_lint` defaults

Replaced the original's private paths (`handoff/`, `docs/audits/`, `docs/handoffs/`, `.pi/`)
with directories any project might have that a linter run at the repo root should never walk
into: VCS metadata (`.git/`, `.hg/`, `.svn/`), dependency directories (`node_modules/`,
`vendor/`, `.venv/`, `venv/`, `env/`), build output (`build/`, `dist/`, `target/`, `site/`,
`_build/`, `out/`), common tool caches (`__pycache__/`, `.pytest_cache/`, `.mypy_cache/`,
`.ruff_cache/`, `.tox/`, `.cache/`, `.next/`, `.nuxt/`), and `CHANGELOG.md` (commonly
auto-generated by release tooling, not hand-authored prose worth linting). This list is a
starting point, not exhaustive -- add your own project's generated/vendored paths. Remember the
path-prefix limitation above: nested instances of these directories are not excluded.

### `abbreviation_allowlist`

The original list (`STE`, `ARI`, `EARS`, `POS`, ...) was tuned to this tool's own internal
vocabulary, which a new user's documents will never contain -- so the `S7-ABBR` check would
flag nothing useful and instead just miss real abbreviations. `the default preset` broadens
this to abbreviations common across technical writing generally: identifiers and data formats
(`ID`/`IDs`, `URL`, `URI`, `JSON`, `XML`, `YAML`, `CSV`, `HTML`, `CSS`, `SQL`, `PDF`), web/infra
terms (`HTTP`/`HTTPS`, `DNS`, `SSH`, `TLS`, `SSL`, `TCP`, `IP`), engineering-process terms
(`API`, `CLI`, `SDK`, `VM`, `CI`, `CD`, `DB`, `OS`, `UI`, `UX`, `CPU`, `GPU`, `RAM`, `IO`),
document conventions (`FAQ`, `TODO`, `README`, `RFC`, `UUID`, `JWT`, `REST`, `UTF`, `ISO`), and
`AI`/`ML`. This is still a starting point -- every project has its own domain vocabulary (a
robotics project has `PID`, `IMU`, `ROS`; a finance project has `KYC`, `AML`) and should extend
this list rather than expect it to be complete. Populating a `terminology.csv` with
`type=ACRONYM` rows achieves the same suppression per-project without editing the shared config
(see `src/ste100/engine.py:index_terminology()`); the allowlist is the zero-setup floor.

### Budgets, thresholds, and `ari_target`: what's real and what isn't

`the default preset` keeps the same numeric shape as the original, but several of these keys
turned out to be entirely unread by the code -- verified by grepping every Python file for each
key name, not by inspection alone:

- **`thresholds.smell_density_max` / `passive_ratio_max` / `paragraph_sentences_max` are dead.**
  `src/ste100/report.py` computes and reports `smell_density` and `passive_ratio` as informational
  metrics on every run (visible in the summary line), but nothing compares them against these
  configured thresholds -- there is no pass/fail gate tied to them. `paragraph_sentences_max` is
  doubly dead: the actual, enforced paragraph budget (6 sentences, `warning`) comes from
  `src/ste100/data/budgets.json`'s `paragraph_budget.sentences`, a completely separate value that
  this config key does not drive.
- **Per-profile `ari_target` is dead.** `src/ste100/discovery.py:ari_grade()` computes a single,
  whole-corpus Automated Readability Index, reported once in the run summary
  (`report.py:build_summary()`) -- there is no per-profile comparison against a target anywhere
  in the codebase; the key is parsed into the config dict and never read again.
  `the default preset` sets `spec`/`reference` to `10` (a commonly-cited plain-language target
  for technical writing) and leaves `prose`/`csv` at `null`, matching the shape of the original,
  but this is aspirational bookkeeping for a feature that does not exist yet, not a live
  setting.

These keys are kept (with generic, internally-consistent values, and an in-place `_note` where
one didn't already exist as a convention in this config) so the schema stays stable and so a
maintainer who wires up either feature later inherits sane defaults rather than stale
company-specific numbers. Other keys that are parsed but never drive behaviour:
`profile_override_comment`, `budgets_file`, `rule_id_taxonomy`,
`t5_oblique_slash_exceptions_regex`, `s7_tbd_pattern`, and top-level `schema_version`.

## Full config key reference

| Key | Read by code? | Meaning / allowed values | Default in `the default preset` |
|---|---|---|---|
| `schema_version` | No (`report.py` uses its own fixed `SCHEMA_VERSION=1` constant) | Informational | `1` |
| `profiles` | Yes | `{name: {path_globs: [glob,...], tests: [str,...], ari_target: number\|null, note?: str}}`. `tests` values `"T1".."T6"` are read by `ste_lint.py`'s dispatcher; `"csv_integrity"` gates the CSV registry checks and `"ears"`/`"ears_review"` gate the EARS, indefinite-article and zero-`shall` checks; `"S7"`/`"structural"` are accepted but not consulted (structural checks ride along with T5) -- `"budgets"` (CSV-field budgets) is the one non-`T*` value that is actually read. `ari_target` is currently dead (see above). | `spec`, `reference`, `csv`, `prose` -- see above |
| `profile_order` | Yes | Ordered list of profile names to try glob-matching, before the unconditional `prose` fallback | `["spec", "reference", "csv", "prose"]` |
| `profile_override_comment` | No -- the actual regex is hardcoded in `src/ste100/discovery.py` (`PROFILE_COMMENT_RE`) | Documents the literal syntax `<!-- lint-profile: NAME -->` | same string, for documentation only |
| `never_lint` | Yes | Forward-slash paths. A single-segment entry (`node_modules/`) excludes that directory name anywhere; a multi-segment entry (`tests/corpus_dirty/`) is anchored at the root. Not a glob -- see above. | see "`never_lint` defaults" above |
| `severity_defaults` | Yes | Default tier per rule name. Beaten by `severity_overrides` (including a `profile: "*"` entry); falls back to the call-site literal for rules not listed. See `docs/rules.md`. | kept in sync with the call-site literals |
| `severity_overrides` | Yes | List of `{rule, profile: name\|list\|"*", tier, source?, note?}`. First matching non-`"*"` profile entry for a rule wins outright; a `"*"` entry only sets a tentative answer. Read by `Engine.severity()`. | see `the default preset`; simplified from the original by dropping the `design`/`vision`/`core` conditional branches that no longer have a matching profile |
| `universal_quantifiers` | Yes, but only into an unused regex | Words like `all`/`every`/`none` -- built into `self.uni_quant_re` in `engine.py` but never matched against any text by any check | same as original (generic already) |
| `nasa_arm_directives` | Yes, but only into an unused regex | Same situation as `universal_quantifiers`, for words like `note`/`consider`/`make sure` | same as original |
| `t4_pronouns` | Yes | Pronoun list for T4's antecedent check | unchanged (already generic English) |
| `t4_comparative_irregulars` | Yes | Irregular comparative/superlative words checked for a stated baseline | unchanged |
| `t4_comparative_min_stem_length` | Yes | Minimum word-stem length before the generic `-er`/`-est` regex considers a match (cuts false positives on short words) | `4`, unchanged |
| `t4_comparative_exclusions` | Yes | Words/phrases excluded from the generic comparative check (e.g. `"test"`, `"other than"`) | unchanged |
| `t5_combinators` | Yes | Combinator words counted for the `spec`-profile second-combinator check | unchanged |
| `t5_punctuation_density_max` | Yes | Max `,;:` count per sentence before `punctuation_density` fires | `3`, unchanged |
| `t5_punctuation_chars` | Yes | Which punctuation characters count toward the density check | `[",", ";", ":"]`, unchanged |
| `t5_oblique_slash_exceptions_regex` | No -- the actual oblique-slash check uses a hardcoded regex in `checks_atomicity.py` | Documents an intended exception for slashes in units/fractions | unchanged, dead |
| `s7_units` | Yes | Lowercase unit words that suppress the bare-number check | unchanged (already generic) |
| `s7_tbd_pattern` | No -- the `tbd` check uses a hardcoded `\btbd\b` regex | Documents the pattern | unchanged, dead |
| `budgets_file` | No -- `src/ste100/paths.py` always loads `src/ste100/data/budgets.json` directly, regardless of this value | Documents where budgets live | unchanged, dead |
| `thresholds` | No -- see above | Aspirational quality gates | unchanged numerically, annotated as dead |
| `abbreviation_allowlist` | Yes | Abbreviations that never trigger `S7-ABBR` | broadened, see above |
| `rule_id_taxonomy` | No -- purely descriptive | Documents the `STE-<test>-<CATEGORY>-<seq4>` ID format | unchanged; `STE-` prefix intentionally not renamed, see `docs/rules.md` |

## Severity tiers and exit codes

Three tiers, resolved per-finding by `Engine.severity()` (full precedence in `docs/rules.md`):

- **`error`** -- shown by default; if any `error`-tier finding exists, `ste_lint.py` exits `1`.
- **`warning`** -- shown by default; does not affect the exit code.
- **`review`** -- hidden by default; shown only with `--stats`. Does not affect the exit code.

A tool-level failure (bad config, unreadable file, crash inside a check) exits `2` and prints to
stderr, distinct from a clean run that simply found `error`-tier issues (exit `1`).

## Writing your own config

Start from `the default preset` and copy it, since it satisfies every key the code requires at
load time (`src/ste100/engine.py:_build_indexes()` will raise `KeyError` on load if any of
`t4_pronouns`, `t4_comparative_irregulars`, `t4_comparative_exclusions`,
`t4_comparative_min_stem_length`, `t5_combinators`, `t5_punctuation_density_max`,
`t5_punctuation_chars`, `s7_units`, `universal_quantifiers`, `nasa_arm_directives`, or
`abbreviation_allowlist` is missing; `discovery.py` and `ste_lint.py` additionally require
`profiles`, `profile_order`, and `never_lint`). Everything else in the table above is optional
at load time.

The two changes most projects will actually want to make:

1. **Add or adjust `profiles[name].path_globs`** to match your own directory layout. Remember
   the `fnmatch` gotchas above -- test with the small Python snippet
   `python -c "import fnmatch; print(fnmatch.fnmatch('your/path.md', 'your-glob'))"` before
   committing to a pattern.
2. **Extend `abbreviation_allowlist`** with your project's own vocabulary, or populate a
   `terminology.csv` with `type=ACRONYM` rows for the same effect without touching the shared
   config (see `docs/rules.md`'s structural-checks section).

Verify any config you write actually loads and produces sane output before trusting it:

```
ste100 --config your_config.json --stats path/to/one/file.md
```

`--stats` is worth using while developing a config, since it surfaces `review`-tier findings
that are otherwise silent -- including any place the `prose` profile-wide cap is quietly
demoting a check you expected to run at a higher tier.
