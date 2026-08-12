"""Notebook API-currency classification.

The corpus teaches agents whatever API surface it retrieves, so every
indexed notebook carries its class and search results flag stale ones.
"""

import json
import re
from pathlib import Path

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
    current = re.search(r"ds\.jobs\.generate|ds\.jobs\.parametric_sweep|"
                        r"dapi\.workflows|from dapi import DSClient", code)
    old = re.search(r"dapi\.auth\.init|generate_job_info|dapi\.jobs\.get_status|"
                    r"from agavepy|dapi\.jobs\.submit_job", code)
    raw = re.search(r"from tapipy|Tapis\(|t\.jobs\.submitJob|getClient", code)
    submits = re.search(r"submitJob|jobs\.submit|parametric_sweep|pipeline", code)
    if current:
        return "current-dapi"
    if old:
        return "old-dapi"
    if raw:
        return "raw-tapisv3"
    if not submits:
        return "local-only"
    return "unclassified"


