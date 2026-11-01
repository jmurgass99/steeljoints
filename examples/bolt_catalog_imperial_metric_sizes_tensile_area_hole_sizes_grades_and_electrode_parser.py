"""Catálogo de tornillos y electrodos: tamaños imperiales y métricos con área nominal y resistente, agujeros estándar y sobredimensionados de AISC Tabla J3.3, grados AISC y EC3, y el lector tolerante de designaciones de electrodo AWS.

`catalog.get_bolt_size("3/4" | "M20")` devuelve d, As y Ab; `get_bolt_grade(grado, código)` las resistencias;
`standard_hole` / `oversized_hole` el agujero; `get_electrode_FEXX` acepta «E70XX», «E7018», «E70T-1», «70 ksi»,
«480 MPa» o un número.

Ejecutar:  python examples/bolt_catalog_imperial_metric_sizes_tensile_area_hole_sizes_grades_and_electrode_parser.py
"""
from steeljoints import catalog
from steeljoints.bolts import bolt_tensile_stress_area


def main() -> None:
    print(f"  {'tamaño':7} {'d [mm]':>7} {'Ab [mm²]':>8} {'As [mm²]':>8} {'As/Ab':>6} {'agujero est.':>12} {'sobredim.':>9}")
    for name in list(catalog.BOLT_SIZES_IMPERIAL)[:6] + list(catalog.BOLT_SIZES_METRIC):
        s = catalog.get_bolt_size(name)
        print(f"  {name:7} {s['d_mm']:7.2f} {s['Ab_mm2']:8.1f} {s['As_mm2']:8.1f} {s['As_mm2'] / s['Ab_mm2']:6.3f} {catalog.standard_hole(s['d_mm']):12.1f} {catalog.oversized_hole(s['d_mm']):9.1f}")
    print(f"\n  As fuera de catálogo por ISO 898-1, π/4·(d − 0,9382·P)²: M33 → {bolt_tensile_stress_area(33.0):.0f} mm², M36 → {bolt_tensile_stress_area(36.0):.0f} mm² (tablas ISO: 694 y 817)")
    print("\nGrados AISC 360-22 Tabla J3.2 [MPa]: " + "; ".join(f"{g}: Fnt {d['Fnt']:.0f}, Fnv-N {d['Fnv_N']:.0f}, Fnv-X {d['Fnv_X']:.0f}" for g, d in catalog.AISC_BOLT_GRADES.items()))
    print("Clases EN ISO 898-1 (EC3 Tabla 3.1) [MPa]: " + "; ".join(f"{g}: fyb {d['fyb']:.0f}, fub {d['fub']:.0f}, αv {d['alpha_v']}" for g, d in catalog.EC3_BOLT_GRADES.items()))
    print("\nLector de electrodos (FEXX en MPa):")
    for e in ("E70XX", "E7018", "E70T-1", "E80", "70 ksi", "FEXX=90", "480 MPa", 70, 482.6, "E110XX"):
        print(f"  {e!r:12} → {catalog.get_electrode_FEXX(e):6.1f}")
    try:
        catalog.get_electrode_FEXX("acero")
    except KeyError as exc:
        print(f"  'acero'      → KeyError: {exc}")
    try:
        catalog.get_bolt_size("M21")
    except KeyError as exc:
        print(f"\nTamaño inexistente → KeyError: {str(exc)[:80]}…")
    print("\nAs/Ab ronda 0,75–0,78: por eso EN 1993-1-8 usa As cuando la rosca está en el plano de corte y en tracción, y AISC lo incorpora en Fnt y en Fnv-N. "
          "El agujero estándar sale de AISC 360-22 Tabla J3.3 (d + 1/16\" por debajo de 1\", d + 1/8\" desde 1\") y de la Tabla J3.3M para métricos (M24 → 27 mm); "
          "EN 1090-2 usa otras holguras (1/2/3 mm, ver bolts.ec3_normal_hole_clearance). La columna de sobredimensionados no está contrastada con la tabla.")


if __name__ == "__main__":
    main()
