#!/usr/bin/env python3
"""Launcher shim invoked by bin/ste100-helve.cmd -- HELVE-ADE's [core].bin target.

Why this exists: helve-tool.toml's [core].bin must point at something
directly executable, relative to the checkout root, with nothing built or
installed as a prerequisite ("nothing required built at install time;
unbuilt checkout is normal development state" -- HELVE-ADE docs). This repo
is a pure-stdlib Python package with no compiled binary, so `bin` cannot
point at a native .exe the way the reference echo-tool's does.

This shim solves it the same way ste_lint.py already solves the analogous
problem for the CLI: insert src/ onto sys.path so `ste100` is importable
straight from a source checkout, with no `pip install` step required, then
hand off to ste100.helve.main(). Kept as its own file (rather than inlining
python -c in the .cmd) so it is plain, testable Python.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ste100.helve import main  # noqa: E402  (path setup must precede the import)

if __name__ == "__main__":
    sys.exit(main())
