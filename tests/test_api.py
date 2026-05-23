"""Tests del REST API con TestClient."""
from __future__ import annotations
import pytest

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from steelconnectionjm.api.app import app


client = TestClient(app)


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "endpoints" in r.json()


def test_single_bolt():
    r = client.post("/api/connections/bolts/single",
                    json={"grade": "A325", "diameter_mm": 22.0})
    assert r.status_code == 200
    assert r.json()["Rn_shear_kN"] > 0


def test_fillet_weld():
    r = client.post("/api/connections/welds/fillet",
                    json={"leg_size_mm": 6, "length_mm": 200})
    assert r.status_code == 200


def test_end_plate():
    r = client.post("/api/connections/end_plate", json={
        "bp_mm": 200, "tp_mm": 20, "db_mm": 500, "bf_mm": 200, "tf_mm": 15,
        "bolt_diameter_mm": 22, "Mu_kNm": 200,
    })
    assert r.status_code == 200


def test_base_plate():
    r = client.post("/api/connections/base_plate", json={
        "Bp_mm": 400, "Np_mm": 400, "tp_mm": 25,
        "d_col_mm": 250, "bf_col_mm": 250, "Pu_kN": 1000,
    })
    assert r.status_code == 200


def test_panel_zone():
    r = client.post("/api/connections/panel_zone", json={
        "d_c_mm": 356, "t_w_mm": 11.2, "d_b_mm": 450,
        "b_f_c_mm": 369, "t_f_c_mm": 18.1,
        "Fy_c_MPa": 345, "V_demand_kN": 500,
    })
    assert r.status_code == 200
    assert r.json()["Vn_kN"] > 0
