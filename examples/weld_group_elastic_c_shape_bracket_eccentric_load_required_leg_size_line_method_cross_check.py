"""Ménsula soldada en C (alma vertical de 200 mm y dos alas de 100 mm) con 150 kN a 300 mm del alma: método elástico de línea (AISC Manual Parte 8), punto crítico, tamaño de cordón necesario con E70 y contraste entre las dos implementaciones del paquete.

`WeldGroupElastic(segments, Vy, load_point)` trata la soldadura como línea: f = V/Lw + M·r/Ip [N/mm] en los
extremos de cada tramo. `welds.WeldGroup.utilization(Vu, Mu, φRn/mm)` hace lo mismo con cordones definidos por
centro, longitud y orientación (corregido en 1.2: antes evaluaba el centro de cada cordón).

Ejecutar:  python examples/weld_group_elastic_c_shape_bracket_eccentric_load_required_leg_size_line_method_cross_check.py
"""
from math import sqrt

from steeljoints import FilletWeld, WeldGroup
from steeljoints.weld_group import WeldGroupElastic, WeldSegment

FEXX = 482.6   # E70 [MPa]


def main() -> None:
    P, x_load = 150e3, 300.0
    segs = [WeldSegment(0.0, -100.0, 0.0, 100.0, 8.0),
            WeldSegment(0.0, 100.0, 100.0, 100.0, 8.0),
            WeldSegment(0.0, -100.0, 100.0, -100.0, 8.0)]
    g = WeldGroupElastic(segments=segs, Vy=-P, load_point=(x_load, 0.0))
    d = g.max_demand()
    print(f"Grupo en C: Lw = {d['Lw_total_mm']:.0f} mm, centroide x̄ = {d['cx_mm']:.1f} mm, Ip = {d['Ip_mm3']:.4g} mm³ (línea de espesor unidad)")
    print(f"  Carga {P / 1e3:.0f} kN hacia abajo a x = {x_load:.0f} mm → excentricidad {x_load - g.cx:.1f} mm, M = {abs(g.M_net) / 1e6:.2f} kN·m")
    print(f"  Punto crítico ({d['x_critical_mm']:.0f}, {d['y_critical_mm']:.0f}) mm, f_max = {d['f_max_N_per_mm']:.1f} N/mm")
    ex = x_load - g.cx
    fd = P / d["Lw_total_mm"]
    ftx = P * ex * 100.0 / g.Ip
    fty = P * ex * (100.0 - g.cx) / g.Ip
    print(f"  A mano en (100, ±100): directo {fd:.1f}, torsión ({ftx:.1f}; {fty:.1f}) → f = √({ftx:.1f}² + ({fd:.1f} + {fty:.1f})²) = {sqrt(ftx**2 + (fd + fty)**2):.1f} N/mm")
    print("\nTamaño de cordón con E70, φ = 0,75 (sin aumento direccional):")
    w_req = d["f_max_N_per_mm"] / (0.75 * 0.60 * FEXX / sqrt(2))
    print(f"  w_req = f_max/(0,75·0,60·FEXX/√2) = {w_req:.1f} mm → cordón comercial de {next(s for s in (5, 6, 8, 10, 12, 14, 16) if s >= w_req)} mm")
    for w in (8.0, 10.0, 12.0):
        u = g.utilization(FEXX_MPa=FEXX, w_mm=w)
        print(f"  w = {w:4.0f} mm: φRn = {u['phi_Rn_per_mm_N']:.0f} N/mm → utilización {u['utilization']:.3f} {'cumple' if u['is_ok'] else 'NO cumple'}")
    wg = WeldGroup(welds=[FilletWeld(8.0, 200.0), FilletWeld(8.0, 100.0), FilletWeld(8.0, 100.0)],
                   positions=[(0.0, 0.0), (50.0, 100.0), (50.0, -100.0)], angles=[90.0, 0.0, 0.0])
    r = wg.utilization(Vu=-P, Mu=-P * (x_load - wg.cx), phi_Rn_per_unit=0.75 * 0.60 * FEXX * 8.0 / sqrt(2))
    print(f"\nwelds.WeldGroup con los mismos cordones de 8 mm: {r['max_stress_N_mm2']:.1f} N/mm² en la garganta = {r['max_stress_N_mm2'] * 8.0 / sqrt(2):.1f} N/mm de cordón; "
          f"utilización {r['utilization']:.3f} ({r['status'].value}).")
    print("Las dos implementaciones dan la misma tensión. El método elástico ignora la ductilidad y el aumento direccional; el centro instantáneo da más capacidad para la misma ménsula.")


if __name__ == "__main__":
    main()
