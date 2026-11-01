"""Pandeo por flexotorsión de una T soldada (ala 200 × 16, alma 250 × 10 mm) según AISC 360-22 §E4: propiedades de la sección calculadas a mano, cúbica general E4-6 frente a la fórmula cerrada E4-5 para secciones con un eje de simetría, y comparación con el pandeo por flexión, barriendo la longitud.

`flexural_torsional.BucklingInput(A, Ix, Iy, J, Cw, xo, yo, E, G, Lcx, Lcy, Lcz)`, `elastic_buckling_stress` (raíz menor
de la cúbica), `flexural_torsional_closed_form` y `critical_load`.

Ejecutar:  python examples/flexural_torsional_buckling_aisc_e4_welded_tee_cubic_vs_closed_form_length_sweep.py
"""
from math import pi

from steeljoints.flexural_torsional import BucklingInput, critical_load, elastic_buckling_stress, flexural_torsional_closed_form


def tee_properties(bf: float, tf: float, hw: float, tw: float) -> dict:
    """T soldada con el ala arriba; y medido hacia abajo desde la cara superior del ala."""
    Af, Aw = bf * tf, hw * tw
    A = Af + Aw
    yc = (Af * tf / 2 + Aw * (tf + hw / 2)) / A
    Ix = bf * tf ** 3 / 12 + Af * (yc - tf / 2) ** 2 + tw * hw ** 3 / 12 + Aw * (tf + hw / 2 - yc) ** 2
    Iy = tf * bf ** 3 / 12 + hw * tw ** 3 / 12
    J = (bf * tf ** 3 + hw * tw ** 3) / 3
    Cw = tf ** 3 * bf ** 3 / 144 + tw ** 3 * (hw + tf / 2) ** 3 / 36
    yo = yc - tf / 2   # centro de cortante en la intersección de las líneas medias
    return dict(A=A, Ix=Ix, Iy=Iy, J=J, Cw=Cw, xo=0.0, yo=yo, yc=yc)


def main() -> None:
    p = tee_properties(200.0, 16.0, 250.0, 10.0)
    print(f"T soldada: A = {p['A']:.0f} mm², ȳ = {p['yc']:.1f} mm desde la cara del ala, Ix = {p['Ix'] / 1e6:.2f}e6, Iy = {p['Iy'] / 1e6:.2f}e6 mm⁴, "
          f"J = {p['J'] / 1e3:.1f}e3 mm⁴, Cw = {p['Cw'] / 1e9:.3f}e9 mm⁶, centro de cortante a yo = {p['yo']:.1f} mm del centroide\n")
    print(f"  {'L [m]':>5} {'Fex':>7} {'Fey':>7} {'Fez':>7} {'Fe cúbica':>9} {'Fe cerrada':>10} {'Pcr [kN]':>8} {'modo':>14}")
    red = {}
    for L in (1.5, 2.0, 3.0, 4.0, 6.0, 8.0):
        b = BucklingInput(A=p["A"], Ix=p["Ix"], Iy=p["Iy"], J=p["J"], Cw=p["Cw"], xo=0.0, yo=p["yo"],
                          E=200000.0, G=77200.0, Lcx=L * 1e3, Lcy=L * 1e3, Lcz=L * 1e3)
        Fe = elastic_buckling_stress(b)
        Fc = flexural_torsional_closed_form(b)
        modo = "flexotorsión" if Fe < min(b.Fex, b.Fey) - 1e-6 else "flexión"
        red[L] = 1 - Fe / min(b.Fey, b.Fez)
        print(f"  {L:5.1f} {b.Fex:7.0f} {b.Fey:7.0f} {b.Fez:7.0f} {Fe:9.1f} {Fc:10.1f} {critical_load(b) / 1e3:8.0f} {modo:>14}")
    b = BucklingInput(A=p["A"], Ix=p["Ix"], Iy=p["Iy"], J=p["J"], Cw=p["Cw"], xo=0.0, yo=p["yo"], E=200000.0, G=77200.0, Lcx=3000.0, Lcy=3000.0, Lcz=3000.0)
    ro2 = p["yo"] ** 2 + (p["Ix"] + p["Iy"]) / p["A"]
    print(f"\nA mano con L = 3 m: r̄o² = yo² + (Ix + Iy)/A = {ro2:.0f} mm² (función {b.ro2:.0f}); H = 1 − yo²/r̄o² = {1 - p['yo'] ** 2 / ro2:.3f}; "
          f"Fez = (π²·E·Cw/Lcz² + G·J)/(A·r̄o²) = {(pi ** 2 * 200000 * p['Cw'] / 3000 ** 2 + 77200 * p['J']) / (p['A'] * ro2):.1f} MPa")
    try:
        flexural_torsional_closed_form(BucklingInput(A=p["A"], Ix=p["Ix"], Iy=p["Iy"], J=p["J"], Cw=p["Cw"], xo=5.0, yo=p["yo"],
                                                     E=200000.0, G=77200.0, Lcx=3000.0, Lcy=3000.0, Lcz=3000.0))
    except ValueError as exc:
        print(f"Sección sin eje de simetría con la fórmula cerrada → ValueError: {exc}")
    print("\nEl eje de simetría es el vertical (y): la flexión alrededor del eje horizontal (Fex) queda desacoplada y la flexión alrededor de y (Fey) se acopla con la torsión (Fez). "
          f"La reducción respecto al menor de Fey y Fez es máxima cuando ambos se igualan ({red[3.0] * 100:.0f} % con 3 m) y pequeña cuando la flexión domina ({red[8.0] * 100:.0f} % con 8 m). "
          "La cúbica y la fórmula cerrada coinciden en todo el barrido.")


if __name__ == "__main__":
    main()
