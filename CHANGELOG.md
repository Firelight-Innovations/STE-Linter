# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project intends to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once the first tagged release ships.

## [Unreleased]

### Added

- The ASD-STE100 writing-quality linter, split out of the Veistra monorepo's
  `tools/` directory into its own standalone repository.
- Installable packaging: `pyproject.toml`, a `src/ste100/` layout, a `ste100`
  console script, and `python -m ste100`. Installs with `pipx`, `uv` or `pip`
  and has no runtime dependencies. `python ste_lint.py` still works from a
  source checkout via a shim.
- New CLI options: `--preset` (choose a shipped configuration), `--root` (the
  tree finding paths are reported against), and `--version`. A project-local
  `ste100.json` or `.ste100.json` is now discovered by walking up from the
  target, so a configured project needs no flags at all.
- `presets/default.json`: a generic configuration for any repository. The
  original monorepo configuration is preserved verbatim as the `veistra`
  preset.
- Documentation: `README.md`, `docs/rules.md` (the full rule catalogue with
  worked before/after rewrites), `docs/configuration.md`, and
  `docs/integrations.md`.
- Integrations: a Claude Code skill (`.claude/skills/ste100-lint/`),
  `.pre-commit-hooks.yaml`, a VS Code task with a `problemMatcher`, and
  copy-pasteable CI configurations under `examples/`.
- Community health files: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
  (Contributor Covenant 2.1), `SECURITY.md`, `NOTICE`.
- `.github/workflows/ci.yml`: cross-platform CI (Linux/macOS/Windows ×
  Python 3.9/3.11/3.13) running all four test suites, plus a packaging job
  that builds the wheel, installs it, and runs `ste100` from an unrelated
  directory to prove the rule tables ship with the package.
- `.github/workflows/release.yml`: PyPI release workflow using Trusted
  Publishing (OIDC), gated behind a `release` environment.
- Issue templates (`bug_report.yml`, `false_positive.yml`,
  `rule_request.yml`) and a pull request template.
- `tests/run_fixer_tests.py`: regression tests for `--fix`, which rewrites
  the user's files and so has a higher bar than the reporting path.

### Changed

- **Rule IDs are now `STE-*` rather than `VEI-*`.** `VEI` stood for Veistra,
  the private monorepo this tool came from. The prefix appears in every
  finding, in `--explain`, and in the JSON output.
- `--fix` no longer applies a substitution whose replacement is empty. Those
  rules mean "delete this phrase", which needs human judgement; they are
  still reported.

### Fixed

- The linter could not run outside the monorepo at all: `paths.py` resolved
  its install location three parents up and expected `<root>/tools/`. Where
  the linter's own rule data lives is now separate from the tree being
  linted. The same assumption was baked into the configuration, both test
  harnesses, and the CSV fixture manifest — and `corpus_clean` was passing
  vacuously against zero discovered files.
- **`--fix` silently deleted words.** 14 T1 rules carry an empty suggestion,
  and the fixer auto-applied any rule with a single candidate, producing
  ungrammatical output such as ` important that the operator selects the  of
  report.`
- **Mojibake on Windows.** The rule tables contain non-ASCII characters, but
  output used the console codepage, so suggestions printed as `?` unless the
  user passed `-X utf8`. The CLI now forces UTF-8 on its own output.
- **93 T1 rules suggested a replacement that was itself banned** by an
  error-tier rule, so following the tool's own advice produced a new finding.
- The `exceptions` field existed in the rule data but was never read, so
  fixed compounds such as "pull request" were flagged as the verb "request".
  It is now honoured by both the checker and `--fix`.
- **The 200-file performance budget now passes** (4.03s → 1.42s against a 2s
  budget). Every Markdown file was being read twice: once to lint it, and
  again to compute the readability metric over the whole tree.
- **`--baseline` silently swallowed new violations.** Findings were matched by
  `(file, rule, message)` presence alone, so a file that already had one
  `utilize` suppressed every later `utilize` added to it — which defeats the
  point of adopting the linter on an existing codebase. Suppression is now by
  occurrence count. Line numbers are deliberately still not part of the key: a
  baseline that invalidates itself whenever anyone edits above a finding would
  be worse than none.
- `--format`, `--fix`, `--explain`, `--baseline`, `--stats` and `--today` had
  no `--help` text, or leaked an internal specification reference.

### Known issues

- The shipped rule tables were calibrated for strict specification writing
  and are noisy on ordinary documentation prose. The repository's own
  dogfooding CI job is non-blocking for this reason.
- `devtools/build_lint_data.py` cannot run here: it reads a source wordlist
  (`handoff/prose_lint_wordlists.json`) that is not part of this repository.
  The JSON tables under `src/ste100/data/` are the source of truth, and a
  re-run of the generator would clobber them. See `CONTRIBUTING.md`.
- Several configuration keys are parsed but never read, including
  `severity_defaults`, `thresholds` and the per-profile `ari_target`.
- `devtools/audit/` and `devtools/weekly_audit.py` implement a
  document-control audit over a bespoke CSV registry schema specific to the
  originating monorepo. They are retained but are not general-purpose.
