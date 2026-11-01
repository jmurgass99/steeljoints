"""Elementos de tracción de EN 1993-1-11 (cables, cordones y barras): resistencia característica por grupo de producto, coeficiente parcial según clase de consecuencias y situación, tensión de flexión en el anclaje por desviación angular y categoría de fatiga.

`ec3_tension_members.tendon_resistance_FRk(d_w, fuk, n_wires, group)` con F_Rk = k·A_m·f_uk (k = 1,00 / 0,92 / 0,85
para los grupos 1, 2 y 3 del módulo), `partial_factor_gM(clase, situación)`, `bending_stress_at_anchorage(F, d, L, E, I)`
y `fatigue_class_strand(d, tipo)`. Los coeficientes son los que trae el módulo, SIN CONTRASTAR con el texto de la norma.

Ejecutar:  python examples/en1993_1_11_cables_and_tendons_resistance_groups_partial_factors_anchorage_bending_fatigue.py
"""
from math import pi, radians

from steeljoints.ec3_tension_members import bending_stress_at_anchorage, fatigue_class_strand, partial_factor_gM, tendon_resistance_FRk


def main() -> None:
    print("Resistencia característica F_Rk [kN] con alambres de 5 mm y f_uk = 1770 MPa:")
    for n in (7, 19, 37, 61):
        Am = n * pi * 5.0 ** 2 / 4
        vals = [tendon_resistance_FRk(5.0, 1770.0, n, g) / 1e3 for g in (1, 2, 3)]
        print(f"  {n:3d} alambres (A_m = {Am:6.0f} mm²): grupo 1 {vals[0]:7.0f} | grupo 2 {vals[1]:7.0f} | grupo 3 {vals[2]:7.0f}")
    print("\nCoeficiente parcial γM del módulo:")
    for clase in (1, 2, 3):
        fila = []
        for sit in ("construction", "service", "fatigue", "accidental"):
            try:
                fila.append(f"{sit} {partial_factor_gM(clase, sit):.3f}")
            except ValueError as exc:
                fila.append(f"{sit} —")
        print(f"  clase {clase}: " + " | ".join(fila))
    FRk = tendon_resistance_FRk(5.0, 1770.0, 37, 2)
    gM = partial_factor_gM(2, "service")
    print(f"\nCordón de 37 alambres, clase 2, servicio: F_Rd = F_Rk/γM = {FRk / 1e3:.0f}/{gM:.2f} = {FRk / gM / 1e3:.0f} kN")
    d = 5.0 * 7
    I = pi * d ** 4 / 64
    print("\nTensión de flexión en el anclaje con una desviación angular de 0,5° (barra maciza equivalente de 35 mm, E = 165 GPa):")
    for F in (200e3, 400e3, 600e3):
        s = bending_stress_at_anchorage(F, d, 5000.0, 165000.0, I, theta_rad=radians(0.5))
        print(f"  F = {F / 1e3:4.0f} kN → σ_b = {s:6.1f} MPa (tensión media {F / (pi * d ** 2 / 4):6.1f} MPa); "
              f"por radián {bending_stress_at_anchorage(F, d, 5000.0, 165000.0, I):7.0f} MPa")
    print("  σ_b = θ·(d/2)·√(F·E/I). El modelo trata el cable como barra maciza (I y d/2 del conjunto); en un cordón cada alambre flecta con su propio radio, así que usa la expresión del fabricante para un cordón real.")
    print("\nCategoría de fatiga del módulo:")
    for tipo in ("wire", "strand", "locked_coil", "bar"):
        print(f"  {tipo:12} d = 36 mm → Δσ_C = {fatigue_class_strand(36.0, tipo)} MPa")
    print("\nγM de servicio = 1,5 por un factor de clase (0,9 / 1,0 / 1,1). "
          "El agrupamiento 1/2/3, los coeficientes 0,92 y 0,85 y los γM son la interpretación del módulo; "
          "compruébalos con EN 1993-1-11 y con la documentación del fabricante antes de usarlos.")


if __name__ == "__main__":
    main()
