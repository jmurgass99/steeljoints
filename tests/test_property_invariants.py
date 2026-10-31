"""Property-based tests de invariantes de diseno de conexiones.

Usa hypothesis para generar casos aleatorios y verificar propiedades
fundamentales que SIEMPRE deben cumplirse.
"""
from __future__ import annotations
import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given, strategies as st, assume, settings


pytestmark = [pytest.mark.property]


# -----------------------------------------------------------------------------
# Strategies - parametros fisicamente plausibles
# -----------------------------------------------------------------------------

valid_bolt_diameter = st.floats(min_value=12.0, max_value=40.0)
valid_n_bolts = st.integers(min_value=2, max_value=20)
valid_bolt_grade = st.sampled_from(["A325", "A490"])
valid_weld_leg = st.floats(min_value=3.0, max_value=20.0)
valid_weld_length = st.floats(min_value=50.0, max_value=500.0)
valid_angle_deg = st.floats(min_value=0.0, max_value=90.0)
valid_plate_thickness = st.floats(min_value=6.0, max_value=50.0)
valid_fy = st.floats(min_value=235.0, max_value=460.0)
valid_fc = st.floats(min_value=20.0, max_value=50.0)


# -----------------------------------------------------------------------------
# Invariantes bolts
# -----------------------------------------------------------------------------

@given(grade=valid_bolt_grade, d=valid_bolt_diameter)
@settings(max_examples=40, deadline=1500)
def test_single_bolt_capacity_positive(grade, d):
    """Capacidad de perno SIEMPRE > 0 para inputs validos."""
    from steeljoints.services.bolts import (
        SingleBoltInput, design_single_bolt,
    )
    res = design_single_bolt(SingleBoltInput(grade=grade, diameter_mm=d))
    assert res.Rn_shear_kN > 0
    assert res.Rn_tension_kN > 0
    assert res.Rn_bearing_kN > 0


@given(d1=valid_bolt_diameter, d2=valid_bolt_diameter)
@settings(max_examples=30, deadline=1500)
def test_bolt_larger_diameter_higher_capacity(d1, d2):
    """A mayor diametro -> mayor capacidad al cortante (misma grade)."""
    assume(d1 < d2)
    from steeljoints.services.bolts import (
        SingleBoltInput, design_single_bolt,
    )
    r1 = design_single_bolt(SingleBoltInput(grade="A325", diameter_mm=d1))
    r2 = design_single_bolt(SingleBoltInput(grade="A325", diameter_mm=d2))
    assert r2.Rn_shear_kN > r1.Rn_shear_kN


@given(n=valid_n_bolts, d=valid_bolt_diameter)
@settings(max_examples=30, deadline=2000)
def test_bolt_group_scales_with_n_bolts(n, d):
    """Grupo concentrico: Rn proportional a n_bolts."""
    from steeljoints.services.bolts import (
        BoltGroupInput, design_bolt_group, SingleBoltInput, design_single_bolt,
    )
    single = design_single_bolt(SingleBoltInput(grade="A325", diameter_mm=d))
    group = design_bolt_group(BoltGroupInput(n_bolts=n, diameter_mm=d,
                                              grade="A325"))
    expected = single.Rn_shear_kN * n
    assert abs(group.Rn_group_kN - expected) / expected < 0.01


@given(n=valid_n_bolts, d=valid_bolt_diameter,
       mu=st.floats(min_value=10.0, max_value=200.0))
@settings(max_examples=20, deadline=2000)
def test_bolt_group_eccentric_lower_than_concentric(n, d, mu):
    """Grupo eccentrico tiene capacidad menor que concentrico."""
    from steeljoints.services.bolts import (
        BoltGroupInput, design_bolt_group,
    )
    conc = design_bolt_group(BoltGroupInput(n_bolts=n, diameter_mm=d))
    ecc = design_bolt_group(BoltGroupInput(n_bolts=n, diameter_mm=d, Mu_kNm=mu))
    assert ecc.Rn_group_kN <= conc.Rn_group_kN + 1e-6


# -----------------------------------------------------------------------------
# Invariantes welds
# -----------------------------------------------------------------------------

@given(leg=valid_weld_leg, L=valid_weld_length, ang=valid_angle_deg)
@settings(max_examples=30, deadline=1500)
def test_fillet_weld_capacity_positive(leg, L, ang):
    """Soldadura de filete SIEMPRE > 0 para inputs validos."""
    from steeljoints.services.welds import (
        FilletWeldInput, design_fillet_weld,
    )
    res = design_fillet_weld(FilletWeldInput(
        leg_size_mm=leg, length_mm=L, angle_load_deg=ang,
    ))
    assert res.Rn_kN > 0
    assert res.throat_mm > 0


@given(leg=valid_weld_leg, L=valid_weld_length)
@settings(max_examples=20, deadline=1500)
def test_fillet_weld_transverse_stronger_than_longitudinal(leg, L):
    """Soldadura transversal (90) mas fuerte que longitudinal (0)."""
    from steeljoints.services.welds import (
        FilletWeldInput, design_fillet_weld,
    )
    long_ = design_fillet_weld(FilletWeldInput(
        leg_size_mm=leg, length_mm=L, angle_load_deg=0.0))
    trans = design_fillet_weld(FilletWeldInput(
        leg_size_mm=leg, length_mm=L, angle_load_deg=90.0))
    assert trans.Rn_kN >= long_.Rn_kN - 1e-6


@given(leg1=valid_weld_leg, leg2=valid_weld_leg, L=valid_weld_length)
@settings(max_examples=20, deadline=1500)
def test_fillet_weld_thicker_leg_higher_capacity(leg1, leg2, L):
    """Mayor leg -> mayor capacidad."""
    assume(leg1 < leg2)
    from steeljoints.services.welds import (
        FilletWeldInput, design_fillet_weld,
    )
    r1 = design_fillet_weld(FilletWeldInput(leg_size_mm=leg1, length_mm=L))
    r2 = design_fillet_weld(FilletWeldInput(leg_size_mm=leg2, length_mm=L))
    assert r2.Rn_kN > r1.Rn_kN


# -----------------------------------------------------------------------------
# Invariantes end_plate / base_plate
# -----------------------------------------------------------------------------

@given(tp=valid_plate_thickness, fy=valid_fy)
@settings(max_examples=20, deadline=2000)
def test_end_plate_thicker_higher_capacity(tp, fy):
    """A mayor espesor de placa -> mayor Mn."""
    from steeljoints.services.end_plate import (
        EndPlateInput, design_end_plate,
    )
    r1 = design_end_plate(EndPlateInput(
        bp_mm=200, tp_mm=tp, db_mm=400, bf_mm=200, tf_mm=12,
        bolt_diameter_mm=22, fy_plate_MPa=fy, Mu_kNm=100,
    ))
    r2 = design_end_plate(EndPlateInput(
        bp_mm=200, tp_mm=tp * 1.5, db_mm=400, bf_mm=200, tf_mm=12,
        bolt_diameter_mm=22, fy_plate_MPa=fy, Mu_kNm=100,
    ))
    assert r2.Mn_kNm > r1.Mn_kNm


@given(fc=valid_fc, pu=st.floats(min_value=100.0, max_value=2000.0))
@settings(max_examples=20, deadline=2000)
def test_base_plate_higher_fc_higher_allowable(fc, pu):
    """Mayor f'c del concreto -> mayor fp_allow."""
    from steeljoints.services.base_plate import (
        BasePlateInput, design_base_plate,
    )
    r1 = design_base_plate(BasePlateInput(
        Bp_mm=400, Np_mm=400, tp_mm=25,
        d_col_mm=200, bf_col_mm=200, fc_MPa=fc, Pu_kN=pu,
    ))
    r2 = design_base_plate(BasePlateInput(
        Bp_mm=400, Np_mm=400, tp_mm=25,
        d_col_mm=200, bf_col_mm=200, fc_MPa=fc + 10, Pu_kN=pu,
    ))
    assert r2.fp_allow_MPa > r1.fp_allow_MPa
