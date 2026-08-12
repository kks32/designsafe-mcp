"""Notebook API-currency classification.

What counts as current, old, or raw API usage is defined in
knowledge/api_surfaces.yaml, per surface with markers and meaning; the
corpus index and NOTEBOOKS.md apply it. The corpus teaches agents
whatever it retrieves, so stale surfaces are flagged at search time.
"""

import json
import re
from pathlib import Path

from .knowledge import load

CURRENT = ("current-dapi", "local-only")


def code_of(nb_path: Path) -> str:
    try:
        nb = json.loads(nb_path.read_text(errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return ""
    return "\n".join("".join(c.get("source", []))
                     for c in nb.get("cells", [])
                     if c.get("cell_type") == "code")


def classify(code: str) -> str:
    spec = load("api_surfaces")
    for surface in spec["surfaces"]:
        if any(re.search(m, code) for m in surface["markers"]):
            return surface["status"]
    if not any(re.search(m, code) for m in spec["submission_markers"]):
        return "local-only"
    return "unclassified"
