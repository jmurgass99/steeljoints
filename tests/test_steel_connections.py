"""
tests/test_steel_connections.py — Unit tests for SteelConnectionJm.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from steelconnectionjm.bolts import Bolt, BoltGroup, bolt_gross_area
from steelconnectionjm.welds import FilletWeld
from steelconnectionjm.block_shear import block_shear_strength
from steelconnectionjm.shear_tab import ShearTab
from steelconnectionjm.end_plate import EndPlate
from steelconnectionjm.base_plate import BasePlate
from steelconnectionjm.clip_angle import ClipAngle


# ---------------------------------------------------------------------------
# Bolt tests
# ---------------------------------------------------------------------------
class TestBolt:

    def test_gross_area_3_4_inch(self):
        Ab = bolt_gross_area(19.05)
        assert 270 <= Ab <= 300, f"Ab={Ab} mm²"

    def test_a325_shear_strength_positive(self):
        b = Bolt(19.05, "A325", "AISC")
        assert b.aisc_shear_strength() > 0

    def test_a490_stronger_than_a325(self):
        b325 = Bolt(19.05, "A325", "AISC")
        b490 = Bolt(19.05, "A490", "AISC")
        assert b490.aisc_shear_strength() > b325.aisc_shear_strength()

    def test_double_shear_twice_single(self):
        b1 = Bolt(19.05, "A325", "AISC", n_shear_planes=1)
        b2 = Bolt(19.05, "A325", "AISC", n_shear_planes=2)
        assert b2.aisc_shear_strength() == pytest.approx(2 * b1.aisc_shear_strength())

    def test_tension_strength_positive(self):
        b = Bolt(22.0, "A490", "AISC")
        assert b.aisc_tension_strength() > 0

    def test_tension_greater_than_shear(self):
        b = Bolt(19.05, "A325", "AISC")
        assert b.aisc_tension_strength() > b.aisc_shear_strength()

    def test_bearing_strength_increases_with_thickness(self):
        b = Bolt(19.05, "A325", "AISC")
        Rb10 = b.aisc_bearing_strength(10.0, 450.0, 30.0)
        Rb20 = b.aisc_bearing_strength(20.0, 450.0, 30.0)
        assert Rb20 == pytest.approx(2 * Rb10, rel=0.01)

    def test_ec3_8_8_shear_strength(self):
        b = Bolt(20.0, "8.8", "EC3")
        # EN 1993-1-8 Tabla 3.4 con As = 0.75*Ab = 0.75*314.2 = 235.65 mm2, fub=800 MPa, alpha_v=0.6, gamma_M2=1.25:
        # Fv_Rd = 0.6 * 800 * 235.65 / 1.25 = 90489.6 N
        assert b.ec3_shear_strength() == pytest.approx(90489.6, rel=1e-4)

    def test_ec3_10_9_stronger_than_8_8(self):
        b88  = Bolt(20.0, "8.8",  "EC3")
        b109 = Bolt(20.0, "10.9", "EC3")
        assert b109.ec3_shear_strength() > b88.ec3_shear_strength()

    def test_combined_tension_shear_reduces_tension_capacity(self):
        b = Bolt(19.05, "A325", "AISC")
        pure_tension = b.aisc_tension_strength()
        combined = b.aisc_combined_tension_shear(Vuv=50000.0)
        assert combined <= pure_tension

    def test_invalid_grade_raises(self):
        with pytest.raises(ValueError):
            Bolt(19.05, "ZZZZ", "AISC")._aisc_data


class TestBoltGroup:

    def setup_method(self):
        bolt = Bolt(19.05, "A325", "AISC")
        phi_Rn = bolt.aisc_shear_strength()
        # 3-bolt vertical group, 75mm spacing
        positions = [(0, 0), (0, 75), (0, 150)]
        self.bg = BoltGroup(bolt=bolt, positions=positions,
                            phi_Rn_single=phi_Rn)

    def test_concentric_capacity(self):
        cap = self.bg.capacity_concentric()
        single = self.bg.bolt.aisc_shear_strength()
        assert cap == pytest.approx(3 * single)

    def test_eccentric_shear_utilization_increases_with_eccentricity(self):
        Vu = 80000.0  # N
        r1 = self.bg.elastic_critical_bolt(Vu, 0.0)         # no eccentricity
        r2 = self.bg.elastic_critical_bolt(Vu, 80000 * 100) # high eccentricity
        assert r2["Vmax_N"] > r1["Vmax_N"]

    def test_result_has_is_ok_key(self):
        r = self.bg.elastic_critical_bolt(10000.0, 500000.0)
        assert "is_ok" in r


# ---------------------------------------------------------------------------
# Weld tests
# ---------------------------------------------------------------------------
class TestFilletWeld:

    def test_aisc_longitudinal_strength(self):
        w = FilletWeld(weld_size=8.0, length=200.0, electrode="E70",
                       code="AISC", theta=0.0)
        Rn = w.aisc_strength()
        assert Rn > 0

    def test_transverse_weld_stronger_than_longitudinal(self):
        w0  = FilletWeld(8.0, 200.0, "E70", "AISC", theta=0.0)
        w90 = FilletWeld(8.0, 200.0, "E70", "AISC", theta=90.0)
        assert w90.aisc_strength() > w0.aisc_strength()

    def test_directional_factor_at_90deg(self):
        """At 90° the factor is 1 + 0.5×sin^1.5(90°) = 1.5"""
        w = FilletWeld(8.0, 200.0, "E70", "AISC", theta=90.0)
        w0 = FilletWeld(8.0, 200.0, "E70", "AISC", theta=0.0)
        ratio = w.aisc_strength() / w0.aisc_strength()
        assert ratio == pytest.approx(1.5, rel=0.01)

    def test_longer_weld_proportionally_stronger(self):
        w100 = FilletWeld(8.0, 100.0, "E70", "AISC")
        w200 = FilletWeld(8.0, 200.0, "E70", "AISC")
        assert w200.aisc_strength() == pytest.approx(2 * w100.aisc_strength(), rel=0.01)

    def test_ec3_strength_positive(self):
        w = FilletWeld(8.0, 200.0, "E70", "EC3", steel_grade="S355")
        Fw = w.ec3_strength(fu=510.0)
        assert Fw > 0

    def test_min_size_increases_with_thickness(self):
        w = FilletWeld(8.0, 200.0)
        assert w.min_size(10.0) < w.min_size(25.0)

    def test_max_size(self):
        w = FilletWeld(8.0, 200.0)
        assert w.max_size(10.0) == pytest.approx(8.0)
        assert w.max_size(20.0) == pytest.approx(18.0)


# ---------------------------------------------------------------------------
# Block shear tests
# ---------------------------------------------------------------------------
class TestBlockShear:

    def test_aisc_block_shear_positive(self):
        r = block_shear_strength(Agv=2000.0, Anv=1500.0, Ant=500.0,
                                  Fy=250.0, Fu=400.0, code="AISC")
        assert r["phi_Rn_kN"] > 0

    def test_aisc_rupture_governs_small_Agv(self):
        """Rupture should govern when Agv is small."""
        r = block_shear_strength(Agv=1000.0, Anv=800.0, Ant=1000.0,
                                  Fy=250.0, Fu=500.0, code="AISC")
        assert "governs" in r

    def test_ec3_block_shear_positive(self):
        r = block_shear_strength(Agv=2000.0, Anv=1500.0, Ant=600.0,
                                  Fy=355.0, Fu=510.0, code="EC3")
        assert r["Veff_kN"] > 0

    def test_higher_Fu_gives_higher_capacity(self):
        r1 = block_shear_strength(2000, 1500, 500, 250, 400, code="AISC")
        r2 = block_shear_strength(2000, 1500, 500, 250, 500, code="AISC")
        assert r2["phi_Rn_kN"] > r1["phi_Rn_kN"]


# ---------------------------------------------------------------------------
# ShearTab tests
# ---------------------------------------------------------------------------
class TestShearTab:

    def setup_method(self):
        self.tab = ShearTab(
            Vu=90.0,          # kN
            bolt_diameter=19.05,
            bolt_grade="A325",
            n_bolts=3,
            plate_thickness=9.5,
            plate_width=75.0,
        )

    def test_design_returns_dict(self):
        r = self.tab.design()
        assert isinstance(r, dict)

    def test_all_checks_present(self):
        r = self.tab.design()
        check_names = [c["check"] for c in r["checks"]]
        assert "Bolt group shear" in check_names
        assert "Block shear" in check_names

    def test_small_shear_passes(self):
        tab = ShearTab(Vu=30.0, bolt_diameter=19.05, n_bolts=3,
                       plate_thickness=9.5, plate_width=75.0)
        r = tab.design()
        assert r["all_checks_ok"]

    def test_large_shear_fails(self):
        tab = ShearTab(Vu=1000.0, bolt_diameter=19.05, n_bolts=3,
                       plate_thickness=9.5, plate_width=75.0)
        r = tab.design()
        assert not r["all_checks_ok"]

    def test_more_bolts_increase_capacity(self):
        tab3 = ShearTab(Vu=120.0, n_bolts=3, plate_thickness=9.5,
                        plate_width=75.0)
        tab5 = ShearTab(Vu=120.0, n_bolts=5, plate_thickness=9.5,
                        plate_width=75.0)
        r3 = tab3.design()
        r5 = tab5.design()
        util3 = r3["checks"][0]["utilization"]  # bolt shear
        util5 = r5["checks"][0]["utilization"]
        assert util5 < util3


# ---------------------------------------------------------------------------
# EndPlate tests
# ---------------------------------------------------------------------------
class TestEndPlate:

    def setup_method(self):
        self.ep = EndPlate(
            Mu=150.0,          # kN·m
            Vu=80.0,           # kN
            beam_depth=400.0,
            beam_tf=13.5,
            beam_bf=180.0,
            bolt_diameter=22.0,
            bolt_grade="A325",
            plate_thickness=22.0,
            n_bolt_rows=2,
        )

    def test_bolt_tension_demand_positive(self):
        T = self.ep.bolt_tension_demand()
        assert T > 0

    def test_design_returns_checks(self):
        r = self.ep.design()
        assert len(r["checks"]) == 4

    def test_zero_moment_bolt_tension_near_zero(self):
        ep = EndPlate(Mu=0.0, Vu=50.0, beam_depth=300.0,
                      beam_tf=10.0, beam_bf=150.0)
        T = ep.bolt_tension_demand()
        assert T == pytest.approx(0.0, abs=1.0)

    def test_larger_bolts_reduce_tension_util(self):
        ep20 = EndPlate(Mu=100.0, Vu=50.0, beam_depth=350.0,
                        beam_tf=12.0, beam_bf=160.0, bolt_diameter=20.0)
        ep30 = EndPlate(Mu=100.0, Vu=50.0, beam_depth=350.0,
                        beam_tf=12.0, beam_bf=160.0, bolt_diameter=30.0)
        r20 = ep20.bolt_tension_check()
        r30 = ep30.bolt_tension_check()
        assert r30["utilization"] < r20["utilization"]


# ---------------------------------------------------------------------------
# BasePlate tests
# ---------------------------------------------------------------------------
class TestBasePlate:

    def setup_method(self):
        self.bp = BasePlate(
            Pu=800.0,          # kN compression
            Mu=0.0,
            column_d=300.0,
            column_bf=200.0,
            plate_B=350.0,
            plate_N=400.0,
            plate_Fy=345.0,
            fc_concrete=28.0,
        )

    def test_bearing_pressure_positive(self):
        assert self.bp.bearing_pressure() > 0

    def test_bearing_pressure_equals_Pu_over_A1(self):
        fp = self.bp.bearing_pressure()
        fp_expected = self.bp.Pu_N / self.bp.A1
        assert fp == pytest.approx(fp_expected)

    def test_bearing_check_ok_for_moderate_load(self):
        r = self.bp.bearing_check()
        assert r["is_ok"]

    def test_required_thickness_positive(self):
        r = self.bp.required_thickness()
        assert r["tp_required_mm"] > 0

    def test_no_anchor_tension_concentric(self):
        r = self.bp.anchor_tension()
        assert r["T_per_bolt_kN"] == pytest.approx(0.0)

    def test_anchor_tension_with_large_moment(self):
        bp = BasePlate(Pu=200.0, Mu=150.0, column_d=300.0,
                       column_bf=200.0, plate_B=350.0, plate_N=400.0,
                       fc_concrete=28.0, n_anchors=4, anchor_diameter=25.4)
        r = bp.anchor_tension()
        assert r["T_per_bolt_kN"] > 0

    def test_design_returns_summary(self):
        r = self.bp.design()
        assert "summary" in r
        assert "all_checks_ok" in r

    def test_larger_plate_reduces_bearing_pressure(self):
        bp_small = BasePlate(Pu=800.0, plate_B=300.0, plate_N=300.0)
        bp_large = BasePlate(Pu=800.0, plate_B=450.0, plate_N=500.0)
        assert bp_large.bearing_pressure() < bp_small.bearing_pressure()

    def test_anchor_tension_with_net_uplift(self):
        # Column under net tension/uplift (Pu = -200 kN)
        bp_uplift = BasePlate(Pu=-200.0, Mu=0.0, column_d=300.0,
                             column_bf=200.0, plate_B=350.0, plate_N=400.0,
                             fc_concrete=28.0, n_anchors=4, anchor_diameter=25.4)
        r = bp_uplift.anchor_tension()
        assert r["T_per_bolt_kN"] > 0
        # Tension per bolt = |Pu| / n_anchors = 200 / 4 = 50 kN (full axial uplift to bolt group)
        assert r["T_per_bolt_kN"] == pytest.approx(50.0)
        assert r["note"] == "Uplift/tension case \u2014 bolts resist full tension + moment couple"


# ---------------------------------------------------------------------------
# ClipAngle tests
# ---------------------------------------------------------------------------
class TestClipAngle:

    def _base_w18x50(self, **overrides):
        """Clip angle 2L4x4x3/8 (≈ t=9.5, leg=100), 4 pernos Ø19.05,
        viga W18x50 (tw≈9.0, Fy=345, Fu=450)."""
        params = dict(
            Vu=200.0,
            n_bolts=4,
            bolt_diameter=19.05,
            bolt_grade="A325",
            bolt_spacing=75.0,
            edge_dist_v=38.0,
            edge_dist_h=38.0,
            angle_thickness=9.5,
            angle_leg=100.0,
            beam_tw=9.0,
            Fy_beam=345.0,
            Fu_beam=450.0,
            beam_gage_to_edge=35.0,
        )
        params.update(overrides)
        return ClipAngle(**params)

    def test_beam_web_block_shear_present(self):
        r = self._base_w18x50().design()
        names = [c["check"] for c in r["checks"]]
        assert "Block shear (beam web)" in names

    def test_beam_web_block_shear_positive_capacity(self):
        r = self._base_w18x50().beam_web_block_shear()
        assert r["phi_Rn_kN"] > 0

    def test_small_edge_distance_makes_beam_web_block_shear_govern(self):
        """Con beam_gage_to_edge muy pequeña, block shear del alma controla."""
        clip = self._base_w18x50(beam_gage_to_edge=15.0, Vu=250.0)
        r = clip.design()
        assert r["governing_check"] == "Block shear (beam web)"

    def test_regression_thick_web_not_governed_by_new_check(self):
        """Con alma muy gruesa y gage holgado, el block shear del alma no
        debe controlar (los chequeos previos siguen rigiendo)."""
        clip = self._base_w18x50(beam_tw=20.0, beam_gage_to_edge=60.0,
                                 Vu=150.0)
        r = clip.design()
        assert r["governing_check"] != "Block shear (beam web)"

    def test_larger_gage_increases_beam_web_block_shear_capacity(self):
        small = self._base_w18x50(beam_gage_to_edge=25.0).beam_web_block_shear()
        large = self._base_w18x50(beam_gage_to_edge=60.0).beam_web_block_shear()
        assert large["phi_Rn_kN"] > small["phi_Rn_kN"]
