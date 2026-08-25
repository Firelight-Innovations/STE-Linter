# Configuration Guide

This guide explains the fields the tool reads from a config file. Read
it once, then keep it nearby for reference.

## Fields

- `name` -- a short label for the project.
- `strict` -- when true, the tool treats every warning as a failure.
- `timeout` -- how many seconds a single check can run before it stops.

You can set any field, or leave it out and let the tool fall back to
its default. Some teams like to pin every field explicitly, and that
is a fine choice too.

## Common questions

**Can I run the tool without a config file?** Yes. The tool will use
its built-in defaults, so a bare run still produces a useful report.

**What happens if a field is spelled wrong?** The tool warns about the
unknown field but keeps running, since one typo should not stop a
whole build.

**Does the tool support comments in the config file?** Not yet. That
is a planned feature; track it on the project's issue tracker.

## Example

```yaml
name: sample-project
strict: true
timeout: 30
```

That example turns on strict mode and gives each check a thirty
second budget. It works well for small and medium projects alike.
