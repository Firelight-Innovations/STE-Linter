#!/usr/bin/env python3
"""Regression tests for the HELVE-ADE Tool integration (src/ste100/helve.py).

Drives `python -X utf8 -m ste100.helve --helve-rpc` as a real subprocess over
stdio, the same way a HELVE-ADE host would, and asserts:

  1. Handshake (helve/hello) succeeds with the right result shape.
  2. A protocol-version mismatch on helve/hello is rejected, not negotiated down.
  3. A ste100/lint call on a fixture returns the expected finding.
  4. Malformed JSON gets -32700.
  5. An unknown method gets -32601.
  6. A notification (no "id") gets no reply at all.
  7. helve/shutdown makes the process exit cleanly after replying.
  8. Closing stdin (no helve/shutdown) also makes the process exit cleanly.
  9. Everything written to stdout across a whole session parses as pure
     NDJSON with nothing else mixed in -- the regression that matters most,
     since a single stray print() corrupts the transport for the host.

Usage: python -X utf8 tests/run_helve_tests.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "helve_fixtures" / "dirty.md"

failures = []


def _spawn():
    env_cmd = [sys.executable, "-X", "utf8", "-m", "ste100.helve", "--helve-rpc"]
    return subprocess.Popen(
        env_cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
        env=_env_with_src_on_path(),
    )


def _env_with_src_on_path():
    import os
    env = dict(os.environ)
    src = str(ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src + (os.pathsep + existing if existing else "")
    return env


def _send(proc, obj):
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()


def _read_response(proc):
    line = proc.stdout.readline()
    if not line:
        return None
    return json.loads(line)


def check(name, condition, detail=""):
    if condition:
        print("PASS {}".format(name))
    else:
        failures.append("{}{}".format(name, ": " + detail if detail else ""))


def _shutdown(proc):
    """Best-effort clean shutdown so a failed assertion never leaks a process."""
    try:
        if proc.poll() is None:
            _send(proc, {"jsonrpc": "2.0", "id": 999999, "method": "helve/shutdown"})
            proc.stdin.close()
            proc.wait(timeout=5)
    except Exception:
        proc.kill()


# ---- 1/2: handshake ---------------------------------------------------------

def test_handshake():
    proc = _spawn()
    try:
        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "helve/hello",
                     "params": {"protocol": 1, "session": {"projectPath": None}}})
        resp = _read_response(proc)
        check("helve/hello succeeds",
              resp is not None and resp.get("result", {}).get("id") == "ste100"
              and resp["result"].get("protocol") == 1 and "version" in resp["result"],
              "got {!r}".format(resp))

        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "helve/hello",
                     "params": {"protocol": 2, "session": {"projectPath": None}}})
        resp2 = _read_response(proc)
        check("protocol mismatch is rejected, not negotiated down",
              resp2 is not None and "error" in resp2 and resp2["error"]["code"] == -32602,
              "got {!r}".format(resp2))
    finally:
        _shutdown(proc)


# ---- 3: lint call -----------------------------------------------------------

def test_lint():
    proc = _spawn()
    try:
        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "helve/hello",
                     "params": {"protocol": 1, "session": {"projectPath": None}}})
        _read_response(proc)

        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "ste100/lint",
                     "params": {"path": str(FIXTURE)}})
        resp = _read_response(proc)
        result = (resp or {}).get("result")
        ok = (
            result is not None
            and result.get("summary", {}).get("errors") == 1
            and len(result.get("findings", [])) == 1
            and result["findings"][0]["rule"].startswith("STE-T1-")
            and result["findings"][0]["test"] == "T1"
            and result["findings"][0]["severity"] == "error"
            and "utilize" in result["findings"][0]["excerpt"]
        )
        check("ste100/lint finds the fixture's T1 violation", ok, "got {!r}".format(resp))
    finally:
        _shutdown(proc)


def test_lint_bad_params():
    proc = _spawn()
    try:
        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "ste100/lint", "params": {}})
        resp = _read_response(proc)
        check("ste100/lint with no path is -32602",
              resp is not None and resp.get("error", {}).get("code") == -32602,
              "got {!r}".format(resp))

        _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "ste100/lint",
                     "params": {"path": "does/not/exist.md"}})
        resp2 = _read_response(proc)
        check("ste100/lint on a missing path is -32602, not a crash",
              resp2 is not None and resp2.get("error", {}).get("code") == -32602,
              "got {!r}".format(resp2))
    finally:
        _shutdown(proc)


# ---- 4/5/6: protocol edge cases ---------------------------------------------

def test_protocol_edge_cases():
    proc = _spawn()
    try:
        proc.stdin.write("not json at all\n")
        proc.stdin.flush()
        resp = _read_response(proc)
        check("malformed JSON gets -32700",
              resp is not None and resp.get("error", {}).get("code") == -32700,
              "got {!r}".format(resp))

        _send(proc, {"jsonrpc": "2.0", "id": 5, "method": "no/such/method"})
        resp2 = _read_response(proc)
        check("unknown method gets -32601",
              resp2 is not None and resp2.get("error", {}).get("code") == -32601,
              "got {!r}".format(resp2))

        # A notification (no "id") must get no reply at all. Prove it by
        # sending one immediately followed by a real request, and checking
        # the next line off stdout answers the *request*, not the notification.
        _send(proc, {"jsonrpc": "2.0", "method": "file/changed", "params": {"path": "a.txt"}})
        _send(proc, {"jsonrpc": "2.0", "id": 6, "method": "helve/hello",
                     "params": {"protocol": 1, "session": {"projectPath": None}}})
        resp3 = _read_response(proc)
        check("a notification gets no response",
              resp3 is not None and resp3.get("id") == 6,
              "expected the id=6 reply next, got {!r}".format(resp3))
    finally:
        _shutdown(proc)


# ---- 7: helve/shutdown -------------------------------------------------------

def test_shutdown_exits():
    proc = _spawn()
    _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "helve/shutdown"})
    resp = _read_response(proc)
    check("helve/shutdown replies with a null result",
          resp is not None and resp.get("result") is None and "error" not in resp,
          "got {!r}".format(resp))
    proc.stdin.close()
    try:
        code = proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        code = None
    check("process exits after helve/shutdown", code == 0, "exit code was {!r}".format(code))


# ---- 8: stdin close -----------------------------------------------------------

def test_stdin_close_exits():
    proc = _spawn()
    proc.stdin.close()
    try:
        code = proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        code = None
    check("process exits cleanly when stdin closes with no shutdown call", code == 0,
          "exit code was {!r}".format(code))


# ---- 9: stdout is pure NDJSON across a whole session -------------------------

def test_stdout_is_pure_ndjson():
    proc = _spawn()
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "helve/hello",
         "params": {"protocol": 1, "session": {"projectPath": None}}},
        {"jsonrpc": "2.0", "method": "file/changed", "params": {"path": "a.txt"}},
        {"jsonrpc": "2.0", "id": 2, "method": "ste100/lint", "params": {"path": str(FIXTURE)}},
        {"jsonrpc": "2.0", "id": 3, "method": "unknown/method"},
        {"jsonrpc": "2.0", "id": 4, "method": "helve/shutdown"},
    ]
    for m in messages:
        _send(proc, m)
    # Do not close stdin here: communicate() closes it itself, and that close
    # is the EOF the server exits on. Closing it first makes communicate()
    # raise ValueError("I/O operation on closed file") on POSIX. Windows takes
    # a different code path in subprocess and happens not to, which is why
    # this only showed up on the Linux and macOS runners.
    try:
        stdout, stderr = proc.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()

    lines = [ln for ln in stdout.split("\n") if ln.strip()]
    all_parse = True
    ids_seen = []
    for ln in lines:
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            all_parse = False
            failures.append("non-JSON line on stdout: {!r}".format(ln))
            continue
        if obj.get("jsonrpc") != "2.0" or ("result" not in obj and "error" not in obj):
            all_parse = False
            failures.append("line on stdout is not a JSON-RPC response: {!r}".format(obj))
        ids_seen.append(obj.get("id"))

    check("every stdout line across the session parses as pure NDJSON", all_parse)
    # 4 requests carried an id (the notification did not); exactly 4 responses.
    check("exactly one response per request (none for the notification)",
          ids_seen == [1, 2, 3, 4], "got ids {!r}".format(ids_seen))


if __name__ == "__main__":
    test_handshake()
    test_lint()
    test_lint_bad_params()
    test_protocol_edge_cases()
    test_shutdown_exits()
    test_stdin_close_exits()
    test_stdout_is_pure_ndjson()

    if failures:
        print("\nFAIL ({} issue(s)):".format(len(failures)))
        for f in failures:
            print(" - {}".format(f))
        sys.exit(1)
    print("\nAll HELVE integration tests passed.")
