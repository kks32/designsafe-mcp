"""Constitutive-model knowledge for calibration planning.

Content is transcribed from the model's own manual, not from a language
model's recall, and every entry cites its source pages. PM4Sand comes
from Boulanger & Ziotopoulou (2023), Report UCD/CGM-23/01 (v3.3), which
ships in community_data/references/ and is indexed for passage search.
The parameter-to-response sensitivity map is what lets an agent answer
"which parameters do I calibrate against which data" before it plans a
quoFEM run.
"""

from typing import Any

_PM4SAND: dict[str, Any] = {
    "model": "PM4Sand",
    "version": "3.3",
    "reference": "Boulanger & Ziotopoulou (2023), UCD/CGM-23/01, "
    "community_data/references/PM4Sand_v3.3_CGM-23-01.pdf",
    "opensees_material": "nDMaterial PM4Sand",
    "primary_parameters": [
        {
            "name": "Dr",
            "meaning": "apparent relative density; controls dilatancy and "
            "cyclic strength",
            "estimate_from": "SPT: Dr = sqrt((N1)60/46); CPT: Dr = "
            "0.465*(qc1N/0.9)^0.264 - 1.063 (manual eqs. 94-95)",
            "typical": "0.35 to 0.75 ((N1)60 of 6 to 26)",
            "sensitive_qois": ["cyclic resistance ratio (CRR)",
                               "dilation and post-triggering strains",
                               "monotonic drained/undrained strength"],
            "informing_data": "penetration resistance (SPT/CPT); adjust as "
            "part of calibration, it is an apparent not a measured density",
            "source_pages": "73",
        },
        {
            "name": "G0",
            "meaning": "shear modulus coefficient; sets small-strain "
            "stiffness Gmax = G0 * pA * sqrt(p/pA)",
            "estimate_from": "in-situ Vs (G = rho*Vs^2) or G0 = "
            "167*sqrt((N1)60 + 2.5) (manual eqs. 96-99)",
            "typical": "477 to 906 for Dr 0.35 to 0.75",
            "sensitive_qois": ["small-strain stiffness and site period",
                               "wave propagation / surface response spectra"],
            "informing_data": "shear-wave velocity profiles; keep Ko "
            "consistent between calibration and the boundary value problem",
            "source_pages": "74",
        },
        {
            "name": "hpo",
            "meaning": "contraction rate parameter; the calibration knob "
            "for liquefaction triggering",
            "estimate_from": "tuned last, to match target CRR from lab "
            "cyclic tests or triggering correlations",
            "typical": "0.40 to 0.63 in the manual's examples",
            "sensitive_qois": ["cycles to liquefaction at a given CSR",
                               "excess pore pressure generation rate"],
            "informing_data": "cyclic DSS or triaxial tests (e.g. the "
            "Ottawa F-65 dataset in the UW quoFEM example)",
            "source_pages": "74-75",
        },
    ],
    "secondary_parameters_note": "About twenty secondary parameters "
    "default sensibly and are modified only in special circumstances "
    "(manual sec. 4.1, pp. 76-79). Worth knowing: Q and R set the "
    "critical state line and can be adjusted to match an experimental "
    "CSL or residual strength (pp. 83-85, fig. 4.22); emax/emin, "
    "phi_cv, and the fabric terms (zmax, cz) shape cyclic degradation. "
    "Calibrate primaries; touch secondaries only with data that "
    "constrains them.",
    "calibration_sequence": [
        "1. Fix Dr from penetration data (SPT/CPT correlations).",
        "2. Fix G0 from Vs measurements or the (N1)60 correlation.",
        ("3. Tune hpo so cyclic element tests reproduce the target CRR "
         "curve (cycles to liquefaction vs CSR)."),
        ("4. Only if data demands it, adjust secondary parameters "
         "(Q, R for critical state; fabric terms for degradation)."),
    ],
    "canonical_example": {
        "what": "Bayesian calibration of (Dr, G0, hpo) against Ottawa "
        "F-65 cyclic DSS data, QoIs = cycles to liquefaction at CSR "
        "0.10-0.20, TMCMC via quoFEM",
        "source": "community_data/University_of_Washington/"
        "quoFEM-Example1-TAPISV3/BayesianCalibration/",
        "snippet_candidate": "quofem-bayesian-calibration-uw",
    },
}

_MATERIALS = {"pm4sand": _PM4SAND}


def describe_material(model: str) -> dict[str, Any]:
    """Parameters, sensitivities, and the calibration sequence for a
    constitutive model, transcribed from its manual with page citations.

    Use this before planning a calibration: it answers which parameters
    exist, what data informs each one, and in what order to calibrate.
    """
    key = model.strip().lower().replace("-", "").replace("_", "")
    if key not in _MATERIALS:
        return {"error": f"no knowledge entry for '{model}'",
                "known": sorted(_MATERIALS),
                "note": "search_community may still find community "
                "notebooks that use it"}
    return _MATERIALS[key]
