"""The calibration method matrix and its planner.

Same design as the OpenSees matrix: the options an expert would weigh
are encoded as data, the choice procedure is deterministic, and the
language model's job is to supply facts and relay questions. Every
option maps to something actually runnable on DesignSafe today, with
its execution status stated rather than implied.
"""

from typing import Any

from ..knowledge import load
from ..tools import search_snippets

CALIBRATION_OPTIONS: list[dict[str, Any]] = load("opensees/calibration_methods")["options"]


def calibration_options() -> list[dict[str, Any]]:
    """Every calibration-stage method runnable on DesignSafe, with its
    engine, what it returns, and its tested/candidate status."""
    return CALIBRATION_OPTIONS


def plan_calibration(
    request: str,
    material_model: str | None = None,
    n_uncertain_parameters: int | None = None,
    uncertainty_required: bool | None = None,
    quofem_wrappable: bool | None = None,
    screened: bool | None = None,
) -> dict[str, Any]:
    """Plan a calibration study from the method matrix.

    Pass what you know; unanswered facts come back as open questions.
    uncertainty_required: must the result carry parameter uncertainty
        into a downstream prediction (posterior), or is a best-fit
        point enough?
    quofem_wrappable: can quoFEM drive the model (OpenSees main script
        with parameter placeholders and a scalar-QoI postprocessor)?
    screened: has a sensitivity study already reduced the parameter set?
    """
    open_questions: list[str] = []
    path: list[str] = []
    steps: list[dict[str, Any]] = []

    if quofem_wrappable is False:
        path.append("model not quoFEM-wrappable -> sweep-fit fallback")
        return _assemble(request, ["sweep-fit"], path, open_questions)

    many = (n_uncertain_parameters or 0) > 4
    if n_uncertain_parameters is None:
        open_questions.append(
            "How many parameters are uncertain? (For PM4Sand the manual "
            "calibrates three primaries: Dr, G0, hpo; see "
            "describe_material.)")
    if many and not screened:
        path.append(f"{n_uncertain_parameters} uncertain parameters -> "
                    "screen with global sensitivity before fitting")
        steps.append(_option("global-sensitivity"))

    if uncertainty_required is None:
        open_questions.append(
            "Must the calibrated parameters carry uncertainty into a "
            "downstream prediction (posterior), or is a best-fit point "
            "estimate enough?")
        return _assemble(request, [s["method"] for s in steps], path,
                         open_questions, undecided=True)

    if uncertainty_required:
        path.append("uncertainty must propagate -> Bayesian calibration "
                    "(TMCMC), then forward propagation of the posterior")
        steps.append(_option("bayesian-calibration"))
        steps.append(_option("forward-propagation"))
    else:
        path.append("point estimate suffices -> deterministic calibration")
        steps.append(_option("deterministic-calibration"))

    plan = _assemble(request, [s["method"] for s in steps], path,
                     open_questions)
    if material_model:
        plan["material_note"] = (
            f"Call describe_material('{material_model}') for the "
            "parameter table, sensitivity map, and the manual's "
            "calibration sequence before building inputs.")
    return plan


def _option(method: str) -> dict[str, Any]:
    return next(o for o in CALIBRATION_OPTIONS if o["method"] == method)


def _assemble(request: str, methods: list[str], path: list[str],
              open_questions: list[str],
              undecided: bool = False) -> dict[str, Any]:
    steps = [_option(m) for m in methods]
    snippets = []
    for s in steps:
        if s["snippet"]:
            hits = search_snippets(s["snippet"].replace("-", " "))
            snippets += [{"id": h["id"], "source": h["source"]}
                         for h in hits[:1]]
    return {
        "decision": None if undecided else {
            "pipeline": [s["method"] for s in steps],
            "engines": sorted({s["engine"].split(" on ")[0] for s in steps}),
        },
        "required_inputs": [
            ("which model: the main script (e.g. the .tcl driving the "
             "element test or analysis)"),
            "which parameters: names, and ranges or priors for each",
            ("what data: the observation/calibration file and which "
             "response quantities (QoIs) it contains"),
            "allocation to charge",
        ],
        "ask_the_user": "Relay any required_inputs the request did not "
        "provide before building the job; the engine can be decided "
        "while these stay open, but the run cannot be built without "
        "them.",
        "steps": steps,
        "matrix_path": path,
        "open_questions": open_questions,
        "snippets": snippets,
        "note": "Statuses marked 'candidate' or 'no local tested example' "
        "must be executed and admitted to the corpus before an agent "
        "composes them unattended.",
    }
