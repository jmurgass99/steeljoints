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

Errata handling (2026-08 campaign): several source fichas in this campaign
contain transcription/arithmetic errors (wrong digit, misapplied factor,
10x slips, etc). Per the "REGLA DE ORO" of this campaign, every golden below
is recomputed by hand from the ficha's *raw geometric/material inputs* using
the cited EC3-1-8 clause, transcribed independently of the ficha's printed
"result" line. Where the ficha's own printed number matches the hand
recomputation, the docstring says so and the golden anchors that number.
Where the ficha's printed number is wrong (W01413 bearing, W01457 T-stub),
the docstring records BOTH the ficha's (wrong) printed value and the
recomputed (correct) value that the golden actually anchors, and explains
the discrepancy — so the errata stays auditable without re-opening the
source ficha.
"""
import pytest

from steelconnectionjm.codes.ec3_1_8 import (
    bolt_shear_Rd,
    bolt_bearing_Rd,
    bolt_tension_Rd,
    fillet_weld_Rd_directional,
    fillet_weld_Rd_simplified,
    t_stub_FT_Rd,
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

    def test_W01412_M20_grade_8_8_threaded_plane(self):
        """W01412 (Unión atornillada y soldada v1, S235) — EC3-1-8 §3.6.1.

        Ficha: M20 gr.8.8, A_s=245 mm² (plano de corte en zona roscada),
        f_ub=800 MPa, γM2=1.25, un plano de corte:
          Fv,Rd = 0.6·800·245/1.25 = 94.08 kN

        Hand recompute matches the ficha's printed 94.1 kN exactly (no
        errata here). Adds coverage for grade 8.8 (αv=0.6), not covered by
        the W01467 (5.6) / W01490 (10.9) goldens above.
        """
        Fv_Rd = bolt_shear_Rd(A_mm2=245.0, fub_MPa=800.0, alpha_v=0.6)
        assert Fv_Rd / 1000.0 == pytest.approx(94.08, abs=0.05)


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

    def test_W01413_M22_grade_8_8_S355_edge_bolt_ERRATA(self):
        """W01413 (Unión atornillada, S355) aplastamiento perno de borde —
        EC3-1-8 §3.6.1, Tabla 3.4.

        ERRATA: the ficha prints F_b,Rd = 112.5 kN/tornillo for this bolt,
        but its own transcribed formula and inputs do NOT produce that
        number. Hand recompute from the ficha's raw inputs:
          d=22, d0=24 (M22, standard hole), t=12, fu=490 (S355), fub=800
          e1=40, e2=40 (e2 large enough that k1 caps at 2.5)
          alpha_d = e1/(3*d0) = 40/72 = 0.5556
          alpha_b = min(0.5556, fub/fu=1.633, 1.0) = 0.5556
          k1 = min(2.8*e2/d0-1.7, 2.5) = min(2.967, 2.5) = 2.5
          Fb,Rd = 2.5*0.5556*490*22*12/1.25 = 143.73 kN
        This 143.73 kN is what this golden anchors — NOT the ficha's
        printed 112.5 kN, which does not match its own stated formula/inputs
        (nor does the ficha's alternative F_v,Rd=141.4 kN check out — see
        report). Confirms the "6 fichas with erratas" warning for this
        campaign.
        """
        Fb_Rd = bolt_bearing_Rd(
            d_mm=22.0, t_mm=12.0, fu_plate_MPa=490.0, fub_MPa=800.0,
            e1=40.0, p1=60.0, e2=40.0, p2=60.0,
            direction_inner=False, d0_mm=24.0,
        )
        assert Fb_Rd / 1000.0 == pytest.approx(143.73, abs=0.05)


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


# ---------------------------------------------------------------------------
# §4.5.3.3 — Soldadura de filete (método simplificado)
# ---------------------------------------------------------------------------
class TestFilletWeldSimplifiedGolden:

    def test_W01412_alma_a8_L150_S235(self):
        """W01412 (Unión atornillada y soldada v1, S235) — EC3-1-8 §4.5.3.3.

        Ficha: cordón de alma a=8mm, L=150mm, S235 (fu=360 MPa), βw=0.80,
        γM2=1.25:
          fvw,d = fu/(√3·βw·γM2) = 360/(1.7320508·0.8·1.25) = 207.85 N/mm²
          Fw,Rd = fvw,d·a·L = 207.85·8·150 = 249.42 kN

        Hand recompute matches the ficha's printed fvw,d=207.8 N/mm² and
        Fw,Rd=249.4 kN exactly (no errata). fillet_weld_Rd_simplified had
        zero prior test coverage.
        """
        Fw_Rd = fillet_weld_Rd_simplified(
            a_mm=8.0, L_mm=150.0, fu_MPa=360.0, steel_grade="S235",
        )
        assert Fw_Rd / 1000.0 == pytest.approx(249.42, abs=0.05)


# ---------------------------------------------------------------------------
# §3.6.1 Tabla 3.4 — Tracción de tornillo  Ft,Rd = k2·fub·As/γM2
# ---------------------------------------------------------------------------
class TestBoltTensionGolden:

    def test_W01449_M20_grade_10_9(self):
        """W01449 (2n parcial exam, IPE270/HEB200 end-plate) — EC3-1-8 §3.6.1.

        Ficha: F_t,Rd = 0.9·f_ub·A_s/γM2 = 0.9·1000·245/1.25 = 176.4 kN
        (M20 gr.10.9, A_s=245 mm², k2=0.9 general, γM2=1.25).

        Hand recompute matches exactly (176400 N, no rounding needed).
        Independently cross-confirmed by W00235 (Tabla 58.7: "F_t,Rd =
        0.9×1000×245/1.25 = 176.4 kN ✓ (tabla confirma)"). bolt_tension_Rd
        had zero prior test coverage.
        """
        Ft_Rd = bolt_tension_Rd(As_mm2=245.0, fub_MPa=1000.0, k2=0.9)
        assert Ft_Rd == pytest.approx(176400.0, abs=1.0)
        assert Ft_Rd / 1000.0 == pytest.approx(176.4, abs=0.01)


# ---------------------------------------------------------------------------
# §6.2.4 Tabla 6.2 — T-stub equivalente (modos de falla 1/2/3)
# ---------------------------------------------------------------------------
class TestTStubGolden:

    def test_W01425_component4_column_flange_mode2_governs(self):
        """W01425 (Weynand & Jaspart, EC3-1-8 Joints textbook) — Componente 4:
        column flange in bending — EC3-1-8 §6.2.4 / §6.2.6.4.

        Ficha (worked textbook example, beam-to-column end-plate joint,
        row 1): l_eff=145.1mm, t_fc=12mm, f_y,fc=235 MPa, m=26.9mm, n=30mm.
        Bolts: M16 gr.8.8, A_s=157mm² → B_t,Rd = 0.9·800·157/1.25 = 90.43
        kN/bolt (independently recomputed via bolt_tension_Rd's formula);
        row of 2 bolts → ΣF_t,Rd = 180.86 kN.

        Hand recompute:
          Mpl,Rd = 0.25·145.1·12²·235 = 1,227,546 N·mm (= l_eff·m_pl with
                   book's m_pl,fc=t²·fy/4=8460 N·mm/mm — same formula,
                   different factoring; 145.1·8460=1,227,546 ✓ matches)
          Modo 1: F1 = 4·Mpl,Rd/m = 182.53 kN   (ficha: 182.5 kN)
          Modo 2: F2 = (2·Mpl,Rd+n·ΣFt,Rd)/(m+n) = 138.51 kN  ← GOBIERNA
                       (ficha: 138.5 kN ← GOVERNS)
          Modo 3: F3 = ΣFt,Rd = 180.86 kN        (ficha: 180.9 kN)
        Clean match, no errata. t_stub_FT_Rd had zero prior test coverage.
        """
        Bt_Rd = bolt_tension_Rd(As_mm2=157.0, fub_MPa=800.0, k2=0.9)
        sum_Ft_Rd = 2.0 * Bt_Rd
        assert Bt_Rd / 1000.0 == pytest.approx(90.43, abs=0.01)

        r = t_stub_FT_Rd(
            leff_mm=145.1, tp_mm=12.0, fy_plate_MPa=235.0,
            Ft_Rd_bolt_N=sum_Ft_Rd, n_mm=30.0, m_mm=26.9,
        )
        assert r["F1_Nmm"] / 1000.0 == pytest.approx(182.53, abs=0.1)
        assert r["F2_N"] / 1000.0 == pytest.approx(138.51, abs=0.1)
        assert r["F3_N"] / 1000.0 == pytest.approx(180.86, abs=0.1)
        assert r["FT_Rd_N"] / 1000.0 == pytest.approx(138.51, abs=0.1)
        assert r["governing_mode"] == "Modo 2"

    def test_W01425_component5_end_plate_mode2_governs(self):
        """W01425 (Weynand & Jaspart) — Componente 5: end plate in bending —
        EC3-1-8 §6.2.4 / §6.2.6.5. Same bolt row as Componente 4 above.

        Ficha: l_eff=185mm, t_p=15mm, f_y,p=235 MPa, m_p=33.66mm, n_p=30mm.

        Hand recompute:
          Mpl,Rd = 0.25·185·15²·235 = 2,445,468.75 N·mm
          Modo 1: F1 = 4·Mpl,Rd/m = 290.55 kN   (ficha: 291 kN — ficha
                       rounds m_pl,p to 13218 N·mm/mm before multiplying,
                       hence the ~0.2% drift; using rel tolerance here)
          Modo 2: F2 = (2·Mpl,Rd+n·ΣFt,Rd)/(m+n) = 162.07 kN  ← GOBIERNA
                       (ficha: 162.1 kN ← GOVERNS)
        No errata (rounding only). ΣFt,Rd = 180.86 kN, same M16 gr.8.8 row
        as Componente 4.
        """
        Bt_Rd = bolt_tension_Rd(As_mm2=157.0, fub_MPa=800.0, k2=0.9)
        sum_Ft_Rd = 2.0 * Bt_Rd

        r = t_stub_FT_Rd(
            leff_mm=185.0, tp_mm=15.0, fy_plate_MPa=235.0,
            Ft_Rd_bolt_N=sum_Ft_Rd, n_mm=30.0, m_mm=33.66,
        )
        assert r["F1_Nmm"] / 1000.0 == pytest.approx(290.55, rel=0.005)
        assert r["F2_N"] / 1000.0 == pytest.approx(162.07, abs=0.1)
        assert r["FT_Rd_N"] / 1000.0 == pytest.approx(162.07, abs=0.1)
        assert r["governing_mode"] == "Modo 2"

    def test_W01457_end_plate_T_stub_mode1_governs_ERRATA(self):
        """W01457 (Connections extra exercises) T-stub chapa frontal, M20
        cl.10.9 — EC3-1-8 §6.2.4.

        ERRATA: the ficha computes M_pl,Rd = 0.25·150·15²·275 and PRINTS
        "23.2 kN·m" — that is wrong by a factor of 10. The correct value
        from the ficha's own formula and inputs (l_eff=150mm, t_f=15mm,
        f_y=275 MPa, γM0=1.0) is:
          Mpl,Rd = 0.25·150·15²·275 = 2,320,312.5 N·mm = 2.32 kN·m  (not 23.2)
        Because the ficha carried the 10x-too-large Mpl,Rd forward, it
        concluded "F_T,1 = 4·23.2/0.040 = 2320 kN (irrealista) → modo 3
        governs" with F_T,Rd = 352.8 kN. With the CORRECT Mpl,Rd, Modo 1
        actually governs:
          F1 = 4·2,320,312.5/40 = 232.03 kN   ← GOBIERNA (not the ficha's
                                                 claimed Modo 3 / 352.8 kN)
          F2 = (2·2,320,312.5 + 45·352800)/(40+45) = 241.37 kN
          F3 = ΣFt,Rd = 2·176.4 = 352.8 kN    (this part of the ficha IS
                                                 correct — see W01449 golden)
        This golden anchors the CORRECT F_T,Rd=232.03 kN / Modo 1 — the
        opposite conclusion from the ficha's printed governing mode.
        """
        Ft_Rd_bolt = bolt_tension_Rd(As_mm2=245.0, fub_MPa=1000.0, k2=0.9)
        sum_Ft_Rd = 2.0 * Ft_Rd_bolt
        assert sum_Ft_Rd / 1000.0 == pytest.approx(352.8, abs=0.1)

        r = t_stub_FT_Rd(
            leff_mm=150.0, tp_mm=15.0, fy_plate_MPa=275.0,
            Ft_Rd_bolt_N=sum_Ft_Rd, n_mm=45.0, m_mm=40.0,
        )
        assert r["Mpl_Rd_Nmm"] == pytest.approx(2_320_312.5, rel=0.001)
        assert r["F1_Nmm"] / 1000.0 == pytest.approx(232.03, abs=0.1)
        assert r["F2_N"] / 1000.0 == pytest.approx(241.37, abs=0.1)
        assert r["F3_N"] / 1000.0 == pytest.approx(352.8, abs=0.1)
        assert r["FT_Rd_N"] / 1000.0 == pytest.approx(232.03, abs=0.1)
        assert r["governing_mode"] == "Modo 1"


# ---------------------------------------------------------------------------
# §3.10.2 — Desgarro de bloque (block tearing) — cross-check, NOT anchored
# ---------------------------------------------------------------------------
class TestBlockTearingCrossCheck:

    def test_W01457_block_tearing_EN1993_correct_value(self):
        """W01457 (Connections extra exercises) block tearing, página 2 —
        EC3-1-8 §3.10.2, Modo 1.

        BUG DE PRODUCCION corregido en `block_shear_multi._en1993_block`
        (independiente de cualquier errata de ficha): el codigo dividia el
        termino de cortante-fluencia por gamma_M2 junto con el de traccion-
        fractura, cuando EC3-1-8 divide el termino de cortante por gamma_M0
        (=1.0). Daba 428.58 kN en vez de 451.45 kN (~5% de menos, sub-reporta
        capacidad — del lado seguro, pero incorrecto). Verificado con dos
        fichas independientes (W01412, W01457).

        Ficha: 2 tornillos M20, e1=35mm, p1=70mm, b=120mm, t=10mm, S275
        (f_y=275, f_u=430 MPa), d0=22mm.
          A_nt = (b - 1·d0)·t = (120-22)·10 = 980 mm²
          A_nv = (e1 + p1 - 1.5·d0)·t = (35+70-33)·10 = 720 mm²
          V_eff,1,Rd = fu·Ant/γM2 + fy·Anv/(√3·γM0)
                     = 430·980/1.25 + 275·720/(1.7320508·1.0)
                     = 337.12 + 114.33 = 451.45 kN
        Hand recompute matches the ficha's printed 451 kN (rounding only,
        no errata in this ficha's own arithmetic). This test asserts the
        CORRECT 451.45 kN against block_shear_multi.block_shear(code="EU"),
        which is expected to currently FAIL (see xfail reason above) because
        that function's EN1993 path has a gamma_M0/gamma_M2 bug independent
        of any ficha errata.
        """
        from steelconnectionjm.block_shear_multi import BlockShearInput, block_shear

        inp = BlockShearInput(
            Agv_mm2=1050.0, Anv_mm2=720.0, Ant_mm2=980.0,
            Fy_MPa=275.0, Fu_MPa=430.0,
        )
        r = block_shear(inp, code="EU")
        assert r.Rd_kN == pytest.approx(451.45, abs=0.1)
