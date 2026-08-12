# Changelog

## Unreleased

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

## 0.1.0 (2026-08-11)

- Initial MCP server: snippet corpus (7 tested entries), community-data
  index over the UW mirror and local docs, job lifecycle tools with the
  sha256 approval-token gate, provenance manifests, DAG workflow preview.
- Executed end-to-end demo against Stampede3 (`demo/transcript.txt`).
