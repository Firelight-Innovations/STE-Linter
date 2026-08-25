# HELVE-ADE integration

This document covers installing and using `ste100-linter` as a
[HELVE-ADE](https://github.com/Firelight-Innovations/HELVE-ADE) **Tool**.
It does not cover the CLI (`ste100 ...` / `python ste_lint.py ...`); see
`docs/configuration.md` and `docs/integrations.md` for that.

## What a "Tool" is

HELVE-ADE distinguishes two ways code runs inside it. Quoting the project's
own wiki:

> "A tool is code the orchestrator finds. An app is code the orchestrator is."

An **App** lives inside the HELVE-ADE monorepo and ships with HELVE itself --
not something an external project can be. A **Tool** is an independent repo
(this one) carrying a `helve-tool.toml` manifest at its root, installed by the
user, and run by the host as a child process speaking JSON-RPC over stdio.
`ste100-linter` is a Tool: `helve-tool.toml` at the repo root declares a
`[core]` only (no UI surface -- see Limitations below), and
`src/ste100/helve.py` is the process HELVE-ADE spawns.

## Installing

HELVE-ADE installs a Tool from a local folder holding `helve-tool.toml`, via
Home's **Install App** action, which "accepts folder holding `helve-tool.toml`."
Point it at the root of a checkout of this repository. Nothing needs to be
built first -- an unbuilt source checkout is the normal state HELVE-ADE
expects a Tool repo to be in.

**Prerequisite:** a `python` (3.9+) interpreter on `PATH`. The Tool core is
pure-stdlib Python (see `pyproject.toml`'s `dependencies = []` and the
project's stdlib-only constraint); no `pip install` of this package is
required, because the launcher inserts the checkout's `src/` onto `sys.path`
itself (`bin/_launch_helve.py`, mirroring how `ste_lint.py` already does this
for the CLI). If a `pip install`-ed `ste100` package is also on that
interpreter's `PYTHONPATH`, the checkout's own `src/` still wins (it is
inserted at position 0), so the Tool always runs the code in the folder
HELVE-ADE was pointed at.

## The `bin` problem, and how it's solved here

`helve-tool.toml`'s `[core].bin` must name something directly executable,
relative to the checkout root, with no build step assumed. The protocol's own
reference tool ships a compiled Rust binary at that path
(`target/debug/helve-echo-tool`) with the Windows resolver trying `bin` then
`bin.exe`. This project has no compiled binary to point at -- it is a Python
package, and its `ste100` console-script entry point (see the `pyproject.toml`
change below) lives in whatever Python environment installs it, not in the
checkout.

The solution shipped here is a small **committed launcher**, since HELVE-ADE
is Windows-only today:

```
[core]
bin  = "bin/ste100-helve.cmd"
args = ["--helve-rpc"]
```

- `bin/ste100-helve.cmd` -- a one-line `.cmd` batch file: `python -X utf8
  "%~dp0_launch_helve.py" %*`. `%~dp0` resolves to the launcher's own
  directory regardless of the caller's working directory.
- `bin/_launch_helve.py` -- inserts `src/` onto `sys.path` (same trick as
  `ste_lint.py`) and calls `ste100.helve.main()`.

**Why `.cmd` rather than a `.py` file named directly as `bin`:** Windows does
not treat `.py` as directly executable unless the Python launcher's file
association is registered on the target machine, which is not guaranteed.
`.cmd`/`.bat` files, by contrast, are natively executable by `cmd.exe`, which
Windows process-spawning APIs invoke transparently for that extension.

**Limitations of this approach, stated plainly:**

- It depends on a host that spawns `.cmd` files correctly. HELVE-ADE's host
  process (like most Rust programs using `std::process::Command`) special-cases
  `.bat`/`.cmd` targets by wrapping them through `cmd.exe /c` -- this was
  verified against a build of this repo's launcher run directly, including
  through a piped stdin, and it works. A host that instead required a literal
  PE executable (no shell wrapping) would not be able to spawn this launcher
  at all; there is no way to satisfy that requirement without a compiled
  binary, which conflicts with this project's stdlib-only, no-build-step
  constraint.
- It requires `python` to resolve on `PATH` inside whatever environment
  HELVE-ADE's child process inherits. If a user has Python installed only via
  the Microsoft Store alias, `py.exe`, or a version manager that does not put
  a `python.exe` on the system `PATH`, the launcher will fail to start. This
  is a real, known gap; documenting the prerequisite is the mitigation used
  here, not a runtime check (a Tool core can't diagnose its own failure to
  launch).
- Manifest `version` is a static string (`0.1.0`) duplicating `pyproject.toml`;
  the two must be bumped together by hand. There is no build step to keep
  them in sync automatically.

## Required `pyproject.toml` change (not made by this change)

Per this task's constraints, `pyproject.toml` was not edited. Add this
console-script entry alongside the existing `ste100` one, so a `pip install`
of the package exposes the RPC server as its own command too (useful for
running it outside a checkout, e.g. once a proper packaged Tool release
exists):

```toml
[project.scripts]
ste100 = "ste100.cli:run"
ste100-helve = "ste100.helve:main"
```

This is optional relative to the manifest above (`bin/ste100-helve.cmd` does
not depend on it -- it runs straight from the checkout via `sys.path`
insertion), but it keeps the RPC server reachable the same way the CLI is for
anyone who `pip install`s this package directly.

## Methods exposed

All three reserved/implemented methods use JSON-RPC 2.0 framed as one object
per line (`\n`-terminated), UTF-8, over stdin/stdout. This is the exact
traffic captured from a real run of `python -X utf8 -m ste100.helve
--helve-rpc` against this repo's own fixture, `tests/helve_fixtures/dirty.md`:

### `helve/hello` (handshake)

Request:
```json
{"jsonrpc": "2.0", "id": 1, "method": "helve/hello", "params": {"protocol": 1, "session": {"projectPath": null}}}
```
Response:
```json
{"jsonrpc": "2.0", "id": 1, "result": {"id": "ste100", "version": "0.1.0", "protocol": 1}}
```
A `params.protocol` other than `1` is rejected outright (`-32602`), not
negotiated down -- per the protocol's own versioning rule ("`helve/hello`
rejects mismatch rather than negotiates down (fail-fast)"). Captured example:
```json
{"jsonrpc": "2.0", "id": 2, "method": "helve/hello", "params": {"protocol": 2, "session": {"projectPath": null}}}
{"jsonrpc": "2.0", "id": 2, "error": {"code": -32602, "message": "unsupported protocol version 2; this tool speaks protocol 1"}}
```

### `helve/shutdown` (clean exit)

Request:
```json
{"jsonrpc": "2.0", "id": 5, "method": "helve/shutdown"}
```
Response:
```json
{"jsonrpc": "2.0", "id": 5, "result": null}
```
The process exits its read loop immediately after writing this response
(well inside the protocol's 2-second grace window). Closing stdin without
ever calling `helve/shutdown` also exits the process cleanly -- the protocol
requires this ("the child exits when stdin closes") so the host is never left
with an orphaned tool process.

### `ste100/lint` (this tool's own method, under its own namespace)

HELVE-ADE defines no diagnostics/findings schema of its own -- there is no
SARIF-like or LSP-like contract, and no documented problems panel to target.
Rather than inventing a second findings shape alongside the CLI's, the RPC
result mirrors `ste100 --format json`'s `{schema_version, summary, findings}`
contract exactly; `findings[]` entries are `Finding.to_dict()` unchanged (see
`src/ste100/units.py`, `src/ste100/report.py`).

Params: `path` (required, string -- a file or directory, absolute or
relative), `preset` (optional string), `profile` (optional string, forces the
profile for every linted file the way `--profile` does), `root` (optional
string, controls what paths are reported relative to), `stats` (optional
bool, default `false` -- when `false`, `review`-tier findings are omitted,
matching `--format json` without `--stats`).

Request:
```json
{"jsonrpc": "2.0", "id": 2, "method": "ste100/lint", "params": {"path": "tests/helve_fixtures/dirty.md"}}
```
Response (captured verbatim, only `run_at` varies between runs):
```json
{"jsonrpc": "2.0", "id": 2, "result": {"schema_version": 1, "run_at": "2026-08-25T05:36:11Z", "summary": {"files": 1, "errors": 1, "warnings": 0, "review": 0, "smell_density": 1.0, "ari_grade": 2.41, "passive_ratio": 0.0, "budget_violations": 0}, "findings": [{"file": "dirty.md", "line": 3, "column": 4, "rule": "STE-T1-SUB-0104", "test": "T1", "severity": "error", "message": "Replaceable: 'utilize' -> 'use'.", "excerpt": "We utilize the tool to co...", "suggestion": "use", "source": "vale_redhat.simple_words"}]}}
```
Missing/invalid `params.path` (or any other param typed wrong) is `-32602`,
never a crash:
```json
{"jsonrpc": "2.0", "id": 3, "method": "ste100/lint", "params": {}}
{"jsonrpc": "2.0", "id": 3, "error": {"code": -32602, "message": "ste100/lint requires params.path"}}
```
An unknown method is `-32601`:
```json
{"jsonrpc": "2.0", "id": 4, "method": "unknown/method"}
{"jsonrpc": "2.0", "id": 4, "error": {"code": -32601, "message": "no such method: unknown/method"}}
```

### Notifications

A message with no `"id"` key is a notification: it is processed (or its
failure logged to stderr) but never gets a response, per the protocol.

### Error codes emitted

`-32700` malformed JSON, `-32600` malformed request shape, `-32601` unknown
method, `-32602` bad/missing params (including a protocol mismatch on
`helve/hello`, and a `ste100/lint` path that does not exist), `-32603` an
unexpected exception inside a handler (logged to stderr with its type and
message; the process stays alive and keeps serving). `-32000`/`-32001`/
`-32002` are host-generated (crash/timeout/handshake failure) and are never
emitted by this process.

## Limitations (stated honestly)

- **No UI surface.** `helve-tool.toml` omits `[frontend]` and `[[surface]]`
  entirely. A core-only Tool is explicitly supported by the protocol. Adding
  a UI would require a JS/TS frontend built against `@helve-ade/bridge` (React
  or otherwise), and there is presently no documented diagnostics-display
  contract on the HELVE-ADE side to build a "problems panel" against --
  building one now would mean guessing at a contract that doesn't exist yet.
  This is left as future work once such a contract is documented.
- **HELVE-ADE itself is Windows-only and pre-alpha.** Everything above was
  validated on Windows, matching the platform HELVE-ADE currently targets.
- **Tools run unsandboxed.** Quoting the protocol docs directly: "A tool's
  core is a child process holding the user's full privileges, and nothing in
  this protocol constrains it." Installing this Tool -- like installing any
  HELVE-ADE Tool -- runs its code with the user's own privileges; nothing in
  the shell limits what it can do. This linter only reads the files it is
  asked to lint and (under `--fix`, CLI-only, not exposed over RPC) rewrites
  them in place; it makes no network calls and needs none. That is a property
  of what this code happens to do, not a guarantee the protocol enforces.
- **`[permissions]` is not a real mechanism yet.** The manifest schema
  reserves a `[permissions]` table, but the protocol docs describe it as
  "Reserved; currently ignored" and, on the "May Still Move" list, "opaque
  `toml::Value`, not yet enforced." `helve-tool.toml` omits it entirely here
  rather than declaring anything speculative against a schema that does not
  exist yet -- unknown keys under a table that does get a real schema later
  could otherwise turn into a parse error on upgrade.
- **`ste100/lint` runs single-threaded, synchronously.** A large directory
  lint blocks the JSON-RPC read loop until it completes; there is no
  cancellation or progress-reporting method. For the sizes of document tree
  this linter targets this has not been a problem in testing, but a very
  large corpus could make a host's 30-second default RPC timeout
  (`@helve-ade/bridge`'s `invoke()`) a real concern.
