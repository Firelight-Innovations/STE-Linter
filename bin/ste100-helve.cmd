@echo off
rem HELVE-ADE Tool core entry point (see helve-tool.toml [core].bin).
rem
rem HELVE-ADE is Windows-only today and spawns this file directly as the
rem tool's core process, with --helve-rpc appended (helve-tool.toml
rem [core].args). It just hands off to the real implementation: a small
rem Python shim that puts src/ on sys.path (so no `pip install` of this
rem package is required -- an unbuilt checkout is enough) and runs the
rem stdlib-only JSON-RPC server in src/ste100/helve.py.
rem
rem Prerequisite: a `python` (3.9+) on PATH. -X utf8 matches the flag
rem ste_lint.py and the CLI use, so stdout/stderr default to UTF-8 even
rem under a non-UTF-8 Windows console codepage.
python -X utf8 "%~dp0_launch_helve.py" %*
