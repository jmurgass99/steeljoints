"""Tests de integración y golden para diseño de chapa de testa desde esfuerzos seccionales (N, V, M).

Normas: AISC 360-16 / AISC 358-16 (Prequalified Moment Connections).
"""
import pytest
from fastapi.testclient import TestClient

from steelconnectionjm.api.app import app
from steelconnectionjm.end_plate import design_end_plate_from_member_forces


@pytest.fixture
def client():
    return TestClient(app)


def test_end_plate_from_member_forces_hand_calc_golden():
    """Golden analítico exacto para momento efectivo con axil de tracción según AISC 360/358.

    Viga W16x40: db = 407 mm, tf = 12.8 mm.
    Demandas: N = 50 kN (tracción), V = 80 kN, M = 120 kN·m.
      h0 = db - tf = 407 - 12.8 = 394.2 mm
      M_eff = M + N * (h0 / 2) * 1e-3 = 120.0 + 50.0 * 0.1971 = 129.855 kN·m
    """
    res = design_end_plate_from_member_forces(
        N_kN=50.0,
        V_kN=80.0,
        M_kNm=120.0,
        beam_depth_mm=407.0,
        beam_tf_mm=12.8,
        beam_bf_mm=178.0,
        bolt_grade="A325",
        plate_thickness_mm=20.0,
        plate_Fy_MPa=345.0,
        n_bolt_rows=2,
    )

    assert res["applied_forces"]["M_effective_kNm"] == pytest.approx(129.855, rel=1e-4)
    assert res["applied_forces"]["N_kN"] == 50.0
    assert res["applied_forces"]["V_kN"] == 80.0
    assert len(res["checks"]) == 4
    assert res["governing_utilization"] > 0.0


def test_end_plate_from_member_forces_api_endpoint(client):
    """Verifica endpoint HTTP /api/connections/end_plate/from_member_forces."""
    payload = {
        "N_kN": 50.0,
        "V_kN": 80.0,
        "M_kNm": 120.0,
        "beam_depth_mm": 407.0,
        "beam_tf_mm": 12.8,
        "beam_bf_mm": 178.0,
        "bolt_grade": "A325",
        "plate_thickness_mm": 20.0,
        "plate_Fy_MPa": 345.0,
        "n_bolt_rows": 2,
    }
    resp = client.post("/api/connections/end_plate/from_member_forces", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["applied_forces"]["M_effective_kNm"] == pytest.approx(129.855, rel=1e-4)
    assert len(data["checks"]) == 4
    assert "governing_utilization" in data
    assert data["governing_utilization"] > 0.0
