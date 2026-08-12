"""Text index over the local corpus: tested examples and community data.

search_community() returns the passages that match, with their source,
so an agent reads aligned context instead of guessing from titles. The
index is rebuilt lazily and cached; pure stdlib, TF-IDF scored.
"""

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).parent.parent
SOURCES = [
    ROOT / "community_data",                      # UW community notebooks and models
    ROOT.parent / "dapi" / "examples",            # our executed, tested examples
    ROOT.parent / "dapi" / "docs",                # dapi user guide (API reference)
    ROOT.parent / "workflows" / "guide",          # ds-workflows book: concepts
    ROOT.parent / "workflows" / "advanced",       # ds-workflows book: apps, DAGs, containers
]
_CACHE = ROOT / ".index_cache.json"
_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")


def _passages_from_notebook(path: Path) -> List[str]:
    try:
        nb = json.loads(path.read_text(errors="ignore"))
    except Exception:
        return []
    out = []
    for c in nb.get("cells", []):
        src = "".join(c.get("source", []))
        if c.get("cell_type") == "markdown" and len(src.strip()) > 60:
            out.append(src.strip()[:800])
        elif c.get("cell_type") == "code" and len(src.strip()) > 40:
            out.append("```python\n" + src.strip()[:600] + "\n```")
    return out


def _build() -> List[Dict[str, Any]]:
    docs = []
    for base in SOURCES:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if "__pycache__" in str(p) or "_staged" in str(p):
                continue
            rel = str(p.relative_to(ROOT.parent))
            if p.suffix == ".ipynb":
                for i, passage in enumerate(_passages_from_notebook(p)):
                    docs.append({"source": rel, "cell": i, "text": passage})
            elif p.suffix in (".tcl", ".py", ".md", ".json") and p.is_file():
                try:
                    head = p.read_text(errors="ignore")[:600]
                except Exception:
                    continue
                docs.append({"source": rel, "cell": 0, "text": head})
    _CACHE.write_text(json.dumps(docs))
    return docs


def _load() -> List[Dict[str, Any]]:
    if _CACHE.exists():
        return json.loads(_CACHE.read_text())
    return _build()


def search_community(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Search every local notebook, model, and script for aligned passages.

    Returns the matching text itself with its source path, so the caller
    can ground a workflow in what the community actually wrote.
    """
    docs = _load()
    n = len(docs)
    df: Counter = Counter()
    tokenized = []
    for d in docs:
        toks = set(w.lower() for w in _WORD.findall(d["text"]))
        tokenized.append(toks)
        df.update(toks)
    q = [w.lower() for w in _WORD.findall(query)]
    scored = []
    for d, toks in zip(docs, tokenized):
        s = sum(math.log(n / (1 + df[t])) for t in q if t in toks)
        if s > 0:
            scored.append((s, d))
    scored.sort(key=lambda x: -x[0])
    return [
        {"score": round(s, 2), "source": d["source"], "passage": d["text"][:500]}
        for s, d in scored[:limit]
    ]


def reindex() -> Dict[str, int]:
    """Rebuild the index after mirroring new community data."""
    return {"documents": len(_build())}
