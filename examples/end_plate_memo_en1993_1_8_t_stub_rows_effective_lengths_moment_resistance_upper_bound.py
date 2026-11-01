"""Memoria de chapa frontal extendida según EN 1993-1-8 §6.2.7.2: resistencia a flexión Mj = Σ h_r·Ft,r del T-stub de cada fila de tornillos (modos 1, 2 y 3), con las longitudes eficaces de la Tabla 6.6 calculadas a partir de la geometría.

`memos.end_plate.render_end_plate_memo(EndPlateInput(M_demand_kNm, bolt_diameter_mm, bolt_grade_Fu_MPa,
plate_thickness_mm, plate_Fy_MPa, plate_width_mm, bolt_rows=(BoltRow(h, leff, m, n), ...)))`. El resultado
es una COTA SUPERIOR: solo cuenta el T-stub de la chapa, no el ala ni el alma del pilar.

Ejecutar:  python examples/end_plate_memo_en1993_1_8_t_stub_rows_effective_lengths_moment_resistance_upper_bound.py
"""
from math import pi, sqrt

from steeljoints.memos.end_plate import BoltRow, EndPlateInput, render_end_plate_memo


def main() -> None:
    # IPE 450 con chapa de 250 × 20 mm extendida 90 mm, tornillos M20, gramil w = 100 mm
    h, tf, tw, bp, w, ext, a_f, a_w = 450.0, 14.6, 9.4, 250.0, 100.0, 90.0, 8.0, 6.0
    e = (bp - w) / 2
    # Fila 1, en la extensión a 45 mm del ala (Tabla 6.6, fila fuera del ala traccionada)
    mx = 45.0 - 0.8 * a_f * sqrt(2)
    ex = ext - 45.0
    nx = min(ex, 1.25 * mx)
    cands1 = {"2π·mx": 2 * pi * mx, "π·mx + w": pi * mx + w, "π·mx + 2e": pi * mx + 2 * e, "4mx + 1,25ex": 4 * mx + 1.25 * ex,
              "e + 2mx + 0,625ex": e + 2 * mx + 0.625 * ex, "0,5·bp": 0.5 * bp, "0,5w + 2mx + 0,625ex": 0.5 * w + 2 * mx + 0.625 * ex}
    leff1 = min(cands1.values())
    # Fila 2, bajo el ala a 50 mm (fila adyacente al ala): leff,cp = 2πm; leff,nc = α·m con α ≥ 4,45 (Fig. 6.11)
    m = (w - tw) / 2 - 0.8 * a_w * sqrt(2)
    n = min(e, 1.25 * m)
    leff2 = min(2 * pi * m, 4.45 * m)
    h1 = h - tf / 2 + 45.0
    h2 = h - tf - 50.0 - tf / 2
    print(f"Fila 1 (extensión): mx = {mx:.1f}, nx = {nx:.1f} mm; leff = mín de la Tabla 6.6 = {leff1:.1f} mm ({min(cands1, key=cands1.get)}); brazo {h1:.1f} mm")
    print(f"Fila 2 (bajo el ala): m = {m:.1f}, n = {n:.1f} mm; leff = mín(2πm, 4,45·m) = {leff2:.1f} mm (α = 4,45 es la cota inferior de la Fig. 6.11); brazo {h2:.1f} mm\n")
    rows = (BoltRow(h_mm=h1, leff_mm=leff1, m_mm=mx, n_mm=nx), BoltRow(h_mm=h2, leff_mm=leff2, m_mm=m, n_mm=n))
    print(f"  {'tp [mm]':>7} {'Mj nominal':>10} {'Mj diseño':>9} {'DCR (200 kN·m)':>14} {'seguro':>7}")
    for tp in (12.0, 15.0, 20.0, 25.0):
        res = render_end_plate_memo(EndPlateInput(M_demand_kNm=200.0, bolt_diameter_mm=20.0, bolt_grade_Fu_MPa=1000.0, n_bolts=4,
                                                  plate_thickness_mm=tp, plate_Fy_MPa=275.0, plate_width_mm=bp, bolt_rows=rows))
        print(f"  {tp:7.0f} {res.M_resistance_nominal_kNm:10.1f} {res.M_resistance_kNm:9.1f} {res.DCR_moment:14.3f} {str(res.is_safe):>7}")
    res = render_end_plate_memo(EndPlateInput(M_demand_kNm=200.0, bolt_diameter_mm=20.0, bolt_grade_Fu_MPa=1000.0, n_bolts=4,
                                              plate_thickness_mm=20.0, plate_Fy_MPa=275.0, plate_width_mm=bp, bolt_rows=rows))
    print("\nFilas con chapa de 20 mm:")
    for r in getattr(res, "rows", []) or []:
        print(f"  h = {r.h_mm:6.1f} mm → Ft,Rd = {r.Ft_Rd_design_kN:6.1f} kN (nominal {r.Ft_Rd_nominal_kN:.1f}), modo {r.governing_mode}")
    sin_filas = render_end_plate_memo(EndPlateInput(M_demand_kNm=200.0, bolt_diameter_mm=20.0, plate_thickness_mm=20.0))
    print(f"\nSin bolt_rows: M_resistance_kNm = {sin_filas.M_resistance_kNm}, DCR_moment = {sin_filas.DCR_moment}, is_safe = {sin_filas.is_safe} (NO CALCULADO, no se inventa el brazo).")
    print("Mj es una cota superior: falta el ala del pilar a flexión, el alma del pilar a tracción, cortante y compresión, el alma de la viga a tracción y los límites de grupo de filas (§6.2.7.2).")


if __name__ == "__main__":
    main()
