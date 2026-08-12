"""Auto-derived dapi tools: introspect, never describe.

dapi's own signatures and docstrings are the single source of ground
truth for what its operations accept. The tools below are generated
from that surface at import time, so a dapi release that adds or
renames a parameter changes these schemas without anyone editing this
repo; nothing here re-declares what dapi already declares.

Only curation happens in this file: which read-only operations are
agent-safe to expose. Anything that spends SUs or mutates state stays
hand-written in tools.py behind the approval gate, and anything with a
*args/**kwargs passthrough signature cannot be exposed (no schema to
derive; the fix is a typed signature in dapi, not a description here).
"""

import inspect
from typing import Any

from .tools import _client, _mock

# tool name -> (attribute path on DSClient, unbound function for schema)
_EXPOSED: dict[str, tuple[str, Any]] = {}


def _curate() -> None:
    from dapi.client import AppMethods, JobMethods, SystemMethods

    for tool, path, fn in (
        ("list_my_jobs", "jobs.list", JobMethods.list),
        ("list_queues", "systems.queues", SystemMethods.queues),
        ("list_systems", "systems.list", SystemMethods.list),
        ("list_app_templates", "apps.templates", AppMethods.templates),
    ):
        params = [p for p in inspect.signature(fn).parameters.values()
                  if p.name != "self"]
        if any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params):
            continue  # passthrough signature; nothing to derive
        _EXPOSED[tool] = (path, fn)


def _serialize(value: Any) -> Any:
    if hasattr(value, "to_dict"):  # pandas frames from output="df"
        return value.to_dict("records")
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    return value


def _make(tool: str, path: str, fn: Any) -> Any:
    def call(**kwargs: Any) -> Any:
        if _mock():
            return {"error": f"{tool} is live-only; not available in "
                    "mock mode"}
        target: Any = _client()
        for part in path.split("."):
            target = getattr(target, part)
        return _serialize(target(**kwargs))

    import dapi

    sig = inspect.signature(fn)
    call.__signature__ = sig.replace(  # type: ignore[attr-defined]
        parameters=[p for p in sig.parameters.values() if p.name != "self"])
    call.__name__ = tool
    call.__doc__ = (
        f"{(fn.__doc__ or '').strip()}\n\n"
        f"[schema introspected from dapi {dapi.__version__} "
        f"({path}); this tool is generated, not maintained by hand]")
    return call


_curate()
DERIVED_TOOLS = [_make(tool, path, fn)
                 for tool, (path, fn) in _EXPOSED.items()]
