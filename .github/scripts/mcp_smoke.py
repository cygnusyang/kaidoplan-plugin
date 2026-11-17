#!/usr/bin/env python3
"""Smoke-test the KaidoPlan MCP server through the plugin launcher.

Spawns the launcher (bin/kaidoplan-mcp) exactly as an MCP host would, performs
the JSON-RPC handshake, lists tools and asserts the expected count. Exits 0
when the server speaks MCP and exposes the expected tool surface.

Usage: python3 mcp_smoke.py <launcher-path> [expected-tool-count]
"""

from __future__ import annotations

import json
import subprocess
import sys

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "kaidoplan-ci-probe", "version": "0.0.1"},
    },
}
INITIALIZED = {"jsonrpc": "2.0", "method": "notifications/initialized"}
TOOLS_LIST = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}


def main() -> int:
    launcher = sys.argv[1] if len(sys.argv) > 1 else "bin/kaidoplan-mcp"
    expected = int(sys.argv[2]) if len(sys.argv) > 2 else 21

    reqs = "\n".join(json.dumps(r) for r in (INITIALIZE, INITIALIZED, TOOLS_LIST)) + "\n"
    try:
        proc = subprocess.run(
            [launcher],
            input=reqs,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print(f"fail: {launcher} did not answer within 60s", file=sys.stderr)
        return 1
    if proc.returncode != 0:
        print(f"fail: {launcher} exited {proc.returncode}: {proc.stderr.strip()}", file=sys.stderr)
        return 1

    responses = {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        if msg.get("id") is not None:
            responses[msg["id"]] = msg

    init = responses.get(1)
    if not init or "result" not in init:
        print("fail: initialize did not return a result", file=sys.stderr)
        return 1
    server_info = init["result"].get("serverInfo", {})
    print(f"server: {server_info.get('name', '?')} {server_info.get('version', '?')}")

    tools = responses.get(2)
    if not tools or "result" not in tools:
        print("fail: tools/list did not return a result", file=sys.stderr)
        return 1
    names = [t["name"] for t in tools["result"]["tools"]]
    if len(names) != expected:
        print(f"fail: tools/list returned {len(names)} tools, expected {expected}", file=sys.stderr)
        print("tools: " + ", ".join(sorted(names)), file=sys.stderr)
        return 1
    if len(names) != len(set(names)):
        print("fail: duplicate tool names", file=sys.stderr)
        return 1
    print(f"ok: tools/list = {len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
