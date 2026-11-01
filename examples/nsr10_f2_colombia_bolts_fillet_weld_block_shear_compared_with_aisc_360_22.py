"""NSR-10 Título F.2 (Colombia): perno individual A307, A325 y A490 con rosca incluida y excluida, cordón de filete con aumento direccional y bloque de cortante, comparados con las clases AISC 360-22 del paquete.

`codes.nsr10_f2.design_bolt_nsr10(NSR10BoltInput(grade, diameter_mm, thread_condition))`,
`design_fillet_weld_nsr10(NSR10FilletWeldInput(leg, L, FEXX, ángulo))` y `design_block_shear_nsr10`.
NSR-10 se basa en AISC 360-05; este módulo usa los valores de AISC 360-10 y posteriores (límite declarado).

Ejecutar:  python examples/nsr10_f2_colombia_bolts_fillet_weld_block_shear_compared_with_aisc_360_22.py
"""
from steeljoints import Bolt, FilletWeld
from steeljoints.codes.nsr10_f2 import (
    BOLT_GRADES_NSR10, NSR10BoltInput, NSR10FilletWeldInput, design_bolt_nsr10, design_fillet_weld_nsr10, info,
)


def main() -> None:
    print(info().splitlines()[0] if info() else "")
    print(f"\n  {'perno':14} {'φRn corte NSR [kN]':>18} {'AISC 360-22 [kN]':>16} {'dif.':>6} {'φRn tracción NSR':>16} {'AISC':>6}")
    for g in ("A307", "A325", "A490"):
        for th in ("N", "X"):
            if g == "A307" and th == "X":
                continue
            r = design_bolt_nsr10(NSR10BoltInput(g, 19.05, th))
            a = Bolt(19.05, g, "AISC", threads_in_shear_plane=(th == "N"))
            av = a.aisc_shear_strength() / 1e3
            label = f"{g}-{th} 3/4" + '"'
            print(f"  {label:14} {r.Rd_shear_kN:18.1f} {av:16.1f} {(r.Rd_shear_kN / av - 1) * 100:+5.1f}% {r.Rd_tension_kN:16.1f} {a.aisc_tension_strength() / 1e3:6.1f}")
    print("\nCordón de 8 mm × 150 mm, E70:")
    for ang in (0.0, 45.0, 90.0):
        w = design_fillet_weld_nsr10(NSR10FilletWeldInput(8.0, 150.0, 482.0, ang))
        a = FilletWeld(8.0, 150.0, "E70", "AISC", theta=ang).aisc_strength() / 1e3
        print(f"  θ = {ang:4.0f}° → NSR-10 φRn = {w.Rd_kN:6.1f} kN, AISC 360-22 {a:6.1f} kN")
    r = design_bolt_nsr10(NSR10BoltInput("A325", 19.05, "X"))
    print(f"\nLa rosca excluida usa Fnv = 0,563·Fu ({0.563 * 825:.0f} MPa en A325) en vez de la Tabla J3.2 (468,8 MPa, 68 ksi); de ahí la diferencia en las filas -X. "
          f"El A490-N de la tabla NSR del módulo tiene {BOLT_GRADES_NSR10['A490']['Fnv_N'] / 1e6:.0f} MPa frente a 468,8 MPa (68 ksi) de AISC 360-22.")
    print(f"Las notas del resultado dicen: {r.notes[0]}")
    print("NSR-10 F.2 sigue a AISC 360-05, donde el A325-N tenía 48 ksi (330 MPa); el módulo usa 372 MPa (54 ksi, AISC 360-10). "
          "Si el proyecto exige la edición literal de NSR-10, comprueba las resistencias nominales de pernos de F.2.10.3 antes de usar estos valores.")


if __name__ == "__main__":
    main()
