# -*- coding: utf-8 -*-
"""Accion de palanca (prying) — AISC Manual Part 9."""
import pytest

from steeljoints.prying import PryingInput, prying_capacity


def _case(t_mm):
    return PryingInput(B_kN=200.0, b_mm=45.0, a_mm=50.0, p_mm=90.0,
                       t_mm=t_mm, d_mm=22.0, Fy_MPa=345.0)


class TestPrying:
    def test_placa_gruesa_sin_palanca(self):
        # t grande (>= t_c) -> no hay palanca, T disponible = B.
        r = prying_capacity(_case(40.0))
        assert not r.prying_governs
        assert r.T_avail_kN == pytest.approx(200.0, rel=1e-9)
        assert r.alpha_prime == 0.0

    def test_placa_delgada_reduce_capacidad(self):
        # t pequeno (< t_c) -> palanca, T disponible < B.
        r = prying_capacity(_case(8.0))
        assert r.prying_governs
        assert r.T_avail_kN < 200.0
        assert 0.0 < r.alpha_prime <= 1.0

    def test_capacidad_crece_con_espesor(self):
        delgada = prying_capacity(_case(8.0)).T_avail_kN
        media = prying_capacity(_case(12.0)).T_avail_kN
        assert media > delgada

    def test_parametros_geometricos(self):
        r = prying_capacity(_case(10.0))
        # b' = b - d/2 = 45 - 11 = 34 ; rho = b'/a' con a' = min(a,1.25b)+d/2
        assert 0.0 < r.rho < 1.0
        # delta = 1 - d_hole/p = 1 - 24/90
        assert r.delta == pytest.approx(1.0 - 24.0 / 90.0, rel=1e-9)

    def test_tc_positivo(self):
        r = prying_capacity(_case(10.0))
        assert r.t_c_mm > 0
