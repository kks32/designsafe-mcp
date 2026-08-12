"""The declared support surface of this server.

This MCP is a bounded subset of the quoFEM pipeline for geotechnical
earthquake engineering, with OpenSees as the forward solver. It is not
a general gateway to DesignSafe or SimCenter. The map below is
organized by scientific domain, one level above any tool: OpenSees and
quoFEM are how a capability is served, not what it is. An agent (or a
human) asks supported_capabilities() to learn what this server can do,
with what, and how much of it is tested; anything outside the map is
out of scope and the honest answer is a refusal that names this list.
"""

from typing import Any

DOMAINS: list[dict[str, Any]] = [
    {
        "domain": "Site response and liquefaction",
        "science": "1D seismic response of soil profiles, pore pressure "
        "generation, liquefaction triggering and its consequences",
        "capabilities": [
            {"what": "single-motion site response of a layered profile "
             "(PM4Sand, coupled u-p elements)",
             "served_by": "OpenSees on opensees-s3 or opensees-express",
             "snippet": "pm4sand-freefield-v1", "status": "tested"},
            {"what": "multi-motion site response in parallel, one motion "
             "per rank",
             "served_by": "OpenSeesMP on opensees-mp-s3",
             "snippet": "openseesmp-multimotion-v1", "status": "tested"},
            {"what": "effective-stress variant (PDMY02) with report "
             "generation",
             "served_by": "OpenSees; UW notebook not yet modernized",
             "snippet": "freefield-effective-uw", "status": "candidate"},
        ],
    },
    {
        "domain": "Constitutive model calibration and UQ",
        "science": "the quoFEM pipeline: which parameters matter, what "
        "values fit the data, what uncertainty remains, and what it "
        "implies for predictions",
        "capabilities": [
            {"what": "global sensitivity analysis (Sobol indices)",
             "served_by": "quoFEM on simcenter-uq-stampede3",
             "snippet": "quofem-sensitivity-v1", "status": "tested"},
            {"what": "Bayesian calibration against lab data (TMCMC), "
             "e.g. PM4Sand against Ottawa F-65 cyclic DSS",
             "served_by": "quoFEM on simcenter-uq-stampede3",
             "snippet": "quofem-bayesian-calibration-uw",
             "status": "candidate"},
            {"what": "deterministic best-fit calibration",
             "served_by": "quoFEM (Dakota) on simcenter-uq-stampede3",
             "snippet": None, "status": "untested"},
            {"what": "forward uncertainty propagation of parameter "
             "distributions",
             "served_by": "quoFEM, or a dapi sweep for non-quoFEM models",
             "snippet": "resonance-pylauncher-sweep-v1", "status": "tested"},
            {"what": "parameter knowledge for calibration planning "
             "(what is sensitive to what, from the model's manual)",
             "served_by": "describe_material (PM4Sand v3.3 manual)",
             "snippet": None, "status": "tested"},
        ],
    },
    {
        "domain": "Parameter studies and pipelines",
        "science": "many related runs and what connects them: sweeps, "
        "ensembles, and multi-stage studies where one stage feeds the "
        "next",
        "capabilities": [
            {"what": "parameter sweep in one HPC job (many tasks, "
             "PyLauncher)",
             "served_by": "python-s3 via dapi parametric_sweep",
             "snippet": "resonance-pylauncher-sweep-v1", "status": "tested"},
            {"what": "sweep feeding a downstream training/fitting stage "
             "as a server-side DAG",
             "served_by": "Tapis Workflows via dapi.workflows",
             "snippet": "opensees-ml-dag-v1", "status": "tested"},
            {"what": "fan-out/fan-in ensembles (independent pieces, one "
             "combining step)",
             "served_by": "Tapis Workflows via dapi.workflows",
             "snippet": "pi-fanout-workflow-v1", "status": "tested"},
        ],
    },
]

OUT_OF_SCOPE = [
    "other SimCenter tools (EE-UQ, WE-UQ, Hydro-UQ, R2D) and their apps",
    "non-OpenSees solvers (OpenFOAM, ADCIRC, LS-DYNA, Ansys, Abaqus)",
    ("DesignSafe data services (project search, published-dataset DOIs); "
     "planned as a later layer"),
    "structural/regional testbeds beyond the geotechnical scope above",
]


def supported_capabilities() -> dict[str, Any]:
    """What this server supports, by scientific domain.

    Consult this before promising anything. Every capability names how
    it is served and whether it is tested; 'candidate' and 'untested'
    entries need a human-run graduation before unattended use. Requests
    outside this map should be declined by pointing at out_of_scope.
    """
    return {
        "scope": "quoFEM-pipeline subset for geotechnical earthquake "
        "engineering, OpenSees as the forward solver",
        "domains": DOMAINS,
        "out_of_scope": OUT_OF_SCOPE,
    }
