# Changelog

## Unreleased

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
