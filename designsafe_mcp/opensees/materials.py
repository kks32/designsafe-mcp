"""Constitutive-model knowledge for calibration planning.

Content lives in knowledge/materials/<model>.yaml, transcribed from
each model's own manual with page citations, never from a language
model's recall. This module only loads and serves it.
"""

from pathlib import Path
from typing import Any

import yaml

_DIR = Path(__file__).parent.parent / "knowledge" / "opensees" / "materials"


def _models() -> dict[str, dict[str, Any]]:
    out = {}
    for f in _DIR.glob("*.yaml"):
        out[f.stem.replace("-", "").replace("_", "")] = yaml.safe_load(
            f.read_text())
    return out


def describe_material(model: str) -> dict[str, Any]:
    """Parameters, sensitivities, and the calibration sequence for a
    constitutive model, transcribed from its manual with page citations.

    Use this before planning a calibration: it answers which parameters
    exist, what data informs each one, and in what order to calibrate.
    """
    key = model.strip().lower().replace("-", "").replace("_", "")
    models = _models()
    if key not in models:
        return {"error": f"no knowledge entry for '{model}'",
                "known": sorted(models),
                "note": "search_community may still find community "
                "notebooks that use it"}
    return models[key]
