# Security Policy

## Scope: what this tool actually does

STE100-Linter is a stdlib-only Python command-line tool. It reads local
Markdown and CSV files that you point it at (or that it discovers by
walking the current directory) and prints findings to stdout. It has no
network access, no telemetry, and no runtime dependencies to carry a
transitive vulnerability.

That means the realistic attack surface here is narrow and specific:
**malformed or adversarial input files** -- a crafted Markdown or CSV file
that causes a crash, hang, excessive memory use, or (in principle, though
nothing in this codebase does file writes outside of `--fix` on files you
explicitly targeted) unintended file modification when run against it.
`tests/run_stress_tests.py` already fuzzes the CSV-integrity checker against
adversarial input as a baseline, but a case it doesn't cover is exactly the
kind of thing worth reporting here.

If you're looking for "can a malicious dependency compromise this tool" --
there are no runtime dependencies (see `CONTRIBUTING.md`), so that class of
issue doesn't apply.

## Supported Versions

This project has not yet made a tagged release. Once it does, security
fixes will target the latest released minor version; this table will be
updated accordingly at that point.

| Version | Supported |
| ------- | --------- |
| main (pre-release) | :white_check_mark: |

## Reporting a Vulnerability

Please report security issues privately, not in a public GitHub issue.

Use **[GitHub Security Advisories](https://github.com/Firelight-Innovations/STE100-Linter/security/advisories/new)**
for this repository ("Security" tab -> "Report a vulnerability"). This opens
a private channel with maintainers before anything is disclosed publicly.

Please include:

- The version or commit you're running (`git rev-parse --short HEAD` if
  you're on a checkout, since there's no `--version` flag yet).
- The input file (or a minimized version of it) that triggers the issue,
  and the exact command line.
- What happened versus what you expected (crash, hang, resource exhaustion,
  unexpected file write, etc.).

We aim to acknowledge new reports within **5 business days** and to provide
an initial assessment (confirmed / not applicable / needs more information)
within **14 days**. This is a small open-source project maintained without
dedicated security staff, so please treat these as good-faith targets rather
than a contractual SLA.

If you haven't heard back after 14 days, it's fine to follow up on the same
advisory thread.

## Disclosure

We'll credit reporters (unless you'd prefer to stay anonymous) in the
advisory and in `CHANGELOG.md` once a fix ships. We don't currently run a
paid bug bounty program.
