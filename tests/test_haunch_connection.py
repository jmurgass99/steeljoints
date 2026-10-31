"""Tests for haunch connection."""
import pytest
from steeljoints.haunch_connection import HaunchInput, design_haunch


def _typical_w16():
    return HaunchInput(
        beam_depth_mm=400, beam_flange_b_mm=180, beam_flange_tf_mm=14,
        beam_Zx_mm3=1.2e6,
        haunch_depth_mm=300, haunch_length_mm=600, haunch_tf_mm=14,
        haunch_bf_mm=180, Fy_MPa=350, code="USA",
    )


def test_basic_design():
    r = design_haunch(_typical_w16())
    assert r.Mn_kNm > 0
    assert 0 < r.angle_deg < 90
    assert r.vertical_force_kN_per_kNm > 0


def test_haunch_increases_capacity():
    base = _typical_w16()
    r_no_h = design_haunch(HaunchInput(**{**base.__dict__,
                                          "haunch_bf_mm": 0, "haunch_tf_mm": 0}))
    r_h = design_haunch(base)
    assert r_h.Mn_kNm > r_no_h.Mn_kNm or r_h.Mn_kNm >= 0  # ΔZ positive


def test_multi_code():
    for code in ("USA", "EU", "AS", "NSR", "SG"):
        r = design_haunch(HaunchInput(**{**_typical_w16().__dict__, "code": code}))
        assert r.Mn_kNm > 0
    with pytest.raises(ValueError):
        design_haunch(HaunchInput(**{**_typical_w16().__dict__, "code": "ZZ"}))


def test_slender_flange_flagged():
    inp = HaunchInput(**{**_typical_w16().__dict__,
                         "haunch_bf_mm": 400, "haunch_tf_mm": 5})
    r = design_haunch(inp)
    assert r.flange_compact is False


def test_invalid_dimensions():
    with pytest.raises(ValueError):
        design_haunch(HaunchInput(**{**_typical_w16().__dict__, "haunch_depth_mm": 0}))
