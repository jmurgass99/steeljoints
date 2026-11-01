"""Soldaduras a tope (AISC 360-22 §J2.1 y Tabla J2.5): penetración completa (CJP) de una chapa de 20 × 300 mm a tracción y a cortante, y penetración parcial (PJP) con garganta efectiva según profundidad, ángulo y proceso, indicando si gobierna la soldadura o el metal base.

`cjp_strength(Fy, Fu, área, load)`: la CJP desarrolla el metal base, φRn = mín(0,90·Fy·A, 0,75·Fu·A) a tracción y
0,90·0,6·Fy·A a cortante. `pjp_effective_throat(profundidad, ángulo, proceso)` resta 3 mm con ranura de 45° a 60°
en SMAW/GMAW/FCAW. `pjp_strength(electrodo, E, L, Fy_base, t_base, load)` compara 0,75·0,60·FEXX·E·L con la
fluencia del metal base.

Ejecutar:  python examples/groove_welds_cjp_plate_tension_shear_pjp_effective_throat_angle_and_governing_metal.py
"""
from steeljoints.groove_welds import cjp_strength, pjp_effective_throat, pjp_strength
from steeljoints import groove_welds


def main() -> None:
    t, L, Fy, Fu = 20.0, 300.0, 345.0, 450.0
    A = t * L
    print(f"Chapa de {t:.0f} × {L:.0f} mm, A572 Gr. 50 (Fy = {Fy:.0f}, Fu = {Fu:.0f} MPa), A = {A:.0f} mm²")
    for load in ("tension", "shear"):
        r = cjp_strength(Fy, Fu, A, load)
        print(f"  CJP a {'tracción' if load == 'tension' else 'cortante'}: Rn = {r.Rn_kN:.0f} kN, φRn = {r.Rd_kN:.0f} kN ({r.governs})")
    print(f"  A mano a tracción: mín(0,90·{Fy:.0f}·{A:.0f}, 0,75·{Fu:.0f}·{A:.0f}) = mín({0.9 * Fy * A / 1e3:.0f}, {0.75 * Fu * A / 1e3:.0f}) kN → fluencia")
    print("\nPJP sobre la misma chapa, electrodo E70, L = 300 mm, tracción normal al eje:")
    print(f"  {'prof. [mm]':>10} {'ángulo':>6} {'proceso':>7} {'E [mm]':>6} {'φRn [kN]':>8} {'gobierna':>10}")
    for depth, ang, proc in ((6, 60, "SMAW"), (10, 60, "SMAW"), (10, 45, "SMAW"), (10, 45, "SAW"), (14, 60, "GMAW"), (20, 60, "SMAW")):
        E = pjp_effective_throat(depth, ang, proc)
        r = pjp_strength("E70", E, L, Fy, t, "tension")
        print(f"  {depth:10.0f} {ang:6.0f} {proc:>7} {E:6.1f} {r.Rd_kN:8.0f} {r.governs:>10}")
    try:
        pjp_effective_throat(10, 30, "SMAW")
    except Exception as exc:
        print(f"  Ranura a 30° → {type(exc).__name__}: {exc}")
    fexx_mod = groove_welds._fexx("E70")
    print(f"\nEste módulo usa FEXX = {fexx_mod:.0f} MPa para E70 (el resto del paquete, 482,6 = 70 ksi exactos: {(fexx_mod / 482.6 - 1) * 100:+.1f} %) "
          f"y φ = {groove_welds.PHI_W} para la soldadura en todos los casos. Un informe de investigación de AISC da Ω = 1,88 (φ = 0,80) para PJP a tracción normal al eje, "
          f"así que aquí sale del lado seguro. El cortante CJP usa φ = {groove_welds.PHI_Y} sobre 0,6·Fy; §J4.2 usa φ = 1,00 para la fluencia por cortante (conservador).")


if __name__ == "__main__":
    main()
