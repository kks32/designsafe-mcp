"""The OpenSees decision matrix as a typed tool, plus agent eval cases.

The matrix mirrors the training deck's slide and the ds-workflows book's
"Choosing a variant" flowchart, so the agent decides the way the class
was taught, and its choice is auditable against the same source.
"""

from typing import Any, Dict, List

MATRIX: List[Dict[str, Any]] = [
    {"variant": "OpenSeesPy (JupyterHub)", "app_id": None,
     "when": "Python model, small enough for an interactive session",
     "notes": "no job at all; move to python-s3 when it outgrows the VM"},
    {"variant": "OpenSeesPy at scale", "app_id": "python-s3",
     "when": "Python model, large runs or parameter sweeps (PyLauncher)",
     "notes": "EXTRA_MODULES=opensees; sweeps via ds.jobs.parametric_sweep"},
    {"variant": "OpenSeesEXPRESS", "app_id": "opensees-express",
     "when": "Tcl model, serial, wants immediate start",
     "notes": "runs on a VM; no queue, no allocation; shared machine"},
    {"variant": "OpenSees (serial on HPC)", "app_id": "opensees-s3",
     "when": "Tcl model, serial, needs Stampede3 (reservation, classroom, big memory)",
     "notes": "Main Program appArg selects the binary; 1 core of 1 node"},
    {"variant": "OpenSeesSP", "app_id": "opensees-s3",
     "when": "Tcl model, ONE large domain; parallel equation solver",
     "notes": "one driver process; Main Program=OpenSeesSP"},
    {"variant": "OpenSeesMP", "app_id": "opensees-mp-s3",
     "when": "Tcl model partitioned into subdomains, or many motions/models in parallel",
     "notes": "every rank runs your script; ranks = nodes x cores; getPID/getNP"},
    {"variant": "quoFEM over OpenSees", "app_id": "simcenter-uq-stampede3",
     "when": "UQ, sensitivity, or parameter calibration wrapping an OpenSees model",
     "notes": "Bayesian calibration and Sobol indices; model becomes the forward solver"},
]


def opensees_matrix() -> List[Dict[str, Any]]:
    """Which OpenSees to use when: the decision matrix from the training."""
    return MATRIX


# Golden eval cases: natural-language intent -> expected decision.
# A harness presents `request` to an agent wired to this MCP and scores
# whether its build_job_request/app choice matches `expect`. Run each
# case with several seeds and several models; ability = pass rate.
EVAL_CASES: List[Dict[str, Any]] = [
    {"id": "serial-tcl-quick", "request": "Run my serial cantilever.tcl quickly, I have no allocation",
     "expect": {"app_id": "opensees-express"}},
    {"id": "serial-tcl-classroom", "request": "Serial site-response tcl on Stampede3 under the class reservation",
     "expect": {"app_id": "opensees-s3", "app_args": {"Main Program": "OpenSees"}}},
    {"id": "partitioned-parallel", "request": "My tcl model is partitioned with getPID/getNP over 3 motions",
     "expect": {"app_id": "opensees-mp-s3"}},
    {"id": "python-sweep", "request": "Sweep 25 damping ratios of an OpenSeesPy pushover in one job",
     "expect": {"app_id": "python-s3", "uses": "parametric_sweep"}},
    {"id": "calibration", "request": "Calibrate PM4Sand parameters against recorded pore pressures",
     "expect": {"app_id": "simcenter-uq-stampede3", "snippet": "quofem-bayesian-calibration-uw"}},
    {"id": "sweep-feeds-training", "request": "Run an OpenSees sweep then train a regression on its results, hands-off",
     "expect": {"workflow": True, "tasks": ["sweep", "train"]}},
]


def eval_cases() -> List[Dict[str, Any]]:
    """Golden test cases for scoring an agent's workflow-building ability."""
    return EVAL_CASES
