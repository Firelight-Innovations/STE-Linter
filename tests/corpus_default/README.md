# Example Tool

Example Tool is a small command-line program that checks configuration
files for common mistakes. It reads a file, runs a set of checks, and
prints a short report.

## Installation

You can install the program from the package index:

```
pip install example-tool
```

## Usage

Run the command against a file, for example `example-tool config.yaml`. The
program will print a short summary when it finishes. If a file has a
syntax error, it exits with a non-zero status.

Most projects only need the default settings. You may pass `--strict`
when you want stricter checks, or `--quiet` when you want less output.
Flags like `--stats` show extra detail that most people skip.

The program is fast, so a typical run finishes in under a second. It
does not change any file unless you pass `--fix`.

## Contributing

Bug reports and small patches are welcome. Please open an issue before
you start a large change, since that gives maintainers a chance to
comment early. Tests should pass before you open a pull request.

## License

This project is under the MIT license.
