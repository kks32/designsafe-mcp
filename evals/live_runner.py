"""Live notebook evals: build a notebook that drives the real MCP tools
end to end on TACC, execute it, and keep the executed notebook as the
eval artifact. Credentials come from dapi's environment; executed
notebooks land in evals/results/live/ (gitignored, they contain job
uuids and user paths).

Run: .venv/bin/python evals/live_runner.py oscillator
"""

import os
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).parent.parent
OUT = Path(__file__).parent / "results" / "live"

OSC = '''import json, numpy as np
xi, wn = 0.05, 1.0
dt, n = 0.002, int(80 * 2 * np.pi / 0.002)
u = v = 0.0
peak = 0.0
for i in range(n):
    t = i * dt
    a = np.sin(wn * t) - 2 * xi * wn * v - wn**2 * u
    v += a * dt
    u += v * dt
    if t > 60 * np.pi:
        peak = max(peak, abs(u))
print("AMPLIFICATION", round(peak * wn**2, 5))
'''

CASES = {
    "oscillator": {
        "app_id": "python-s3", "script": "oscillator.py",
        "files": {"oscillator.py": OSC}, "max_minutes": 10,
        "queue": "skx-dev",
        "assert_re": r"AMPLIFICATION\\s+(\\d+\\.\\d+)",
        "assert_range": (9.0, 11.0),
    },
}


def build(case_id: str) -> Path:
    c = CASES[case_id]
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    alloc = os.environ.get("DAPI_ALLOCATION", "DS-Portal-SPARC2026")
    nb = nbf.v4.new_notebook()
    nb.cells = [
        md(f"# Live end-to-end eval: {case_id}\n\nEvery cell below is a "
           "real MCP tool call against TACC. The executed notebook is "
           "the eval artifact."),
        code(f"""import json, os, re, time
from pathlib import Path
os.environ.pop("DESIGNSAFE_MCP_MOCK", None)   # LIVE
from designsafe_mcp import tools
work = Path({str(OUT / case_id)!r}); work.mkdir(parents=True, exist_ok=True)
for name, body in {c['files']!r}.items():
    (work / name).write_text(body)
uri = tools.stage_inputs(str(work), app_id={c['app_id']!r})
print(uri)"""),
        code(f"""job = tools.build_job_request(
    app_id={c['app_id']!r}, input_dir_uri=uri,
    script_filename={c['script']!r}, allocation={alloc!r},
    max_minutes={c['max_minutes']}, queue={c['queue']!r},
    job_name="mcp-live-eval-{case_id}")
v = tools.validate_job(job); print(v); assert v["ok"], v
print(tools.estimate_cost(job))"""),
        code("""token = tools.approve_submission(job)   # human-authorized run
out = tools.submit_job(job, token); print(out)
assert out["submitted"], out
uuid = out["uuid"]"""),
        code("""status = None
for _ in range(120):
    s = tools.job_status(uuid); status = s["status"]
    if status in ("FINISHED", "FAILED", "CANCELLED", "STOPPED"):
        break
    time.sleep(20)
print(uuid, status)
assert status == "FINISHED", status"""),
        code(f"""listing = tools.get_results(uuid)
print([i["name"] for i in listing["items"]])
out_text = tools.get_results(uuid, "tapisjob.out")["content"]
m = re.search(r"{c['assert_re']}", out_text)
assert m, out_text[-800:]
value = float(m.group(1))
print("measured:", value)
assert {c['assert_range'][0]} < value < {c['assert_range'][1]}
manifest = tools.write_manifest(
    "live eval {case_id}", ["oscillator-single-job-v1"], job, uuid,
    str(work / "manifest.json"))
print(manifest); assert isinstance(manifest, str)
print("LIVE EVAL PASS")"""),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"live-{case_id}.ipynb"
    nbf.write(nb, path)
    return path


def _load_credentials() -> None:
    """Export dapi credentials to the kernel's environment. Values are
    never printed or written; the executed notebook inherits them the
    same way a JupyterHub session would."""
    env = ROOT.parent / "dapi" / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


if __name__ == "__main__":
    _load_credentials()
    case = sys.argv[1] if len(sys.argv) > 1 else "oscillator"
    path = build(case)
    nb = nbf.read(path, as_version=4)
    NotebookClient(nb, timeout=3000).execute()
    nbf.write(nb, path)
    print(f"executed: {path}")
