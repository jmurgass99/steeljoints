"""Zona de panel de un pilar de 400 mm (alma de 13 mm) con dos vigas de 600 mm: los cuatro casos de AISC 360-22 §J10.6 (deformación del panel considerada o no, axil por debajo o por encima del umbral), barrido del axil, chapa de refuerzo necesaria y la memoria de cálculo.

`panel_zone.PanelZone(Mu_left, Mu_right, Vu_col, Pr, Py, db, bf_b, tf_b, dc, tw_c, bcf, tcf, inelastic_action)` con
`.capacity()`, `.required_doubler()` y `.design()`; `panel_zone.shear_capacity` (API funcional) y
`memos.panel_zone.render_panel_zone_memo`.
Sin deformación del panel: Rn = 0,60·Fy·dc·tw si Pr ≤ 0,4·Pc, y ×(1,4 − Pr/Pc) por encima.
Con deformación del panel (acción inelástica): Rn = 0,60·Fy·dc·tw·(1 + 3·bcf·tcf²/(db·dc·tw)) si Pr ≤ 0,75·Pc,
y ×(1,9 − 1,2·Pr/Pc) por encima.

Ejecutar:  python examples/panel_zone_aisc_j10_6_four_cases_axial_sweep_doubler_plate_and_memo.py
"""
from steeljoints.memos.panel_zone import PanelZoneInput, render_panel_zone_memo
from steeljoints.panel_zone import PanelZone

BASE = dict(Mu_left_kNm=600.0, Mu_right_kNm=500.0, Vu_col_kN=150.0, Py_kN=7000.0, db_mm=600.0, bf_b_mm=228.0, tf_b_mm=17.3,
            dc_mm=400.0, tw_c_mm=13.0, bcf_mm=400.0, tcf_mm=24.0)


def main() -> None:
    pz = PanelZone(Pr_kN=0.0, **BASE)
    print(f"Demanda del panel: ΣMu/(db − tf) − Vc = {pz.panel_demand_kN():.0f} kN (vigas de 600 y 500 kN·m)\n")
    print(f"  {'Pr/Pc':>5} {'φRn sin deform. [kN]':>20} {'φRn con deform. [kN]':>20}")
    for ratio in (0.0, 0.2, 0.4, 0.5, 0.6, 0.75, 0.85, 1.0):
        a = PanelZone(Pr_kN=ratio * 7000.0, inelastic_action=False, **BASE).capacity()
        b = PanelZone(Pr_kN=ratio * 7000.0, inelastic_action=True, **BASE).capacity()
        print(f"  {ratio:5.2f} {a['phi_Rn_kN']:20.1f} {b['phi_Rn_kN']:20.1f}")
    rn0 = 0.9 * 0.60 * 345.0 * 400.0 * 13.0 / 1e3
    bonus = 1 + 3 * 400.0 * 24.0 ** 2 / (600.0 * 400.0 * 13.0)
    print(f"\nA mano, Pr = 0: φ·0,6·Fy·dc·tw = {rn0:.1f} kN; con deformación ×(1 + 3·bcf·tcf²/(db·dc·tw)) = ×{bonus:.3f} = {rn0 * bonus:.1f} kN")
    print("\nChapa de refuerzo con Pr = 0,3·Pc, sin considerar la deformación del panel:")
    d = PanelZone(Pr_kN=2100.0, **BASE).design()
    dbl = d.get("doubler_plate", {})
    print(f"  utilización sin refuerzo {d['utilization']:.2f}; refuerzo {dbl.get('t_doubler_governing_mm', float('nan')):.1f} mm "
          f"(resistencia {dbl.get('t_doubler_mm', float('nan')):.1f} mm, estabilidad {dbl.get('t_doubler_min_stability_mm', float('nan')):.1f} mm) → φRn {dbl.get('phi_Rn_with_doubler_kN', float('nan')):.0f} kN")
    m = render_panel_zone_memo(PanelZoneInput(M_f1_kNm=600.0, M_f2_kNm=500.0, d_beam_mm=600.0, d_column_mm=400.0, t_web_column_mm=13.0,
                                              b_flange_column_mm=400.0, t_flange_column_mm=24.0, V_column_kN=150.0))
    print(f"\nMemoria: ecuación {m.equation}, demanda {m.V_demand_kN:.0f} kN, φRn {m.phi_Rn_kN:.0f} kN, DCR {m.DCR:.2f}, refuerzo {'sí' if m.needs_doubler else 'no'}; {len(m.markdown)} caracteres de Markdown.")
    print(f"La memoria usa V = 0,8·(Mf1 + Mf2)/d_b − Vc, con un coeficiente 0,8 que su propio texto declara sin trazar a norma y el canto d_b como brazo: "
          f"su demanda ({m.V_demand_kN:.0f} kN) queda un {(1 - m.V_demand_kN / pz.panel_demand_kN()) * 100:.0f} % por debajo de la de la clase ({pz.panel_demand_kN():.0f} kN, ΣMu/(db − tf) − Vc). "
          "Para verificar usa la clase PanelZone. "
          "Considerar la deformación del panel aumenta la capacidad y retrasa la reducción por axil (umbral 0,75·Pc en vez de 0,4·Pc), pero exige que el análisis la incluya.")


if __name__ == "__main__":
    main()
