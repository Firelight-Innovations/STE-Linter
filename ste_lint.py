#!/usr/bin/env python3
"""Compatibility shim: `python ste_lint.py` still works from a source checkout.

The linter is now the installed `ste100` package (src/ste100/), exposed as the
`ste100` console script. This wrapper stays so existing invocations, CI steps
and the test harnesses keep working without an install step.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ste100.cli import run  # noqa: E402  (path setup must precede the import)

if __name__ == "__main__":
    run()
