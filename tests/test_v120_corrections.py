"""Correcciones de la 1.2.0, cada una contra un cálculo a mano o un método independiente del paquete."""
import math
import sys
import tomllib
from pathlib import Path

import pytest

import steeljoints
from steeljoints import BoltGroupICR, WeldGroupICR, WeldSegment, rectangular_pattern
from steeljoints.block_shear import block_shear_strength
from steeljoints.block_shear_multi import BlockShearInput, block_shear
from steeljoints.bolts import Bolt, bolt_gross_area, bolt_tensile_stress_area, ec3_normal_hole_clearance
from steeljoints.codes import aisc358
from steeljoints.end_plate import EndPlate
from steeljoints.exceptions import DependencyError
from steeljoints.panel_zone import PanelZone, PanelZoneInput, shear_capacity
from steeljoints.prying import PryingInput, prying_capacity

KSI = 6.894757


# ---------------------------------------------------------------- pernos AISC 360-22 Tabla J3.2
def test_aisc_shear_threads_included_uses_fnv_n_on_gross_area_once():
    b = Bolt(19.05, "A325", "AISC", threads_in_shear_plane=True)
    Ab = bolt_gross_area(19.05)                      # 285.0 mm2 (3/4")
    assert b.aisc_shear_strength() == pytest.approx(0.75 * 54 * KSI * Ab, rel=1e-3)   # ≈ 79,6 kN
    assert b.aisc_shear_strength() / 1e3 == pytest.approx(79.6, abs=0.1)


def test_aisc_shear_threads_excluded_uses_fnv_x():
    bn = Bolt(19.05, "A325", "AISC", threads_in_shear_plane=True)
    bx = Bolt(19.05, "A325", "AISC", threads_in_shear_plane=False)
    assert bx.aisc_shear_strength() / bn.aisc_shear_strength() == pytest.approx(68 / 54, rel=1e-3)


def test_a490_n_is_68_ksi():
    b = Bolt(19.05, "A490", "AISC")
    assert b.aisc_shear_strength() == pytest.approx(0.75 * 68 * KSI * bolt_gross_area(19.05), rel=1e-3)


# ---------------------------------------------------------------- pernos EN 1993-1-8 Tabla 3.4
def test_tensile_stress_area_m20_and_iso_formula():
    assert bolt_tensile_stress_area(20.0) == pytest.approx(245.0)
    # fuera de catálogo: π/4·(33 − 0.9382·3.5)² = 693.6 mm2 (M33, ISO 898-1: 694)
    assert bolt_tensile_stress_area(33.0) == pytest.approx(694.0, rel=2e-3)


def test_ec3_tension_uses_as_not_gross_area():
    b = Bolt(20.0, "8.8", "EC3")
    assert b.ec3_tension_strength() == pytest.approx(0.9 * 800 * 245 / 1.25)          # 141 120 N


def test_ec3_bearing_uses_hole_diameter_in_position_ratios():
    b = Bolt(20.0, "8.8", "EC3")
    assert ec3_normal_hole_clearance(20.0) == 2.0 and ec3_normal_hole_clearance(12.0) == 1.0 and ec3_normal_hole_clearance(30.0) == 3.0
    t, fu, e1, p1, e2, p2, d0 = 10.0, 360.0, 40.0, 70.0, 30.0, 60.0, 22.0
    alpha = min(e1 / (3 * d0), p1 / (3 * d0) - 0.25, 800 / fu, 1.0)
    k1 = min(2.8 * e2 / d0 - 1.7, 1.4 * p2 / d0 - 1.7, 2.5)
    expected = k1 * alpha * fu * 20.0 * t / 1.25
    assert b.ec3_bearing_strength(t, fu, e1, p1, e2, p2) == pytest.approx(expected)
    assert b.ec3_bearing_strength(t, fu, e1, p1, e2, p2, d0=20.0) > expected        # con d en vez de d0 sale mayor


# ---------------------------------------------------------------- bloque de cortante EC3
def test_block_shear_ec3_matches_block_shear_multi():
    Agv, Anv, Ant, Fy, Fu = 2400.0, 1800.0, 450.0, 275.0, 430.0
    legacy = block_shear_strength(Agv, Anv, Ant, Fy, Fu, code="EC3")
    multi = block_shear(BlockShearInput(Agv_mm2=Agv, Anv_mm2=Anv, Ant_mm2=Ant, Fy_MPa=Fy, Fu_MPa=Fu), code="EU")
    assert legacy["Veff_kN"] == pytest.approx(multi.Rd_kN, rel=1e-4)
    assert legacy["Veff_N"] == pytest.approx(Fu * Ant / 1.25 + Fy * Anv / math.sqrt(3), rel=1e-6)


# ---------------------------------------------------------------- zona de panel, los cuatro casos de §J10.6
def _pz(P_ratio, considered):
    return PanelZoneInput(d_c=0.356, t_w=0.0112, d_b=0.450, b_f_c=0.369, t_f_c=0.0181, Fy_c=345e6,
                          P_u=P_ratio * 4.5e6, P_y=4.5e6, consider_plastification=considered)


def test_panel_zone_functional_api_reduces_without_deformation_above_0_4():
    base = 0.60 * 345e6 * 0.356 * 0.0112
    assert shear_capacity(_pz(0.3, False)).Vn == pytest.approx(base)
    assert shear_capacity(_pz(0.6, False)).Vn == pytest.approx(base * (1.4 - 0.6))
    factor = 1 + 3 * 0.369 * 0.0181 ** 2 / (0.450 * 0.356 * 0.0112)
    assert shear_capacity(_pz(0.6, True)).Vn == pytest.approx(base * factor)                # ≤ 0.75: sin reducción
    assert shear_capacity(_pz(0.85, True)).Vn == pytest.approx(base * factor * (1.9 - 1.2 * 0.85))


def test_panel_zone_class_considered_branch_uses_0_75_threshold():
    kw = dict(Mu_left_kNm=400.0, Mu_right_kNm=400.0, Vu_col_kN=50.0, Py_kN=4500.0, db_mm=450.0, bf_b_mm=190.0,
              tf_b_mm=14.6, dc_mm=356.0, tw_c_mm=11.2, bcf_mm=369.0, tcf_mm=18.1, Fy_col_MPa=345.0)
    base = 0.60 * 345.0 * 356.0 * 11.2
    incr = 1 + 3 * 369.0 * 18.1 ** 2 / (450.0 * 356.0 * 11.2)
    assert PanelZone(Pr_kN=0.6 * 4500, inelastic_action=True, **kw).capacity()["Rn_N"] == pytest.approx(base * incr, rel=1e-6)
    assert PanelZone(Pr_kN=0.6 * 4500, inelastic_action=False, **kw).capacity()["Rn_N"] == pytest.approx(base * 0.8, rel=1e-6)


# ---------------------------------------------------------------- chapa frontal: h1 al eje del ala comprimida
def test_end_plate_h1_measured_to_compression_flange_centreline():
    ep = EndPlate(Mu=200.0, Vu=100.0, beam_depth=450.0, beam_tf=15.0, beam_bf=190.0, bolt_diameter=22.0,
                  plate_thickness=20.0, plate_width=215.0, pfo=40.0, pfi=40.0, g=140.0)
    s = math.sqrt(215.0 * 140.0) / 2
    h0 = 450.0 - 7.5 + 40.0
    h1 = 450.0 - 22.5 - 40.0
    assert ep._Yp() == pytest.approx(aisc358.Yp_4E_unstiffened(215.0, 140.0, 40.0, 40.0, h0, h1, s))


# ---------------------------------------------------------------- prying con Fu (Manual AISC 13.ª ed. en adelante)
def test_prying_tc_uses_fu_when_given():
    kw = dict(B_kN=200.0, b_mm=45.0, a_mm=50.0, p_mm=90.0, t_mm=20.0, d_mm=22.0, Fy_MPa=345.0)
    r_fy = prying_capacity(PryingInput(**kw))
    r_fu = prying_capacity(PryingInput(Fu_MPa=450.0, **kw))
    assert r_fu.t_c_mm == pytest.approx(r_fy.t_c_mm * math.sqrt(345.0 / 450.0))


# ---------------------------------------------------------------- servicios
def test_service_bolt_group_elastic_line():
    from steeljoints.services.bolts import BoltGroupInput, SingleBoltInput, design_bolt_group, design_single_bolt
    single = design_single_bolt(SingleBoltInput(grade="A325", diameter_mm=22.0))
    r = design_bolt_group(BoltGroupInput(n_bolts=4, diameter_mm=22.0, spacing_mm=76.0, Vu_kN=100.0, Mu_kNm=10.0))
    ys = [-114.0, -38.0, 38.0, 114.0]
    f_M = 10e3 * 114.0 / sum(y * y for y in ys)                       # kN
    f_crit = math.hypot(100.0 / 4, f_M)
    assert r.DCR_shear == pytest.approx(f_crit / single.Rd_shear_kN)
    assert r.Rn_group_kN == pytest.approx(4 * math.sqrt(single.Rn_shear_kN ** 2 - f_M ** 2))
    with pytest.raises(ValueError):
        design_bolt_group(BoltGroupInput(n_bolts=4, diameter_mm=22.0, layout="grid"))


def test_service_ec3_bolt_alpha_v_by_grade_and_as_in_thread():
    from steeljoints.services.bolts import SingleBoltInput, design_single_bolt
    r88 = design_single_bolt(SingleBoltInput(grade="8.8", diameter_mm=20.0, standard="EC3", thread_condition="N"))
    r109 = design_single_bolt(SingleBoltInput(grade="10.9", diameter_mm=20.0, standard="EC3", thread_condition="N"))
    assert r88.Rd_shear_kN == pytest.approx(0.6 * 800 * 245 / 1.25 / 1e3)
    assert r109.Rd_shear_kN == pytest.approx(0.5 * 1000 * 245 / 1.25 / 1e3)
    assert r88.Rn_tension_kN == pytest.approx(0.9 * 800 * 245 / 1e3)


def test_service_end_plate_delegates_to_endplate_yield_lines():
    from steeljoints.services.end_plate import EndPlateInput, design_end_plate
    r = design_end_plate(EndPlateInput(bp_mm=215, tp_mm=20, db_mm=450, bf_mm=190, tf_mm=15, bolt_diameter_mm=22, Mu_kNm=200))
    ep = EndPlate(Mu=200, Vu=0, beam_depth=450, beam_tf=15, beam_bf=190, bolt_diameter=22, plate_thickness=20, plate_width=215)
    assert r.Mn_kNm == pytest.approx(ep.plate_flexure_check()["phi_Mn_kNm"])
    assert r.Mn_kNm > 100.0                       # antes ≈ 6 kN·m por una fórmula dimensionalmente errónea


def test_service_base_plate_delegates_and_checks_thickness():
    from steeljoints.base_plate import BasePlate
    from steeljoints.services.base_plate import BasePlateInput, design_base_plate
    r = design_base_plate(BasePlateInput(Bp_mm=450, Np_mm=500, tp_mm=25, d_col_mm=310, bf_col_mm=305, fc_MPa=28, fy_plate_MPa=250, Pu_kN=2000))
    bp = BasePlate(Pu=2000, column_d=310, column_bf=305, plate_B=450, plate_N=500, plate_Fy=250, fc_concrete=28)
    assert r.tp_required_mm == pytest.approx(bp.required_thickness()["tp_required_mm"])
    assert r.DCR == pytest.approx(max(bp.bearing_check()["utilization"], r.tp_required_mm / 25))


# ---------------------------------------------------------------- scipy ausente -> DependencyError, no ImportError crudo
def test_icr_without_scipy_raises_dependency_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "scipy.optimize", None)
    segs = [WeldSegment(0, 0, 0, 200, w_mm=8.0), WeldSegment(100, 0, 100, 200, w_mm=8.0)]
    with pytest.raises(DependencyError):
        WeldGroupICR(segments=segs, Pu_N=100e3, ex_mm=150.0).solve()
    g = BoltGroupICR(positions=rectangular_pattern(2, 3, 75, 75), Pu_N=1e5, ex_mm=150.0, load_angle_deg=30.0, Rult_N=1e5)
    with pytest.raises(DependencyError):
        g.solve()


# ---------------------------------------------------------------- versión única
def test_single_version():
    pyproject = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8"))
    assert steeljoints.__version__ == pyproject["project"]["version"] == "1.2.0"
    pytest.importorskip("fastapi")
    from steeljoints.api.app import app
    assert app.version == "1.2.0"


def test_aisc_standard_hole_tables_j3_3_and_j3_3m():
    from steeljoints.catalog import standard_hole
    # J3.3M (métrico) y J3.3 (imperial, 360-16/22: d + 1/8" desde 1")
    assert [standard_hole(d) for d in (16.0, 20.0, 22.0, 24.0, 27.0, 30.0)] == [18.0, 22.0, 24.0, 27.0, 30.0, 33.0]
    assert standard_hole(36.0) == 39.0
    assert standard_hole(19.05) == pytest.approx(19.05 + 1.5875)
    assert standard_hole(25.4) == pytest.approx(28.575)
    assert standard_hole(20.0, metric=False) == pytest.approx(21.5875)


def test_weldgroup_elastic_evaluates_segment_ends_and_matches_line_method():
    from steeljoints.weld_group import WeldGroupElastic, WeldSegment
    from steeljoints.welds import FilletWeld, WeldGroup
    # un cordón vertical centrado: el momento ya no desaparece
    g1 = WeldGroup(welds=[FilletWeld(8.0, 200.0)], positions=[(0.0, 0.0)], angles=[90.0])
    sin_m = g1.utilization(100e3, 0.0, 1000.0)["max_stress_N_mm2"]
    con_m = g1.utilization(100e3, 20e6, 1000.0)["max_stress_N_mm2"]
    assert con_m > 3 * sin_m
    # dos cordones horizontales de 200 mm a ±100 mm: igual que el método de línea
    g2 = WeldGroup(welds=[FilletWeld(8.0, 200.0), FilletWeld(8.0, 200.0)], positions=[(0.0, -100.0), (0.0, 100.0)])
    mine = g2.utilization(500e3, 50e6, 1000.0)["max_stress_N_mm2"]
    line = WeldGroupElastic(
        segments=[WeldSegment(-100.0, -100.0, 100.0, -100.0, 8.0), WeldSegment(-100.0, 100.0, 100.0, 100.0, 8.0)],
        Vy=500e3, Mz=50e6,
    ).max_demand()["f_max_N_per_mm"] / (8.0 / math.sqrt(2.0))
    assert mine == pytest.approx(line, rel=1e-4)


def test_ec3_weld_functions_refuse_unknown_grade_instead_of_defaulting_beta_w():
    from steeljoints.codes.ec3_1_8 import beta_w, fillet_weld_Rd_directional, fillet_weld_Rd_simplified
    assert beta_w("S355JR") == beta_w("s355") == 0.90
    with pytest.raises(ValueError):
        fillet_weld_Rd_simplified(5.0, 100.0, 540.0, steel_grade="S690")
    with pytest.raises(ValueError):
        fillet_weld_Rd_directional(5.0, 100.0, 540.0, steel_grade="")
    # S460 con su βw = 1,00, no con 0,85
    assert fillet_weld_Rd_simplified(5.0, 100.0, 540.0, steel_grade="S460") == pytest.approx(540.0 / (1.00 * math.sqrt(3) * 1.25) * 500.0)


def test_weld_icr_centered_load_uses_deformation_compatibility():
    from steeljoints.weld_group import _weld_capacity_at_angle_deformation
    FEXX, w = 482.6, 8.0
    c_shape = [WeldSegment(0.0, -100.0, 0.0, 100.0, w), WeldSegment(0.0, 100.0, 100.0, 100.0, w),
               WeldSegment(0.0, -100.0, 100.0, -100.0, w)]
    Pn = WeldGroupICR(segments=c_shape, Pu_N=1.0, ex_mm=0.0, FEXX_MPa=FEXX).solve()["Pn_N"]
    w_in = w / 25.4
    du = lambda th: min(1.087 * w_in * (th + 6.0) ** -0.65, 0.17 * w_in) * 25.4
    d_crit = du(90.0)   # el transversal es el menos dúctil
    oracle = 200.0 * _weld_capacity_at_angle_deformation(0.0, d_crit, w, FEXX) + 200.0 * _weld_capacity_at_angle_deformation(90.0, d_crit, w, FEXX)
    assert Pn == pytest.approx(oracle, rel=1e-4)
    # AISC 360-22 §J2.4(b)(2): máx(Rnwl + Rnwt, 0,85·Rnwl + 1,5·Rnwt) con Rn sin aumento direccional
    rn = 0.60 * FEXX * w / math.sqrt(2.0) * 200.0
    assert Pn == pytest.approx(max(2 * rn, 0.85 * rn + 1.5 * rn), rel=0.02)
    # una sola orientación: cada cordón a su capacidad completa, como antes
    lines = [WeldSegment(-50.0, -100.0, -50.0, 100.0, w), WeldSegment(50.0, -100.0, 50.0, 100.0, w)]
    assert WeldGroupICR(segments=lines, Pu_N=1.0, ex_mm=0.0, FEXX_MPa=FEXX).solve()["Pn_N"] == pytest.approx(2 * rn, rel=1e-4)


def test_fillet_weld_ec3_accepts_quality_suffix():
    from steeljoints.welds import FilletWeld
    assert FilletWeld(8.0, 100.0, code="EC3", steel_grade="S355J2").ec3_strength(510.0) == pytest.approx(
        FilletWeld(8.0, 100.0, code="EC3", steel_grade="S355").ec3_strength(510.0))


def test_shear_tab_block_shear_tension_path_goes_to_the_free_edge():
    from steeljoints.shear_tab import ShearTab
    narrow = ShearTab(Vu=100.0, plate_width=75.0, edge_dist_h=38.0).plate_block_shear()
    wide = ShearTab(Vu=100.0, plate_width=115.0, edge_dist_h=38.0).plate_block_shear()
    assert wide["phi_Rn_N"] == pytest.approx(narrow["phi_Rn_N"])
    from steeljoints.block_shear import block_shear_strength
    dh, tp, h = 19.05 + 2.0, 9.5, 2 * 75.0 + 2 * 38.0
    Agv = (h - 38.0) * tp
    expected = block_shear_strength(Agv, Agv - 2.5 * dh * tp, (38.0 - dh / 2) * tp, 345.0, 450.0, Ubs=1.0, code="AISC")
    assert narrow["phi_Rn_N"] == pytest.approx(expected["phi_Rn_N"])


def test_as4100_block_shear_has_yield_cap_and_kbs():
    from steeljoints.block_shear_multi import BlockShearInput, block_shear
    inp = BlockShearInput(Agv_mm2=1500.0, Anv_mm2=1400.0, Ant_mm2=300.0, Fy_MPa=250.0, Fu_MPa=410.0, Ubs=0.5)
    au, us = block_shear(inp, "AU"), block_shear(inp, "US")
    assert au.Rd_kN == pytest.approx(us.Rd_kN)
    assert au.governing == "yield"          # 0,6·250·1500 < 0,6·410·1400
    assert au.Rn_kN == pytest.approx((0.6 * 250 * 1500 + 0.5 * 410 * 300) / 1e3)


def test_service_single_bolt_bearing_uses_edge_distance():
    from steeljoints.services.bolts import SingleBoltInput, design_single_bolt
    r = design_single_bolt(SingleBoltInput("A325", 19.05, plate_thickness_mm=10.0, plate_fu_MPa=400.0, edge_distance_mm=30.0))
    lc = 30.0 - (19.05 + 1.5875) / 2
    assert r.Rn_bearing_kN == pytest.approx(1.2 * lc * 10.0 * 400.0 / 1e3)
    assert r.governs == "bearing"
    far = design_single_bolt(SingleBoltInput("A325", 19.05, plate_thickness_mm=10.0, plate_fu_MPa=400.0, edge_distance_mm=60.0))
    assert far.Rn_bearing_kN == pytest.approx(2.4 * 19.05 * 10.0 * 400.0 / 1e3)
    ec3 = design_single_bolt(SingleBoltInput("8.8", 20.0, standard="EC3", plate_thickness_mm=10.0, plate_fu_MPa=400.0, edge_distance_mm=30.0))
    assert ec3.Rn_bearing_kN == pytest.approx(2.5 * (30.0 / 66.0) * 400.0 * 20.0 * 10.0 / 1e3)


def test_bridge_reports_connections_without_demand():
    from steeljoints.integration.seismodyn_bridge import BeamDynamicDemand, RBSConnectionDefinition, verify_connections_vs_demand
    from steeljoints._common.audit_status import CalculationStatus
    conns = [RBSConnectionDefinition(f"B{i}", beam_d=608.0, beam_bf=228.0, beam_tf=17.3, beam_Z_x=3_050_000.0,
                                     a=140.0, b=460.0, c=45.0, L_clear=6.0, wu=15.0) for i in range(3)]
    rep = verify_connections_vs_demand(conns, [BeamDynamicDemand("B0", 400.0, 80.0)])
    assert rep.n_total == 3 and rep.n_sin_veredicto == 2
    sin = [r for r in rep.rows if r.beam_id != "B0"]
    assert all(r.calculation_status is CalculationStatus.NO_CALCULADO and not r.is_safe for r in sin)
    assert all(r.M_demand_kNm is None for r in sin)


def test_bridge_short_beam_is_a_review_row_not_an_aborted_report():
    from steeljoints.integration.seismodyn_bridge import BeamDynamicDemand, RBSConnectionDefinition, verify_connections_vs_demand
    from steeljoints._common.audit_status import CalculationStatus
    ok = RBSConnectionDefinition("B0", beam_d=608.0, beam_bf=228.0, beam_tf=17.3, beam_Z_x=3_050_000.0, a=140.0, b=460.0, c=45.0, L_clear=6.0, wu=15.0)
    corta = RBSConnectionDefinition("B1", beam_d=608.0, beam_bf=228.0, beam_tf=17.3, beam_Z_x=3_050_000.0, a=140.0, b=460.0, c=45.0, L_clear=0.6, wu=15.0)
    rep = verify_connections_vs_demand([ok, corta], [BeamDynamicDemand("B0", 400.0, 80.0), BeamDynamicDemand("B1", 300.0, 80.0)])
    assert rep.n_total == 2 and rep.n_safe == 1
    fila = next(r for r in rep.rows if r.beam_id == "B1")
    assert fila.calculation_status is CalculationStatus.REQUIERE_REVISION and fila.M_pr_capacity_kNm is None


def test_wuf_scwb_uses_probable_moment_projected_to_column_axis():
    from steeljoints.services.wuf import WUFInput, design_wuf
    r = design_wuf(WUFInput(beam_d_mm=612.0, beam_bf_mm=229.0, beam_tf_mm=19.6, beam_tw_mm=11.9, beam_Zx_mm3=3.67e6,
                            beam_Fy_MPa=345.0, beam_Fu_MPa=450.0, beam_length_m=7.0, col_d_mm=400.0, col_bf_mm=400.0,
                            col_tf_mm=24.0, col_tw_mm=15.0, col_Zx_mm3=5.5e6, col_Fy_MPa=345.0,
                            Mu_demand_kNm=1000.0, Pu_col_kN=2000.0, Py_col_kN=7000.0))
    m_pb = r.M_pr_kNm + r.V_pr_kN * 0.2
    assert r.scwb_ratio == pytest.approx(5.5e6 * 345.0 / 1e6 * (1 - 2000.0 / 7000.0) / m_pb)


def test_rbs_memo_shear_matches_service_and_has_consistent_units():
    from steeljoints.memos.rbs_aisc358 import rbs_aisc358_memo
    from steeljoints.services.rbs import RBSInput, design_rbs
    g = dict(d=612.0, bf=229.0, tf=19.6, Zx=3.67e6, a=143.0, b=459.0, c=45.0)
    _, m = rbs_aisc358_memo(beam_d=g["d"], beam_bf=g["bf"], beam_tf=g["tf"], beam_Z_x=g["Zx"], a=g["a"], b=g["b"], c=g["c"], L_clear=7.0, wu=30.0)
    s = design_rbs(RBSInput(d_mm=g["d"], bf_mm=g["bf"], tf_mm=g["tf"], tw_mm=11.9, Zx_mm3=g["Zx"], Fy_MPa=345.0, Fu_MPa=450.0,
                            a_mm=g["a"], b_mm=g["b"], c_mm=g["c"], L_clear_m=7.0, wu_kN_per_m=30.0))
    assert m.Vp_kN == pytest.approx(s.V_pr_kN, rel=1e-6)
    assert m.M_f_kNm == pytest.approx(s.M_f_kNm, rel=1e-6)
    sh = (g["a"] + g["b"] / 2) / 1000
    assert m.Vp_kN == pytest.approx(2 * m.M_pr_kNm / (7.0 - 2 * sh) + 30.0 * 7.0 / 2, rel=1e-6)


def test_anchorage_bending_stress_scales_with_misalignment_angle():
    from math import pi, radians
    from steeljoints.ec3_tension_members import bending_stress_at_anchorage
    I = pi * 35.0 ** 4 / 64
    per_rad = bending_stress_at_anchorage(200e3, 35.0, 5000.0, 165000.0, I)
    half_deg = bending_stress_at_anchorage(200e3, 35.0, 5000.0, 165000.0, I, theta_rad=radians(0.5))
    assert half_deg == pytest.approx(per_rad * radians(0.5))
