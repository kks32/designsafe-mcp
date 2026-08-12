# designsafe-mcp

An agent-first cyberinfrastructure layer for DesignSafe. The server exposes
scientific actions, find a tested workflow, build and validate a job, price
it, run it after human approval, and package the result with provenance,
so an AI agent (or a researcher) composes reproducible computational science
instead of driving low-level APIs.

dapi and Tapis remain the substrate; this layer translates research intent
into trustworthy workflows. Orchestration comes from a tested snippet corpus
(executed, self-checking, version-pinned examples), never from a model's
recall of the API.

## Tools

| Action | Tool |
|---|---|
| Find a tested workflow | `search_snippets(query)` |
| Ground in the real app interface | `describe_app(app_id)` |
| Move data | `stage_inputs(local_dir)` |
| Construct the experiment | `build_job_request(...)`, `build_workflow_preview(...)` |
| Check before spending | `validate_job(job)`, `estimate_cost(job)` |
| Human gate | `approve_submission(job)` -> token; `submit_job(job, token)` refuses without it |
| Execute and monitor | `submit_job`, `job_status`, `get_results` |
| Provenance | `write_manifest(...)` |

## Run

```
pip install -e .
python -m designsafe_mcp.server        # stdio MCP server
python demo/demo_first_workflow.py     # agent-shaped walkthrough with a live job
```

`demo/transcript.txt` holds an executed transcript: discovery, grounding,
staging, validation, cost, a refused unapproved submission, the approved run,
results, the manifest, and a compiled two-stage DAG preview.
