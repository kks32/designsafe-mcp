"""The declared support surface of this server.

The capability map is data (knowledge/capabilities.yaml): scientific
domains one level above any tool, each capability naming how it is
served and whether it is tested. This module only loads and serves it;
requests outside the map are out of scope by design.
"""

from typing import Any

from .knowledge import load

DOMAINS: list[dict[str, Any]] = load("capabilities")["domains"]
OUT_OF_SCOPE: list[str] = load("capabilities")["out_of_scope"]


def supported_capabilities() -> dict[str, Any]:
    """What this server supports, by scientific domain.

    Consult this before promising anything. Every capability names how
    it is served and whether it is tested; 'candidate' and 'untested'
    entries need a human-run graduation before unattended use. Requests
    outside this map should be declined by pointing at out_of_scope.
    """
    return dict(load("capabilities"))
