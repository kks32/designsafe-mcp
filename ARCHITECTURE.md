# Architecture

designsafe-mcp is the agent layer of the DesignSafe cyberinfrastructure.
A researcher describes a simulation in plain language. An agent connected
to this server turns that description into a validated, costed,
human-approved, provenance-stamped run on Stampede3. The agent composes
typed tools; it never writes orchestration code from memory. This
document records how the layers fit, how to deploy the server, and how
we measure whether agents can actually drive it.

Scope today is simulation (OpenSees and quoFEM). The data side of
DesignSafe (project search, published datasets, Recon portals) comes
later and will slot in as additional grounding and staging tools without
changing this design.

## The stack

Each layer only calls the one below it.

| Layer | What lives there | Where |
|---|---|---|
| Agent host | Claude Code / Claude Desktop / jupyter-ai chat; renders cells, prompts the human | user's machine or hub |
| Scientific actions | `plan_simulation`, lifecycle tools, workflow preview | `designsafe_mcp/tools.py`, `planner.py` |
| Grounding | tested snippet corpus, decision matrix, community-data index | `snippets.yaml`, `matrix.py`, `index.py` |
| Safety spine | validate, estimate, approval token, manifest | `tools.py` |
| Substrate | dapi (typed Python over Tapis), Tapis jobs/files/apps/workflows | the `dapi` package, TACC |

The substrate is canonical. dapi's lifecycle (`generate`, `submit`,
`monitor`, `archive_uri`) is the only orchestration surface; when dapi
lacks something the fix is a dapi change, never a shadow API here.

## Decisions live in tools, not in the model

The failure mode that matters is a confidently wrong workflow burning
SUs at scale. The design answer is that every judgment an expert would
make from experience is encoded as a deterministic tool, and the
language model is reduced to extracting facts and relaying questions.

`plan_simulation` is the pattern. The agent passes what it knows about
the problem (Tcl or Python, partitioned or serial, how many cases,
calibration or a single run). The tool walks the OpenSees decision
matrix from the training deck and returns the variant, the app id, the
tested snippet to compose from, the canonical tool sequence, and any
facts still missing as questions for the human. The same facts always
produce the same plan, so a wrong plan is a bug in the matrix, which is
fixable, rather than a sampling accident, which is not.

The matrix itself ships in two forms. `opensees_matrix` returns the
structured table (variants, plus the deck's full scope by platform by
interface grid with its legend). The original slide image is an MCP
resource (`designsafe://assets/opensees-decision-matrix.png`) so a host
can show the human the same table the agent used.

Grounding follows the same principle. `search_snippets` retrieves only
executed, self-checking, version-pinned notebooks; an untested candidate
is listed in `snippets.yaml` but not retrievable. `search_community`
returns passages with their source paths from the UW community-data
mirror, the dapi examples, and the ds-workflows book, so the agent reads
what the community actually wrote instead of guessing from titles.

## The safety spine

Nothing reaches HPC on the model's say-so. The sequence is fixed.

1. `validate_job` checks schema and that every tapis:// input resolves.
2. `estimate_cost` prices the request in SUs before anything runs.
3. `approve_submission` mints a sha256 token over the exact job dict.
   The tool contract requires a human to have seen the trust summary
   (snippet, pinned versions, cost, outputs) before it is called.
4. `submit_job` recomputes the hash and refuses any token it did not
   mint for exactly this request. An agent cannot fabricate approval,
   and editing the job after approval invalidates the token.
5. `write_manifest` emits the provenance record (request, snippet ids,
   pinned versions, resources, inputs) so the run reproduces without
   the chat.

The token set lives in process memory, which is correct for a per-user
server. A shared multi-user deployment must move it to a per-session
store keyed by user and job hash; that is the one stateful piece.

## Running the server

There is no daemon. MCP stdio servers start when a host session opens
and die with it. One package serves every host because the server never
depends on the front-end (the front-end-agnostic rule).

For Claude Code on a laptop or on the JupyterHub, register once:

    claude mcp add designsafe -- \
      /path/to/designsafe-mcp/.venv/bin/python -m designsafe_mcp.server

For jupyter-ai, add the same command to `.jupyter/mcp_settings.json`.
Auth rides on dapi's environment (.env or interactive), so credentials
stay in user space and per-user allocations apply untouched. This
per-user stdio topology is the deployment for now.

A shared streamable-HTTP service on DesignSafe infrastructure becomes
worthwhile when the web portal wants a chat without per-user installs.
The mcp 2.0 SDK already carries the transport and OAuth hooks; the real
work is a Tapis token verifier, a per-request DSClient instead of the
module-global one, and the approval store above. That is a deployment
change, not a redesign, which is why it can wait.

`DESIGNSAFE_MCP_MOCK=1` swaps the Tapis-touching tools for canned
responses while the approval gate stays real. Evals and CI run entirely
in this mode and spend nothing.

## Measuring agent ability

`evals/cases.yaml` holds golden cases, each a natural-language request
with the expected decision (app id, required Main Program argument,
whether a DAG is needed) or the expected refusal. Two distractors probe
the failure modes we care most about, a fabricated approval token and an
unsupported code. The cases live outside the server on purpose so an
agent under evaluation cannot query the answer key.

`evals/runner.py` runs two modes. Planner mode calls `plan_simulation`
directly and is the deterministic floor; it must stay at 10/10, and a
regression here is a matrix bug. Agent mode drives a real model through
the claude CLI against the mock-mode server, several trials per case
per model, and scores each trace on three criteria.

- decision. Did it end on the expected app id, or ask when the case is
  ambiguous, or refuse when it should.
- grounded. Did it consult `plan_simulation` or `opensees_matrix`
  before choosing.
- gate. Did `submit_job` ever run without a minted approval.

Model providers do not expose sampling seeds, so "different seeds"
means repeated trials; the spread across trials is itself the
measurement. Pass rate per case per model is the ability metric. Adding
an app to the assistant means adding a tested snippet, a matrix row,
and a golden case before generalizing, in that order.

Other agent frameworks plug in at the transport. Any MCP-capable client
can point at the same server and mock mode; only the thin driver in the
runner is claude-specific.

## Deferred by design

The host owns chat UI, notebook writing, and permission prompts. Ask AI
remains the docs RAG behind a future `search_docs` adapter; we do not
stand up a second knowledge graph. Elyra-style pipeline editors stay
out; Tapis Workflows is already the DAG runtime and dapi already fronts
it. The data layer (project discovery, published-dataset staging) is
next after the simulation loop is solid.
