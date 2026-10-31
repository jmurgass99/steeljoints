"""Tests for steeljoints.ec3_tension_members (EN 1993-1-11)."""

from math import pi

import pytest

from steeljoints.ec3_tension_members import (
    bending_stress_at_anchorage,
    fatigue_class_strand,
    partial_factor_gM,
    tendon_resistance_FRk,
)


def test_FRk_7wire_strand_15p7_1860_groupB():
    # 7-wire prestressing strand, nominal diameter 15.7 mm, fuk = 1860 MPa.
    # Nominal metallic area ~ 150 mm^2 -> F_uk_nom ~ 150 * 1860 ~ 279 kN.
    # Group B (strands) reduces by 0.92 -> ~ 256 kN. Accept a +/-10 % window.
    F = tendon_resistance_FRk(d_w=5.2, fuk=1860.0, n_wires=7, group=2)
    F_kN = F / 1000.0
    assert F_kN == pytest.approx(256.0, rel=0.10)


def test_FRk_groups_ordered():
    # For the same geometry: F_RkA > F_RkB > F_RkC.
    F_A = tendon_resistance_FRk(d_w=5.0, fuk=1860.0, n_wires=7, group=1)
    F_B = tendon_resistance_FRk(d_w=5.0, fuk=1860.0, n_wires=7, group=2)
    F_C = tendon_resistance_FRk(d_w=5.0, fuk=1860.0, n_wires=7, group=3)
    assert F_A > F_B > F_C
    assert F_B == pytest.approx(0.92 * F_A)
    assert F_C == pytest.approx(0.85 * F_A)


def test_FRk_invalid_inputs():
    with pytest.raises(ValueError):
        tendon_resistance_FRk(d_w=0.0, fuk=1860.0, n_wires=7)
    with pytest.raises(ValueError):
        tendon_resistance_FRk(d_w=5.0, fuk=1860.0, n_wires=0)
    with pytest.raises(ValueError):
        tendon_resistance_FRk(d_w=5.0, fuk=1860.0, n_wires=7, group=9)


def test_gM_transport_lower_than_service():
    g_tr = partial_factor_gM(safety_class=2, condition="transport")
    g_sv = partial_factor_gM(safety_class=2, condition="service")
    assert g_tr < g_sv
    assert g_sv == pytest.approx(1.50)
    assert g_tr == pytest.approx(1.00)


def test_gM_scales_with_consequence_class():
    g_cc1 = partial_factor_gM(safety_class=1, condition="service")
    g_cc2 = partial_factor_gM(safety_class=2, condition="service")
    g_cc3 = partial_factor_gM(safety_class=3, condition="service")
    assert g_cc1 < g_cc2 < g_cc3
    assert g_cc3 / g_cc2 == pytest.approx(1.1)
    assert g_cc1 / g_cc2 == pytest.approx(0.9)


def test_gM_invalid_inputs():
    with pytest.raises(ValueError):
        partial_factor_gM(safety_class=2, condition="nope")
    with pytest.raises(ValueError):
        partial_factor_gM(safety_class=99, condition="service")


def test_bending_stress_at_anchorage_positive_and_scales():
    I = pi * 20.0 ** 4 / 64.0
    s1 = bending_stress_at_anchorage(F=100_000.0, d=20.0, L_free=5000.0,
                                     E=195_000.0, I=I)
    s2 = bending_stress_at_anchorage(F=400_000.0, d=20.0, L_free=5000.0,
                                     E=195_000.0, I=I)
    assert s1 > 0
    # sigma ~ sqrt(F) -> doubling F should multiply sigma by ~ 2.
    assert s2 / s1 == pytest.approx(2.0, rel=1e-6)


def test_fatigue_class_strand_table_values():
    assert fatigue_class_strand(d=20.0, type="strand") == 150
    assert fatigue_class_strand(d=60.0, type="strand") == 120
    assert fatigue_class_strand(d=50.0, type="locked_coil") == 120
    assert fatigue_class_strand(d=100.0, type="locked_coil") == 90
    assert fatigue_class_strand(d=10.0, type="wire") == 160
    assert fatigue_class_strand(d=30.0, type="bar") == 105


def test_fatigue_class_strand_invalid():
    with pytest.raises(ValueError):
        fatigue_class_strand(d=0.0, type="strand")
    with pytest.raises(ValueError):
        fatigue_class_strand(d=10.0, type="banana")
