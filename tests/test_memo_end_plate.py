"""Tests memo end-plate."""
import pytest

from steelconnectionjm.memos.end_plate import (
    EndPlateInput, render_end_plate_memo,
)


def test_demanda_baja_safe():
    # End-plate suficientemente gruesa para resistir 20 kN.m
    r = render_end_plate_memo(EndPlateInput(
        M_demand_kNm=20, bolt_diameter_mm=25.4,
        plate_thickness_mm=50, plate_width_mm=400,
    ))
    assert r.is_safe
    assert r.DCR_moment < 1


def test_demanda_alta_falla():
    r = render_end_plate_memo(EndPlateInput(
        M_demand_kNm=2000, bolt_diameter_mm=20,
        plate_thickness_mm=20, plate_width_mm=200,
    ))
    assert not r.is_safe


def test_markdown_estructura():
    r = render_end_plate_memo(EndPlateInput(M_demand_kNm=300,
                                              bolt_diameter_mm=22))
    for kw in ("Paso 1", "Paso 2", "Paso 3", "DCR"):
        assert kw in r.markdown
