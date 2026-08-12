"""Headless tests for the decision matrix, planner, and safety spine.

Everything runs in mock mode; no Tapis, no credentials, no SUs.
"""

import os

import pytest

os.environ["DESIGNSAFE_MCP_MOCK"] = "1"

from designsafe_mcp import matrix, tools  # noqa: E402
from designsafe_mcp.planner import plan_simulation  # noqa: E402


def test_matrix_variants_map_to_known_apps():
    m = matrix.opensees_matrix()
    known = set(tools._MOCK_APPS) | {None}
    assert {v["app_id"] for v in m["variants"]} <= known


def test_matrix_cells_use_legend_verdicts():
    m = matrix.opensees_matrix()
    legend = set(m["legend"])
    for row in m["platform_matrix"]:
        for col in ("sequential", "sp", "mp", "openseespy"):
            assert row[col] in legend, f"{row['platform']}/{row['interface']}:{col}"


@pytest.mark.parametrize(
    ("request_text", "app_id"),
    [
        ("serial cantilever.tcl, no TACC allocation, fast", "opensees-express"),
        ("serial site-response tcl on Stampede3 with the class reservation", "opensees-s3"),
        ("tcl model partitioned with getPID over 3 motions", "opensees-mp-s3"),
        ("one large tcl domain needing a parallel equation solver", "opensees-s3"),
        ("sweep 25 damping values of an OpenSeesPy pushover", "python-s3"),
        ("Bayesian calibration of PM4Sand parameters", "simcenter-uq-stampede3"),
    ],
)
def test_planner_decides_from_the_matrix(request_text, app_id):
    plan = plan_simulation(request_text)
    assert plan["decision"] is not None, plan["open_questions"]
    assert plan["decision"]["app_id"] == app_id
    assert plan["snippets"], "a decision must carry a tested snippet"


def test_planner_asks_instead_of_guessing():
    plan = plan_simulation("run a site response analysis on DesignSafe")
    assert plan["decision"] is None
    assert plan["open_questions"]


def test_planner_sets_main_program_for_sp():
    plan = plan_simulation("one large tcl domain needing a parallel equation solver")
    assert plan["decision"]["extra_app_args"] == [
        {"name": "Main Program", "arg": "OpenSeesSP"}
    ]


def _mock_job():
    return tools.build_job_request(
        app_id="opensees-express",
        input_dir_uri="tapis://designsafe.storage.default/mockuser/inputs",
        script_filename="run.tcl",
        allocation="TEST-ALLOC",
    )


def test_mock_job_builds_validates_and_prices():
    job = _mock_job()
    assert tools.validate_job(job)["ok"]
    assert tools.estimate_cost(job)["estimated_su"] > 0


def test_submit_refuses_fabricated_token():
    job = _mock_job()
    out = tools.submit_job(job, "abc123")
    assert out["submitted"] is False


def test_submit_refuses_token_after_job_edit():
    job = _mock_job()
    token = tools.approve_submission(job)
    job["maxMinutes"] = 2000
    out = tools.submit_job(job, token)
    assert out["submitted"] is False


def test_submit_accepts_minted_token():
    job = _mock_job()
    token = tools.approve_submission(job)
    out = tools.submit_job(job, token)
    assert out["submitted"] is True
    assert out["uuid"].startswith("mock-")


def test_workflow_preview_compiles_in_mock_mode():
    a = _mock_job()
    b = _mock_job()
    preview = tools.build_workflow_preview(
        "two-stage",
        [
            {"task_id": "first", "job": a},
            {"task_id": "second", "job": b, "depends_on": ["first"],
             "input_from": {"task_id": "first"}},
        ],
    )
    ids = {t["id"] for t in preview["tasks"]}
    assert ids == {"first", "second"}


def test_material_knowledge_cites_the_manual():
    from designsafe_mcp.materials import describe_material

    m = describe_material("PM4Sand")
    assert [p["name"] for p in m["primary_parameters"]] == ["Dr", "G0", "hpo"]
    assert all(p["source_pages"] for p in m["primary_parameters"])
    assert "UCD/CGM-23/01" in m["reference"]
    assert describe_material("unknownium")["error"]


def test_calibration_planner_forks():
    from designsafe_mcp.methods import plan_calibration

    bayes = plan_calibration("x", n_uncertain_parameters=3,
                             uncertainty_required=True, quofem_wrappable=True)
    assert bayes["decision"]["pipeline"] == [
        "bayesian-calibration", "forward-propagation"]
    screened = plan_calibration("x", n_uncertain_parameters=12,
                                uncertainty_required=True,
                                quofem_wrappable=True)
    assert screened["decision"]["pipeline"][0] == "global-sensitivity"
    fallback = plan_calibration("x", quofem_wrappable=False)
    assert fallback["decision"]["pipeline"] == ["sweep-fit"]
    undecided = plan_calibration("calibrate something")
    assert undecided["decision"] is None and undecided["open_questions"]


def test_calibration_options_state_status():
    from designsafe_mcp.methods import calibration_options

    for opt in calibration_options():
        assert opt["status"], opt["method"]
