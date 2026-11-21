#!/usr/bin/env python3
"""Smoke-test the KaidoPlan MCP server through the plugin launcher.

Spawns the launcher (bin/kaidoplan-mcp) exactly as an MCP host would, performs
the JSON-RPC handshake, lists tools and checks the required tool names. Exits 0
when the server speaks MCP and exposes the expected tool surface.

Usage: python3 mcp_smoke.py <launcher-path>
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


# The shared KaidoPlan skill relies on these tools.
REQUIRED_TOOLS = {
    "project_create",
    "project_open",
    "schedule_compute",
    "schedule_critical_path",
    "status_update",
    "task_get",
    "task_list",
    "task_update",
    "violations_list",
    "wbs_import",
}


def main() -> int:
    launcher = sys.argv[1] if len(sys.argv) > 1 else "bin/kaidoplan-mcp"

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
    missing = REQUIRED_TOOLS.difference(names)
    if missing:
        print("fail: missing required tools: " + ", ".join(sorted(missing)), file=sys.stderr)
        return 1
    if len(names) != len(set(names)):
        print("fail: duplicate tool names", file=sys.stderr)
        return 1
    print(f"ok: tools/list = {len(names)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
