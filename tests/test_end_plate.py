"""
tests/test_end_plate.py — New tests covering the catalog + AISC 358 refactor
of `steeljoints.end_plate.EndPlate`.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from steeljoints.end_plate import EndPlate
from steeljoints import catalog
from steeljoints.codes import aisc358


# ---------------------------------------------------------------------------
# 1. Seismic 4E with Cpr/Mpr applied (AISC 358 §2.4.3 + §6)
# ---------------------------------------------------------------------------
def test_seismic_4E_applies_Mpr():
    """GOLDEN. En modo sísmico el momento de diseño es Mpr = Cpr·Ry·Fy·Zx.

    Fuente Normativa:
      - AISC 358-16: Prequalified Connections for Special and Intermediate Steel Moment Frames for Seismic Applications.
      - Chapter 2 §2.4.3: Probable Maximum Moment at Plastic Hinge: Mpr = Cpr·Ry·Fy·Zx.
      - Chapter 6 §6.8: Extended End-Plate Moment Connections.
    """
    Zx = 1.5e6   # mm³ (typical W18 beam)
    Fy, Fu = 345.0, 450.0
    ep_static = EndPlate(
        Mu=150.0, Vu=80.0, beam_depth=460.0,
        beam_tf=14.0, beam_bf=190.0,
        bolt_size="1", bolt_grade="A490",
        plate_thickness=25.0,
        n_bolt_rows=2,
        Zx=Zx, beam_Fy=Fy, beam_Fu=Fu, Ry=1.1,
        seismic=False,
    )
    ep_seismic = EndPlate(
        Mu=150.0, Vu=80.0, beam_depth=460.0,
        beam_tf=14.0, beam_bf=190.0,
        bolt_size="1", bolt_grade="A490",
        plate_thickness=25.0,
        n_bolt_rows=2,
        Zx=Zx, beam_Fy=Fy, beam_Fu=Fu, Ry=1.1,
        seismic=True,
    )
    Mpr_expected = aisc358.Mpr(Zx, Fy, Fu, 1.1)        # N·mm
    Cpr_expected = aisc358.Cpr(Fy, Fu)
    assert ep_seismic.Mpr_Nmm == pytest.approx(Mpr_expected, rel=1e-6)
    assert ep_seismic.Cpr_factor == pytest.approx(Cpr_expected, rel=1e-6)
    # Demand moment used internally must be Mpr (greater than the static Mu)
    assert ep_seismic.Mu_Nmm == pytest.approx(Mpr_expected, rel=1e-6)
    assert ep_seismic.Mu_Nmm > ep_static.Mu_Nmm
    # Higher demand → larger bolt-tension demand
    assert ep_seismic.bolt_tension_demand() > ep_static.bolt_tension_demand()
    rep = ep_seismic.design()
    assert rep["seismic"] is True
    assert "Cpr" in rep and "Mpr_kNm" in rep


# ---------------------------------------------------------------------------
# 2. Catalog resolution: A325 vs A490 at 1"Ø ⇒ different Pn
# ---------------------------------------------------------------------------
def test_catalog_A325_vs_A490_1in_diameter():
    common = dict(Mu=100.0, Vu=50.0, beam_depth=400.0,
                  beam_tf=13.0, beam_bf=180.0,
                  bolt_size="1", plate_thickness=22.0,
                  n_bolt_rows=2)
    ep325 = EndPlate(bolt_grade="A325", **common)
    ep490 = EndPlate(bolt_grade="A490", **common)

    # Tension capacity (kN) from each design report
    rt325 = ep325.bolt_tension_check()
    rt490 = ep490.bolt_tension_check()
    rs325 = ep325.bolt_shear_check()
    rs490 = ep490.bolt_shear_check()

    # Geometry identical → demand equal
    assert rt325["T_demand_kN"] == pytest.approx(rt490["T_demand_kN"])
    # Capacities must differ — A490 stronger in both tension and shear
    assert rt490["phi_Rnt_kN"] > rt325["phi_Rnt_kN"]
    assert rs490["phi_Rnv_kN"] > rs325["phi_Rnv_kN"]

    # Sanity: ratios consistent with catalog Fnt ratio (~779/620)
    expected_ratio = (catalog.AISC_BOLT_GRADES["A490"]["Fnt"]
                      / catalog.AISC_BOLT_GRADES["A325"]["Fnt"])
    got_ratio = rt490["phi_Rnt_kN"] / rt325["phi_Rnt_kN"]
    assert got_ratio == pytest.approx(expected_ratio, rel=0.02)


# ---------------------------------------------------------------------------
# 3. Electrode E70XX vs E80XX ⇒ different fillet-weld strength
# ---------------------------------------------------------------------------
def test_electrode_E70_vs_E80_weld_strength():
    common = dict(Mu=120.0, Vu=200.0, beam_depth=400.0,
                  beam_tf=13.0, beam_bf=180.0,
                  bolt_size="7/8", bolt_grade="A325",
                  plate_thickness=22.0, n_bolt_rows=2)
    ep70 = EndPlate(electrode="E70XX", **common)
    ep80 = EndPlate(electrode="E80XX", **common)

    w70 = ep70.weld_check()
    w80 = ep80.weld_check()

    # FEXX comes from the catalog
    assert w70["FEXX_MPa"] == pytest.approx(catalog.get_electrode_FEXX("E70XX"))
    assert w80["FEXX_MPa"] == pytest.approx(catalog.get_electrode_FEXX("E80XX"))

    # Higher FEXX → larger fillet-weld design capacity (flange CJP is set by
    # Fy and unchanged, so compare web capacity)
    assert w80["phi_Rn_web_kN"] > w70["phi_Rn_web_kN"]
    # Linear scaling expected (Rn = 0.60·FEXX·Aw·dir)
    ratio = w80["phi_Rn_web_kN"] / w70["phi_Rn_web_kN"]
    expected = (catalog.get_electrode_FEXX("E80XX")
                / catalog.get_electrode_FEXX("E70XX"))
    assert ratio == pytest.approx(expected, rel=0.01)


# ---------------------------------------------------------------------------
# Backward-compat smoke test — old call signature still works
# ---------------------------------------------------------------------------
def test_legacy_signature_still_works():
    ep = EndPlate(Mu=150.0, Vu=80.0, beam_depth=400.0,
                  beam_tf=13.5, beam_bf=180.0,
                  bolt_diameter=22.0, bolt_grade="A325",
                  plate_thickness=22.0, n_bolt_rows=2)
    rep = ep.design()
    assert "checks" in rep and len(rep["checks"]) == 4
    assert rep["seismic"] is False
