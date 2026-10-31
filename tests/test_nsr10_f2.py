"""Tests de la implementación NSR-10 F.2."""
from __future__ import annotations
import math
import pytest

from steeljoints.codes.nsr10_f2 import (
    design_bolt_nsr10, NSR10BoltInput,
    design_fillet_weld_nsr10, NSR10FilletWeldInput,
    design_block_shear_nsr10, NSR10BlockShearInput,
    PHI_BOLT_SHEAR, PHI_WELD, BOLT_GRADES_NSR10, info,
)
from steeljoints.exceptions import CodeError, ConfigurationError


def test_info_returns_string():
    txt = info()
    assert "NSR-10" in txt
    assert "F.2" in txt


def test_bolt_a325_basic():
    res = design_bolt_nsr10(NSR10BoltInput(grade="A325", diameter_mm=22))
    assert res.Rn_shear_kN > 0
    assert res.Rd_shear_kN == pytest.approx(
        PHI_BOLT_SHEAR * res.Rn_shear_kN, rel=0.001)


def test_bolt_a490_stronger_than_a325():
    a325 = design_bolt_nsr10(NSR10BoltInput(grade="A325", diameter_mm=22))
    a490 = design_bolt_nsr10(NSR10BoltInput(grade="A490", diameter_mm=22))
    assert a490.Rn_shear_kN > a325.Rn_shear_kN


def test_bolt_invalid_grade_raises_code_error():
    with pytest.raises(CodeError):
        design_bolt_nsr10(NSR10BoltInput(grade="UNKNOWN", diameter_mm=22))


def test_bolt_invalid_thread_raises_config_error():
    with pytest.raises(ConfigurationError):
        design_bolt_nsr10(NSR10BoltInput(grade="A325", diameter_mm=22,
                                         thread_condition="Z"))


def test_bolt_thread_excluded_stronger():
    n = design_bolt_nsr10(NSR10BoltInput(grade="A325", diameter_mm=22,
                                         thread_condition="N"))
    x = design_bolt_nsr10(NSR10BoltInput(grade="A325", diameter_mm=22,
                                         thread_condition="X"))
    assert x.Rn_shear_kN > n.Rn_shear_kN


def test_fillet_weld_basic():
    res = design_fillet_weld_nsr10(NSR10FilletWeldInput(leg_size_mm=6,
                                                        length_mm=200))
    assert res.throat_mm == pytest.approx(0.707 * 6, rel=0.01)
    assert res.Rd_kN == pytest.approx(PHI_WELD * res.Rn_kN, rel=0.001)


def test_fillet_weld_transverse_stronger():
    long_ = design_fillet_weld_nsr10(NSR10FilletWeldInput(
        leg_size_mm=6, length_mm=200, angle_load_deg=0))
    trans = design_fillet_weld_nsr10(NSR10FilletWeldInput(
        leg_size_mm=6, length_mm=200, angle_load_deg=90))
    assert trans.Rn_kN > long_.Rn_kN


def test_block_shear_governs_correctly():
    res = design_block_shear_nsr10(NSR10BlockShearInput(
        Agv_mm2=2000, Anv_mm2=1500, Ant_mm2=600,
    ))
    assert res.Rn_kN > 0
    assert res.governing in ("shear_yield", "shear_rupture")
