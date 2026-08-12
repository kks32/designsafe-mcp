"""Demonstration: an agent-shaped walk through the MCP tools.

Plays the role of an agent handling: "run the damped oscillator at
resonance on Stampede3 and show me the amplification", then previews a
two-stage DAG the same way. Every step is a tool call the MCP server
exposes; nothing here touches dapi directly.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from designsafe_mcp import tools  # noqa: E402

ALLOCATION = "DS-Portal-SPARC2026"


def say(step, payload=None):
    print(f"\n=== {step} ===", flush=True)
    if payload is not None:
        print(json.dumps(payload, indent=2, default=str)[:1200], flush=True)


# 1. Discover: which tested snippet covers the request?
hits = tools.search_snippets("oscillator resonance single job")
say("search_snippets('oscillator resonance single job')",
    [{"id": h["id"], "title": h["title"], "test": h["test"]} for h in hits[:2]])
snippet = hits[0]

# 2. Ground: the app's real interface.
say("describe_app('python-s3')", tools.describe_app("python-s3"))

# 3. Stage inputs (from the snippet's contract: one script).
work = Path(tempfile.mkdtemp())
(work / "oscillator.py").write_text('''\
import json
import numpy as np
xi, wn, w = 0.05, 1.0, 1.0
dt = 0.002
n = int(80 * 2 * np.pi / wn / dt)
x = np.zeros(n); t = np.arange(n) * dt
for i in range(1, n - 1):
    a = np.sin(w * t[i]) - 2 * xi * wn * (x[i] - x[i - 1]) / dt - wn**2 * x[i]
    x[i + 1] = 2 * x[i] - x[i - 1] + a * dt**2
amp = float(np.max(np.abs(x[int(0.75 * n):])) * wn**2)
json.dump({"amplification": amp}, open("result.json", "w"))
print("amplification:", amp)
''')
input_uri = tools.stage_inputs(str(work))
say("stage_inputs(local folder)", {"input_uri": input_uri})

# 4. Build the job request from the app definition.
job = tools.build_job_request(
    app_id=snippet["app_id"],
    input_dir_uri=input_uri,
    script_filename="oscillator.py",
    allocation=ALLOCATION,
    max_minutes=15,
    job_name="mcp-demo-oscillator",
)
say("build_job_request(...)", {k: job[k] for k in ("name", "appId", "maxMinutes")})

# 5. Validate and price it BEFORE anything is spent.
checks = tools.validate_job(job)
cost = tools.estimate_cost(job)
say("validate_job", checks)
say("estimate_cost", cost)
assert checks["ok"], checks

# 6. The approval gate: submission refuses without the human-minted token.
refused = tools.submit_job(job, approval_token="fabricated-by-agent")
say("submit_job with a fabricated token (must refuse)", refused)
assert not refused["submitted"]

print("\n--- trust summary shown to the human ---")
print(f"snippet: {snippet['id']}  (test: {snippet['test']})")
print(f"pinned:  {snippet['pinned_versions']}")
print(f"cost:    {cost['estimated_su']} SU   produces: result.json")
token = tools.approve_submission(job)  # the human says yes

# 7. Submit, monitor, retrieve.
sub = tools.submit_job(job, approval_token=token)
say("submit_job (approved)", sub)
uuid = sub["uuid"]

import time
while True:
    st = tools.job_status(uuid)
    print(f"  status: {st['status']}", flush=True)
    if st["status"] in ("FINISHED", "FAILED", "CANCELLED", "STOPPED"):
        break
    time.sleep(30)

result = tools.get_results(uuid, "inputDirectory/result.json")
say("get_results(result.json)", json.loads(result["content"]))

# 8. Provenance: the run must reproduce without this chat.
manifest = tools.write_manifest(
    request="run the damped oscillator at resonance and report amplification",
    snippet_ids=[snippet["id"]],
    job=job,
    uuid=uuid,
    estimated_su=cost["estimated_su"],
    out_path=str(Path(__file__).parent / "manifest-oscillator.json"),
)
say("write_manifest", {"path": manifest})

# 9. Workflows compose the same way: preview a two-stage DAG, no submission.
sweep_job = dict(job, name="mcp-demo-sweep")
train_job = tools.build_job_request(
    app_id="python-s3",
    input_dir_uri="tapis://designsafe.storage.default/placeholder",
    script_filename="train.py",
    allocation=ALLOCATION,
    job_name="mcp-demo-train",
)
preview = tools.build_workflow_preview(
    "mcp-demo",
    [
        {"task_id": "sweep", "job": sweep_job},
        {"task_id": "train", "job": train_job,
         "input_from": {"task_id": "sweep", "suffix": "/inputDirectory"}},
    ],
)
say("build_workflow_preview (sweep -> train, nothing submitted)", preview)

print("\nDEMO COMPLETE", flush=True)
