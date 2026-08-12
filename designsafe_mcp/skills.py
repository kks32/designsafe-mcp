"""Serve skills as MCP prompts.

Skills are markdown playbooks with frontmatter. Skills about dapi's
mechanics live in the dapi repo next to the code they describe (one
ground truth, updated in the same PR as the feature) and reach this
server through the same resolution as dapi's docs: local checkout
first, live-fetched corpus cache otherwise. Scientific playbooks, when
they exist, live in this repo's skills/. MCP prompts are part of the
protocol, so any MCP client gets the same skills; nothing here is
Claude-specific.
"""

import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent

_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _skill_dirs() -> list[Path]:
    from .fetch import LOGICAL_SOURCES, resolve_source

    dirs = [ROOT / "skills"]
    for spec in LOGICAL_SOURCES:
        if spec["name"] != "dapi":
            continue
        for path in resolve_source(spec):
            # local resolve gives .../dapi/examples and .../dapi/docs;
            # the cache gives corpus/dapi. skills/ sits beside both.
            root = path.parent if path.name in ("examples", "docs") else path
            dirs.append(root / "skills")
    return dirs


def load_skills() -> list[dict[str, Any]]:
    """Every skill the server can currently resolve, deduplicated by
    name with local checkouts winning over fetched caches."""
    seen: dict[str, dict[str, Any]] = {}
    for d in _skill_dirs():
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            text = f.read_text(errors="ignore")
            m = _FRONT.match(text)
            meta: dict[str, str] = {}
            if m:
                for line in m.group(1).splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()
            name = meta.get("name", f.stem)
            if name in seen:
                continue
            seen[name] = {
                "name": name,
                "description": meta.get("description", ""),
                "body": text[m.end():] if m else text,
                "source": str(f),
            }
    return list(seen.values())


def register(mcp: Any) -> int:
    """Register every resolved skill as an MCP prompt."""
    def _make(body: str) -> Any:
        def prompt() -> str:
            return body
        return prompt

    count = 0
    for s in load_skills():
        fn = _make(s["body"])
        fn.__name__ = s["name"].replace("-", "_")
        fn.__doc__ = s["description"]
        mcp.prompt(name=s["name"], description=s["description"])(fn)
        count += 1
    return count
