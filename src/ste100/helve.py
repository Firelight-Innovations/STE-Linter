"""JSON-RPC (stdio) server that exposes the linter as a HELVE-ADE Tool core.

Protocol: HELVE-ADE Tool Protocol v1, "Transport A" (docs/tool-protocol.md at
https://github.com/Firelight-Innovations/HELVE-ADE). Newline-delimited JSON
over stdio:

    {"jsonrpc":"2.0","id":1,"method":"...","params":{...}}\\n
    {"jsonrpc":"2.0","id":1,"result":{...}}\\n

stdout carries protocol traffic ONLY -- every diagnostic goes to stderr. A
stray print() on stdout corrupts the whole session for the host, the same way
an unreconfigured stdout previously mojibake'd this tool's own CLI output on
Windows (see cli.py's _force_utf8_output); do not reintroduce either bug here.

Reserved methods this core implements: helve/hello (handshake) and
helve/shutdown (clean exit). The linter itself is exposed as ste100/lint,
under our own namespace per the protocol's convention (no diagnostics schema
is defined by HELVE itself, so the result shape mirrors --format json's
{schema_version, summary, findings} contract rather than inventing a second
one).

Run standalone: `python -X utf8 -m ste100.helve --helve-rpc`
Any other invocation (or none) prints a usage message to stderr and exits
non-zero -- matching the reference echo-tool's documented behaviour for a
tool core run outside the host.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .csv_integrity import check_csv_integrity, load_all_csvs
from .discovery import detect_profile, discover_files
from .engine import Engine
from .paths import SCHEMA_VERSION, load_json, load_lint_data, resolve_config, set_root
from .report import build_summary
from .units import build_csv_units, build_markdown_units

TOOL_ID = "ste100"
PROTOCOL_VERSION = 1

# JSON-RPC 2.0 reserved error codes (tool-protocol.md). -32000/-32001/-32002
# are host-generated (process crash/timeout/handshake failure) and must never
# be emitted by this process.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _log(message):
    """The only sanctioned destination for anything that is not protocol JSON."""
    print(message, file=sys.stderr, flush=True)


def _force_utf8_stdio():
    """Force UTF-8 on stdin/stdout/stderr regardless of the console codepage.

    Same fix as cli.py's _force_utf8_output (Windows defaults to cp1252),
    extended to stdin because this module reads NDJSON requests as well as
    writing NDJSON responses. newline="\\n" keeps line framing exact -- the
    transport is one JSON object per '\\n', not '\\r\\n'.

    stdin decodes as utf-8-sig rather than plain utf-8: some Windows-side
    writers (PowerShell's default pipeline encoding among them) prepend a
    UTF-8 byte-order mark, which is otherwise indistinguishable from bytes
    json.loads rejects as a parse error on the very first message. utf-8-sig
    strips a leading BOM if present and decodes identically to utf-8 if not,
    so this is strictly more permissive, never less correct. Only stdin gets
    this treatment -- stdout must stay plain utf-8, since a BOM is not
    protocol traffic either.
    """
    if hasattr(sys.stdin, "reconfigure"):
        try:
            sys.stdin.reconfigure(encoding="utf-8-sig", newline="\n")
        except (AttributeError, OSError, ValueError):
            pass
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", newline="\n")
            except (AttributeError, OSError, ValueError):
                pass  # a redirected/replaced stream we do not control


class RpcError(Exception):
    """Raised by a method handler to produce a JSON-RPC error response."""

    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


def _write(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.stdout.write("\n")
    sys.stdout.flush()


def _result(msg_id, result):
    _write({"jsonrpc": "2.0", "id": msg_id, "result": result})


def _error(msg_id, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    _write({"jsonrpc": "2.0", "id": msg_id, "error": err})


# ---- method handlers -------------------------------------------------------

def _handle_hello(params):
    if not isinstance(params, dict):
        raise RpcError(INVALID_PARAMS, "helve/hello requires an object params")
    protocol = params.get("protocol")
    if protocol != PROTOCOL_VERSION:
        # tool-protocol.md, Versioning Rule: "helve/hello rejects mismatch
        # rather than negotiates down." A host speaking any protocol other
        # than the one we implement gets a hard error here, not a best-effort
        # downgrade.
        raise RpcError(
            INVALID_PARAMS,
            "unsupported protocol version {!r}; this tool speaks protocol {}".format(
                protocol, PROTOCOL_VERSION))
    return {"id": TOOL_ID, "version": __version__, "protocol": PROTOCOL_VERSION}


def _handle_shutdown(params):
    return None


def _run_lint(target_path, preset=None, profile_override=None, explicit_root=None):
    """Lint one file or directory; return (summary_dict, findings_list).

    This mirrors cli.py main()'s pipeline (discovery -> config/engine build ->
    per-file units -> checks -> CSV integrity -> summary) so the RPC surface
    and the CLI produce the same findings for the same input. It is a
    deliberate parallel implementation rather than an import from cli.py:
    cli.py is being edited concurrently elsewhere, main() is not factored
    into a reusable function, and it also does argv parsing, --fix and
    --baseline handling this RPC method does not need.
    """
    target = Path(target_path)
    if not target.is_absolute():
        target = (Path(explicit_root) if explicit_root else Path.cwd()) / target
    target = target.resolve()
    if not target.exists():
        raise RpcError(INVALID_PARAMS, "path not found: {}".format(target_path))

    # No explicit root: lint a single file relative to its own directory, or a
    # directory relative to itself -- so findings report short relative paths
    # instead of '../../..' climbs out of some unrelated cwd.
    if explicit_root:
        set_root(explicit_root)
    elif target.is_dir():
        set_root(target)
    else:
        set_root(target.parent)

    try:
        config = load_json(resolve_config(cli_config=None, cli_preset=preset))
    except FileNotFoundError as e:
        raise RpcError(INVALID_PARAMS, str(e))
    data = load_lint_data()
    engine = Engine(config, data)

    today = datetime.now(timezone.utc).date()

    targets = discover_files([str(target)], config)
    if not targets:
        empty_summary = {
            "files": 0, "errors": 0, "warnings": 0, "review": 0,
            "smell_density": 0.0, "ari_grade": 0.0, "passive_ratio": 0.0,
            "budget_violations": 0,
        }
        return empty_summary, []

    target_rel_set = {rel for rel, _ in targets}
    # Same whole-project-view rationale as cli.py main(): CSV cross-file id
    # resolution needs every CSV under root, plus whatever was targeted
    # explicitly (which may sit under a never_lint prefix, e.g. test fixtures).
    csv_targets_all = dict((rel, abs_) for rel, abs_ in discover_files([], config) if rel.endswith(".csv"))
    for rel, abs_ in targets:
        if rel.endswith(".csv"):
            csv_targets_all[rel] = abs_
    registry = load_all_csvs(sorted(csv_targets_all.items()))
    engine.index_terminology(registry, today)

    findings = []
    for rel_path, abs_path in targets:
        text = abs_path.read_text(encoding="utf-8")
        first_line = text.split("\n", 1)[0] if text else ""
        profile = detect_profile(rel_path, config, override_first_line=first_line,
                                  cli_profile=profile_override)

        if rel_path.endswith(".md"):
            units = build_markdown_units(rel_path, text, profile)
            engine.check_whole_file_budget(rel_path, text, findings)
            engine.check_paragraph_budget(units, findings)
        elif rel_path.endswith(".csv"):
            sheet = registry.get(rel_path)
            if not sheet:
                continue
            units = build_csv_units(rel_path, sheet["rows"], sheet["header"], profile)
        else:
            continue

        profile_tests = set(config["profiles"].get(profile, config["profiles"]["prose"])["tests"])
        for unit in units:
            if "T1" in profile_tests:
                engine.check_t1(unit, findings)
            if "T3" in profile_tests:
                engine.check_t3(unit, findings)
            if "T6" in profile_tests:
                engine.check_t6(unit, findings)
            if unit.kind == "field" and "budgets" in profile_tests:
                engine.check_bud_csv_field(unit, findings)
            if unit.kind == "sentence":
                if "T2" in profile_tests:
                    engine.check_t2(unit, findings)
                if "T4" in profile_tests:
                    engine.check_t4(unit, findings)
                if "T5" in profile_tests:
                    engine.check_t5_and_structural(unit, findings)

    csv_findings = check_csv_integrity(registry, today, engine, target_rel_set)
    findings.extend(csv_findings)

    findings.sort(key=lambda f: (f.file, f.line, f.column, f.rule))
    summary, _error_n = build_summary(targets, findings)
    return summary, findings


def _handle_lint(params):
    if not isinstance(params, dict) or "path" not in params:
        raise RpcError(INVALID_PARAMS, "ste100/lint requires params.path")

    path = params.get("path")
    if not isinstance(path, str) or not path:
        raise RpcError(INVALID_PARAMS, "params.path must be a non-empty string")

    preset = params.get("preset")
    if preset is not None and not isinstance(preset, str):
        raise RpcError(INVALID_PARAMS, "params.preset must be a string")

    profile = params.get("profile")
    if profile is not None and not isinstance(profile, str):
        raise RpcError(INVALID_PARAMS, "params.profile must be a string")

    explicit_root = params.get("root")
    if explicit_root is not None and not isinstance(explicit_root, str):
        raise RpcError(INVALID_PARAMS, "params.root must be a string")

    stats = params.get("stats", False)
    if not isinstance(stats, bool):
        raise RpcError(INVALID_PARAMS, "params.stats must be a boolean")

    summary, findings = _run_lint(path, preset=preset, profile_override=profile,
                                   explicit_root=explicit_root)

    # Same severity filter as --format json without --stats: review-tier
    # findings are advisory-only unless the caller asks for everything.
    report_findings = [f for f in findings if stats or f.severity in ("error", "warning")]

    return {
        "schema_version": SCHEMA_VERSION,
        "run_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
        "findings": [f.to_dict() for f in report_findings],
    }


METHODS = {
    "helve/hello": _handle_hello,
    "helve/shutdown": _handle_shutdown,
    "ste100/lint": _handle_lint,
}


def _dispatch(msg):
    """Handle one decoded JSON-RPC message. Returns 'shutdown' or 'continue'."""
    is_notification = isinstance(msg, dict) and "id" not in msg
    msg_id = msg.get("id") if isinstance(msg, dict) else None

    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or "method" not in msg:
        if not is_notification:
            _error(msg_id, INVALID_REQUEST, "invalid request")
        else:
            _log("dropped malformed notification: {!r}".format(msg))
        return "continue"

    method = msg.get("method")
    params = msg.get("params")
    handler = METHODS.get(method)

    if handler is None:
        if not is_notification:
            _error(msg_id, METHOD_NOT_FOUND, "no such method: {}".format(method))
        else:
            _log("dropped notification for unknown method: {}".format(method))
        return "continue"

    try:
        result = handler(params)
    except RpcError as e:
        if not is_notification:
            _error(msg_id, e.code, e.message, e.data)
        else:
            _log("notification {} failed: {}".format(method, e.message))
        return "continue"
    except Exception as e:  # noqa: BLE001 -- must never crash the process or print a traceback to stdout
        _log("internal error handling {}: {}: {}".format(method, type(e).__name__, e))
        if not is_notification:
            _error(msg_id, INTERNAL_ERROR, "internal error: {}: {}".format(type(e).__name__, e))
        return "continue"

    if not is_notification:
        _result(msg_id, result)

    if method == "helve/shutdown":
        # "reply, then exit within 2s" -- exiting the read loop right away is
        # well inside that budget, and applies whether shutdown arrived as a
        # request or (degenerate but harmless) as a notification.
        return "shutdown"
    return "continue"


def serve(stdin=None):
    _force_utf8_stdio()
    stream = stdin if stdin is not None else sys.stdin
    for line in stream:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            _error(None, PARSE_ERROR, "parse error: {}".format(e))
            continue
        if _dispatch(msg) == "shutdown":
            break
    # Falls through here either on helve/shutdown or on stdin closing --
    # both are a clean exit, per the protocol ("child exits when stdin closes").


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--helve-rpc" not in argv:
        _log("usage: python -m ste100.helve --helve-rpc")
        _log("Speaks the HELVE-ADE Tool Protocol v1 (NDJSON over stdio); "
             "this is a tool core, not meant to be run directly by a person.")
        return 1
    serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
