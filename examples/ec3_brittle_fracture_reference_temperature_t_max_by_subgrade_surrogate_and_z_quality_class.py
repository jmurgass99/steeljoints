"""Elección del acero frente a rotura frágil y desgarro laminar (EN 1993-1-10): temperatura de referencia del detalle, espesor máximo admisible por subgrado (JR, J0, J2, K2) y tensión, y clase de calidad Z de EN 10164 según la demanda Z_Ed.

`ec3_fracture.reference_temperature(T_md, T_r, …)` suma las contribuciones de §2.2(5); `t_max_brittle_fracture(T_Ed,
σEd, fy(t), steel_grade, subgrade)` es un SUSTITUTO PARAMÉTRICO continuo ajustado a la Tabla 2.1 (no la tabla), y
`Z_property_required(Z_Ed, conditions)` sigue la Tabla 3.2 (≤ 10 nada, Z15, Z25, Z35).

Ejecutar:  python examples/ec3_brittle_fracture_reference_temperature_t_max_by_subgrade_surrogate_and_z_quality_class.py
"""
from steeljoints.ec3_fracture import Z_property_required, reference_temperature, t_max_brittle_fracture


def main() -> None:
    T_Ed = reference_temperature(T_md=-20.0, T_r=-5.0)
    print(f"Temperatura de referencia: T_md = −20 °C (mínima del aire) + ΔT_r = −5 (radiación) = {T_Ed:.0f} °C\n")
    print("Espesor máximo [mm] de S355 según subgrado y nivel de tensión σEd/fy(t) (sustituto de la Tabla 2.1):")
    print(f"  {'subgrado':8} " + " ".join(f"{s:>8}" for s in ("0,25·fy", "0,50·fy", "0,75·fy")))
    for sg in ("JR", "J0", "J2", "K2", "ML"):
        vals = [t_max_brittle_fracture(T_Ed, k * 355.0, 355.0, steel_grade="S355", subgrade=sg) for k in (0.25, 0.50, 0.75)]
        print(f"  S355{sg:4} " + " ".join(f"{v:8.0f}" for v in vals))
    print("\nTemperatura de servicio (S355J2, σEd = 0,75·fy):")
    for T in (10.0, -10.0, -30.0, -50.0):
        print(f"  T_Ed = {T:5.0f} °C → t_max = {t_max_brittle_fracture(T, 0.75 * 355.0, 355.0, subgrade='J2'):5.0f} mm")
    print("\nGrado, mismo subgrado J2, T_Ed = −25 °C, σEd = 0,75·fy:")
    for g, fy in (("S235", 235.0), ("S275", 275.0), ("S355", 355.0), ("S460", 460.0)):
        print(f"  {g}J2 → {t_max_brittle_fracture(-25.0, 0.75 * fy, fy, steel_grade=g + 'J2'):5.0f} mm")
    print("\nDesgarro laminar: clase Z según Z_Ed = Za + Zb + Zc + Zd + Ze (Tabla 3.2):")
    casos = (("ala de 20 mm, cordón 5 mm, sin coacción", {"Za": 0, "Zb": 3, "Zc": 2, "Zd": 0}),
             ("chapa de 40 mm en T, cordón 10 mm", {"Za": 6, "Zb": 5, "Zc": 4, "Zd": 3}),
             ("chapa de 60 mm en cruz, cordón 20 mm, coacción alta", {"Za": 12, "Zb": 8, "Zc": 6, "Zd": 5}),
             ("igual, con precalentamiento", {"Za": 12, "Zb": 8, "Zc": 6, "Zd": 5, "Ze": -8}))
    for txt, c in casos:
        print(f"  {txt:52} Z_Ed = {sum(c.values()):3d} → {Z_property_required(0.0, c)}")
    try:
        t_max_brittle_fracture(-20.0, 200.0, 355.0, subgrade="X9")
    except ValueError as exc:
        print(f"\nSubgrado inexistente → ValueError: {exc}")
    print("Las contribuciones Za…Ze de la tabla son datos de ejemplo; tómalas de la Tabla 3.2 para tu detalle. "
          "El espesor máximo sale de un ajuste continuo con anclas en −10 °C y 0,75·fy: para proyecto, lee la Tabla 2.1.")


if __name__ == "__main__":
    main()
