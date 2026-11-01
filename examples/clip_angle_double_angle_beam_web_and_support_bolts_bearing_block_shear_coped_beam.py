"""Unión a cortante con doble angular (2L 100 × 100 × 9,5, A36) y tres pernos A325-N de 3/4" en el alma de una viga despatinada: pernos a doble cortante en el alma y a cortante simple en el soporte, aplastamiento, fluencia y rotura de los angulares y bloque de cortante en angulares y en el alma.

`ClipAngle(Vu, n_bolts, bolt_diameter, angle_thickness, angle_leg, beam_tw, Fy/Fu_angle, Fy/Fu_beam,
beam_gage_to_edge).design()` (AISC 360-22 + Manual Parte 10). Se contrasta con el servicio provisional
`services.clip_angle.design_clip_angle`, que solo hace fluencia bruta.

Ejecutar:  python examples/clip_angle_double_angle_beam_web_and_support_bolts_bearing_block_shear_coped_beam.py
"""
from steeljoints.clip_angle import ClipAngle
from steeljoints.services.clip_angle import ClipAngleInput, design_clip_angle


def main() -> None:
    Vu = 250.0
    r = ClipAngle(Vu=Vu, n_bolts=3, beam_tw=8.0).design()
    print(f"Vu = {Vu:.0f} kN, 3 pernos a 75 mm, angulares de 9,5 mm, alma de 8 mm (A572 Gr. 50), gramil al borde del alma 35 mm:")
    for c in r["checks"]:
        print(f"  {c['check']:46} φRn = {c['phi_Rn_kN']:7.1f} kN → {c['utilization']:.3f} {'cumple' if c['is_ok'] else 'NO cumple'}")
    print(f"  Gobierna: {r['governing_check']} ({r['governing_utilization']:.3f})\n")
    print("Espesor del alma de la viga:")
    gov_tw = {}
    for tw in (5.0, 6.5, 8.0, 10.0, 12.0, 14.0, 16.0):
        d = ClipAngle(Vu=Vu, n_bolts=3, beam_tw=tw).design()
        gov_tw[tw] = d["governing_check"]
        print(f"  tw = {tw:4.1f} mm → gobierna {d['governing_check']:46} {d['governing_utilization']:.3f}")
    print("\nNúmero de pernos con alma de 8 mm:")
    for n in (2, 3, 4, 5):
        d = ClipAngle(Vu=Vu, n_bolts=n, beam_tw=8.0).design()
        cap = min(c["phi_Rn_kN"] for c in d["checks"])
        print(f"  n = {n} → altura de angular {d['angle_h_mm']:.0f} mm, φRn = {cap:6.1f} kN ({d['governing_check']})")
    s = design_clip_angle(ClipAngleInput(leg_a_mm=100, leg_b_mm=100, thickness_mm=9.5, Vu_kN=Vu))
    full = min(c["phi_Rn_kN"] for c in r["checks"])
    print(f"\nServicio provisional: Rn = {s.Rn_kN:.1f} kN, DCR = {s.DCR:.2f} frente a {r['governing_utilization']:.2f} de la clase completa ({full:.1f} kN).")
    print(f"  Nota del servicio: {s.notes[-1]}")
    cambio = next((tw for tw, g in gov_tw.items() if g != gov_tw[5.0]), None)
    print(f"\nHasta un alma de {max(t for t, g in gov_tw.items() if g == gov_tw[5.0]):.0f} mm manda «{gov_tw[5.0]}»"
          + (f"; desde {cambio:.0f} mm pasa a mandar «{gov_tw[cambio]}»." if cambio else ".")
          + " El servicio ignora pernos, aplastamiento y bloque: úsalo solo como orden de magnitud.")


if __name__ == "__main__":
    main()
