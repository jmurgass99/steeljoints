"""Tests RBS AISC 358 memo."""
from __future__ import annotations
import pytest

handcalcs = pytest.importorskip("handcalcs")
from steeljoints.memos import rbs_aisc358_memo


def _w24x76_typical():
    """W24x76: d=608 mm, bf=228 mm, tf=17.3 mm, Z_x ~ 3050000 mm3."""
    return dict(
        beam_d=608.0, beam_bf=228.0, beam_tf=17.3, beam_Z_x=3050000.0,
        a=140.0, b=460.0, c=45.0, L_clear=6.0, wu=15.0,
        Fy=345.0, Ry=1.1, Cpr=1.15,
    )


def test_rbs_basic_output():
    latex, res = rbs_aisc358_memo(**_w24x76_typical())
    assert res.M_pr_kNm > 0
    assert res.Vp_kN > 0
    assert res.M_f_kNm > res.M_pr_kNm
    assert res.Z_RBS_mm3 < 3050000.0
    assert "\\" in latex


def test_rbs_geometry_ok_for_typical():
    _, res = rbs_aisc358_memo(**_w24x76_typical())
    assert res.is_geometry_ok


def test_rbs_geometry_fails_for_extreme_c():
    c = _w24x76_typical()
    c["c"] = 100.0  # > 0.25*bf = 57 mm
    _, res = rbs_aisc358_memo(**c)
    assert not res.is_geometry_ok


def test_rbs_invalid_inputs():
    c = _w24x76_typical()
    with pytest.raises(ValueError):
        rbs_aisc358_memo(**{**c, "beam_d": -1})
    with pytest.raises(ValueError):
        rbs_aisc358_memo(**{**c, "b": 0})
    with pytest.raises(ValueError):
        rbs_aisc358_memo(**{**c, "Ry": 0.5})


def test_rbs_larger_cut_lower_capacity():
    c = _w24x76_typical()
    _, r1 = rbs_aisc358_memo(**c)
    c2 = dict(c); c2["c"] = 55.0  # mayor recorte
    _, r2 = rbs_aisc358_memo(**c2)
    assert r2.M_pr_kNm < r1.M_pr_kNm
