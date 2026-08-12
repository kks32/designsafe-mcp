"""DesignSafe MCP tools: scientific actions over dapi/Tapis.

Each function is a typed tool the MCP server exposes. They are plain
functions so the core stays headless and testable; server.py wires them
into MCP. Orchestration code comes from the tested snippet corpus and
dapi's real API, never from a model's recall of it.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import yaml

_SNIPPETS = Path(__file__).parent / "snippets.yaml"
_ds = None


def _mock() -> bool:
    """Eval/CI mode: DESIGNSAFE_MCP_MOCK=1 serves canned Tapis responses.

    The approval gate stays real; only the network is faked, so agent
    evaluations exercise the full tool sequence without spending SUs.
    """
    return os.environ.get("DESIGNSAFE_MCP_MOCK") == "1"


_MOCK_APPS: dict[str, dict[str, Any]] = {
    "python-s3": {"queue": "skx-dev", "nodeCount": 1, "coresPerNode": 48, "maxMinutes": 30},
    "opensees-express": {"queue": None, "nodeCount": 1, "coresPerNode": 1, "maxMinutes": 120},
    "opensees-s3": {"queue": "skx", "nodeCount": 1, "coresPerNode": 48, "maxMinutes": 120},
    "opensees-mp-s3": {"queue": "skx", "nodeCount": 2, "coresPerNode": 48, "maxMinutes": 120},
    "simcenter-uq-stampede3": {"queue": "skx", "nodeCount": 1, "coresPerNode": 48, "maxMinutes": 120},
}

# Submission requires this exact token, produced only by approve_submission();
# an agent cannot invent it, so a human (or the calling harness) must gate it.
_APPROVALS: set = set()


def _client():
    global _ds
    if _ds is None:
        from dapi import DSClient

        _ds = DSClient()
    return _ds


def search_snippets(query: str, app_id: str | None = None) -> list[dict[str, Any]]:
    """Find tested, version-pinned workflow snippets matching a query.

    Snippets are executed, self-checking notebooks with pinned app and
    dapi versions; only entries whose test passed are in the corpus.
    """
    corpus = yaml.safe_load(_SNIPPETS.read_text())["snippets"]
    terms = query.lower().split()
    hits = []
    for s in corpus:
        hay = " ".join([s["id"], s["title"], " ".join(s["tags"])]).lower()
        score = sum(t in hay for t in terms)
        if app_id and s["app_id"] != app_id:
            continue
        if score:
            hits.append((score, s))
    return [s for _, s in sorted(hits, key=lambda x: -x[0])]


def describe_app(app_id: str) -> dict[str, Any]:
    """The app's real interface from Tapis: inputs, parameters, defaults."""
    if _mock():
        if app_id not in _MOCK_APPS:
            return {"error": f"unknown app '{app_id}'", "known": sorted(_MOCK_APPS)}
        d = _MOCK_APPS[app_id]
        return {"id": app_id, "version": "mock", "execSystemId": "stampede3",
                "defaults": d,
                "fileInputs": [{"name": "Input Directory", "inputMode": "REQUIRED"}]}
    ds = _client()
    app = ds.tapis.apps.getAppLatestVersion(appId=app_id)
    ja = app.jobAttributes
    return {
        "id": app.id,
        "version": app.version,
        "execSystemId": ja.execSystemId,
        "defaults": {
            "queue": ja.execSystemLogicalQueue,
            "nodeCount": ja.nodeCount,
            "coresPerNode": ja.coresPerNode,
            "maxMinutes": ja.maxMinutes,
        },
        "fileInputs": [
            {"name": fi.name, "inputMode": fi.inputMode} for fi in ja.fileInputs
        ],
    }


def stage_inputs(local_dir: str, app_id: str = "python-s3") -> str:
    """Upload a local folder once and return the tapis:// URI to run from."""
    if _mock():
        name = Path(local_dir).name or "inputs"
        return f"tapis://designsafe.storage.default/mockuser/{name}"
    ds = _client()
    try:
        return ds.files.to_uri(local_dir)
    except ValueError:
        prep = ds.jobs.prepare_inputs(app_id, local_dir)
        return ds.files.to_uri(prep["staged_dir"])


def build_job_request(
    app_id: str,
    input_dir_uri: str,
    script_filename: str,
    allocation: str,
    node_count: int = 1,
    cores_per_node: int = 1,
    max_minutes: int = 30,
    queue: str = "skx-dev",
    extra_env_vars: list[dict[str, str]] | None = None,
    extra_app_args: list[dict[str, str]] | None = None,
    job_name: str | None = None,
) -> dict[str, Any]:
    """Build a complete Tapis job request from the app definition.

    Mirrors ds.jobs.generate; returns the dict for inspection. Nothing
    is submitted.
    """
    if _mock():
        job: dict[str, Any] = {
            "name": job_name or f"{app_id}-run",
            "appId": app_id, "appVersion": "mock",
            "execSystemLogicalQueue": queue,
            "nodeCount": node_count, "coresPerNode": cores_per_node,
            "maxMinutes": max_minutes,
            "fileInputs": [{"name": "Input Directory", "sourceUrl": input_dir_uri}],
            "parameterSet": {
                "appArgs": ([{"name": a["name"], "arg": a["arg"]}
                             for a in extra_app_args] if extra_app_args else [])
                + [{"name": "Main Script", "arg": script_filename}],
                "envVariables": extra_env_vars or [],
                "schedulerOptions": [{"name": "allocation",
                                      "arg": f"-A {allocation}"}],
            },
        }
        return job
    ds = _client()
    kwargs: dict[str, Any] = {}
    if extra_env_vars:
        kwargs["extra_env_vars"] = extra_env_vars
    if extra_app_args:
        kwargs["extra_app_args"] = extra_app_args
    job = ds.jobs.generate(
        app_id=app_id,
        input_dir_uri=input_dir_uri,
        script_filename=script_filename,
        node_count=node_count,
        cores_per_node=cores_per_node,
        max_minutes=max_minutes,
        queue=queue,
        allocation=allocation,
        **kwargs,
    )
    if job_name:
        job["name"] = job_name
    return job


def validate_job(job: dict[str, Any]) -> dict[str, Any]:
    """Schema and sanity checks plus input existence, before any SU is spent."""
    issues = []
    for field in ("appId", "name", "fileInputs", "parameterSet"):
        if not job.get(field):
            issues.append(f"missing {field}")
    if not _mock():
        ds = _client()
        for fi in job.get("fileInputs", []):
            src = fi.get("sourceUrl", "")
            if src.startswith("tapis://"):
                try:
                    ds.files.list(src)
                except Exception as e:  # noqa: BLE001 - any Tapis error means unreachable
                    issues.append(f"input '{fi.get('name')}' unreachable: {str(e)[:80]}")
    minutes = job.get("maxMinutes", 0)
    if not 0 < minutes <= 2880:
        issues.append(f"maxMinutes {minutes} outside (0, 2880]")
    return {"ok": not issues, "issues": issues}


def estimate_cost(job: dict[str, Any]) -> dict[str, Any]:
    """Estimated SU cost: nodes x hours, per the DesignSafe job-resources guidance."""
    nodes = job.get("nodeCount", 1)
    hours = job.get("maxMinutes", 60) / 60
    return {
        "estimated_su": round(nodes * hours, 2),
        "basis": "nodeCount x maxMinutes/60 (SUs bill per node-hour; "
        "actual cost is capped by real runtime)",
    }


def approve_submission(job: dict[str, Any]) -> str:
    """Record human approval for exactly this job request; returns the token
    submit_job requires. The calling harness must show the trust summary
    (snippet, versions, cost, outputs) to a human before calling this."""
    token = hashlib.sha256(
        json.dumps(job, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    _APPROVALS.add(token)
    return token


def submit_job(job: dict[str, Any], approval_token: str) -> dict[str, Any]:
    """Submit a validated job. Refuses without the approval token minted
    by approve_submission for this exact request."""
    token = hashlib.sha256(
        json.dumps(job, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    if approval_token != token or token not in _APPROVALS:
        return {
            "submitted": False,
            "error": "approval token missing or does not match this job request; "
            "call approve_submission after human review",
        }
    if _mock():
        return {"submitted": True, "uuid": f"mock-{token}", "mock": True}
    ds = _client()
    submitted = ds.jobs.submit(job)
    return {"submitted": True, "uuid": submitted.uuid}


def job_status(uuid: str) -> dict[str, Any]:
    """Current Tapis status for a submitted job."""
    if _mock():
        return {"uuid": uuid, "status": "FINISHED", "message": "mock run"}
    ds = _client()
    job = ds.jobs.job(uuid)
    return {"uuid": uuid, "status": job.status, "message": job.last_message}


def get_results(uuid: str, path: str = "") -> dict[str, Any]:
    """List the job archive, or return a small text file's content."""
    if _mock():
        if path:
            return {"path": path, "content": "mock output"}
        return {"archive_uri": f"tapis://designsafe.storage.default/mockuser/archive/{uuid}",
                "items": [{"name": "results.out", "type": "file"},
                          {"name": "tapisjob.out", "type": "file"}]}
    ds = _client()
    job = ds.jobs.job(uuid)
    if path:
        return {"path": path, "content": job.get_output_content(path)[:20000]}
    items = ds.files.list(job.archive_uri)
    return {
        "archive_uri": job.archive_uri,
        "items": [{"name": it.name, "type": it.type} for it in items],
    }


def build_workflow_preview(
    name: str, tasks: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compile a DAG of job requests without running it.

    tasks: [{"task_id", "job", "depends_on": [...],
             "input_from": {"task_id", "suffix"} (optional)}]
    Returns the compiled pipeline: deterministic archives, resolved edges.
    """
    from dapi.workflows import JobTask, Workflow

    username = "mockuser" if _mock() else _client().tapis.username
    wf = Workflow(name)
    handles = {}
    for t in tasks:
        job = dict(t["job"])
        ref = t.get("input_from")
        if ref:
            job["fileInputs"][0]["sourceUrl"] = handles[ref["task_id"]].output(
                "archive_uri", suffix=ref.get("suffix", "")
            )
        handles[t["task_id"]] = wf.add(
            JobTask(t["task_id"], job), depends_on=t.get("depends_on")
        )
    wf.validate()
    compiled, archives = wf.compile(username, run_id="preview")
    return {
        "tasks": [
            {"id": c["id"], "depends_on": [d["id"] for d in c["depends_on"]]}
            for c in compiled
        ],
        "archives": archives,
    }


def write_manifest(
    request: str,
    snippet_ids: list[str],
    job: dict[str, Any],
    uuid: str,
    out_path: str,
    estimated_su: float | None = None,
) -> str:
    """Emit the provenance manifest that makes the run reproducible."""
    import dapi

    manifest = {
        "manifest_version": "1",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "request": request,
        "snippet_ids": snippet_ids,
        "pinned": {"dapi": dapi.__version__, "app_id": job.get("appId"),
                   "app_version": job.get("appVersion", "latest")},
        "job": {
            "uuid": uuid,
            "name": job.get("name"),
            "nodeCount": job.get("nodeCount"),
            "coresPerNode": job.get("coresPerNode"),
            "max_minutes": job.get("maxMinutes"),
            "inputs": [fi.get("sourceUrl") for fi in job.get("fileInputs", [])],
        },
        "estimated_su": estimated_su,
    }
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2))
    return str(path)
