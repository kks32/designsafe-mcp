"""Corpus consistency: the snippets, the notebooks, and the audit agree.

The eval philosophy is that notebooks are the ground truth. These tests
pin that: every tested snippet's source notebook exists, uses the
current dapi surface, and actually exercises the app the snippet
claims. A failure here means the corpus is lying to agents.
"""

from pathlib import Path

import yaml

from designsafe_mcp.audit import CURRENT, classify, code_of

ROOT = Path(__file__).parent.parent
SNIPPETS = yaml.safe_load((ROOT / "designsafe_mcp" / "snippets.yaml").read_text())


def _source_path(source: str) -> Path:
    rel = Path(source)
    if rel.parts[0] in ("dapi", "workflows"):
        return ROOT.parent / rel
    return ROOT / rel


def test_every_tested_snippet_source_exists():
    for s in SNIPPETS["snippets"]:
        assert _source_path(s["source"]).exists(), s["id"]


def test_every_tested_snippet_notebook_is_current_dapi():
    for s in SNIPPETS["snippets"]:
        code = code_of(_source_path(s["source"]))
        assert classify(code) in CURRENT, (
            f"{s['id']}: source notebook is stale; modernize it or "
            "retire the snippet")


def test_every_tested_snippet_notebook_uses_its_app():
    for s in SNIPPETS["snippets"]:
        code = code_of(_source_path(s["source"]))
        assert s["app_id"] in code, (
            f"{s['id']}: notebook never references app '{s['app_id']}'")


def test_candidates_are_not_retrievable():
    from designsafe_mcp.tools import search_snippets

    retrievable = {s["id"] for s in SNIPPETS["snippets"]}
    for c in SNIPPETS.get("candidates", []):
        assert c["id"] not in retrievable
        hits = search_snippets(c["id"].replace("-", " "))
        assert all(h["id"] != c["id"] for h in hits)


def test_stale_notebooks_carry_warnings_in_search():
    from designsafe_mcp.index import search_community

    hits = search_community("tapipy submitJob freeFieldEffective TAPISV3")
    stale_hits = [h for h in hits if "warning" in h]
    assert stale_hits, "expected at least one flagged stale passage"
    assert "stale API surface" in stale_hits[0]["warning"]


def test_capability_snippets_exist_in_corpus():
    from designsafe_mcp.capabilities import supported_capabilities

    tested = {s["id"] for s in SNIPPETS["snippets"]}
    candidates = {c["id"] for c in SNIPPETS.get("candidates", [])}
    caps = supported_capabilities()
    assert caps["out_of_scope"]
    for domain in caps["domains"]:
        for cap in domain["capabilities"]:
            if cap["snippet"] is None:
                continue
            if cap["status"] == "tested":
                assert cap["snippet"] in tested, cap["what"]
            elif cap["status"] == "candidate":
                assert cap["snippet"] in candidates, cap["what"]


def test_sources_resolve_local_first_then_fetched_cache(tmp_path):
    from designsafe_mcp import fetch

    spec = {"name": "x", "local": [tmp_path / "missing"], "github": None}
    assert fetch.resolve_source(spec) == []
    cached = fetch.CACHE / "x"
    cached.mkdir(parents=True, exist_ok=True)
    try:
        assert fetch.resolve_source(spec) == [cached]
        present = tmp_path / "present"
        present.mkdir()
        spec["local"] = [present]
        assert fetch.resolve_source(spec) == [present]
    finally:
        cached.rmdir()


def test_corpus_status_names_every_logical_source():
    from designsafe_mcp.index import corpus_status

    status = corpus_status()
    names = {s["name"] for s in status["sources"]}
    assert names == {"notebooks", "dapi", "ds-workflows", "quofem-docs"}
    assert status["total_documents"] > 1000
    for s in status["sources"]:
        assert s["via"] in ("local", "fetched-cache", "absent")


def test_search_docs_returns_only_documentation_sources():
    from designsafe_mcp.index import _DOC_MARKERS, search_docs

    hits = search_docs("TMCMC Bayesian calibration quoFEM")
    assert hits, "quoFEM docs should be fetched and indexed"
    for h in hits:
        assert any(m in h["source"] for m in _DOC_MARKERS), h["source"]
        assert h["indexed"]


def test_quofem_docs_is_a_logical_source():
    from designsafe_mcp.index import corpus_status

    status = corpus_status()
    quofem = next(s for s in status["sources"] if s["name"] == "quofem-docs")
    assert quofem["via"] in ("fetched-cache", "absent")
