"""
example_aisc_manual_part10.py — Ejemplos basados en AISC Manual Part 10.

1. ShearTab — Example II.A-1 (conexión simple de cortante)
2. BoltGroupICR — bolt group excéntrico (verificación contra Table 7-7 AISC)
3. WeldGroupICR — weld group con momento (verificación contra Table 8-4)
4. ClipAngle — doble ángulo a cortante
5. PanelZone — verificación con doubler plate
"""
from steelconnectionjm import (
    ShearTab, ClipAngle, PanelZone,
    BoltGroupICR, WeldSegment, WeldGroupElastic, WeldGroupICR,
    rectangular_pattern, catalog,
)


def main() -> None:
    print("=" * 70)
    print("Ejemplos SteelConnectionJm — AISC Manual Part 10")
    print("=" * 70)

    # --------------------------------------------------------------
    # 1. Shear tab
    # --------------------------------------------------------------
    print("\n[1] Shear tab — 3 pernos Ø3/4 A325, placa 9.5x75 mm")
    tab = ShearTab(Vu=120.0, bolt_diameter=19.05, bolt_grade="A325",
                   n_bolts=3, plate_thickness=9.5, plate_width=100.0)
    r = tab.design()
    print(f"  Vu = {r['Vu_kN']} kN — Governing: {r['governing_check']} "
          f"(util={r['governing_utilization']}) — OK={r['all_checks_ok']}")

    # --------------------------------------------------------------
    # 2. Bolt group ICR (excéntrico)
    # --------------------------------------------------------------
    print("\n[2] Bolt group ICR — 6 pernos (2x3), e=200 mm, vertical load")
    positions = rectangular_pattern(nx=2, ny=3, sx=75.0, sy=75.0)
    # Capacidad de un perno Ø3/4 A325-N en corte simple
    bolt = catalog.get_bolt_size("3/4")
    grade = catalog.get_bolt_grade("A325", "AISC")
    Rult = grade["Fnv_N"] * bolt["Ab_mm2"]   # N — corte simple, sin φ
    g = BoltGroupICR(positions=positions, Pu_N=200_000.0,
                     ex_mm=200.0, load_angle_deg=0.0, Rult_N=Rult)
    res = g.solve()
    print(f"  Pn = {res['Pn_kN']} kN, C = {res['C_coefficient']}, "
          f"IC=({res['IC_x_mm']},{res['IC_y_mm']}) — OK={res['is_ok']}")

    # --------------------------------------------------------------
    # 3. Weld group elastic + ICR
    # --------------------------------------------------------------
    print("\n[3] Weld group — L=300mm, 2 cordones laterales, e=150")
    segs = [
        WeldSegment(0.0,   0.0, 0.0,   300.0, w_mm=6.35),
        WeldSegment(100.0, 0.0, 100.0, 300.0, w_mm=6.35),
    ]
    we = WeldGroupElastic(segments=segs, Vx=0, Vy=-150_000.0,
                          load_point=(250.0, 150.0))
    out_e = we.utilization(FEXX_MPa=482.6, w_mm=6.35)
    print(f"  Elástico: f_max={out_e['f_max_N_per_mm']} N/mm — util={out_e['utilization']}")
    wi = WeldGroupICR(segments=segs, Pu_N=150_000.0, ex_mm=150.0,
                      load_angle_deg=0.0, FEXX_MPa=482.6, n_subdiv=20)
    out_i = wi.solve()
    print(f"  ICR: Pn={out_i['Pn_kN']} kN, IC=({out_i['IC_x_mm']},{out_i['IC_y_mm']})"
          f" — OK={out_i['is_ok']}")

    # --------------------------------------------------------------
    # 4. Clip angle (doble L)
    # --------------------------------------------------------------
    print("\n[4] Clip angle — 3 pernos Ø3/4, L100x9.5")
    clip = ClipAngle(Vu=140.0, n_bolts=3, bolt_diameter=19.05,
                     angle_thickness=9.5, angle_leg=100.0, beam_tw=8.0)
    cr = clip.design()
    print(f"  Governing: {cr['governing_check']} (util={cr['governing_utilization']})"
          f" — OK={cr['all_checks_ok']}")

    # --------------------------------------------------------------
    # 5. Panel zone con doubler
    # --------------------------------------------------------------
    print("\n[5] Panel zone W14x90 col + W24x76 beam, Mu=500 kN·m c/lado")
    pz = PanelZone(Mu_left_kNm=500.0, Mu_right_kNm=500.0, Vu_col_kN=50.0,
                   Pr_kN=600.0, Py_kN=4500.0,
                   db_mm=608.0, bf_b_mm=228.0, tf_b_mm=17.3,
                   dc_mm=356.0, tw_c_mm=11.2, bcf_mm=369.0, tcf_mm=18.0,
                   Fy_col_MPa=345.0, inelastic_action=False)
    pr = pz.design()
    print(f"  Vu_panel={pr['Vu_panel_kN']} kN, phiRn={pr['phi_Rn_kN']} kN, "
          f"util={pr['utilization']} — OK={pr['is_ok']}")
    if not pr["is_ok"]:
        dp = pr["doubler_plate"]
        print(f"  -> Doubler: t={dp['t_doubler_mm']} mm (gobierna "
              f"{dp['t_doubler_governing_mm']} mm con estabilidad)")


if __name__ == "__main__":
    main()
