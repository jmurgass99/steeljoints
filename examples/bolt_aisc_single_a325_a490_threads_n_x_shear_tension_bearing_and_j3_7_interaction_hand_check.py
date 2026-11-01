"""Perno individual según AISC 360-22: cortante con la rosca incluida (-N) o excluida (-X), tracción, aplastamiento y la interacción tracción-cortante de §J3.7, comprobados a mano para un A325 de 3/4".

`Bolt(d, grado, "AISC", threads_in_shear_plane, n_shear_planes)` usa la Tabla J3.2 (Fnt, Fnv en ksi
convertidos a MPa) sobre el área nominal Ab: φRn = 0,75·Fnv·Ab·planos, φRnt = 0,75·Fnt·Ab,
aplastamiento φ·min(1,2·lc·t·Fu, 2,4·d·t·Fu) (§J3.10) y F'nt = 1,3·Fnt − Fnt/(φ·Fnv)·frv ≤ Fnt (Ec. J3-3a).

Ejecutar:  python examples/bolt_aisc_single_a325_a490_threads_n_x_shear_tension_bearing_and_j3_7_interaction_hand_check.py
"""
from steeljoints import Bolt
from steeljoints.bolts import bolt_gross_area

KSI = 6.894757


def main() -> None:
    print("φRn por perno [kN], AISC 360-22 Tabla J3.2, φ = 0,75:")
    print(f"  {'perno':10} {'Ab [mm²]':>8} {'corte -N':>8} {'corte -X':>8} {'doble -N':>8} {'tracción':>8}")
    for d, nombre in ((15.875, '5/8"'), (19.05, '3/4"'), (22.225, '7/8"'), (25.4, '1"')):
        for g in ("A325", "A490"):
            bn = Bolt(d, g, "AISC", threads_in_shear_plane=True)
            bx = Bolt(d, g, "AISC", threads_in_shear_plane=False)
            b2 = Bolt(d, g, "AISC", threads_in_shear_plane=True, n_shear_planes=2)
            print(f"  {g + ' ' + nombre:10} {bn.Ab:8.1f} {bn.aisc_shear_strength() / 1e3:8.1f} {bx.aisc_shear_strength() / 1e3:8.1f} {b2.aisc_shear_strength() / 1e3:8.1f} {bn.aisc_tension_strength() / 1e3:8.1f}")
    b = Bolt(19.05, "A325", "AISC")
    Ab = bolt_gross_area(19.05)
    print(f"\nA mano, A325-N de 3/4\": Ab = {Ab:.1f} mm²; φRn = 0,75·54 ksi·Ab = 0,75·{54 * KSI:.1f}·{Ab:.1f} = {0.75 * 54 * KSI * Ab / 1e3:.2f} kN (función {b.aisc_shear_strength() / 1e3:.2f})")
    print(f"  En unidades US: 0,75·54·0,442 in² = {0.75 * 54 * 0.4418:.2f} kip = {0.75 * 54 * 0.4418 * 4.448222:.1f} kN (Manual AISC Tabla 7-1: 17,9 kip)")
    print("\nAplastamiento en una chapa de 10 mm, Fu = 450 MPa, con la deformación como estado de servicio (§J3.10):")
    for lc in (20.0, 30.0, 38.1, 50.0):
        print(f"  lc = {lc:5.1f} mm → φRn = {b.aisc_bearing_strength(10.0, 450.0, lc) / 1e3:6.1f} kN (desgarro 1,2·lc·t·Fu, tope 2,4·d·t·Fu = {0.75 * 2.4 * 19.05 * 10 * 450 / 1e3:.1f} kN)")
    print("\nInteracción J3.7 (rosca incluida): resistencia a tracción disponible con cortante concomitante")
    print(f"  {'Vu/perno [kN]':>13} {'frv [MPa]':>9} {'F′nt [MPa]':>10} {'φR′nt [kN]':>10}")
    for V in (0.0, 20.0, 40.0, 60.0, 80.0, 100.0):
        Rnt = b.aisc_combined_tension_shear(V * 1e3)
        print(f"  {V:13.0f} {V * 1e3 / Ab:9.1f} {Rnt / 0.75 / Ab:10.1f} {Rnt / 1e3:10.1f}")
    print(f"  A mano con 40 kN: F′nt = 1,3·620,5 − 620,5/(0,75·372,3)·{40e3 / Ab:.1f} = {1.3 * 620.5 - 620.5 / (0.75 * 372.3) * 40e3 / Ab:.1f} MPa")
    print("\nHasta la versión 1.1 el cortante -N se calculaba con 0,75·Ab además de Fnv-N (59,7 kN en vez de 79,6 kN para el A325 de 3/4\") y la rosca excluida no subía a Fnv-X. "
          "El aplastamiento toma lc como dato: calcúlalo con el agujero real (d + 1/16\" estándar).")


if __name__ == "__main__":
    main()
