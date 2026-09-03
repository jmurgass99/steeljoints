"""
test_consistency_block_shear_triplicate.py
===========================================
Campaña AG38 — Bloque A: Consistencia cruzada entre las tres implementaciones
de desgarro en bloque (block shear) del monorepo:
  1. steelconnectionjm.block_shear (canónica, multi-código)
  2. fastsap.codes.block_shear.block_shear (punto 28, delegada en AG38)
  3. asistentejm.tools.block_shear (tool de asistente, delegada en AG38)

Citas normativas:
  - ANSI/AISC 360-16 / 360-22 §J4.3 "Block Shear Strength", Ec. (J4-5).
  - EN 1993-1-8:2005 §3.10.2(2) "Block tearing", Ec. (3.9).
"""
from __future__ import annotations

import pytest
from steelconnectionjm import (
    BlockShearInput,
    block_shear as canonical_block_shear,
)
from fastsap.codes.block_shear import block_shear as fastsap_block_shear
from asistentejm.tools import block_shear as asistente_block_shear


# Geometría de referencia AISC: 3 tornillos M20, d0=22 mm, t=10 mm, s=60 mm, Le=40 mm.
#   Agv = 160·10 = 1600 mm², Anv = (160 - 2.5·22)·10 = 1050 mm²
#   Ant = (40 - 0.5·22)·10 = 290 mm²
_GEOM_FRACTURE = {
    "Agv": 1600.0,
    "Anv": 1050.0,
    "Ant": 290.0,
    "Fy": 345.0,
    "Fu": 450.0,
    "Ubs": 1.0,
}


def test_cross_consistency_triplicate_shear_fracture_governs():
    """Caso donde la fractura por cortante gobierna el estado límite AISC.

    Termino fractura : 0.6·Fu·Anv + Ubs·Fu·Ant = 0.6·450·1050 + 1.0·450·290
                     = 283 500 + 130 500 = 414 000 N = 414.0 kN  <-- GOBIERNA
    Termino fluencia : 0.6·Fy·Agv + Ubs·Fu·Ant = 0.6·345·1600 + 130 500
                     = 331 200 + 130 500 = 461 700 N = 461.7 kN
    Rn = min(414.0, 461.7) = 414.0 kN.
    """
    g = _GEOM_FRACTURE
    # 1. Canónica
    inp = BlockShearInput(
        Agv_mm2=g["Agv"], Anv_mm2=g["Anv"], Ant_mm2=g["Ant"],
        Fy_MPa=g["Fy"], Fu_MPa=g["Fu"], Ubs=g["Ubs"],
    )
    res_canon = canonical_block_shear(inp, code="US")

    # 2. FastSAP (delegada)
    res_fs = fastsap_block_shear(
        Fy=g["Fy"], Fu=g["Fu"], Agv=g["Agv"], Anv=g["Anv"], Ant=g["Ant"], Ubs=g["Ubs"],
    )

    # 3. AsistenteJm (delegada)
    res_as = asistente_block_shear(
        Agv_mm2=g["Agv"], Anv_mm2=g["Anv"], Ant_mm2=g["Ant"],
        Fy_MPa=g["Fy"], Fu_MPa=g["Fu"], Ubs=g["Ubs"], code="US",
    )

    # Consistencia cruzada exacta
    assert res_canon.Rn_kN == pytest.approx(414.0, abs=1e-6)
    assert res_canon.Rd_kN == pytest.approx(310.5, abs=1e-6)   # phi = 0.75
    assert res_canon.governing == "fracture"

    assert res_fs.Rn == pytest.approx(414000.0, abs=1.0)
    assert res_fs.governs in ("shear_rupture", "fracture")
    assert res_fs.Rn == pytest.approx(res_canon.Rn_kN * 1000.0, abs=1e-3)

    assert res_as["Rn_kN"] == pytest.approx(res_canon.Rn_kN, abs=1e-6)
    assert res_as["R_design_kN"] == pytest.approx(res_canon.Rd_kN, abs=1e-6)


def test_cross_consistency_triplicate_shear_yielding_governs():
    """Caso con Agv reducida a 1200 mm² donde la fluencia por cortante gobierna.

    Termino fractura : 414 000 N = 414.0 kN
    Termino fluencia : 0.6·345·1200 + 130 500 = 248 400 + 130 500 = 378 900 N = 378.9 kN <-- GOBIERNA
    Rn = min(414.0, 378.9) = 378.9 kN.
    """
    g = dict(_GEOM_FRACTURE, Agv=1200.0)

    inp = BlockShearInput(
        Agv_mm2=g["Agv"], Anv_mm2=g["Anv"], Ant_mm2=g["Ant"],
        Fy_MPa=g["Fy"], Fu_MPa=g["Fu"], Ubs=g["Ubs"],
    )
    res_canon = canonical_block_shear(inp, code="US")
    res_fs = fastsap_block_shear(
        Fy=g["Fy"], Fu=g["Fu"], Agv=g["Agv"], Anv=g["Anv"], Ant=g["Ant"], Ubs=g["Ubs"],
    )
    res_as = asistente_block_shear(
        Agv_mm2=g["Agv"], Anv_mm2=g["Anv"], Ant_mm2=g["Ant"],
        Fy_MPa=g["Fy"], Fu_MPa=g["Fu"], Ubs=g["Ubs"], code="US",
    )

    assert res_canon.Rn_kN == pytest.approx(378.9, abs=1e-6)
    assert res_canon.Rd_kN == pytest.approx(284.175, abs=1e-6)
    assert res_canon.governing == "yield"

    assert res_fs.Rn == pytest.approx(378900.0, abs=1.0)
    assert res_fs.governs in ("shear_yield", "yield")
    assert res_fs.Rn == pytest.approx(res_canon.Rn_kN * 1000.0, abs=1e-3)

    assert res_as["Rn_kN"] == pytest.approx(res_canon.Rn_kN, abs=1e-6)
    assert res_as["R_design_kN"] == pytest.approx(res_canon.Rd_kN, abs=1e-6)


def test_cross_consistency_triplicate_non_uniform_tension():
    """Caso con Ubs=0.5 (tensión no uniforme en vigas con alas/almas asimétricas)."""
    Agv, Anv, Ant = 2000.0, 1500.0, 500.0
    Fy, Fu, Ubs = 250.0, 400.0, 0.5

    inp = BlockShearInput(
        Agv_mm2=Agv, Anv_mm2=Anv, Ant_mm2=Ant,
        Fy_MPa=Fy, Fu_MPa=Fu, Ubs=Ubs,
    )
    res_canon = canonical_block_shear(inp, code="US")
    res_fs = fastsap_block_shear(
        Fy=Fy, Fu=Fu, Agv=Agv, Anv=Anv, Ant=Ant, Ubs=Ubs,
    )
    res_as = asistente_block_shear(
        Agv_mm2=Agv, Anv_mm2=Anv, Ant_mm2=Ant,
        Fy_MPa=Fy, Fu_MPa=Fu, Ubs=Ubs, code="US",
    )

    # Rn_rupture = 0.6·400·1500 + 0.5·400·500 = 360 000 + 100 000 = 460 kN
    # Rn_yield   = 0.6·250·2000 + 0.5·400·500 = 300 000 + 100 000 = 400 kN <-- GOBIERNA
    assert res_canon.Rn_kN == pytest.approx(400.0, abs=1e-6)
    assert res_fs.Rn == pytest.approx(400000.0, abs=1.0)
    assert res_as["Rn_kN"] == pytest.approx(400.0, abs=1e-6)


def test_golden_published_w01457_en1993_1_8():
    """Golden publicado: Ficha W01457 (Connections extra exercises, pág 2).

    Norma: EN 1993-1-8:2005 §3.10.2(2) Ec. (3.9) Modo 1.
    Geometría: 2 tornillos M20, e1=35mm, p1=70mm, b=120mm, t=10mm, S275 (fy=275, fu=430 MPa), d0=22mm.
      Ant = (120 - 1·22)·10 = 980 mm²
      Anv = (35 + 70 - 1.5·22)·10 = 720 mm²
      gamma_M2 = 1.25, gamma_M0 = 1.00
      Veff,1,Rd = fu·Ant/gamma_M2 + (1/√3)·fy·Anv/gamma_M0
                = 430·980/1.25 + 275·720/(1.7320508·1.00)
                = 337.12 + 114.33 = 451.45 kN.
    """
    inp = BlockShearInput(
        Agv_mm2=1050.0, Anv_mm2=720.0, Ant_mm2=980.0,
        Fy_MPa=275.0, Fu_MPa=430.0,
    )
    r = canonical_block_shear(inp, code="EU")
    assert r.Rd_kN == pytest.approx(451.45, abs=0.1)
