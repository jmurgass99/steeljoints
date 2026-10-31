# -*- coding: utf-8 -*-
"""Soldaduras de ranura CJP/PJP (AISC §J2)."""
import pytest

from steeljoints.groove_welds import (
    cjp_strength,
    pjp_effective_throat,
    pjp_strength,
)


class TestCJP:
    def test_gobierna_metal_base(self):
        r = cjp_strength(Fy_MPa=345.0, Fu_MPa=450.0, area_mm2=5000.0, load="tension")
        assert r.governs == "metal_base"
        # Rd = min(0.90·Fy·A, 0.75·Fu·A) = min(0.9·345·5000, 0.75·450·5000)/1e3
        Rd = min(0.90 * 345 * 5000, 0.75 * 450 * 5000) / 1e3
        assert r.Rd_kN == pytest.approx(Rd, rel=1e-9)

    def test_cortante(self):
        r = cjp_strength(345.0, 450.0, 5000.0, "shear")
        assert r.Rn_kN == pytest.approx(0.6 * 345 * 5000 / 1e3, rel=1e-9)

    def test_carga_invalida(self):
        with pytest.raises(Exception):
            cjp_strength(345.0, 450.0, 5000.0, "torsion")


class TestPJPThroat:
    def test_angulo_grande_garganta_completa(self):
        assert pjp_effective_throat(10.0, groove_angle_deg=60.0) == 10.0

    def test_angulo_pequeno_descuenta_3mm(self):
        assert pjp_effective_throat(10.0, groove_angle_deg=50.0, process="SMAW") == 7.0

    def test_angulo_invalido(self):
        with pytest.raises(Exception):
            pjp_effective_throat(10.0, groove_angle_deg=30.0)


class TestPJPStrength:
    def test_soldadura_gobierna_con_garganta_pequena(self):
        # Garganta pequeña -> la soldadura gobierna sobre el metal base.
        r = pjp_strength("E70", throat_mm=5.0, length_mm=200.0, Fy_base_MPa=345.0, t_base_mm=20.0)
        assert r.governs == "soldadura"
        assert r.Rn_kN == pytest.approx(0.60 * 485.0 * 5.0 * 200.0 / 1e3, rel=1e-9)

    def test_metal_base_gobierna_con_garganta_grande(self):
        # Garganta casi igual al espesor -> puede gobernar el metal base.
        r = pjp_strength("E70", throat_mm=18.0, length_mm=200.0, Fy_base_MPa=250.0, t_base_mm=12.0)
        assert r.governs == "metal_base"

    def test_mas_garganta_mas_resistencia(self):
        a = pjp_strength("E70", 4.0, 200.0, 345.0, 20.0).Rd_kN
        b = pjp_strength("E70", 8.0, 200.0, 345.0, 20.0).Rd_kN
        assert b > a
