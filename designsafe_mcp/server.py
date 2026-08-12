"""MCP server exposing DesignSafe scientific actions.

Run: python -m designsafe_mcp.server  (stdio transport)
Register in an MCP host (Claude Code/Desktop, jupyter-ai) as a stdio server.
"""

from pathlib import Path

try:  # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP  # type: ignore[assignment,no-redef]

from . import (
    bridge,
    capabilities,
    fetch,
    index,
    materials,
    matrix,
    methods,
    planner,
    tools,
)

_ASSETS = Path(__file__).parent.parent / "assets"

mcp = FastMCP(
    "designsafe",
    instructions=(
        "Scientific workflow actions for DesignSafe, scoped to a bounded "
        "subset of the quoFEM pipeline for geotechnical earthquake "
        "engineering with OpenSees as the forward solver. "
        "supported_capabilities() is the authority on what this server "
        "does; decline requests outside it by naming that list. "
        "Start every run request with "
        "plan_simulation; it walks the OpenSees decision matrix and returns "
        "the app, the tested snippet, and any facts still missing. Do not "
        "choose an app yourself. For calibration or UQ studies start with "
        "plan_calibration, and consult describe_material for the model's "
        "parameters, sensitivities, and calibration sequence before "
        "building inputs. Compose runs from tested snippets "
        "(search_snippets) and ground context with search_community over the "
        "local corpus, never from memory of the API. Before submit_job, "
        "always: validate_job, estimate_cost, then show the user which "
        "snippet, pinned versions, cost, and outputs, and obtain approval "
        "via approve_submission. Finish every compute action with "
        "write_manifest so the run reproduces without the chat."
    ),
)

for fn in (
    capabilities.supported_capabilities,
    planner.plan_simulation,
    methods.plan_calibration,
    methods.calibration_options,
    materials.describe_material,
    tools.search_snippets,
    index.search_community,
    index.search_docs,
    index.corpus_status,
    index.reindex,
    fetch.fetch_corpus,
    matrix.opensees_matrix,
    tools.describe_app,
    tools.stage_inputs,
    tools.build_job_request,
    tools.validate_job,
    tools.estimate_cost,
    tools.approve_submission,
    tools.submit_job,
    tools.job_status,
    tools.get_results,
    tools.build_workflow_preview,
    tools.write_manifest,
    *bridge.DERIVED_TOOLS,
):
    mcp.tool()(fn)


@mcp.resource("designsafe://assets/opensees-decision-matrix.png", mime_type="image/png")
def opensees_matrix_image() -> bytes:
    """The training deck's OpenSees decision matrix, as shown to humans."""
    return (_ASSETS / "opensees-decision-matrix.png").read_bytes()


@mcp.resource("designsafe://assets/resource-selection-flowchart.png", mime_type="image/png")
def resource_flowchart_image() -> bytes:
    """Which DesignSafe resource to use: the deck's decision flowchart."""
    return (_ASSETS / "resource-selection-flowchart.png").read_bytes()


if __name__ == "__main__":
    mcp.run()
