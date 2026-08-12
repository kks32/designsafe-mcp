"""One source of ground truth: dapi's surface, never a description of it.

The bridge derives tool schemas from dapi signatures at import time;
the contract tests here are the drift alarm for the few hand-written
wrappers the safety spine requires. When dapi renames or removes a
parameter these fail, which is the moment the MCP must be looked at.
"""

import inspect

from designsafe_mcp import bridge, tools


def test_derived_tools_carry_dapi_signatures():
    assert bridge.DERIVED_TOOLS, "curated dapi surface should expose tools"
    for fn in bridge.DERIVED_TOOLS:
        sig = inspect.signature(fn)
        assert "self" not in sig.parameters
        assert "introspected from dapi" in (fn.__doc__ or "")


def test_build_job_request_is_a_subset_of_dapi_generate():
    from dapi.client import JobMethods

    dapi_params = set(inspect.signature(JobMethods.generate).parameters)
    ours = set(inspect.signature(tools.build_job_request).parameters)
    drift = ours - dapi_params
    assert not drift, (
        f"tools.build_job_request declares {drift} which dapi's "
        "JobMethods.generate does not accept; reconcile with the "
        "current dapi surface")


def test_submit_wrapper_matches_dapi_submit_contract():
    from dapi.client import JobMethods

    dapi_params = [p for p in inspect.signature(JobMethods.submit).parameters
                   if p != "self"]
    assert dapi_params == ["job_request"], (
        "dapi's submit contract changed; update tools.submit_job")


def test_passthrough_signatures_are_never_exposed():
    for fn in bridge.DERIVED_TOOLS:
        for p in inspect.signature(fn).parameters.values():
            assert p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD), fn.__name__
