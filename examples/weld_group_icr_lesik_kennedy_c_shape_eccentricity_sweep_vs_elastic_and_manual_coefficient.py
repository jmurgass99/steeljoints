"""Ménsula en C soldada con cordones de 8 mm E70: capacidad nominal por centro instantáneo (Lesik y Kennedy, AISC Manual Parte 8) frente al método elástico, en función de la excentricidad, y el coeficiente C del Manual.

`WeldGroupICR(segments, Pu_N, ex_mm, load_angle_deg, FEXX_MPa, n_subdiv)` divide cada tramo en elementos con
R(θ, Δ) = 0,60·FEXX·a·(1 + 0,50·sin^1,5 θ)·[p(1,9 − 0,9p)]^0,3 y Δu = 1,087·w·(θ + 6)^−0,65 ≤ 0,17·w, y busca el
centro que equilibra la carga. Devuelve Pn nominal (sin φ). El coeficiente del Manual es C = Pn/(D·l) con D en
dieciseisavos de pulgada y l en pulgadas (Tablas 8-4 a 8-11, aquí no comparadas valor a valor).

Ejecutar:  python examples/weld_group_icr_lesik_kennedy_c_shape_eccentricity_sweep_vs_elastic_and_manual_coefficient.py
"""
import logging
from math import sqrt

from steeljoints.weld_group import WeldGroupElastic, WeldGroupICR, WeldSegment

FEXX, W = 482.6, 8.0
KIP = 4448.222


def segments() -> list[WeldSegment]:
    return [WeldSegment(0.0, -100.0, 0.0, 100.0, W),
            WeldSegment(0.0, 100.0, 100.0, 100.0, W),
            WeldSegment(0.0, -100.0, 100.0, -100.0, W)]


def main() -> None:
    logging.getLogger("steeljoints").setLevel(logging.ERROR)   # el solver usado sale en la tabla
    rn_mm = 0.60 * FEXX * W / sqrt(2)   # N/mm, nominal, carga longitudinal
    D = W / (25.4 / 16)                 # dieciseisavos
    l_in = 200.0 / 25.4
    print(f"C de 200 × 100 mm, cordón de {W:.0f} mm E70 (Rn longitudinal {rn_mm:.0f} N/mm), carga vertical, excentricidad desde el centroide.\n")
    print(f"  {'ex [mm]':>7} {'Pn ICR [kN]':>11} {'Pn elást. [kN]':>14} {'ICR/elás.':>9} {'IC x [mm]':>9} {'C Manual':>8} {'solver':>14}")
    rows = []
    for ex in (0.0, 50.0, 100.0, 150.0, 200.0, 300.0, 400.0):
        icr = WeldGroupICR(segments=segments(), Pu_N=1.0, ex_mm=ex, FEXX_MPa=FEXX, n_subdiv=30).solve()
        cx = WeldGroupElastic(segments=segments()).cx
        el = WeldGroupElastic(segments=segments(), Vy=-1e6, load_point=(cx + ex, 0.0)).max_demand()["f_max_N_per_mm"]
        pn_el = rn_mm * 1e6 / el
        C = icr["Pn_N"] / KIP / (D * l_in)
        ic = "∞" if ex == 0 else f"{icr['IC_x_mm']:.0f}"
        rows.append((ex, icr["Pn_N"] / pn_el, icr["solver"]))
        print(f"  {ex:7.0f} {icr['Pn_kN']:11.1f} {pn_el / 1e3:14.1f} {icr['Pn_N'] / pn_el:9.3f} {ic:>9} {C:8.3f} {icr['solver']:>14}")
    rnl = rn_mm * 200.0
    j24 = max(2 * rnl, 0.85 * rnl + 1.5 * rnl)
    print(f"\nCarga centrada: todos los cordones se deforman lo mismo y manda la deformación última de las alas transversales, así que el alma no llega a su capacidad. "
          f"ICR {rows[0][1] * 2 * rnl / 1e3:.1f} kN frente a AISC 360-22 §J2.4(b)(2) máx(Rnwl + Rnwt, 0,85·Rnwl + 1,5·Rnwt) = {j24 / 1e3:.1f} kN.")
    print(f"Con excentricidad el ICR da entre {min(r for _, r, _ in rows[1:]):.2f} y {max(r for _, r, _ in rows[1:]):.2f} veces la capacidad elástica. "
          f"Newton 2D no convergió con ex = {', '.join(f'{e:.0f}' for e, _, s in rows if s == 'bisection_fallback')} mm y se usó la bisección, exacta aquí porque la C es simétrica respecto a la horizontal.")
    r = WeldGroupICR(segments=segments(), Pu_N=150e3 / 0.75, ex_mm=300.0 - WeldGroupElastic(segments=segments()).cx, FEXX_MPa=FEXX).solve()
    print(f"\nLa ménsula del caso elástico (150 kN a 300 mm del alma): φPn = 0,75·{r['Pn_kN']:.1f} = {0.75 * r['Pn_kN']:.1f} kN → utilización {r['utilization']:.3f} {'cumple' if r['is_ok'] else 'NO cumple'} con cordón de 8 mm.")


if __name__ == "__main__":
    main()
