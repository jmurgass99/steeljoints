"""Tests del service layer headless."""
from __future__ import annotations
import pytest

from steeljoints.services.bolts import (
    SingleBoltInput, BoltGroupInput, design_single_bolt, design_bolt_group,
)
from steeljoints.services.welds import FilletWeldInput, design_fillet_weld
from steeljoints.services.end_plate import EndPlateInput, design_end_plate
from steeljoints.services.base_plate import BasePlateInput, design_base_plate
from steeljoints.services.panel_zone import (
    PanelZoneServiceInput, design_panel_zone,
)
from steeljoints.services.splice import SpliceInput, design_splice
from steeljoints.services.clip_angle import ClipAngleInput, design_clip_angle


def test_single_bolt_a325():
    res = design_single_bolt(SingleBoltInput(
        grade="A325", diameter_mm=22.0, plate_thickness_mm=10,
    ))
    assert res.Rn_shear_kN > 0
    assert res.Rn_tension_kN > res.Rn_shear_kN


def test_single_bolt_a490_stronger_than_a325():
    a325 = design_single_bolt(SingleBoltInput(grade="A325", diameter_mm=22))
    a490 = design_single_bolt(SingleBoltInput(grade="A490", diameter_mm=22))
    assert a490.Rn_shear_kN > a325.Rn_shear_kN


def test_bolt_group_concentric():
    res = design_bolt_group(BoltGroupInput(n_bolts=6, diameter_mm=22))
    assert res.Rn_group_kN > 0


def test_bolt_group_eccentric_reduces_capacity():
    conc = design_bolt_group(BoltGroupInput(n_bolts=6, diameter_mm=22))
    ecc = design_bolt_group(BoltGroupInput(n_bolts=6, diameter_mm=22, Mu_kNm=100))
    assert ecc.Rn_group_kN < conc.Rn_group_kN


def test_fillet_weld_basic():
    res = design_fillet_weld(FilletWeldInput(leg_size_mm=6, length_mm=200))
    assert res.throat_mm > 0
    assert res.Rd_kN > 0


def test_fillet_weld_transverse_stronger():
    long = design_fillet_weld(FilletWeldInput(leg_size_mm=6, length_mm=200,
                                              angle_load_deg=0))
    trans = design_fillet_weld(FilletWeldInput(leg_size_mm=6, length_mm=200,
                                               angle_load_deg=90))
    assert trans.Rn_kN > long.Rn_kN


def test_end_plate_basic():
    res = design_end_plate(EndPlateInput(
        bp_mm=200, tp_mm=20, db_mm=500, bf_mm=200, tf_mm=15,
        bolt_diameter_mm=22, Mu_kNm=200,
    ))
    assert res.Mn_kNm > 0
    assert res.plate_thickness_required_mm > 0


def test_base_plate_axial():
    res = design_base_plate(BasePlateInput(
        Bp_mm=400, Np_mm=400, tp_mm=25, d_col_mm=250, bf_col_mm=250, Pu_kN=1000,
    ))
    assert res.fp_actual_MPa > 0
    assert res.tp_required_mm > 0


def test_panel_zone_service():
    res = design_panel_zone(PanelZoneServiceInput(
        d_c_mm=356, t_w_mm=11.2, d_b_mm=450, b_f_c_mm=369, t_f_c_mm=18.1,
        Fy_c_MPa=345, V_demand_kN=500,
    ))
    assert res.Vn_kN > 0


def test_splice_basic():
    res = design_splice(SpliceInput(Mu_kNm=150, Vu_kN=100))
    assert res.Mn_kNm > 0


def test_clip_angle_double_stronger_than_single():
    single = design_clip_angle(ClipAngleInput(
        leg_a_mm=100, leg_b_mm=100, thickness_mm=10, Vu_kN=50, angle_type="single"))
    double = design_clip_angle(ClipAngleInput(
        leg_a_mm=100, leg_b_mm=100, thickness_mm=10, Vu_kN=50, angle_type="double"))
    assert double.Rn_kN == pytest.approx(2 * single.Rn_kN, rel=0.001)
