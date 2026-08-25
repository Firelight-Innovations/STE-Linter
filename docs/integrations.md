# Integrations

How to run `ste100`/`ste_lint.py` from the command line on all three OSes,
wire it into pre-commit, CI, VS Code, adopt it incrementally on an existing
codebase, and use it as a Claude Code skill.

Every command below was actually run in this repo's worktree while writing
this doc, except where marked otherwise.

## A note on the command name

This doc shows `ste100 <args>` as the primary form. That assumes a
`console_scripts` entry point named `ste100` from a packaging change
(`pyproject.toml`) landing alongside this doc, in parallel with this work.
**That entry point did not exist yet in this worktree at the time this doc
was written** -- every `ste100 ...` command shown here is the intended
post-packaging form, not something verified to run as `ste100` in this
repo. The fallback form, `ste100 <args>`, is what was
actually executed to produce every captured output sample in this doc and
in `.claude/skills/ste100-lint/SKILL.md`. If `ste100` is not yet on your
PATH, use the fallback form (from the directory containing `ste_lint.py`).

## Command line

### macOS / Linux

```bash
ste100 docs/README.md
# or, before the package ships:
python3 -X utf8 ste_lint.py docs/README.md
```

`-X utf8` is a harmless no-op on macOS/Linux (they default to UTF-8
already) -- include it anyway so the same command works everywhere,
including Windows.

### Windows -- PowerShell

```powershell
ste100 .\docs\README.md
# or:
ste100 .\docs\README.md
```

### Windows -- cmd.exe

```bat
ste100 docs\README.md
:: or:
ste100 docs\README.md
```

### Why `-X utf8` matters on Windows

`ste_lint.py` always reads source files as UTF-8 (`encoding="utf-8"` is
hardcoded in `src/ste100/paths.py` and `ste_lint.py`) -- file reading is never the
problem. The risk is **stdout**: Python's default `sys.stdout.encoding` on
Windows can fall back to the console's legacy code page (e.g. cp1252/cp437)
rather than UTF-8, depending on your Python version, `PYTHONUTF8`, and OS
locale settings. A finding's excerpt line can contain non-ASCII characters
(smart quotes, em dashes, non-Latin terms in your prose), and printing those
through a non-UTF-8 stdout can mangle the output or raise
`UnicodeEncodeError` and abort the run. `-X utf8` forces Python's UTF-8 mode
(PEP 540) for stdio regardless of the console's code page.

We verified the read side is always safe -- linting a file containing an
em dash and curly quotes produced identical, correctly-rendered output with
and without `-X utf8` in this environment (PowerShell 5.1 and `cmd.exe`,
including with the code page forced to `437`), because this environment's
system locale is already configured for UTF-8 end to end. **That does not
mean the flag is unnecessary** -- it means this particular machine already
has the safe configuration `-X utf8` guarantees explicitly. On a Windows
machine with an unconfigured/legacy locale, the same run can fail without
it. Treat `-X utf8` as always-on and free, not as something to verify per
machine.

## pre-commit

This repo publishes hook definitions in its own `.pre-commit-hooks.yaml`:
`ste100-lint` (check only, blocks the commit on any ERROR-tier finding) and
`ste100-lint-fix` (opt-in, applies `--fix`'s narrow T1 auto-fixes and
re-stages).

In a *consumer* repo's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/Firelight-Innovations/STE100-Linter
    rev: v0.1.0  # pin to a real tag/commit once one is cut
    hooks:
      - id: ste100-lint
```

A full sample is in `examples/config/pre-commit-config.sample.yaml`.

`language: python` in the hook definition means pre-commit installs this
repo as a Python package into an isolated venv per-hook and resolves
`entry: ste100` from that venv -- it does not require the linter to already
be installed on the developer's machine, but it does depend on the
`console_scripts` entry point actually being declared in `pyproject.toml`
(see "A note on the command name" above). Both hooks set `types_or:
[markdown, csv]` and `pass_filenames: true`, matching the file types
`ste_lint.py` itself ever walks or lints.

## CI

### GitHub Actions

A full sample workflow is in `examples/github-actions/ste100-lint.yml`. The
core step:

```yaml
- name: Run linter
  run: ste100 .
```

Exit code `1` (error-tier findings) fails the job by default, which is what
you want for a lint gate; exit code `2` (tool failure -- bad config, missing
file) also fails the job, which is also correct.

### GitLab CI

A full sample job is in `examples/gitlab-ci/ste100-lint.gitlab-ci.yml`:

```yaml
ste100-lint:
  image: python:3.12-slim
  stage: test
  script:
    - pip install ste100-linter
    - ste100 .
```

## VS Code

`examples/vscode/tasks.json` defines two tasks ("STE100: Lint workspace" and
"STE100: Lint current file") wired to a `problemMatcher` that parses
`ste_lint.py`'s text output straight into the Problems panel.

The output format, from `src/ste100/report.py`, is:

```
file:line:col SEVERITY TEST RULE_ID -- message
    <excerpt>
```

with CSV findings inserting a `[row_id:field]` tag before the severity:

```
file:0:1 [ROW_ID:field] SEVERITY TEST RULE_ID -- message
```

Real captured examples (from `ste100 tests/corpus_dirty/dirty_t3.md`
and `tests/corpus_dirty/decisions_dirty.csv` in this repo):

```
tests/corpus_dirty/dirty_t3.md:6:16 ERROR T3 STE-T3-MOD-0007 -- Optional (optionality): 'if possible'.
    Ship the patch if possible...
tests/corpus_dirty/decisions_dirty.csv:0:1 [DEC-DIRTY-001:superseded_by] ERROR csv_integrity STE-CSV-0001 -- CSV integrity: status=SUPERSEDED needs a resolving superseded_by.
```

The `tasks.json` regex:

```
^(.*):(\d+):(\d+)(?:\s+\[[^\]]+\])?\s+(ERROR|WARNING|REVIEW)\s+(\S+)\s+(\S+)\s+--\s+(.*)$
```

groups: `1` file, `2` line, `3` column, `4` severity, `5` test family, `6`
rule ID (used as VS Code's "code"), `7` message. The optional
`(?:\s+\[[^\]]+\])?` absorbs the CSV row/field tag without capturing it.

This regex is checked against both hand-picked cases and a live linter run
in `examples/vscode/test_problem_matcher.py` -- run
`python examples/vscode/test_problem_matcher.py` to re-verify it if
`src/ste100/report.py`'s format ever changes. All 7 cases pass, and every finding
line from a live run of `dirty_t3.md` matches while its summary line and
excerpt lines correctly do not.

One caveat: VS Code's `problemMatcher` maps matched severity text to
`error`/`warning`/`info`. `REVIEW`-tier findings only ever appear when you
add `--stats` to the task's `args` -- the sample tasks do not do this, so
you will only ever see `ERROR`/`WARNING` lines in the Problems panel, which
VS Code maps as expected. If you add `--stats`, `REVIEW` text will not match
either recognized keyword and VS Code's fallback behavior for an
unrecognized severity string should not be relied on -- verify locally
before depending on it.

## Adopting on an existing codebase: `--baseline`

`--baseline PATH` filters out any finding whose `(file, rule, message)`
triple already appears in the baseline JSON's `findings` list -- **not** by
line/column, so the baseline survives unrelated edits elsewhere in the file
that shift line numbers. It **does** key off the message text, which
includes the specific matched word/phrase (e.g. `"Optional (hedge):
'many'"`), so a *different* occurrence of the same rule with a different
matched word is treated as new, not baselined away.

Workflow, verified in this repo:

1. Generate the baseline from the current state of the codebase. Use
   `--format json --stats` so the baseline captures every tier (matters if
   you ever turn on `--stats` for day-to-day runs later; findings not in the
   baseline file are never suppressed):

   ```
   ste100 --format json --stats . > .ste100-baseline.json
   ```

2. Commit `.ste100-baseline.json`.

3. Run day-to-day (locally, pre-commit, CI) with the baseline applied:

   ```
   ste100 --baseline .ste100-baseline.json .
   ```

   Every finding present when the baseline was captured is suppressed;
   anything new -- a new file, a new sentence, a new violation -- still
   fails the run.

4. Chip away at the baselined findings over time by fixing prose and
   re-generating the baseline (step 1) to shrink it, or by deleting entries
   from it directly.

Confirmed end to end in this repo: generating a baseline from
`tests/corpus_dirty/dirty_t4.md` (3 findings) and re-running with
`--baseline` against the same file dropped it to 0 errors/0 warnings/0
review and exit code 0.

## Using it as a Claude Code skill

`.claude/skills/ste100-lint/SKILL.md` teaches Claude how to run the linter,
read every output format, resolve unclear findings with `--explain`, rewrite
prose per test family (T1-T6, structural) with worked before/after examples,
and when to suppress a finding (via `--profile` or a
`<!-- lint-profile: NAME -->` comment) instead of mangling correct prose to
satisfy it. It triggers automatically when Claude is writing/editing
technical prose, or on explicit requests like "lint this", "run STE100",
"check my writing", or "simplify this". No separate setup is needed beyond
having the skill file present in the repo Claude Code is running in.
