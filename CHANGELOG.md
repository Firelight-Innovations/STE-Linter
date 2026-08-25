# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project intends to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
once the first tagged release ships.

## [Unreleased]

### Added

- Imported the ASD-STE100 writing-quality linter (`ste_lint.py`, `lint/`,
  `lint_data/`, `tests/`, `audit/`, `build_lint_data.py`) as its own
  standalone repository, split out of the Veistra monorepo's `tools/`
  directory.
- Community health files: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
  (Contributor Covenant 2.1), `SECURITY.md`, `NOTICE`.
- `.github/workflows/ci.yml`: cross-platform CI (Linux/macOS/Windows x
  Python 3.9/3.11/3.13) running the corpus test suite, a non-blocking
  Markdown dogfooding step, and a non-blocking stress-test job that tracks
  the known-failing 200-file performance budget.
- `.github/workflows/release.yml`: skeleton PyPI release workflow using
  Trusted Publishing (OIDC), gated behind a `release` environment and a
  packaging layout (`pyproject.toml`) landing separately.
- Issue templates (`bug_report.yml`, `false_positive.yml`,
  `rule_request.yml`, `config.yml`) and a pull request template.

### Fixed

- `lint/paths.py` and `lint_config.json` hardcoded a `<repo-root>/tools/`
  install location left over from the monorepo, so config and rule-data
  loading failed once this tree became its own repository. `REPO_ROOT`
  (where the linter's own config/data live) and `ROOT` (the tree being
  linted -- now the caller's current working directory) are now separate.

### Known issues

- `tests/run_stress_tests.py`'s 200-file performance check budgets 2
  seconds; it has been observed taking as long as ~4s on some hardware
  since the standalone-repo path fix (previously masked because file
  discovery found zero files and returned instantly). Tracked as a
  non-blocking CI job rather than silenced by widening the budget.
- `build_lint_data.py` and `lint_data/budgets.json`'s whole-file-budget
  targets still reference paths from the original Veistra monorepo
  (`handoff/prose_lint_wordlists.json`, `core/00-READ-FIRST.md`, etc.)
  that don't exist in this repository. See `CONTRIBUTING.md` for the
  current workaround (edit `lint_data/*.json` by hand).
