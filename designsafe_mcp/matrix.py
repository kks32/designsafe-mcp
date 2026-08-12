"""The OpenSees decision matrix as a typed tool.

Two layers, both from the training deck (Day1a, "Example: OpenSees") and
the ds-workflows book's "Choosing a variant" flowchart, so an agent
decides the way the class was taught and its choice is auditable
against the same sources.

- VARIANTS answers "which OpenSees binary and which DesignSafe app".
- PLATFORM_MATRIX is the deck's full table: problem scope crossed with
  platform, interface, and variant. The original slide image ships in
  assets/opensees-decision-matrix.png and is registered as an MCP
  resource, so a host can show the human the same table the agent used.
"""

from typing import Any

VARIANTS: list[dict[str, Any]] = [
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

# Cell verdicts, from the slide legend.
_LEGEND: dict[str, str] = {
    "run-serial": "run the sequential application interactively (small jobs)",
    "run-mpi": "run the parallel application interactively using MPI (small jobs)",
    "run-mpi-large": "run the parallel application interactively using MPI (large jobs)",
    "submit-express": "submit sequential jobs to the OpenSees-EXPRESS VM (small jobs)",
    "submit-hpc-small": "submit parallel jobs to the HPC small queue (small-medium jobs)",
    "submit-hpc": "submit parallel jobs to HPC (large jobs)",
    "submit-launcher": "submit sets of parallel jobs through a launcher (large sets of large jobs)",
    "inefficient": "possible, but not the most efficient way to run this",
    "unavailable": "not available on this interface",
}

# Columns: sequential OpenSees, OpenSeesSP, OpenSeesMP, OpenSeesPy.
PLATFORM_MATRIX: list[dict[str, Any]] = [
    {"scope": "small", "platform": "Interactive VM", "interface": "Linux terminal",
     "sequential": "run-serial", "sp": "run-mpi", "mp": "run-mpi", "openseespy": "run-mpi"},
    {"scope": "small", "platform": "Interactive VM", "interface": "Jupyter notebook",
     "sequential": "unavailable", "sp": "unavailable", "mp": "unavailable", "openseespy": "run-mpi"},
    {"scope": "small", "platform": "Interactive VM", "interface": "Python console",
     "sequential": "unavailable", "sp": "unavailable", "mp": "unavailable", "openseespy": "run-mpi"},
    {"scope": "small-medium", "platform": "Web portal", "interface": "OpenSees-EXPRESS VM",
     "sequential": "submit-express", "sp": "unavailable", "mp": "unavailable", "openseespy": "unavailable"},
    {"scope": "small-medium", "platform": "Web portal", "interface": "small-queue HPC app",
     "sequential": "inefficient", "sp": "submit-hpc-small", "mp": "submit-hpc-small", "openseespy": "unavailable"},
    {"scope": "small-large", "platform": "JupyterHub VM", "interface": "Jupyter notebook",
     "sequential": "submit-express", "sp": "submit-hpc", "mp": "submit-hpc", "openseespy": "run-serial"},
    {"scope": "small-large", "platform": "JupyterHub VM", "interface": "console",
     "sequential": "submit-express", "sp": "submit-hpc", "mp": "submit-hpc", "openseespy": "run-serial"},
    {"scope": "small-large", "platform": "JupyterHub VM", "interface": "Linux terminal",
     "sequential": "unavailable", "sp": "unavailable", "mp": "unavailable", "openseespy": "run-serial"},
    {"scope": "large-xlarge", "platform": "HPC (TACC)", "interface": "Linux terminal",
     "sequential": "inefficient", "sp": "run-mpi-large", "mp": "run-mpi-large", "openseespy": "run-mpi-large"},
    {"scope": "large-xlarge", "platform": "HPC (TACC)", "interface": "launcher",
     "sequential": "inefficient", "sp": "submit-launcher", "mp": "submit-launcher", "openseespy": "submit-launcher"},
]

_NOTES: list[str] = [
    "The Interactive VM, OpenSees-EXPRESS, and JupyterHub each run on a dedicated shared-resource VM; no allocation is needed there.",
    "HPC submissions through Tapis apps (opensees-s3, opensees-mp-s3, python-s3) need a TACC allocation and archive to Stampede3.",
    "From the JupyterHub notebook, dapi is the submission path: the notebook stays the record while jobs run on HPC.",
    "Job submission through an agent goes through dapi app ids, never a terminal on the compute node; the scope column still governs which variant fits.",
]


def opensees_matrix() -> dict[str, Any]:
    """Which OpenSees to use when: the decision matrix from the training deck.

    Returns the variant table (variant -> app_id -> when), the full
    scope x platform x interface matrix with its legend, and the path of
    the original slide image for display to the user.
    """
    return {
        "variants": VARIANTS,
        "platform_matrix": PLATFORM_MATRIX,
        "legend": _LEGEND,
        "notes": _NOTES,
        "image": "assets/opensees-decision-matrix.png",
        "source": "DesignSafe workflows training deck, 'Decision Matrix for OpenSees on DesignSafe Cyberinfrastructure'; ds-workflows book apps/opensees.md",
    }
