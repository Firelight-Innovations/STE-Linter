# STE100-Linter

A writing linter for technical documentation, in the spirit of [ASD-STE100 Simplified Technical English](https://www.asd-ste100.org/).

It reads your Markdown and CSV and reports the specific words and sentence shapes that make technical writing imprecise — hedges that let a requirement mean anything, references with no antecedent, sentences carrying three requirements at once, and filler that survives deletion without loss.

No dependencies. No build step. One command.

```console
$ ste100 docs/
ste100: 1 files, 9 errors, 2 warnings, 4 review
smell_density=5.5 ari_grade=8.2 passive_ratio=0.0 budget_violations=0
docs/guide.md:3:20 ERROR T1 STE-T1-SUB-0104 -- Replaceable: 'utilize' -> 'use'.
    ...operator shall utilize the interface...
docs/guide.md:3:42 ERROR T1 STE-T1-SUB-0122 -- Replaceable: 'in order to' -> 'to'.
    ...the interface in order to facilitate the...
docs/guide.md:5:1 ERROR T6 STE-T6-AI-0004 -- Zero-information (AI tell, hedging_opener): 'It is important to note that'.
    It is important to note that the system may...
docs/guide.md:5:41 ERROR T3 STE-T3-HDG-0064 -- Optional (hedge): 'may'.
    ...hat the system may possibly retur...
docs/guide.md:5:69 ERROR T1 STE-T1-SUB-0231 -- Replaceable: 'and/or' -> '… or … or both'.
    ...return a value and/or an error.
```

> **Status: beta.** The rules and CLI are stable enough to use daily. Rule IDs are stable from v0.1.0 onward. See [known limitations](#known-limitations) before adopting it in blocking CI.

---

## Contents

- [Why](#why)
- [Install](#install)
- [Quick start](#quick-start)
- [What it checks](#what-it-checks)
- [Severity and exit codes](#severity-and-exit-codes)
- [Configuration](#configuration)
- [Adopting it on an existing codebase](#adopting-it-on-an-existing-codebase)
- [Integrations](#integrations)
- [Known limitations](#known-limitations)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Why

Most writing tools optimise for readability scores. This one optimises for **precision** — whether a sentence can be misread by someone who has to act on it.

That distinction matters most in documents where ambiguity has a cost: requirements, specifications, runbooks, API references, safety and compliance material. "The system should handle errors appropriately" scores well on readability and means nothing. Three separate rules fire on it here.

The rules draw on ASD-STE100 alongside the requirements-quality literature — INCOSE's guide, the NASA Systems Engineering Handbook, MIL-STD-961E, the EARS templates, and Femmer et al. on requirements smells. Every rule cites its source, and `--explain` will tell you which.

**It is not a grammar checker and not a style guide.** It will not catch a factual error or an awkward paragraph. It catches a bounded, well-defined set of ambiguity patterns, and it is deliberately quiet about everything else.

## Install

Requires **Python 3.9+**. Nothing else — the linter is standard library only, so there is no dependency tree to audit and no compilation step.

```bash
# Recommended: an isolated install that puts `ste100` on your PATH
pipx install ste100-linter

# Or with uv
uv tool install ste100-linter

# Or plain pip
pip install ste100-linter
```

Verify:

```bash
ste100 --version
```

<details>
<summary>Run from a source checkout, without installing</summary>

```bash
git clone https://github.com/Firelight-Innovations/STE100-Linter.git
cd STE100-Linter
python ste_lint.py --help
```

`ste_lint.py` is a shim that puts `src/` on the path and calls the same entry point, so every example below works with `python ste_lint.py` substituted for `ste100`.
</details>

**Windows:** `ste100` forces UTF-8 on its own output, so suggestions containing non-ASCII render correctly in PowerShell and `cmd` without `-X utf8` or a `chcp` dance.

## Quick start

```bash
ste100                      # lint the current directory tree
ste100 docs/ README.md      # lint specific paths
ste100 --stats docs/        # include advisory review-tier findings
ste100 --format json docs/  # machine-readable output
ste100 --fix docs/          # apply the unambiguous substitutions in place
```

When a finding is unclear, ask:

```console
$ ste100 --explain STE-T5-ANDOR-0001
STE-T5-ANDOR-0001: T5 Non-atomic: 'and/or' is always an error (MIL-STD-961E, NASA SEH).
```

### Reading the output

```
docs/guide.md:5:41 ERROR T3 STE-T3-HDG-0064 -- Optional (hedge): 'may'.
    ...hat the system may possibly retur...
└── file  ·  line:column  ·  severity  ·  test  ·  rule id  ·  message
```

`--format json` returns the same findings as objects, plus summary metrics (`smell_density`, `ari_grade`, `passive_ratio`, `budget_violations`), which is what you want for dashboards or custom reporting.

## What it checks

Six tests, each targeting a different way a sentence loses precision.

| Test | Name | Catches | Example |
|:--|:--|:--|:--|
| **T1** | Replaceable | A long word where a short one is exact | `utilize` → `use` |
| **T2** | Unfalsifiable | Claims with no test that could fail | `robust`, `seamless`, `user-friendly` |
| **T3** | Optional | Hedges and escape clauses that void the sentence | `may`, `as appropriate`, `if necessary` |
| **T4** | Referentially open | References with no resolvable antecedent | `it`, `this`, `faster` (than what?) |
| **T5** | Non-atomic | One sentence carrying several requirements | `and/or`, two `shall`s, four commas |
| **T6** | Zero-information | Text that survives deletion without loss | `actually`, `leverage synergies`, AI tells |

Plus **structural** checks (passive voice, bare numbers with no unit, `TBD`, undefined abbreviations, `must` where `shall` is the mandatory keyword), **budget** checks (sentence, paragraph and whole-file length), and optional **CSV integrity** checks for document-control registries.

The rule tables ship with the package: 424 substitutions, 420 filler and weasel entries, 193 hedge patterns, 84 vague terms, and 11 AI-tell phrases. Every entry carries a stable ID and a citation.

Full catalogue with worked before/after rewrites: **[docs/rules.md](docs/rules.md)**.

## Severity and exit codes

| Tier | Meaning | Shown by default | Affects exit code |
|:--|:--|:--:|:--:|
| `error` | A defect worth fixing | yes | **yes** |
| `warning` | Likely a defect; needs judgement | yes | no |
| `review` | Advisory only | no (`--stats`) | no |

| Exit code | Meaning |
|:--|:--|
| `0` | No error-tier findings |
| `1` | One or more error-tier findings |
| `2` | Tool failure (bad config, unreadable file) |

Only `error` breaks a build. Distinguish `1` from `2` in CI — the first means your docs need work, the second means the linter is misconfigured.

## Configuration

Zero config required. The shipped `default` preset is tuned for general technical documentation.

Configuration resolves in this order, first match winning:

1. `--config path/to/file.json`
2. `--preset <name>` — `default` or `veistra`
3. `ste100.json` or `.ste100.json`, found by walking up from the target
4. the shipped `default` preset

**Profiles** apply different strictness to different documents, selected by path glob, by a `--profile` override, or per file with a first-line comment:

```markdown
<!-- lint-profile: spec -->
```

Full key reference and profile semantics: **[docs/configuration.md](docs/configuration.md)**.

## Adopting it on an existing codebase

Running a new linter over years of documentation produces an unusable wall of findings. Use a baseline: record what exists today, then enforce only on new writing.

```bash
ste100 --format json docs/ > .ste100-baseline.json   # snapshot today's findings
ste100 --baseline .ste100-baseline.json docs/        # only new findings surface
```

Commit the baseline. Shrink it deliberately over time rather than all at once.

## Integrations

<details>
<summary><b>Claude Code skill</b></summary>

This repo ships a skill at `.claude/skills/ste100-lint/`. It teaches the model not just to run the linter but to *rewrite* prose in response to each test family — and, importantly, when a finding is a false positive that should be scoped rather than obeyed.
</details>

<details>
<summary><b>pre-commit</b></summary>

```yaml
repos:
  - repo: https://github.com/Firelight-Innovations/STE100-Linter
    rev: v0.1.0
    hooks:
      - id: ste100-lint
```
</details>

<details>
<summary><b>GitHub Actions</b></summary>

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.x"
- run: pip install ste100-linter
- run: ste100 docs/
```
</details>

<details>
<summary><b>VS Code</b></summary>

`examples/vscode/tasks.json` includes a `problemMatcher` that maps findings into the Problems panel.
</details>

<details>
<summary><b>HELVE-ADE</b></summary>

Installable as a HELVE Tool via `helve-tool.toml`, speaking JSON-RPC over stdio. See **[docs/helve.md](docs/helve.md)**.
</details>

More, with copy-pasteable configs: **[docs/integrations.md](docs/integrations.md)** and **[examples/](examples/)**.

## Known limitations

Stated plainly, because a linter that oversells itself gets uninstalled.

- **It is lexical, not semantic.** Rules match words and sentence shapes. It cannot tell a hedge that matters from one that does not, so some findings need your judgement. That is why `warning` and `review` tiers exist — do not treat every finding as a defect.
- **Prose registers differ.** The rules were calibrated on specification writing. Narrative documentation legitimately uses words the `spec` profile rejects. Pick the right profile rather than flattening your prose to satisfy the strictest one.
- **`--fix` is deliberately narrow.** It applies only T1 substitutions with exactly one unambiguous replacement, never deletes text, and skips lines containing code spans. Everything else is reported for a human.
- **CSV integrity checks target a specific schema.** The `STE-CSV-*` rules validate a document-control registry (`truths.csv`, `decisions-*.csv`, `terminology.csv`). They are off in the `default` preset.
- **The rule-data generator is not runnable.** `devtools/build_lint_data.py` needs a source wordlist that is not in this repo. The JSON tables under `src/ste100/data/` are the source of truth; edit them directly. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentation

| Document | Contents |
|:--|:--|
| [docs/rules.md](docs/rules.md) | Every rule, its rationale and before/after examples |
| [docs/configuration.md](docs/configuration.md) | Config keys, profiles, severity resolution |
| [docs/integrations.md](docs/integrations.md) | CLI, CI, editors, pre-commit, baselines |
| [docs/helve.md](docs/helve.md) | HELVE-ADE tool integration |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Setup, tests, proposing a rule |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

## Contributing

Contributions are welcome — especially **false-positive reports**, which are the most useful signal for a linter. There is a dedicated issue template that captures the sentence, the rule, and the profile.

```bash
git clone https://github.com/Firelight-Innovations/STE100-Linter.git
cd STE100-Linter
python tests/run_corpus_tests.py      # rule behaviour against the fixture corpus
python tests/run_suggestion_tests.py  # suggestions never point at banned words
python tests/run_fixer_tests.py       # --fix never corrupts prose
python tests/run_stress_tests.py      # adversarial input and the performance budget
```

No install or virtualenv needed to run the tests. See [CONTRIBUTING.md](CONTRIBUTING.md) for how the rule data is structured and how rule IDs are assigned.

## License

[Apache-2.0](LICENSE). Copyright 2026 Firelight Innovations.
