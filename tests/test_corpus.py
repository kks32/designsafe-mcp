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
