"""The OpenSees decision matrix as a typed tool.

The matrix itself is data (knowledge/opensees_matrix.yaml), from the
training deck and the ds-workflows book; the original slide ships as an
MCP resource so a host can show the human the same table the agent
used. This module only loads and serves it.
"""

from typing import Any

from .knowledge import load

VARIANTS: list[dict[str, Any]] = load("opensees_matrix")["variants"]
PLATFORM_MATRIX: list[dict[str, Any]] = load("opensees_matrix")["platform_matrix"]


def opensees_matrix() -> dict[str, Any]:
    """Which OpenSees to use when: the decision matrix from the training deck.

    Returns the variant table (variant -> app_id -> when), the full
    scope x platform x interface matrix with its legend, and the path of
    the original slide image for display to the user.
    """
    return dict(load("opensees_matrix"))
