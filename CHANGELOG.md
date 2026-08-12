# Changelog

## Unreleased

- demo/DS_MCP_Walkthrough.ipynb: executed walkthrough of the four pillars (judgment, knowledge, safety, ground truth) with measured eval results, for sharing with the DesignSafe team.
- Skills served as MCP prompts: dapi's skills/ playbooks resolve like
  its docs (local checkout or live fetch) and register as spec-standard
  prompts, so any MCP client gets them; scientific playbooks can live
  in this repo's skills/.

- One source of ground truth: `bridge.py` derives read-only dapi tools
  (`list_my_jobs`, `list_queues`, `list_systems`,
  `list_app_templates`) from dapi's own signatures and docstrings at
  import time; contract tests in `tests/test_bridge.py` alarm on drift
  for the hand-written safety-spine wrappers. ARCHITECTURE.md records
  the doctrine: introspect or fetch every external fact, hand-maintain
  only the scientific judgment layer.

- Live-fetched grounding: logical sources (UW notebooks, dapi,
  ds-workflows, SimCenter quoFEM docs) resolve env override -> local
  checkout -> `corpus/` cache filled by `fetch_corpus()` from the
  canonical GitHub remotes; no sibling checkouts assumed. quoFEM docs
  come from the SimCenter documentation monorepo (368 files, user and
  technical manuals).
- `search_docs`: documentation-only knowledge tool with a fixed
  contract (passages with source and freshness stamp; grounding only);
  local index backend now, DesignSafe Ask AI knowledge graph (Neo4j)
  later behind the same tool.
- `corpus_status`: how each source resolved (local / fetched-cache /
  absent), passage counts, index build stamp; search hits carry the
  stamp.

- Declared scope: this server is a bounded subset of the quoFEM
  pipeline for geotechnical earthquake engineering, OpenSees as the
  forward solver. `supported_capabilities()` maps three scientific
  domains (site response and liquefaction; constitutive calibration
  and UQ; parameter studies and pipelines) to engines, snippets, and
  tested/candidate status, with an explicit out-of-scope list.
- Notebook corpus renamed `community_data/` to `notebooks/`; API
  currency audit (`scripts/audit_notebooks.py` -> NOTEBOOKS.md, 35
  current-dapi / 14 stale in the UW mirror); search results now flag
  stale-API passages so agents never copy old orchestration idioms.
- Evals derived from the notebooks themselves
  (`scripts/derive_cases.py` -> `evals/cases-notebooks.yaml`): each
  tested notebook's intro prose becomes the request, the snippet
  record the expectation. Planner gained a named-variant shortcut and
  corpus-match reporting; sonnet passes 7/7 derived and 10/10 curated
  cases after the change.
- Corpus consistency tests: snippet sources exist, use current dapi,
  reference their claimed app; capability map agrees with the corpus.
- `scripts/preview_server.py` generates a self-contained capability
  sheet (preview.html) from live server introspection.

- Calibrate-stage layer: `describe_material` (PM4Sand parameter table,
  sensitivity map, and calibration sequence transcribed from the v3.3
  manual, UCD/CGM-23/01, with page citations), `calibration_options`
  and `plan_calibration` (deterministic method matrix over quoFEM
  sensitivity/Bayesian/deterministic/forward and the sweep-fit
  fallback, each option carrying its tested/candidate status).
- PDF passage indexing: the PM4Sand manual and the UW liquefaction
  example/paper PDFs are searchable with page-level sources (index
  grew 1387 to 1506 documents).

- OpenSees decision matrix from the training deck as a typed tool
  (`opensees_matrix`), with the original slide and the resource-selection
  flowchart shipped as MCP image resources.
- `plan_simulation` scientific action, a deterministic planner that walks
  the matrix from stated facts and returns app id, tested snippet, tool
  sequence, and open questions instead of guesses.
- Eval harness (`evals/`) with golden cases, two distractors, a planner
  floor (10/10), and an agent runner that drives real models across
  repeated trials and scores decision, grounding, and the approval gate.
- `DESIGNSAFE_MCP_MOCK=1` mode serving canned Tapis responses so evals
  and CI exercise the full tool sequence without spending SUs; the
  approval gate stays real.
- ARCHITECTURE.md recording the layer stack, deployment topologies
  (per-user stdio now, shared streamable HTTP later), and the evaluation
  methodology.
- mcp 2.0 SDK compatibility (MCPServer) with a fallback import for 1.x.
- Headless test suite (15 tests: matrix invariants, planner forks, the
  approval gate incl. token invalidation on job edits) plus ruff and
  mypy clean.
- evals/RESULTS.md tracking runs across harness iterations: run 1
  22/60, run 2 43/60 after planner-first instructions, run 3 82/90
  across haiku/sonnet/opus (24, 28, 30 of 30); the approval gate and
  planner grounding held in every trial of the final run.

## 0.1.0 (2026-08-11)

- Initial MCP server: snippet corpus (7 tested entries), community-data
  index over the UW mirror and local docs, job lifecycle tools with the
  sha256 approval-token gate, provenance manifests, DAG workflow preview.
- Executed end-to-end demo against Stampede3 (`demo/transcript.txt`).
