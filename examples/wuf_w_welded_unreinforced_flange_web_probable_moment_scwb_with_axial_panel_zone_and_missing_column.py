"""Unión soldada WUF-W (AISC 358 cap. 8 y AISC 341 §E3) de una W610 × 125 a un pilar de 400 mm: momento probable, cortante en la rótula, compacidad para alta ductilidad, pilar fuerte–viga débil con el axil del pilar, zona de panel y soldaduras, y qué pasa si falta el pilar.

`services.wuf.design_wuf(WUFInput(...))` con veredicto canónico (CALCULADO_CUMPLE / CALCULADO_FALLA /
NO_CALCULADO); `wuf_w.design_wuf_w(WUFWInput(...))` es la versión simplificada anterior, sin zona de panel.

Ejecutar:  python examples/wuf_w_welded_unreinforced_flange_web_probable_moment_scwb_with_axial_panel_zone_and_missing_column.py
"""
from steeljoints.services.wuf import WUFInput, design_wuf
from steeljoints.wuf_w import WUFWInput, design_wuf_w

BEAM = dict(beam_d_mm=612.0, beam_bf_mm=229.0, beam_tf_mm=19.6, beam_tw_mm=11.9, beam_Zx_mm3=3.67e6, beam_Fy_MPa=345.0, beam_Fu_MPa=450.0, beam_length_m=7.0)


def main() -> None:
    print("Pilar de 400 × 400 (tf 24, tw 15, Zx 5,5e6 mm³, Fy 345), Mu = 1000 kN·m, Vu = 300 kN:")
    print(f"  {'Pu/Py':>5} {'Mpr':>6} {'Vpr':>5} {'compacta':>8} {'SCWB':>6} {'PZ DCR':>6} {'DCR':>6} {'estado':>16}")
    for pu in (0.0, 1000.0, 2000.0, 3500.0, 5000.0):
        r = design_wuf(WUFInput(**BEAM, col_d_mm=400.0, col_bf_mm=400.0, col_tf_mm=24.0, col_tw_mm=15.0, col_Zx_mm3=5.5e6, col_Fy_MPa=345.0,
                                Mu_demand_kNm=1000.0, Vu_demand_kN=300.0, Pu_col_kN=pu, Py_col_kN=7000.0))
        print(f"  {pu / 7000:5.2f} {r.M_pr_kNm:6.0f} {r.V_pr_kN:5.0f} {str(r.is_compact):>8} {r.scwb_ratio:6.2f} {r.pz_DCR:6.2f} {r.DCR:6.2f} {r.calculation_status.value:>16}")
    r = design_wuf(WUFInput(**BEAM, col_d_mm=400.0, col_bf_mm=400.0, col_tf_mm=24.0, col_tw_mm=15.0, col_Zx_mm3=5.5e6, col_Fy_MPa=345.0,
                            Mu_demand_kNm=1000.0, Pu_col_kN=2000.0, Py_col_kN=7000.0))
    print("\nNotas con Pu = 2000 kN:")
    for n in r.notes:
        print(f"  · {n}")
    mpr = 1.15 * 1.1 * 345 * 3.67e6 / 1e6
    print(f"  A mano: Mpr = 1,15·1,1·345·3,67e6 = {mpr:.0f} kN·m; M*pb = Mpr + Vpr·dc/2 = {mpr:.0f} + {r.V_pr_kN:.0f}·0,2 = {mpr + r.V_pr_kN * 0.2:.0f} kN·m; "
          f"SCWB = Zc·Fyc·(1 − Pu/Py)/M*pb = {5.5e6 * 345 * (1 - 2000 / 7000) / 1e6 / (mpr + r.V_pr_kN * 0.2):.2f} (un pilar y una viga; en un nudo interior con dos pilares y dos vigas el cociente es el mismo)")
    sin = design_wuf(WUFInput(**BEAM, Mu_demand_kNm=1000.0))
    print(f"\nSin pilar declarado: estado {sin.calculation_status.value}, scwb_ratio {sin.scwb_ratio}, faltan {getattr(sin, 'missing_inputs', None)}")
    old = design_wuf_w(WUFWInput(beam_Zx_mm3=3.67e6, beam_db_mm=612.0, beam_bf_mm=229.0, beam_tf_mm=19.6, beam_tw_mm=11.9,
                                 column_Zx_mm3=5.5e6, column_Pu_kN=2000.0, column_Ag_mm2=7000e3 / 345.0, column_dc_mm=400.0), beam_length_m=7.0)
    print(f"design_wuf_w (simplificado): Mpr {old.Mpr_kNm:.0f} kN·m, Vu {old.Vu_kN:.0f} kN, compacta {old.is_compact_per_AISC341}, SCWB {old.scwb_ratio:.2f}")
    print(f"\nCon este pilar fallan la zona de panel (DCR {r.pz_DCR:.2f}) y, en cuanto el axil pasa de cero, el pilar fuerte–viga débil. Hace falta chapa de refuerzo "
          "(ver el caso de zona de panel) y un pilar con más módulo plástico. Sin pilar, el servicio no inventa uno: el veredicto queda NO_CALCULADO. "
          "Hasta la versión 1.1 el servicio dividía por Zb·Fyb nominal y daba SCWB 1,07 (cumple) en este mismo nudo.")


if __name__ == "__main__":
    main()
