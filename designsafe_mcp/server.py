"""MCP server exposing DesignSafe scientific actions.

Run: python -m designsafe_mcp.server  (stdio transport)
Register in an MCP host (Claude Code/Desktop, jupyter-ai) as a stdio server.
"""

from mcp.server.fastmcp import FastMCP

from . import index, matrix, tools

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
    matrix.eval_cases,
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


if __name__ == "__main__":
    mcp.run()
