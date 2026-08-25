# Support

This page routes each question to its channel. One maintainer reads them all; the correct channel saves a round trip.

## Where to go

| You have | Go to |
| --- | --- |
| A rule that fired on text that is correct | [False positive](https://github.com/Firelight-Innovations/STE-Linter/issues/new?template=false_positive.yml) |
| A crash, a wrong exit code, or bad file discovery | [Bug report](https://github.com/Firelight-Innovations/STE-Linter/issues/new?template=bug_report.yml) |
| A word, phrase, or check the linter does not cover yet | [New rule / word-list addition](https://github.com/Firelight-Innovations/STE-Linter/issues/new?template=rule_request.yml) |
| A usage question, or an open-ended proposal | [Discussions](https://github.com/Firelight-Innovations/STE-Linter/discussions) |
| A security vulnerability | [SECURITY.md](SECURITY.md) -- report it privately, never in an issue |

## Before you open an issue

**Read the finding first.** `--explain` prints what a rule catches and the source it cites:

```bash
ste100 --explain STE-T3-ESC-0012
```

From a source checkout, use `python -X utf8 ste_lint.py --explain STE-T3-ESC-0012`.

**Check whether the answer is configuration.** Severity tiers, profiles, and excluded paths are all configurable. A rule that reads as strict for your documents is often the wrong profile applied to the file. See [docs/configuration.md](docs/configuration.md).

**A false-positive report is the contribution this project values highest.** Four fields make a report usable: the exact sentence, the rule ID, the profile, and the correct behaviour. The template asks for each. All four go into the regression test that stops the same false positive from returning.

## Documentation

- [README](README.md) -- what the tool does, install, quick start.
- [Wiki](https://github.com/Firelight-Innovations/STE-Linter/wiki) -- orientation, CLI reference, configuration, integrations.
- [docs/rules.md](docs/rules.md) -- every rule and its source.
- [docs/configuration.md](docs/configuration.md) -- profiles, severity tiers, presets.
- [docs/integrations.md](docs/integrations.md) -- pre-commit, GitHub Actions, GitLab CI, VS Code.
- [docs/helve.md](docs/helve.md) -- the HELVE-ADE JSON-RPC server.
- [CONTRIBUTING.md](CONTRIBUTING.md) -- how to change the tool.

## Response times

This is a small open-source project with one maintainer. Issues and pull requests get a response in days, not hours.

Security reports have their own targets in [SECURITY.md](SECURITY.md): acknowledgement within five business days, a first assessment within fourteen. Treat every figure here as a good-faith target, not a guarantee. A follow-up comment after a quiet week is welcome.
