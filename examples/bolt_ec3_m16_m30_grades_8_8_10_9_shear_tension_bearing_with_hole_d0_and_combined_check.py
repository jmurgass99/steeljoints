"""Tornillos según EN 1993-1-8 Tabla 3.4: cortante con el área resistente As (rosca en el plano) o la bruta, tracción con As, aplastamiento con el diámetro de agujero d0 de EN 1090-2 y la interacción Fv/Fv,Rd + Ft/(1,4·Ft,Rd) ≤ 1.

`Bolt(d, "8.8"|"10.9", "EC3")` da Fv,Rd = αv·fub·A/γM2 (αv 0,6 para 8.8, 0,5 para 10.9), Ft,Rd =
0,9·fub·As/γM2 y Fb,Rd = k1·αb·fu·d·t/γM2 con αd y k1 calculados con d0 (holgura normal 1/2/3 mm).
`codes.ec3_1_8.bolt_combined_check` evalúa la interacción. γM2 = 1,25 (valor recomendado).

Ejecutar:  python examples/bolt_ec3_m16_m30_grades_8_8_10_9_shear_tension_bearing_with_hole_d0_and_combined_check.py
"""
from steeljoints import Bolt
from steeljoints.bolts import bolt_tensile_stress_area, ec3_normal_hole_clearance
from steeljoints.codes.ec3_1_8 import bolt_combined_check


def main() -> None:
    print("Resistencias de cálculo por tornillo [kN], un plano de corte, γM2 = 1,25:")
    print(f"  {'tornillo':9} {'As':>5} {'d0':>4} {'Fv,Rd rosca':>11} {'Fv,Rd vástago':>13} {'Ft,Rd':>6}")
    for d in (16.0, 20.0, 24.0, 30.0):
        for g in ("8.8", "10.9"):
            bt = Bolt(d, g, "EC3", threads_in_shear_plane=True)
            bs = Bolt(d, g, "EC3", threads_in_shear_plane=False)
            print(f"  M{d:.0f} {g:5} {bolt_tensile_stress_area(d):5.0f} {d + ec3_normal_hole_clearance(d):4.0f} {bt.ec3_shear_strength() / 1e3:11.1f} {bs.ec3_shear_strength() / 1e3:13.1f} {bt.ec3_tension_strength() / 1e3:6.1f}")
    b = Bolt(20.0, "8.8", "EC3")
    print(f"\nA mano, M20 8.8: Fv,Rd = 0,6·800·245/1,25 = {0.6 * 800 * 245 / 1.25 / 1e3:.2f} kN; Ft,Rd = 0,9·800·245/1,25 = {0.9 * 800 * 245 / 1.25 / 1e3:.2f} kN (tablas habituales: 94,1 y 141,1 kN)")
    print("\nAplastamiento de un M20 8.8 en chapa S275 (fu = 430 MPa) de 12 mm, d0 = 22 mm:")
    print(f"  {'e1':>4} {'p1':>4} {'e2':>4} {'p2':>4} {'αd':>6} {'k1':>6} {'Fb,Rd [kN]':>10} {'con d en vez de d0':>18}")
    for e1, p1, e2, p2 in ((30, 55, 30, 55), (40, 70, 35, 70), (50, 80, 40, 80), (66, 90, 50, 90)):
        d0 = 22.0
        ad = min(e1 / (3 * d0), p1 / (3 * d0) - 0.25, 800 / 430, 1.0)
        k1 = min(2.8 * e2 / d0 - 1.7, 1.4 * p2 / d0 - 1.7, 2.5)
        Fb = b.ec3_bearing_strength(12.0, 430.0, e1, p1, e2, p2)
        Fb_d = b.ec3_bearing_strength(12.0, 430.0, e1, p1, e2, p2, d0=20.0)
        print(f"  {e1:4.0f} {p1:4.0f} {e2:4.0f} {p2:4.0f} {ad:6.3f} {k1:6.3f} {Fb / 1e3:10.1f} {Fb_d / 1e3:18.1f}")
    print("  Con e1 = 3·d0 = 66 mm y p2 ≥ 3·d0 se alcanzan αd = 1 y k1 = 2,5: Fb,Rd = 2,5·fu·d·t/γM2 = "
          f"{2.5 * 430 * 20 * 12 / 1.25 / 1e3:.1f} kN.")
    print("\nInteracción cortante-tracción (Tabla 3.4): Fv,Ed/Fv,Rd + Ft,Ed/(1,4·Ft,Rd) ≤ 1")
    Fv, Ft = b.ec3_shear_strength(), b.ec3_tension_strength()
    for fv, ft in ((40e3, 60e3), (60e3, 80e3), (70e3, 100e3), (90e3, 30e3)):
        u = bolt_combined_check(fv, Fv, ft, Ft)
        print(f"  Fv,Ed = {fv / 1e3:4.0f} kN, Ft,Ed = {ft / 1e3:4.0f} kN → {u:.3f} {'cumple' if u <= 1 else 'NO cumple'}")
    print("\nEl aplastamiento toma el tornillo más desfavorable de la unión (mín. de los casos de borde e interior para αd y k1), una envolvente conservadora; "
          "para tornillos concretos usa codes.ec3_1_8.bolt_bearing_Rd(direction_inner=…, d0_mm=…). Sin punzonamiento ni deslizamiento aquí (funciones aparte en codes.ec3_1_8).")


if __name__ == "__main__":
    main()
