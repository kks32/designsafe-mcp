"""plan_simulation: the scientific action above the job-lifecycle tools.

The agent brings facts about the problem; this tool walks the OpenSees
decision matrix deterministically and returns the plan: which variant,
which DesignSafe app, which tested snippet to compose from, what to run
next, and which facts are still missing. The language model extracts
facts and relays questions to the human. It does not make the decision;
the matrix does, so the same facts always produce the same plan.
"""

import re
from typing import Any

from ..tools import search_snippets

_SEQUENCE = [
    "describe_app", "stage_inputs", "build_job_request", "validate_job",
    "estimate_cost", "approve_submission (after human review)", "submit_job",
    "job_status / get_results", "write_manifest",
]


def _infer(request: str) -> dict[str, Any]:
    """Conservative fact extraction from the request text.

    Only unambiguous signals fill a fact; everything else stays None and
    comes back as an open question.
    """
    r = request.lower()
    facts: dict[str, Any] = {
        "model_language": None, "parallelism": None, "n_cases": None,
        "uq_or_calibration": None, "has_allocation": None, "pipeline": None,
        "named_variant": None,
    }
    # A request that names the variant or app outright has already
    # decided; record it so the matrix walk can honor the name.
    for pattern, variant in (
        (r"opensees[- ]?mp\b|opensees-mp-s3", "mp"),
        (r"opensees[- ]?sp\b", "sp"),
        (r"opensees[- ]?express", "express"),
        (r"openseespy|python-s3", "py"),
        (r"quofem|simcenter-uq", "quofem"),
    ):
        if re.search(pattern, r):
            facts["named_variant"] = variant
            break
    if re.search(r"openseespy|\.py\b|python model", r):
        facts["model_language"] = "python"
    elif re.search(r"\.tcl\b|tcl", r):
        facts["model_language"] = "tcl"
    if re.search(r"getpid|getnp|partition|subdomain|domain decomposition", r):
        facts["parallelism"] = "domain-decomposition"
    elif re.search(r"parallel (?:equation )?solver|(?:single|one) (?:large )?domain|opensees ?sp\b", r):
        facts["parallelism"] = "single-domain-parallel-solver"
    elif re.search(r"sweep|parameter stud|motions|pushover curves|realizations|cases\b", r):
        facts["parallelism"] = "many-independent-cases"
    elif re.search(r"\bserial\b|single (run|analysis|motion)\b", r):
        facts["parallelism"] = "serial"
    m = re.search(r"(\d+)\s*(?:runs?|motions?|cases?|values?|frequencies|models?|curves?)", r)
    if m:
        facts["n_cases"] = int(m.group(1))
        if facts["parallelism"] is None:
            facts["parallelism"] = "many-independent-cases"
    if re.search(r"calibrat|bayesian|sensitivit|sobol|uncertainty|quofem", r):
        facts["uq_or_calibration"] = True
    if re.search(r"no (?:\w+ )?allocation|without an? allocation|don'?t have an? allocation", r):
        facts["has_allocation"] = False
    elif re.search(r"allocation|reservation|class", r):
        facts["has_allocation"] = True
    if re.search(r"then (train|fit|plot|post-?process)|feeding|pipeline|hands-?off|workflow", r):
        facts["pipeline"] = True
    return facts


def plan_simulation(
    request: str,
    model_language: str | None = None,
    parallelism: str | None = None,
    n_cases: int | None = None,
    uq_or_calibration: bool | None = None,
    has_allocation: bool | None = None,
    pipeline: bool | None = None,
) -> dict[str, Any]:
    """Plan an OpenSees/quoFEM simulation from the decision matrix.

    Pass the facts you know; anything left None is inferred from the
    request only when unambiguous, and otherwise returned in
    open_questions for you to ask the user. The decision is the
    matrix's, not yours: do not override app_id, and compose the cells
    from the returned snippet, not from memory.

    model_language: "tcl" | "python"
    parallelism: "serial" | "domain-decomposition" |
                 "single-domain-parallel-solver" | "many-independent-cases"
    """
    inferred = _infer(request)
    facts = {
        "model_language": model_language or inferred["model_language"],
        "parallelism": parallelism or inferred["parallelism"],
        "n_cases": n_cases if n_cases is not None else inferred["n_cases"],
        "uq_or_calibration": uq_or_calibration if uq_or_calibration is not None
        else inferred["uq_or_calibration"],
        "has_allocation": has_allocation if has_allocation is not None
        else inferred["has_allocation"],
        "pipeline": pipeline if pipeline is not None else inferred["pipeline"],
    }
    open_questions: list[str] = []
    path: list[str] = []

    # Fork 0: the request names the variant; the name is the decision.
    named = inferred.get("named_variant")
    if named:
        path.append(f"request names the variant -> {named}")
        if named == "mp":
            return _plan("OpenSeesMP", "opensees-mp-s3",
                         "openseesmp multi-motion parallel", facts, path, [])
        if named == "sp":
            plan = _plan("OpenSeesSP", "opensees-s3",
                         "pm4sand site response opensees", facts, path, [])
            plan["decision"]["extra_app_args"] = [
                {"name": "Main Program", "arg": "OpenSeesSP"}]
            return plan
        if named == "express":
            return _plan("OpenSeesEXPRESS", "opensees-express",
                         "pm4sand site response", facts, path, [])
        if named == "py":
            query = ("resonance pylauncher sweep"
                     if facts["parallelism"] == "many-independent-cases"
                     else "oscillator single job first-job")
            return _plan("OpenSeesPy at scale", "python-s3", query,
                         facts, path, [])
        if named == "quofem":
            return _plan("quoFEM over OpenSees", "simcenter-uq-stampede3",
                         "quofem sensitivity calibration", facts, path, [])

    # Fork 1: UQ wraps everything else; quoFEM drives the model as its solver.
    if facts["uq_or_calibration"]:
        path.append("UQ/calibration wraps the model -> quoFEM")
        return _plan("quoFEM over OpenSees", "simcenter-uq-stampede3",
                     "quofem sensitivity calibration", facts, path, open_questions)

    # Fork 2: model language.
    if facts["model_language"] is None:
        open_questions.append("Is the model Tcl or OpenSeesPy (Python)?")
    if facts["model_language"] == "python":
        path.append("Python model -> OpenSeesPy")
        if facts["parallelism"] == "many-independent-cases":
            path.append("many independent cases -> PyLauncher sweep in one python-s3 job")
            return _plan("OpenSeesPy sweep (PyLauncher)", "python-s3",
                         "resonance pylauncher sweep", facts, path, open_questions)
        path.append("single run -> JupyterHub if small, python-s3 job if large")
        return _plan("OpenSeesPy at scale", "python-s3",
                     "oscillator single job first-job", facts, path, open_questions)

    # Tcl branch: fork on parallelism.
    if facts["model_language"] == "tcl":
        p = facts["parallelism"]
        if p is None:
            open_questions.append(
                "Is the run serial, partitioned into subdomains (getPID/getNP), "
                "one large domain needing a parallel solver, or many independent cases?")
        if p == "domain-decomposition":
            path.append("Tcl, partitioned into subdomains -> OpenSeesMP")
            return _plan("OpenSeesMP", "opensees-mp-s3",
                         "openseesmp multi-motion parallel", facts, path, open_questions)
        if p == "single-domain-parallel-solver":
            path.append("Tcl, one large domain -> OpenSeesSP (parallel solver, one driver)")
            plan = _plan("OpenSeesSP", "opensees-s3",
                         "pm4sand site response opensees", facts, path, open_questions)
            plan["decision"]["extra_app_args"] = [{"name": "Main Program", "arg": "OpenSeesSP"}]
            return plan
        if p == "many-independent-cases":
            path.append("Tcl, many independent cases -> OpenSeesMP one case per rank; "
                        "PyLauncher via python-s3 is the tested alternative for large sets")
            return _plan("OpenSeesMP (case-per-rank)", "opensees-mp-s3",
                         "openseesmp multi-motion parallel", facts, path, open_questions)
        if p == "serial":
            if facts["has_allocation"] is False:
                path.append("Tcl, serial, no allocation -> OpenSees-EXPRESS VM (no queue)")
                return _plan("OpenSeesEXPRESS", "opensees-express",
                             "pm4sand site response", facts, path, open_questions)
            if facts["has_allocation"] is None:
                open_questions.append(
                    "Do you have a TACC allocation, or should this run on the "
                    "no-allocation OpenSees-EXPRESS VM?")
            path.append("Tcl, serial, allocation available -> OpenSees on Stampede3")
            plan = _plan("OpenSees (serial on HPC)", "opensees-s3",
                         "pm4sand site response opensees", facts, path, open_questions)
            plan["decision"]["extra_app_args"] = [{"name": "Main Program", "arg": "OpenSees"}]
            return plan

    # Not enough facts for a decision; return the questions, never a
    # guess. Attach corpus matches: when the request describes one of
    # the corpus's own tested examples, the matching snippet's app
    # stands in for the missing facts; when it is the user's own model,
    # the questions stand.
    matches = search_snippets(request)[:2]
    return {
        "decision": None,
        "facts": facts,
        "open_questions": open_questions,
        "matrix_path": path,
        "corpus_matches": [
            {"id": m["id"], "app_id": m["app_id"], "title": m["title"],
             "source": m["source"]} for m in matches
        ],
        "note": "Ask the user the open questions, then call plan_simulation "
        "again with the answers. Exception: if the request describes a "
        "tested corpus example (see corpus_matches), use that snippet's "
        "app. Do not pick an app for the user's own model without the "
        "matrix.",
    }


def _plan(variant: str, app_id: str, snippet_query: str,
          facts: dict[str, Any], path: list[str],
          open_questions: list[str]) -> dict[str, Any]:
    snippets = search_snippets(snippet_query, app_id=app_id) or search_snippets(snippet_query)
    plan: dict[str, Any] = {
        "decision": {"variant": variant, "app_id": app_id},
        "facts": facts,
        "matrix_path": path,
        "snippets": [{"id": s["id"], "title": s["title"], "source": s["source"],
                      "pinned_versions": s["pinned_versions"]} for s in snippets[:2]],
        "open_questions": open_questions,
        "next_tools": list(_SEQUENCE),
    }
    if facts.get("pipeline"):
        plan["workflow"] = {
            "needed": True,
            "note": "Downstream stage detected: compose a DAG with "
            "build_workflow_preview; see snippet opensees-ml-dag-v1 for the "
            "sweep-feeds-training pattern and pi-fanout-workflow-v1 for fan-in.",
        }
    return plan
