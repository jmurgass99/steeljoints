"""Chapa frontal extendida de 4 pernos (4E, AISC 358 cap. 6) en una viga de 450 mm con Mu = 250 kN·m: tracción y cortante de pernos A325 de 7/8", flexión de la chapa por líneas de fluencia, soldaduras, y barrido del espesor. Muestra también el parámetro Yp que el módulo marca SIN CONTRASTAR frente a la forma habitual de 4E.

`EndPlate(Mu, Vu, beam_depth, beam_tf, beam_bf, bolt_diameter, plate_thickness, plate_width, pfo, pfi, g).design()`:
tracción por perno = Mu/(2·(h0 + h1)), chapa φMn = 0,90·Fy·tp²·Yp, soldadura CJP de alas y filete de alma.

Ejecutar:  python examples/end_plate_4e_extended_aisc358_bolt_tension_plate_yield_line_thickness_sweep_and_flagged_yp.py
"""
from math import sqrt

from steeljoints.end_plate import EndPlate

GEOM = dict(beam_depth=450.0, beam_tf=14.6, beam_bf=190.0, bolt_diameter=22.225, plate_width=230.0, pfo=38.0, pfi=38.0, g=140.0)


def yp_4e_habitual(bp: float, g: float, pfo: float, pfi: float, d: float, tf: float) -> float:
    """Forma habitual de 4E sin rigidizar (AISC 358 Tabla 6.2 / Design Guide 4), escrita aquí para comparar."""
    s = 0.5 * sqrt(bp * g)
    h0 = d - tf / 2 + pfo
    h1 = d - 1.5 * tf - pfi
    return bp / 2 * (h1 * (1 / pfi + 1 / s) + h0 / pfo - 0.5) + 2 / g * h1 * (pfi + s)


def main() -> None:
    r = EndPlate(Mu=250.0, Vu=120.0, plate_thickness=22.0, **GEOM).design()
    print("Viga de 450 × 190 × 14,6 mm, chapa de 230 × 22 mm (Fy 345 MPa), pernos A325 de 7/8\", pfo = pfi = 38 mm, gramil 140 mm:")
    for c in r["checks"]:
        print(f"  {c['check']:32} utilización {c['utilization']:.3f} {'cumple' if c['is_ok'] else 'NO cumple'}")
    print(f"  Gobierna: {r['governing_check']} ({r['governing_utilization']:.3f})")
    t_dem = next(c for c in r["checks"] if c["check"] == "Bolt tension")
    h0 = 450.0 - 14.6 / 2 + 38.0
    h1 = 450.0 - 1.5 * 14.6 - 38.0
    print(f"  A mano: T = Mu/(2·(h0 + h1)) = 250e3/(2·({h0:.1f} + {h1:.1f})) = {250e3 / (2 * (h0 + h1)):.1f} kN (función {t_dem['T_demand_kN']:.1f})")

    plate = next(c for c in r["checks"] if c["check"] == "End plate flexure")
    yp_hab = yp_4e_habitual(230.0, 140.0, 38.0, 38.0, 450.0, 14.6)
    print(f"\nYp del módulo = {plate['Yp_mm']:.0f} mm; forma habitual de 4E = {yp_hab:.0f} mm ({(plate['Yp_mm'] / yp_hab - 1) * 100:+.0f} %).")
    print(f"  {'tp [mm]':>7} {'φMn módulo':>10} {'φMn Yp habitual':>15} {'gobierna':>32} {'util.':>6}")
    for tp in (14.0, 16.0, 19.0, 22.0, 25.0):
        d = EndPlate(Mu=250.0, Vu=120.0, plate_thickness=tp, **GEOM).design()
        pl = next(c for c in d["checks"] if c["check"] == "End plate flexure")
        hab = 0.90 * 345.0 * tp ** 2 * yp_hab / 1e6
        print(f"  {tp:7.1f} {pl['phi_Mn_kNm']:10.1f} {hab:15.1f} {d['governing_check']:>32} {d['governing_utilization']:6.3f}")
    tp_req_mod = sqrt(250e6 / (0.90 * 345.0 * plate["Yp_mm"]))
    tp_req_hab = sqrt(250e6 / (0.90 * 345.0 * yp_hab))
    print(f"\nEspesor necesario para 250 kN·m: {tp_req_mod:.1f} mm con el Yp del módulo y {tp_req_hab:.1f} mm con la forma habitual.")
    print("El Yp del módulo incluye términos que la forma habitual de 4E no tiene y no se ha podido contrastar con AISC 358; hasta resolverlo, "
          "dimensiona la chapa con el mayor de los dos espesores. La comprobación sísmica (seismic=True con Zx y Ry) usa Mpr en lugar de Mu.")


if __name__ == "__main__":
    main()
