"""Live fetching of grounding sources.

No deployment can assume sibling checkouts of dapi and the
ds-workflows book, and the UW notebooks live in DesignSafe
CommunityData, not in this repo. Each logical source therefore knows
three ways to exist, tried in order: an environment override, a local
sibling checkout (developer machines), and a fetched cache under
corpus/ populated live from the canonical remote (everywhere else).

fetch_corpus() downloads the public GitHub sources; the CommunityData
mirror needs Tapis credentials and stays in scripts/mirror_notebooks.py.
"""

import io
import tarfile
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
CACHE = ROOT / "corpus"

LOGICAL_SOURCES: list[dict[str, Any]] = [
    {
        "name": "notebooks",
        "what": "UW CommunityData notebooks, models, and reference PDFs",
        "local": [ROOT / "notebooks"],
        "remote": "tapis://designsafe.storage.community (run "
        "scripts/mirror_notebooks.py, needs Tapis auth) and "
        "scripts/fetch_references.py for the manuals",
        "github": None,
    },
    {
        "name": "dapi",
        "what": "dapi executed examples and user guide",
        "local": [ROOT.parent / "dapi" / "examples",
                  ROOT.parent / "dapi" / "docs"],
        "remote": "github.com/DesignSafe-CI/dapi",
        "github": {"repo": "DesignSafe-CI/dapi", "branch": "main",
                   "subdirs": ["examples", "docs", "skills"]},
    },
    {
        "name": "ds-workflows",
        "what": "the ds-workflows book: concepts, apps, DAGs, containers",
        "local": [ROOT.parent / "workflows" / "guide",
                  ROOT.parent / "workflows" / "advanced"],
        "remote": "github.com/DesignSafe-CI/ds-workflows",
        "github": {"repo": "DesignSafe-CI/ds-workflows", "branch": "main",
                   "subdirs": ["guide", "advanced"]},
    },
    {
        "name": "quofem-docs",
        "what": "SimCenter quoFEM documentation source: UQ methods, "
        "examples, verification (from the SimCenter docs monorepo)",
        "local": [],
        "remote": "github.com/NHERI-SimCenter/SimCenterDocumentation",
        "github": {"repo": "NHERI-SimCenter/SimCenterDocumentation",
                   "branch": "master",
                   "subdirs": ["docs/common/user_manual",
                               "docs/common/technical_manual"]},
    },
]

_KEEP = (".ipynb", ".md", ".rst", ".py", ".tcl", ".json", ".pdf")


def resolve_source(spec: dict[str, Any]) -> list[Path]:
    """Paths this logical source resolves to right now, tried in order:
    local checkout first, then the fetched cache."""
    local = [p for p in spec["local"] if p.exists()]
    if local:
        return local
    cached = CACHE / spec["name"]
    if cached.exists():
        return [cached]
    return []


def fetch_corpus(source: str = "") -> dict[str, Any]:
    """Fetch grounding sources live from their canonical GitHub repos
    into corpus/, for deployments without local checkouts.

    source: fetch just one logical source by name; empty fetches every
    GitHub-backed source. CommunityData is not fetched here (needs
    Tapis auth; see corpus_status for the command). Run reindex after.
    """
    report: dict[str, Any] = {}
    for spec in LOGICAL_SOURCES:
        if source and spec["name"] != source:
            continue
        gh = spec["github"]
        if gh is None:
            report[spec["name"]] = f"not fetchable here: {spec['remote']}"
            continue
        url = (f"https://github.com/{gh['repo']}/archive/refs/heads/"
               f"{gh['branch']}.tar.gz")
        with urllib.request.urlopen(url, timeout=120) as resp:
            data = resp.read()
        dest = CACHE / spec["name"]
        kept = 0
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile() or not member.name.endswith(_KEEP):
                    continue
                rel = Path(*Path(member.name).parts[1:])  # strip repo-branch/
                if gh["subdirs"] and not any(
                        str(rel).startswith(f"{s}/") for s in gh["subdirs"]):
                    continue
                out = dest / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                extracted = tar.extractfile(member)
                if extracted:
                    out.write_bytes(extracted.read())
                    kept += 1
        import time

        (dest / ".fetched").write_text(
            time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        report[spec["name"]] = f"{kept} files -> {dest}"
    return report
