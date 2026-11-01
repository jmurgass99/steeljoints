"""Tamaño mínimo y máximo de un cordón (AISC 360-22 Tabla J2.4 y §J2.2b) y cómo se comporta el paquete cuando falta un dato: la capacidad ausente sale como NO_CALCULADO con utilización infinita y un grado de acero desconocido se rechaza, nunca se aprueba por omisión.

`FilletWeld.min_size(t_thinner)` y `max_size(t_edge)`; `WeldGroup.utilization` y `WeldGroupElastic.utilization`
con capacidad nula; `FilletWeld.ec3_strength` y `codes.ec3_1_8.beta_w` con un grado fuera de la Tabla 4.1.

Ejecutar:  python examples/fillet_weld_min_max_leg_size_and_missing_capacity_unknown_grade_propagated_never_as_pass.py
"""
from steeljoints import FilletWeld, WeldGroup
from steeljoints.codes.ec3_1_8 import beta_w
from steeljoints.weld_group import WeldGroupElastic, WeldSegment


def main() -> None:
    w = FilletWeld(6.0, 100.0)
    print("Tamaño mínimo por la chapa más delgada (Tabla J2.4):")
    for t in (5.0, 6.35, 10.0, 16.0, 19.05, 25.0):
        m = w.min_size(t_thinner=t)
        print(f"  t = {t:5.2f} mm → w_min = {m:5.2f} mm ({m / (25.4 / 16):.1f}/16\")")
    print("\nTamaño máximo en el borde de una chapa (§J2.2b: t si t < 1/4\", t − 1/16\" si no):")
    for t in (5.0, 6.35, 10.0, 20.0):
        norma = t if t < 6.35 else t - 25.4 / 16
        print(f"  t = {t:5.2f} mm → función {w.max_size(t):5.2f} mm; norma {norma:5.2f} mm")
    print("  La función resta 2 mm en vez de 1/16\" (1,6 mm): 0,4 mm del lado seguro.")

    print("\nDatos ausentes:")
    g = WeldGroup(welds=[FilletWeld(8.0, 200.0), FilletWeld(8.0, 200.0)], positions=[(0.0, -100.0), (0.0, 100.0)])
    r = g.utilization(Vu=200e3, Mu=10e6, phi_Rn_per_unit=0.0)
    print(f"  WeldGroup sin capacidad: utilización {r['utilization']}, is_ok {r['is_ok']}, {r['status'].value}, falta {r['missing_inputs']}, demanda {r['max_stress_N_mm2']:.1f} N/mm² (se publica)")
    r = g.utilization(Vu=200e3, Mu=10e6, phi_Rn_per_unit=1228.5)
    print(f"  WeldGroup con capacidad 1228,5 N/mm: utilización {r['utilization']:.3f}, {r['status'].value}")
    e = WeldGroupElastic(segments=[WeldSegment(0.0, -100.0, 0.0, 100.0, 8.0)], Vy=-200e3, Mz=10e6).utilization(FEXX_MPa=0.0, w_mm=8.0)
    print(f"  WeldGroupElastic con FEXX = 0: utilización {e['utilization']}, is_ok {e['is_ok']}")
    for grade in ("S355", "S355J2", "S690", ""):
        try:
            fw = FilletWeld(8.0, 100.0, code="EC3", steel_grade=grade).ec3_strength(fu=510.0)
            print(f"  FilletWeld EC3 grado {grade!r}: Fw,Rd = {fw / 1e3:.1f} kN")
        except ValueError as exc:
            print(f"  FilletWeld EC3 grado {grade!r}: ValueError: {str(exc)[:90]}…")
    print(f"  codes.ec3_1_8.beta_w('S355J2') = {beta_w('S355J2')}; 'S690' → ", end="")
    try:
        beta_w("S690")
    except ValueError:
        print("ValueError (EN 1993-1-8:2005 Tabla 4.1 llega a S460)")
    print("\nUn cero de capacidad leído como «utilización 0» aprobaría la unión; aquí la ausencia se propaga como ausencia. "
          "FilletWeld exige el grado exacto de la tabla y beta_w() acepta sufijos de calidad (J2, JR, N…).")


if __name__ == "__main__":
    main()
