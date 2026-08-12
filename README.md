# designsafe-mcp

An agent-first cyberinfrastructure layer for DesignSafe, scoped to a
bounded subset of the quoFEM pipeline for geotechnical earthquake
engineering with OpenSees as the forward solver. The server exposes
scientific actions, find a tested workflow, build and validate a job, price
it, run it after human approval, and package the result with provenance,
so an AI agent (or a researcher) composes reproducible computational science
instead of driving low-level APIs. `supported_capabilities()` declares
exactly what is supported, in which scientific domain, and how much of
it is tested; requests outside that map are declined by design.

dapi and Tapis remain the substrate; this layer translates research intent
into trustworthy workflows. Orchestration comes from a tested snippet corpus
(executed, self-checking, version-pinned examples), never from a model's
recall of the API.

`ARCHITECTURE.md` records the full design: the layer stack, why decisions
live in tools rather than in the model, deployment topologies, and the
evaluation methodology.

## Tools

| Action | Tool |
|---|---|
| Decide how to run it | `plan_simulation(request, facts...)` walks the OpenSees decision matrix |
| See the matrix itself | `opensees_matrix()`; the deck's slide ships as an MCP resource |
| Find a tested workflow | `search_snippets(query)` |
| Search the corpus | `search_community(query)` over UW community data, dapi examples, the ds-workflows book |
| Ground in the real app interface | `describe_app(app_id)` |
| Move data | `stage_inputs(local_dir)` |
| Construct the experiment | `build_job_request(...)`, `build_workflow_preview(...)` |
| Check before spending | `validate_job(job)`, `estimate_cost(job)` |
| Human gate | `approve_submission(job)` -> token; `submit_job(job, token)` refuses without it |
| Execute and monitor | `submit_job`, `job_status`, `get_results` |
| Provenance | `write_manifest(...)` |

## Run

```
uv venv .venv && uv pip install -p .venv/bin/python -e .
.venv/bin/python -m designsafe_mcp.server   # stdio MCP server
```

Register it once for Claude Code with
`claude mcp add designsafe -- $PWD/.venv/bin/python -m designsafe_mcp.server`,
or add the same command to `.jupyter/mcp_settings.json` for jupyter-ai.
Auth rides on dapi's environment; nothing is stored here.

`demo/transcript.txt` holds an executed transcript: discovery, grounding,
staging, validation, cost, a refused unapproved submission, the approved run,
results, the manifest, and a compiled two-stage DAG preview.

## Evals

```
.venv/bin/python evals/runner.py --mode planner                       # deterministic floor
.venv/bin/python evals/runner.py --mode agent --models haiku,sonnet --trials 3
```

Golden cases in `evals/cases.yaml` map natural-language requests to the
expected decision; agent mode drives real models against the server in
`DESIGNSAFE_MCP_MOCK=1` mode (no Tapis calls, no SUs) and scores each
trace on decision, grounding, and the approval gate. Pass rate per case
per model is the ability metric.
