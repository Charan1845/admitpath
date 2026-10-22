"""Talk to a running AdmitPath server over MCP (JSON-RPC over Streamable HTTP), like Alexa+ would, and time each answer.

    python scripts/smoke_test.py [http://localhost:8000/mcp]
"""

from __future__ import annotations

import sys
import time

import requests

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"
HEADERS = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-11-25"}
_id = 0


def rpc(method: str, params: dict | None = None) -> tuple[dict, float]:
    global _id
    _id += 1
    t0 = time.perf_counter()
    r = requests.post(URL, json={"jsonrpc": "2.0", "id": _id, "method": method, "params": params or {}},
                      headers=HEADERS, timeout=30)
    ms = (time.perf_counter() - t0) * 1000
    r.raise_for_status()
    return r.json(), ms


def call(tool: str, **args) -> None:
    out, ms = rpc("tools/call", {"name": tool, "arguments": args})
    text = out["result"]["content"][0]["text"]
    print(f"\n> {tool}({', '.join(f'{k}={v!r}' for k, v in args.items())})   [{ms:.0f} ms]\n{text}")


init, _ = rpc("initialize", {"protocolVersion": "2025-11-25", "capabilities": {},
                             "clientInfo": {"name": "smoke-test", "version": "1"}})
print("server:", init["result"]["serverInfo"], "protocol:", init["result"]["protocolVersion"])
tools, _ = rpc("tools/list")
print("tools:", [t["name"] for t in tools["result"]["tools"]])

call("set_student", name="Riya", jee_main_rank=15000, category="OBC", category_rank=3500, gender="Female", home_state="Telangana")
call("predict_colleges", branch="computer science", institute_type="NIT")
call("check_option", institute="NIT Warangal", branch="CSE")
call("compare_options", institute_a="NIT Warangal", branch_a="CSE", institute_b="NIT Trichy", branch_b="ECE")
call("add_choice", institute="NIT Warangal", branch="CSE", position=1)
call("add_choice", institute="IIIT Allahabad", branch="IT")
call("read_choices")
call("explain_term", term="float")
call("check_option", institute="IIIT Hyderabad", branch="CSE")
