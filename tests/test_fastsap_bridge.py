"""Tests del bridge FastSAP usando mock client."""
from __future__ import annotations
from types import SimpleNamespace
import pytest

from steelconnectionjm.integration.fastsap_bridge import (
    ConnectionForces, extract_beam_column_forces, design_panel_zone_from_sap,
)


def test_extract_forces_no_client_raises():
    with pytest.raises(ValueError):
        extract_beam_column_forces(None, joint_name="J1")


def test_extract_forces_with_mock_returns_placeholder():
    class _Setup:
        @staticmethod
        def DeselectAllCasesAndCombosForOutput(): return 0
        @staticmethod
        def SetCaseSelectedForOutput(case): return 0

    class _Results:
        Setup = _Setup
        @staticmethod
        def FrameForce(name, item):
            return tuple([0] * 10 + [[100e3]] + [0]*3 + [[200e3]])

    sap_model = SimpleNamespace(Results=_Results)
    sap = SimpleNamespace(SapModel=sap_model)
    f = extract_beam_column_forces(sap, joint_name="J1", beam_name="B1")
    assert isinstance(f, ConnectionForces)
    assert f.joint_name == "J1"


def test_design_panel_zone_from_sap_e2e():
    class _Setup:
        @staticmethod
        def DeselectAllCasesAndCombosForOutput(): return 0
        @staticmethod
        def SetCaseSelectedForOutput(case): return 0

    class _Results:
        Setup = _Setup
        @staticmethod
        def FrameForce(name, item):
            return tuple([0]*10 + [[50e3]] + [0]*3 + [[200e3]])

    sap = SimpleNamespace(SapModel=SimpleNamespace(Results=_Results))
    res, forces = design_panel_zone_from_sap(
        sap, joint_name="J1", beam_name="B1",
        column_section_dims={
            "d_c_mm": 356, "t_w_mm": 11.2, "d_b_mm": 450,
            "b_f_c_mm": 369, "t_f_c_mm": 18.1,
        },
    )
    assert res.Vn_kN > 0
    assert isinstance(forces, ConnectionForces)
