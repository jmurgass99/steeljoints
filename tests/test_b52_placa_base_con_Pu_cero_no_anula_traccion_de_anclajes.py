"""B52 (§8.17): `BasePlate.anchor_tension` con `Pu = 0` y `Mu != 0` no anula la tracción.

Antes:
    e = abs(self.Mu_Nmm) / max(abs(self.Pu_N), 1)
    T_total_N = (e - kern) / (self.plate_N / 2 - kern) * abs(self.Pu_N)

Con `Pu = +0.001 kN` y `Mu = 150 kN·m` daba `T_per_bolt_kN = 281.25 kN`,
`utilization = 1.1932`, `is_ok = False`.
Con `Pu = 0.0 kN` (caso estrictamente peor: cero axil de compresión para estabilizar
el mismo momento) multiplicaba por `abs(Pu_N) = 0` y devolvía `T_per_bolt_kN = 0.0`,
`utilization = 0.0`, `is_ok = True`, haciendo que `design()` firmara `all_checks_ok = True`.
"""
from __future__ import annotations

import pytest

from steelconnectionjm.base_plate import BasePlate


def test_placa_base_con_Pu_cero_y_momento_conserva_la_traccion_limite() -> None:
    bp_eps = BasePlate(Pu=0.001, Mu=150.0, plate_B=350.0, plate_N=400.0, n_anchors=4)
    bp_zero = BasePlate(Pu=0.0, Mu=150.0, plate_B=350.0, plate_N=400.0, n_anchors=4)

    res_eps = bp_eps.design()
    res_zero = bp_zero.design()

    # Con Pu = 0.0 el aprovechamiento de anclaje es el límite continuo cuando Pu -> 0+
    # (y ligeramente mayor o igual que con Pu = +0.001 kN).
    assert res_zero["all_checks_ok"] is False
    assert res_zero["governing_check"] == "Anchor bolt tension"
    assert res_zero["governing_utilization"] >= res_eps["governing_utilization"]
    assert res_zero["governing_utilization"] == pytest.approx(1.1932, abs=1e-3)


def test_GUARDA_placa_base_en_nucleo_central_sigue_sin_traccion() -> None:
    # e = Mu / Pu = 10 / 500 = 0.02 m = 20 mm <= N/6 = 66.67 mm
    bp = BasePlate(Pu=500.0, Mu=10.0, plate_B=350.0, plate_N=400.0, n_anchors=4)
    anch = bp.anchor_tension()
    assert anch["T_per_bolt_kN"] == 0.0
    assert anch["utilization"] == 0.0
    assert anch["is_ok"] is True
