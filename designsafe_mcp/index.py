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
from typing import Any

ROOT = Path(__file__).parent.parent

# Grounding sources resolve through fetch.LOGICAL_SOURCES: local
# checkouts when present, the live-fetched corpus/ cache otherwise
# (fetch_corpus pulls the public GitHub sources). An environment
# override (DESIGNSAFE_MCP_SOURCES, colon-separated paths) replaces
# the whole list. corpus_status() reports what actually resolved, so
# a degraded index is visible instead of silent.
def _sources() -> list[Path]:
    import os

    env = os.environ.get("DESIGNSAFE_MCP_SOURCES")
    if env:
        return [Path(p).expanduser() for p in env.split(":") if p]
    from .fetch import LOGICAL_SOURCES, resolve_source

    paths: list[Path] = []
    for spec in LOGICAL_SOURCES:
        paths.extend(resolve_source(spec))
    return paths


_CACHE = ROOT / ".index_cache.json"
_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")


def _passages_from_notebook(path: Path) -> list[str]:
    try:
        nb = json.loads(path.read_text(errors="ignore"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return []
    out = []
    for c in nb.get("cells", []):
        src = "".join(c.get("source", []))
        if c.get("cell_type") == "markdown" and len(src.strip()) > 60:
            out.append(src.strip()[:800])
        elif c.get("cell_type") == "code" and len(src.strip()) > 40:
            out.append("```python\n" + src.strip()[:600] + "\n```")
    return out


def _passages_from_pdf(path: Path) -> list[str]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
    except Exception:  # noqa: BLE001 - unreadable or pypdf absent; skip
        return []
    out = []
    for page in reader.pages:
        text = " ".join((page.extract_text() or "").split())
        if len(text) > 200:
            out.append(text[:1200])
    return out


def _build() -> dict[str, Any]:
    import time

    docs: list[dict[str, Any]] = []
    per_source: dict[str, Any] = {}
    for base in _sources():
        if not base.exists():
            per_source[str(base)] = {"present": False, "documents": 0}
            continue
        start = len(docs)
        for p in base.rglob("*"):
            if "__pycache__" in str(p) or "_staged" in str(p):
                continue
            rel = str(p.relative_to(ROOT.parent))
            if p.suffix == ".ipynb":
                from .audit import classify, code_of

                status = classify(code_of(p))
                for i, passage in enumerate(_passages_from_notebook(p)):
                    docs.append({"source": rel, "cell": i, "text": passage,
                                 "api_status": status})
            elif p.suffix == ".pdf":
                for i, passage in enumerate(_passages_from_pdf(p)):
                    docs.append({"source": f"{rel}#page{i + 1}", "cell": i,
                                 "text": passage})
            elif p.suffix in (".tcl", ".py", ".md", ".rst",
                              ".json") and p.is_file():
                try:
                    head = p.read_text(errors="ignore")[:600]
                except OSError:  # unreadable file in the mirror; skip it
                    continue
                docs.append({"source": rel, "cell": 0, "text": head})
        per_source[str(base)] = {"present": True,
                                 "documents": len(docs) - start}
    payload = {"built": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "sources": per_source, "docs": docs}
    _CACHE.write_text(json.dumps(payload))
    return payload


def _load() -> dict[str, Any]:
    if _CACHE.exists():
        payload = json.loads(_CACHE.read_text())
        if isinstance(payload, dict) and "docs" in payload:
            return payload
    return _build()


# Passages from these path fragments are documentation rather than
# community notebooks; search_docs filters on them. The backend is the
# local TF-IDF index today and the DesignSafe Ask AI knowledge graph
# (Neo4j) later; the tool contract does not change when it swaps.
_DOC_MARKERS = ("dapi/docs", "workflows/guide", "workflows/advanced",
                "ds-workflows", "quofem-docs", "notebooks/references")


def search_docs(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Search the documentation corpus: the dapi user guide, the
    ds-workflows book, SimCenter quoFEM docs, and reference manuals.

    Grounding only, never the source of orchestration code; snippets
    remain the only source an agent may compose runs from. Results
    carry source and index stamp. Backend today is a local index over
    live-fetched docs; the Ask AI knowledge graph replaces it later
    behind this same tool.
    """
    hits = _search(query, limit * 4)
    docs = [h for h in hits
            if any(m in h["source"] for m in _DOC_MARKERS)]
    return docs[:limit]


def search_community(query: str, limit: int = 8) -> list[dict[str, Any]]:
    """Search every local notebook, model, and script for aligned passages.

    Returns the matching text itself with its source path and the
    index build stamp, so the caller can ground a workflow in what the
    community actually wrote and knows how fresh that knowledge is.
    Call corpus_status() to see which sources the index covers; use
    search_docs for documentation-only search.
    """
    return _search(query, limit)


def _search(query: str, limit: int) -> list[dict[str, Any]]:
    payload = _load()
    docs = payload["docs"]
    built = payload.get("built", "unknown")
    n = len(docs)
    df: Counter = Counter()
    tokenized = []
    for d in docs:
        toks = {w.lower() for w in _WORD.findall(d["text"])}
        tokenized.append(toks)
        df.update(toks)
    q = [w.lower() for w in _WORD.findall(query)]
    scored = []
    for d, toks in zip(docs, tokenized):
        s = sum(math.log(n / (1 + df[t])) for t in q if t in toks)
        if s > 0:
            scored.append((s, d))
    scored.sort(key=lambda x: -x[0])
    out = []
    for s, d in scored[:limit]:
        hit = {"score": round(s, 2), "source": d["source"],
               "indexed": built, "passage": d["text"][:500]}
        status = d.get("api_status")
        if status and status not in ("current-dapi", "local-only"):
            hit["warning"] = (
                f"stale API surface ({status}); do not copy its "
                "orchestration code, use the current dapi equivalent")
        out.append(hit)
    return out


def corpus_status() -> dict[str, Any]:
    """What the grounding index covers and where it came from: each
    logical source (UW notebooks, dapi, the ds-workflows book), how it
    resolved (local checkout, fetched cache, or absent), how many
    passages it contributes, and when the index was built. An absent
    source means degraded grounding; say so rather than answering from
    partial knowledge, and fetch_corpus() can fill the gap live."""
    from .fetch import LOGICAL_SOURCES, resolve_source

    payload = _load()
    indexed = payload.get("sources", {})
    sources = []
    for spec in LOGICAL_SOURCES:
        paths = resolve_source(spec)
        docs = sum(indexed.get(str(p), {}).get("documents", 0)
                   for p in paths)
        sources.append({
            "name": spec["name"],
            "what": spec["what"],
            "resolved": [str(p) for p in paths] or None,
            "via": ("local" if paths and "corpus" not in str(paths[0])
                    else "fetched-cache" if paths else "absent"),
            "documents_indexed": docs,
            "fetch": None if paths else (
                "fetch_corpus() then reindex()" if spec["github"]
                else spec["remote"]),
        })
    return {
        "built": payload.get("built", "unknown"),
        "total_documents": len(payload["docs"]),
        "sources": sources,
    }


def reindex() -> dict[str, Any]:
    """Rebuild the index after mirroring new notebooks or references."""
    payload = _build()
    return {"documents": len(payload["docs"]), "built": payload["built"],
            "sources": payload["sources"]}
