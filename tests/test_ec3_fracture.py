"""Tests for steeljoints.ec3_fracture (EN 1993-1-10)."""

import pytest

from steeljoints.ec3_fracture import (
    Z_property_required,
    reference_temperature,
    t_max_brittle_fracture,
)


def test_reference_temperature_additive():
    # T_md = -15, T_r = -5, T_sigma=-10 -> T_Ed = -30 deg C
    T_Ed = reference_temperature(T_md=-15.0, T_r=-5.0, T_sigma=-10.0)
    assert T_Ed == pytest.approx(-30.0)


def test_t_max_s355_j0_neg30_half_fy_against_table():
    # S355 J0, T_Ed = -30 deg C, sigma_Ed = 0.5 * fy_t_ref.
    # Table 2.1 of EN 1993-1-10 gives an admissible thickness of about
    # 50-65 mm for this combination; the calibrated surrogate must land in
    # that physically reasonable window (and strictly above the 0.75*fy
    # anchor, which is 40*exp(-0.023*20) ~ 25 mm).
    t = t_max_brittle_fracture(
        T_Ed=-30.0, sigma_Ed=0.5 * 355.0, fy_t_ref=355.0,
        steel_grade="S355", subgrade="J0",
    )
    assert 30.0 <= t <= 70.0


def test_t_max_orders_with_subgrade():
    # Higher subgrade quality -> larger admissible thickness.
    sigma = 0.5 * 355.0
    t_JR = t_max_brittle_fracture(-20.0, sigma, 355.0, subgrade="JR")
    t_J0 = t_max_brittle_fracture(-20.0, sigma, 355.0, subgrade="J0")
    t_J2 = t_max_brittle_fracture(-20.0, sigma, 355.0, subgrade="J2")
    t_K2 = t_max_brittle_fracture(-20.0, sigma, 355.0, subgrade="K2")
    assert t_JR < t_J0 < t_J2 < t_K2


def test_t_max_decreases_with_lower_temperature():
    sigma = 0.5 * 355.0
    t_warm = t_max_brittle_fracture(0.0, sigma, 355.0, subgrade="J2")
    t_cold = t_max_brittle_fracture(-40.0, sigma, 355.0, subgrade="J2")
    assert t_cold < t_warm


def test_t_max_decreases_with_higher_stress():
    t_low = t_max_brittle_fracture(-20.0, 0.25 * 355.0, 355.0, subgrade="J0")
    t_high = t_max_brittle_fracture(-20.0, 0.75 * 355.0, 355.0, subgrade="J0")
    assert t_high < t_low


def test_z_property_z15_when_z_demand_in_range():
    # EN 1993-1-10 Tabla 3.2: Z_Ed in (10, 20] -> Z15 (v1.1 decía Z25).
    cls = Z_property_required(z_Ed=0.0, conditions={"Za": 3, "Zb": 5, "Zc": 8})
    assert cls == "Z15"


def test_z_property_not_required_up_to_10():
    # Z_Ed <= 10 -> sin requisito de calidad Z.
    assert Z_property_required(z_Ed=8.0) == "none"
    assert Z_property_required(z_Ed=10.0) == "none"


def test_z_property_z25_and_z35_bands():
    assert Z_property_required(z_Ed=25.0) == "Z25"
    assert Z_property_required(z_Ed=30.0) == "Z25"
    assert Z_property_required(z_Ed=35.0) == "Z35"


def test_t_max_invalid_inputs():
    with pytest.raises(ValueError):
        t_max_brittle_fracture(-10.0, -1.0, 355.0)
    with pytest.raises(ValueError):
        t_max_brittle_fracture(-10.0, 100.0, 0.0)
    with pytest.raises(ValueError):
        t_max_brittle_fracture(-10.0, 100.0, 355.0, subgrade="ZZ")
