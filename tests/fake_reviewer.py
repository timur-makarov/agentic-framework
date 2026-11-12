#!/usr/bin/env python3
"""A stand-in for `claude -p` in tests: it answers review briefs from a queue the test writes, and logs each brief.

Queue items: a review/v1 object; "timeout" (sleep past timeout_secs); {"raw": text} (print text as is);
{"touch": path, ...} (write a scratch file first, to test the reset). With --consult it answers as the consult pack's
command does: advice text ending in a VERDICT line.
"""
import json
import os
import sys
import time

brief = sys.stdin.read()
log = os.environ.get("RAIL_FAKE_LOG")
if log:
    with open(log, "a") as f:
        f.write(json.dumps({"cwd": os.getcwd(), "brief": brief, "consult": "--consult" in sys.argv,
                            "model": os.environ.get("ANTHROPIC_MODEL")}) + "\n")
if "--consult" in sys.argv:
    print("The check expects a + b. Change the operator.\nVERDICT: change")
    sys.exit(0)
response = {"summary": "Read the diff and the ticket.", "findings": []}
queue_path = os.environ.get("RAIL_FAKE_REVIEWS")
if queue_path and os.path.exists(queue_path):
    with open(queue_path) as f:
        queue = json.load(f)
    if queue:
        response = queue.pop(0)
        with open(queue_path, "w") as f:
            json.dump(queue, f)
if response == "timeout":
    time.sleep(30)
if isinstance(response, dict) and "raw" in response:
    print(response["raw"])
    sys.exit(0)
if isinstance(response, dict) and "touch" in response:
    with open(response.pop("touch"), "w") as f:
        f.write("scratch\n")
    with open("src/calc.py", "a") as f:
        f.write("# the reviewer was here\n")
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "", "total_cost_usd": 0.01,
                  "modelUsage": {"a-small-helper": {"costUSD": 0.001},
                                 os.environ.get("ANTHROPIC_MODEL") or "fake-model": {"costUSD": 0.009}},
                  "structured_output": response}))
