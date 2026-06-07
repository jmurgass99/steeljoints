"""
tests/test_ec3_1_8_golden.py — Golden tests for the canonical EC3-1-8 pure
functions in ``steelconnectionjm.codes.ec3_1_8``.

Each test anchors a canonical function to the *published numbers* of a solved
master exam problem (WorkID + EN 1993-1-8 clause cited in the docstring). The
goldens are honest: they hard-code the value the ficha computed and feed the
ficha's inputs to the function — they do NOT re-derive the expected value with
the same formula inside the test.

The pure functions in ec3_1_8.py had no direct test coverage prior to this
file (test_steel_connections.py only exercises the OOP Bolt/FilletWeld
wrappers).

Note: W01467 and W01490 are *failing* connection designs in their fichas
(applied force > resistance). The pure functions only return the design
resistance Rd, so these goldens pin the Rd value, not the pass/fail verdict.
"""
import pytest

from steelconnectionjm.codes.ec3_1_8 import (
    bolt_shear_Rd,
    bolt_bearing_Rd,
    fillet_weld_Rd_directional,
    BETA_W,
)


# ---------------------------------------------------------------------------
# §3.6.1 Tabla 3.4 — Cortante de tornillo  Fv,Rd = αv·fub·A/γM2
# ---------------------------------------------------------------------------
class TestBoltShearGolden:

    def test_W01467_T20_grade_5_6_single_plane(self):
        """W01467 (Ex Connections 2, L100.10/S355, 2T20 gr.5.6) — EC3-1-8 §3.6.1.

        Ficha: Fv,Rd = αv·fub·A/γM2 = 0.6·500·314.16/1.25 = 75.4 kN
        (T20 gr.5.6 → fub=500 MPa, αv=0.6; A = π·10² = 314.16 mm² (zona lisa);
        γM2=1.25). Un plano de corte.
        """
        Fv_Rd = bolt_shear_Rd(A_mm2=314.16, fub_MPa=500.0, alpha_v=0.6)
        assert Fv_Rd / 1000.0 == pytest.approx(75.4, abs=0.1)

    def test_W01490_M22_grade_10_9_two_shear_planes(self):
        """W01490 (Exercise 17 Bolted connection, M22 gr.10.9) — EC3-1-8 §3.6.1.

        Ficha (diapo 9): Fv,Rd = (αv·fub·As·n)/γM2
        = (0.5·1000·303·2)/1.25 = 242.4 kN por tornillo (n=2 planos de corte).
        αv=0.5 para grado 10.9 con rosca en el plano de corte; As=303 mm².

        bolt_shear_Rd da la resistencia por plano; se multiplica por n=2
        explícitamente, reflejando el ·n de la ficha.
        """
        n_planes = 2
        Fv_Rd_per_plane = bolt_shear_Rd(A_mm2=303.0, fub_MPa=1000.0, alpha_v=0.5)
        assert Fv_Rd_per_plane / 1000.0 == pytest.approx(121.2, abs=0.1)
        assert n_planes * Fv_Rd_per_plane / 1000.0 == pytest.approx(242.4, abs=0.1)


# ---------------------------------------------------------------------------
# §3.6.1 Tabla 3.4 — Aplastamiento  Fb,Rd = k1·αb·fu·d·t/γM2
# ---------------------------------------------------------------------------
class TestBoltBearingGolden:

    def test_W01467_edge_bolt_bearing(self):
        """W01467 (Ex Connections 2) aplastamiento perno de borde — EC3-1-8 §3.6.1.

        Ficha: α = min(e1/(3·d0), p1/(3·d0)−1/4, fub/fu, 1) = min(50/66, …) = 0.76
               k1 = 2.5 (cap)
               Fb,Rd = 0.76·2.5·490·20·10/1.25 = 148.96 kN
        Datos: d=20 (vástago), d0=22 (agujero), t=10, fu=490 (S355),
               fub=500, e1=50, p1=100. e2 grande ⇒ k1 = 2.5.

        EC3 Tabla 3.4 usa d0 en αd y d en el área; se pasa d0_mm=22.
        """
        Fb_Rd = bolt_bearing_Rd(
            d_mm=20.0, t_mm=10.0, fu_plate_MPa=490.0, fub_MPa=500.0,
            e1=50.0, p1=100.0, e2=50.0, p2=100.0,
            direction_inner=False, d0_mm=22.0,
        )
        # Ficha redondea αd a 0.76 (148.96 kN); αd exacto = 50/66 = 0.7576
        # (148.48 kN). La tolerancia cubre el redondeo de la ficha.
        assert Fb_Rd / 1000.0 == pytest.approx(148.96, rel=0.005)

    def test_d0_defaults_to_shank_diameter_backward_compatible(self):
        """Sin d0_mm, αd usa d_mm (comportamiento previo intacto)."""
        with_default = bolt_bearing_Rd(
            d_mm=20.0, t_mm=10.0, fu_plate_MPa=490.0, fub_MPa=500.0,
            e1=50.0, p1=100.0, e2=50.0, p2=100.0, direction_inner=False,
        )
        explicit_d0_equals_d = bolt_bearing_Rd(
            d_mm=20.0, t_mm=10.0, fu_plate_MPa=490.0, fub_MPa=500.0,
            e1=50.0, p1=100.0, e2=50.0, p2=100.0, direction_inner=False,
            d0_mm=20.0,
        )
        assert with_default == pytest.approx(explicit_d0_equals_d)


# ---------------------------------------------------------------------------
# §4.5.3 — Soldadura de filete (método direccional) + βw Tabla 4.1
# ---------------------------------------------------------------------------
class TestFilletWeldDirectionalGolden:

    def test_W01464_HEB180_backplate_directional(self):
        """W01464 (Ex Connection 1, HEB180→chapa dorsal, S235JR) — EC3-1-8 §4.5.3.

        Ficha (cordones a=8, S235, fu=360, γM2=1.25, βw=0.80). Tensiones en el
        plano de garganta en la esquina más desfavorable:
          σ⊥ = 215.24 MPa, τ⊥ = 112.12 MPa, τ∥ = 31.25 MPa
        Comprobaciones:
          a) √(σ⊥²+3(τ⊥²+τ∥²)) = 294.91 MPa  ≤ fu/(βw·γM2) = 360.0 MPa  (VERIFICA)
          b) σ⊥ = 215.24 MPa                 ≤ 0.9·fu/γM2  = 259.2 MPa  (VERIFICA)
        """
        r = fillet_weld_Rd_directional(
            a_mm=8.0, L_mm=180.0, fu_MPa=360.0, steel_grade="S235",
            sigma_perp=215.24, tau_perp=112.12, tau_par=31.25,
        )
        # βw Tabla 4.1 §4.5.3.2(7) para S235
        assert r["beta_w"] == pytest.approx(0.80)
        # Lado izquierdo de la condición a) — número titular de la ficha
        assert r["von_mises_MPa"] == pytest.approx(294.91, abs=0.05)
        # Límites de las condiciones a) y b)
        assert r["limit_1_MPa"] == pytest.approx(360.0, abs=0.05)
        assert r["limit_2_MPa"] == pytest.approx(259.2, abs=0.05)
        # VERIFICA ⇒ utilización < 1; gobierna σ⊥/limit_2 = 215.24/259.2
        assert r["utilization"] == pytest.approx(0.830, abs=0.005)
        assert r["utilization"] < 1.0

    def test_beta_w_table_4_1_values(self):
        """βw EN 1993-1-8 Tabla 4.1 (§4.5.3.2(7)) — anclado a W01464/W01467."""
        assert BETA_W["S235"] == pytest.approx(0.80)
        assert BETA_W["S275"] == pytest.approx(0.85)
        assert BETA_W["S355"] == pytest.approx(0.90)
