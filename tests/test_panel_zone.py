"""Tests del chequeo de panel zone."""
from __future__ import annotations
import pytest

from steelconnectionjm.panel_zone import (
    PanelZoneInput, shear_capacity, PanelZoneResult,
)


def _w14x90():
    return PanelZoneInput(
        d_c=0.356, t_w=0.0112, d_b=0.450, b_f_c=0.369, t_f_c=0.0181,
        Fy_c=345e6, P_u=0.0, P_y=4.5e6, consider_plastification=False,
    )


def test_elastic_only():
    r = shear_capacity(_w14x90(), V_demand=500e3)
    assert r.governs == "elastic"
    assert r.Vn > 0
    assert r.DCR > 0


def test_plastic_increases_capacity():
    p_el = PanelZoneInput(d_c=0.356, t_w=0.0112, d_b=0.450, b_f_c=0.369,
                            t_f_c=0.0181, Fy_c=345e6,
                            P_u=0.0, P_y=4.5e6, consider_plastification=False)
    p_pl = PanelZoneInput(d_c=0.356, t_w=0.0112, d_b=0.450, b_f_c=0.369,
                            t_f_c=0.0181, Fy_c=345e6,
                            P_u=0.0, P_y=4.5e6, consider_plastification=True)
    r1 = shear_capacity(p_el)
    r2 = shear_capacity(p_pl)
    assert r2.Vn > r1.Vn


def test_high_axial_reduces_capacity():
    p_low = PanelZoneInput(d_c=0.356, t_w=0.0112, d_b=0.450, b_f_c=0.369,
                             t_f_c=0.0181, Fy_c=345e6,
                             P_u=0.4 * 4.5e6, P_y=4.5e6,
                             consider_plastification=True)
    p_high = PanelZoneInput(d_c=0.356, t_w=0.0112, d_b=0.450, b_f_c=0.369,
                              t_f_c=0.0181, Fy_c=345e6,
                              P_u=0.85 * 4.5e6, P_y=4.5e6,
                              consider_plastification=True)
    r_low = shear_capacity(p_low)
    r_high = shear_capacity(p_high)
    assert r_high.Vn < r_low.Vn


def test_dcr_below_one_when_demand_low():
    r = shear_capacity(_w14x90(), V_demand=100e3)
    assert r.DCR < 1.0


def test_notes_include_phi():
    r = shear_capacity(_w14x90(), V_demand=200e3)
    assert any("phiVn" in n or "phi" in n.lower() or "DCR" in n for n in r.notes)
