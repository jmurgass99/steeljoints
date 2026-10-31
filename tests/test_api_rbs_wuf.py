"""Tests para endpoints REST /api/connections/rbs y /api/connections/wuf."""
from __future__ import annotations
import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from steeljoints.api.app import app


client = TestClient(app)


# -----------------------------------------------------------------------
# RBS — /api/connections/rbs
# -----------------------------------------------------------------------

def _rbs_valid_payload() -> dict:
    """W24x76 tipico con corte RBS dentro de limites AISC 358."""
    return {
        "d_mm": 608.0,
        "bf_mm": 228.0,
        "tf_mm": 17.3,
        "tw_mm": 11.2,
        "Zx_mm3": 3_050_000.0,
        "Fy_MPa": 345.0,
        "Fu_MPa": 450.0,
        "a_mm": 140.0,
        "b_mm": 460.0,
        "c_mm": 45.0,
        "L_clear_m": 6.0,
        "wu_kN_per_m": 15.0,
    }


def test_rbs_valid_basic():
    """Caso valido: respuesta 200, campos positivos y geometria OK."""
    r = client.post("/api/connections/rbs", json=_rbs_valid_payload())
    assert r.status_code == 200
    data = r.json()
    assert data["M_pr_kNm"] > 0
    assert data["V_pr_kN"] > 0
    assert data["M_f_kNm"] > data["M_pr_kNm"]
    assert data["Z_RBS_mm3"] < 3_050_000.0
    assert data["is_geometry_ok"] is True
    # AC-03: este test afirmaba `status == "OK"` con un payload SIN momento de
    # demanda, es decir, dejaba escrito el defecto (ausencia -> DCR 0.0 -> OK).
    # Sin demanda no hay veredicto; el caso valido con demanda esta en
    # test_rbs_moment_contract.py.
    assert "Mu_demand_kNm" not in _rbs_valid_payload()
    assert data["status"] != "OK"
    assert data["calculation_status"] == "NO_CALCULADO"
    assert data["DCR"] is None


def test_rbs_geometry_out_of_limits():
    """c = 100 mm >> 0.25*bf = 57 mm -> geometry NG."""
    payload = _rbs_valid_payload()
    payload["c_mm"] = 100.0
    r = client.post("/api/connections/rbs", json=payload)
    assert r.status_code == 200
    assert r.json()["is_geometry_ok"] is False


def test_rbs_larger_cut_lower_capacity():
    """Mayor profundidad de corte -> menor M_pr."""
    r1 = client.post("/api/connections/rbs", json=_rbs_valid_payload())
    payload2 = _rbs_valid_payload()
    payload2["c_mm"] = 55.0
    r2 = client.post("/api/connections/rbs", json=payload2)
    assert r2.json()["M_pr_kNm"] < r1.json()["M_pr_kNm"]


def test_rbs_error_missing_required():
    """Payload vacio -> 422 (validación Pydantic; antes 400 vía dict→dataclass)."""
    r = client.post("/api/connections/rbs", json={})
    assert r.status_code == 422


def test_rbs_error_negative_depth():
    """Peralte negativo -> 422 (Pydantic gt=0; antes 400 vía ValueError)."""
    payload = _rbs_valid_payload()
    payload["d_mm"] = -1.0
    r = client.post("/api/connections/rbs", json=payload)
    assert r.status_code == 422


# -----------------------------------------------------------------------
# WUF — /api/connections/wuf
# -----------------------------------------------------------------------

def _wuf_valid_payload() -> dict:
    """W21x62 viga + W14x159 columna, tipico SMF."""
    return {
        "beam_d_mm": 533.0,
        "beam_bf_mm": 209.0,
        "beam_tf_mm": 15.6,
        "beam_tw_mm": 10.2,
        "beam_Zx_mm3": 2_350_000.0,
        "beam_Fy_MPa": 345.0,
        "beam_Fu_MPa": 450.0,
        "col_d_mm": 381.0,
        "col_bf_mm": 394.0,
        "col_tf_mm": 30.2,
        "col_tw_mm": 18.6,
        "col_Zx_mm3": 4_700_000.0,
        "col_Fy_MPa": 345.0,
        "beam_length_m": 7.0,
    }


def test_wuf_valid_basic():
    """Caso valido: respuesta 200, campos positivos."""
    r = client.post("/api/connections/wuf", json=_wuf_valid_payload())
    assert r.status_code == 200
    data = r.json()
    assert data["M_pr_kNm"] > 0
    assert data["V_pr_kN"] > 0
    assert data["pz_Vn_kN"] > 0
    assert data["weld_capacity_kN"] > 0
    assert data["scwb_ratio"] > 0


def test_wuf_weak_column_detected():
    """Columna debil: col_Zx pequeno -> scwb < 1.0 y status NG."""
    payload = _wuf_valid_payload()
    payload["col_Zx_mm3"] = 500_000.0  # columna muy pequena
    r = client.post("/api/connections/wuf", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["scwb_ratio"] < 1.0
    assert data["status"] == "NG"


def test_wuf_compact_check():
    """Seccion compacta tipica -> is_compact True."""
    r = client.post("/api/connections/wuf", json=_wuf_valid_payload())
    assert r.status_code == 200
    assert r.json()["is_compact"] is True


def test_wuf_error_missing_required():
    """Payload vacio -> 422 (validación Pydantic; antes 400 vía dict→dataclass)."""
    r = client.post("/api/connections/wuf", json={})
    assert r.status_code == 422


def test_wuf_error_negative_zx():
    """Zx negativo -> 422 (Pydantic gt=0; antes 400 vía ValueError)."""
    payload = _wuf_valid_payload()
    payload["beam_Zx_mm3"] = -100.0
    r = client.post("/api/connections/wuf", json=payload)
    assert r.status_code == 422
