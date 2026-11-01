"""Chapa simple a cortante (shear tab) de 9,5 mm con pernos A325-N de 3/4" en una línea: estados límite de pernos, aplastamiento, fluencia y rotura a cortante y bloque de cortante para 2 a 6 pernos, el que gobierna y la capacidad resultante.

`ShearTab(Vu, n_bolts, bolt_spacing, edge_dist_v, edge_dist_h, plate_thickness, plate_width, Fy_plate, Fu_plate)`
y `.design()` (AISC 360-22 §J3, §J4.2 y §J4.3). La altura de la chapa es (n − 1)·s + 2·e_v.

Ejecutar:  python examples/shear_tab_single_plate_two_to_six_bolts_all_limit_states_governing_check_and_capacity.py
"""
from steeljoints import ShearTab

NOMBRES = {
    "Bolt group shear": "cortante pernos",
    "Bolt bearing on plate": "aplastamiento",
    "Plate shear yielding": "fluencia cortante",
    "Plate shear rupture": "rotura cortante",
    "Block shear": "bloque",
}


def main() -> None:
    print("Chapa de 9,5 mm, A572 Gr. 50 (Fy 345 / Fu 450 MPa), paso 75 mm, bordes 38 mm, ancho 75 mm. φRn [kN]:\n")
    print(f"  {'n':>2} {'h [mm]':>6} " + " ".join(f"{v:>17}" for v in NOMBRES.values()) + f" {'gobierna':>17} {'φRn [kN]':>8}")
    gob = {}
    for n in range(2, 7):
        r = ShearTab(Vu=1.0, n_bolts=n, plate_thickness=9.5, plate_width=75.0).design()
        by = {c["check"]: c["phi_Rn_kN"] for c in r["checks"]}
        cap = min(by.values())
        g = NOMBRES[min(by, key=by.get)]
        gob[n] = g
        print(f"  {n:2d} {r['plate_h_mm']:6.0f} " + " ".join(f"{by[k]:17.1f}" for k in NOMBRES) + f" {g:>17} {cap:8.1f}")
    print("\nComprobación de una viga con Vu = 280 kN y 4 pernos:")
    r = ShearTab(Vu=280.0, n_bolts=4, plate_thickness=9.5, plate_width=75.0).design()
    for c in r["checks"]:
        print(f"  {NOMBRES[c['check']]:17} φRn = {c['phi_Rn_kN']:7.1f} kN → {c['utilization']:.3f} {'cumple' if c['is_ok'] else 'NO cumple'}")
    print(f"  Gobierna {NOMBRES[r['governing_check']]} con {r['governing_utilization']:.3f}: {'cumple' if r['all_checks_ok'] else 'NO cumple'}.")
    t6 = ShearTab(Vu=280.0, n_bolts=4, plate_thickness=6.4, plate_width=75.0).design()
    print(f"  Con chapa de 6,4 mm gobierna {NOMBRES[t6['governing_check']]} con {t6['governing_utilization']:.3f}: {'cumple' if t6['all_checks_ok'] else 'NO cumple'}.")
    r4 = {c["check"]: c["phi_Rn_kN"] for c in r["checks"]}
    second = sorted(r4.values())[1]
    print(f"\nCon la chapa de 9,5 mm gobierna «{gob[2]}» de 2 a 6 pernos; el siguiente estado límite (rotura a cortante) queda un {(second / min(r4.values()) - 1) * 100:.0f} % por encima con 4 pernos. "
          "Al adelgazar la chapa la rotura a cortante pasa delante. "
          "La clase no comprueba la flexión de la chapa ni la excentricidad de los pernos (Manual AISC Parte 10, configuración convencional), "
          "la soldadura al soporte ni el aplastamiento en el alma de la viga, y descuenta agujeros de d + 2 mm (§B4.3b pediría d + 1/8\" en el área neta).")


if __name__ == "__main__":
    main()
