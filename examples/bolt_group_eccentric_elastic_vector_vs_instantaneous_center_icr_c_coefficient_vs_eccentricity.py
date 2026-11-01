"""Grupo de seis pernos (2 × 3 a 75 mm) con carga vertical excéntrica: método elástico vectorial frente al centro instantáneo de rotación (Crawford-Kulak, AISC Manual Parte 7), coeficiente C y posición del centro según la excentricidad.

`BoltGroupICR(positions, Pu_N, ex_mm, load_angle_deg, Rult_N)` resuelve el centro instantáneo con la
curva R = Rult·(1 − e^(−10Δ))^0,55 y Δmax = 0,34" del perno más alejado; con `Rult_N = 1` devuelve C
(capacidad = C·Rult). `BoltGroup.elastic_critical_bolt` suma cortante directo V/n y torsión M·r/Ip.
Con carga vertical sobre un eje de simetría el solver es la bisección 1D (exacta para ese caso).

Ejecutar:  python examples/bolt_group_eccentric_elastic_vector_vs_instantaneous_center_icr_c_coefficient_vs_eccentricity.py
"""
from steeljoints import Bolt, BoltGroup, BoltGroupICR, rectangular_pattern


def main() -> None:
    pos = rectangular_pattern(nx=2, ny=3, sx=75.0, sy=75.0)
    bolt = Bolt(19.05, "A325", "AISC")
    phi_rn = bolt.aisc_shear_strength()
    print(f"Grupo 2 × 3 (gramil 75 mm, paso 75 mm), A325-N de 3/4\": φrn = {phi_rn / 1e3:.1f} kN por perno")
    print(f"  {'e [mm]':>6} {'C elástico':>10} {'C ICR':>7} {'ICR/elás.':>9} {'IC (x, y) [mm]':>16} {'φRn ICR [kN]':>12} {'solver':>9}")
    for e in (0.0, 50.0, 100.0, 150.0, 200.0, 300.0, 500.0):
        g = BoltGroup(bolt=bolt, positions=pos, phi_Rn_single=1.0)
        # C elástico = P / fuerza del perno crítico. Carga de 1 MN porque la función redondea Vmax a 0,1 N.
        r_unit = g.elastic_critical_bolt(Vu=1e6, Mu=1e6 * e)
        C_el = 1e6 / r_unit["Vmax_N"]
        icr = BoltGroupICR(positions=pos, Pu_N=1.0, ex_mm=e, load_angle_deg=0.0, Rult_N=1.0).solve()
        ic = "∞" if e == 0 else f"({icr['IC_x_mm']:.0f}, {icr['IC_y_mm']:.0f})"
        print(f"  {e:6.0f} {C_el:10.3f} {icr['C_coefficient']:7.3f} {icr['C_coefficient'] / C_el:9.3f} {ic:>16} {icr['C_coefficient'] * phi_rn / 1e3:12.1f} {icr['solver']:>9}")
    r = BoltGroupICR(positions=pos, Pu_N=200e3, ex_mm=200.0, Rult_N=phi_rn).solve()
    print(f"\nComprobación de una ménsula con Pu = 200 kN a 200 mm: φRn = C·φrn = {r['Pn_kN']:.1f} kN → utilización {r['utilization']:.2f} {'cumple' if r['is_ok'] else 'NO cumple'}")
    el = BoltGroup(bolt=bolt, positions=pos, phi_Rn_single=phi_rn).elastic_critical_bolt(200e3, 200e3 * 200.0)
    print(f"  Método elástico: perno crítico {el['Vmax_kN']:.1f} kN frente a {phi_rn / 1e3:.1f} kN → utilización {el['utilization']:.2f}")
    ratios = []
    for e in (50.0, 100.0, 150.0, 200.0, 300.0, 500.0):
        c_el = 1e6 / BoltGroup(bolt=bolt, positions=pos, phi_Rn_single=1.0).elastic_critical_bolt(1e6, 1e6 * e)["Vmax_N"]
        ratios.append(BoltGroupICR(positions=pos, Pu_N=1.0, ex_mm=e, Rult_N=1.0).solve()["C_coefficient"] / c_el)
    print(f"\nCon e = 0 los dos métodos dan C = n = 6. Con excentricidad el ICR da entre un {(min(ratios) - 1) * 100:.0f} % y un {(max(ratios) - 1) * 100:.0f} % más que el elástico: "
          "es la reserva por ductilidad de los pernos interiores que el método elástico no usa. "
          "Los C de las Tablas 7-6 a 7-14 del Manual salen de este mismo modelo, pero aquí no se han comparado valor a valor.")


if __name__ == "__main__":
    main()
