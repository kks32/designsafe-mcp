"""MCP server exposing DesignSafe scientific actions.

Run: python -m designsafe_mcp.server  (stdio transport)
Register in an MCP host (Claude Code/Desktop, jupyter-ai) as a stdio server.
"""

from pathlib import Path

try:  # mcp >= 2.0
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP

from . import index, matrix, tools

_ASSETS = Path(__file__).parent.parent / "assets"

mcp = FastMCP(
    "designsafe",
    instructions=(
        "Scientific workflow actions for DesignSafe. Scope: OpenSees and quoFEM simulation workflows. Compose runs from "
        "tested snippets (search_snippets) and ground context with "
        "search_community over the local corpus, never from memory of the API. "
        "Before submit_job, always: validate_job, estimate_cost, then show "
        "the user which snippet, pinned versions, cost, and outputs, and "
        "obtain approval via approve_submission. Finish every compute "
        "action with write_manifest so the run reproduces without the chat."
    ),
)

for fn in (
    tools.search_snippets,
    index.search_community,
    index.reindex,
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
