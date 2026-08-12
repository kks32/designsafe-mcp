"""The calibration method matrix and its planner.

Same design as the OpenSees matrix: the options an expert would weigh
are encoded as data, the choice procedure is deterministic, and the
language model's job is to supply facts and relay questions. Every
option maps to something actually runnable on DesignSafe today, with
its execution status stated rather than implied.
"""

from typing import Any

from .tools import search_snippets

CALIBRATION_OPTIONS: list[dict[str, Any]] = [
    {
        "method": "global-sensitivity",
        "what": "Sobol indices over the parameter space; screening, not "
        "fitting. Run first when more parameters are uncertain than data "
        "can constrain.",
        "engine": "quoFEM (SimCenterUQ/Dakota) on simcenter-uq-stampede3",
        "returns": "first-order and total Sobol indices per QoI",
        "status": "tested",
        "snippet": "quofem-sensitivity-v1",
    },
    {
        "method": "bayesian-calibration",
        "what": "Posterior distribution on parameters given observations, "
        "via Transitional MCMC. The choice when the answer must carry "
        "uncertainty into a downstream prediction.",
        "engine": "quoFEM (UCSD_UQ TMCMC) on simcenter-uq-stampede3",
        "returns": "posterior samples per parameter, ready for forward "
        "propagation",
        "cost_note": "particles x TMCMC stages model runs (the UW example "
        "uses 100 particles); the model must run in seconds to minutes",
        "status": "candidate (UW notebook mirrored, not yet executed by "
        "the corpus harness)",
        "snippet": "quofem-bayesian-calibration-uw",
    },
    {
        "method": "deterministic-calibration",
        "what": "Point estimate by nonlinear least squares (Dakota "
        "NL2SOL). Cheapest; right when a single best-fit parameter set "
        "suffices and residuals are well-behaved.",
        "engine": "quoFEM (Dakota) on simcenter-uq-stampede3",
        "returns": "best-fit parameter vector and residuals",
        "status": "available in quoFEM, no local tested example yet",
        "snippet": None,
    },
    {
        "method": "forward-propagation",
        "what": "Push parameter distributions (prior or posterior) "
        "through the model. The validation step after calibration and "
        "the bridge to system-level prediction.",
        "engine": "quoFEM on simcenter-uq-stampede3, or a dapi/PyLauncher "
        "sweep when the forward model is not quoFEM-wrapped",
        "returns": "QoI distributions / prediction intervals",
        "status": "tested (quoFEM forward example runs via dapi; sweeps "
        "are the resonance and OpenSees pylauncher snippets)",
        "snippet": "resonance-pylauncher-sweep-v1",
    },
    {
        "method": "sweep-fit",
        "what": "Grid or LHS sweep on HPC plus a local fit. The fallback "
        "when quoFEM cannot wrap the model or the QoI needs custom "
        "post-processing.",
        "engine": "python-s3 + PyLauncher via dapi; fit locally",
        "returns": "response surface and best-fit region; no formal "
        "posterior",
        "status": "tested (mechanism is the pylauncher sweep + ML-DAG "
        "snippets)",
        "snippet": "opensees-ml-dag-v1",
    },
]


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
        "steps": steps,
        "matrix_path": path,
        "open_questions": open_questions,
        "snippets": snippets,
        "note": "Statuses marked 'candidate' or 'no local tested example' "
        "must be executed and admitted to the corpus before an agent "
        "composes them unattended.",
    }
