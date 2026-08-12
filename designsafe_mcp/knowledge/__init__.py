"""Loader for the knowledge/ data layer.

Domain content (decision matrices, capabilities, calibration methods,
material knowledge, API-surface definitions) lives in YAML under
knowledge/, where a domain expert can read and edit it without touching
Python. Modules load it here; logic stays in code, knowledge does not.
"""

from functools import cache
from pathlib import Path
from typing import Any

import yaml

_DIR = Path(__file__).parent


@cache
def load(name: str) -> dict[str, Any]:
    return yaml.safe_load((_DIR / f"{name}.yaml").read_text())
