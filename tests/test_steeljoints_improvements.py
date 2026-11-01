"""Tests for steeljoints engineering and normative improvements."""
from __future__ import annotations

from math import sqrt
import pytest

from steeljoints.base_plate import BasePlate
from steeljoints.codes import aisc358, ec3_1_8
from steeljoints.services.base_plate import BasePlateInput, design_base_plate
from steeljoints.services.clip_angle import ClipAngleInput, design_clip_angle
from steeljoints.services.splice import SpliceInput, design_splice


def test_dg1_eccentric_pressure_small_and_large_moment() -> None:
    bp_small = BasePlate(
        Pu=1200.0,
        Mu=40.0,
        column_d=300.0,
        column_bf=250.0,
        plate_B=450.0,
        plate_N=500.0,
        fc_concrete=28.0,
    )
    res_small = bp_small.dg1_eccentric_pressure(edge_dist_f_mm=50.0)
    assert res_small["regime"] == "small_moment"
    assert res_small["Tu_total_kN"] == pytest.approx(0.0)
    assert res_small["Y_mm"] == pytest.approx(500.0 - 2.0 * (40e6 / 1.2e6), rel=1e-4)

    bp_large = BasePlate(
        Pu=600.0,
        Mu=180.0,
        column_d=300.0,
        column_bf=250.0,
        plate_B=450.0,
        plate_N=500.0,
        fc_concrete=28.0,
    )
    res_large = bp_large.dg1_eccentric_pressure(edge_dist_f_mm=50.0)
    assert res_large["regime"] == "large_moment"
    assert res_large["Tu_total_kN"] > 0.0
    assert 0.0 < res_large["Y_mm"] < 500.0


def test_service_base_plate_with_moment_and_anchors() -> None:
    r0 = design_base_plate(
        BasePlateInput(
            Bp_mm=450.0,
            Np_mm=500.0,
            tp_mm=30.0,
            d_col_mm=300.0,
            bf_col_mm=250.0,
            fc_MPa=28.0,
            fy_plate_MPa=345.0,
            Pu_kN=600.0,
            Mu_kNm=0.0,
        )
    )
    rm = design_base_plate(
        BasePlateInput(
            Bp_mm=450.0,
            Np_mm=500.0,
            tp_mm=30.0,
            d_col_mm=300.0,
            bf_col_mm=250.0,
            fc_MPa=28.0,
            fy_plate_MPa=345.0,
            Pu_kN=600.0,
            Mu_kNm=180.0,
        )
    )
    assert r0.T_anchor_per_bolt_kN == 0.0
    assert rm.T_anchor_per_bolt_kN > 0.0
    assert rm.DCR > r0.DCR


def test_aisc358_yp_4e_unstiffened_vs_4es_stiffened() -> None:
    bp, g, pfo, pfi, h0, h1 = 215.0, 140.0, 40.0, 40.0, 482.5, 387.5
    s = sqrt(bp * g) / 2.0
    yp_4e = aisc358.Yp_4E_unstiffened(bp, g, pfo, pfi, h0, h1, s)
    yp_4es = aisc358.Yp_4ES_stiffened(bp, g, pfo, pfi, h0, h1, s, de=40.0)
    expected_4e = (bp / 2.0) * (h1 * (1.0 / pfi + 1.0 / s) + h0 / pfo - 0.5) + (2.0 / g) * (h1 * (pfi + s))
    assert yp_4e == pytest.approx(expected_4e, rel=1e-9)
    assert yp_4es > yp_4e


def test_service_splice_and_clip_angle_delegation() -> None:
    sp_no_bolts = design_splice(SpliceInput(Mu_kNm=150.0, Vu_kN=100.0, beam_depth_mm=500.0))
    sp_with_bolts = design_splice(
        SpliceInput(
            Mu_kNm=150.0,
            Vu_kN=100.0,
            beam_depth_mm=500.0,
            n_bolts_web=6,
            bolt_capacity_kN=80.0,
        )
    )
    assert sp_no_bolts.bolt_demand_max_kN == 0.0
    assert sp_with_bolts.bolt_demand_max_kN > 0.0
    assert sp_with_bolts.bolt_dcr > 0.0

    ca_full = design_clip_angle(
        ClipAngleInput(
            leg_a_mm=100.0,
            leg_b_mm=100.0,
            thickness_mm=9.5,
            Vu_kN=180.0,
            angle_type="double",
            full_aisc_checks=True,
            n_bolts=4,
        )
    )
    assert ca_full.Rn_kN > 0.0
    assert ca_full.DCR > 0.0
    assert ca_full.governing_check != ""


def test_ec3_bolt_bearing_inner_vs_edge() -> None:
    fb_edge = ec3_1_8.bolt_bearing_Rd(
        d_mm=20.0,
        t_mm=12.0,
        fu_plate_MPa=430.0,
        fub_MPa=800.0,
        e1=35.0,
        p1=70.0,
        e2=30.0,
        p2=60.0,
        direction_inner=False,
        d0_mm=22.0,
    )
    fb_inner = ec3_1_8.bolt_bearing_Rd(
        d_mm=20.0,
        t_mm=12.0,
        fu_plate_MPa=430.0,
        fub_MPa=800.0,
        e1=35.0,
        p1=70.0,
        e2=30.0,
        p2=60.0,
        direction_inner=True,
        d0_mm=22.0,
    )
    assert fb_inner != fb_edge
    assert fb_inner > 0.0
