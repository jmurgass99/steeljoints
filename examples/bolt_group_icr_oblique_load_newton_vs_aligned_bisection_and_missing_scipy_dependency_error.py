"""Centro instantáneo con carga oblicua: el solver de Newton 2D (scipy) para ángulos de 0° a 90°, la bisección 1D exacta cuando la carga es paralela a un eje, y el `DependencyError` que se obtiene sin scipy.

`BoltGroupICR.solve(solver="auto")` usa bisección si la carga va a 0° o 90° y Newton 2D (``scipy.optimize.fsolve``)
en otro caso; `solver="newton2d"` lo fuerza. Sin scipy instalado (extra `numeric`) la carga oblicua lanza
`DependencyError` con la instrucción de instalación en lugar de un `ImportError` crudo.

Ejecutar:  python examples/bolt_group_icr_oblique_load_newton_vs_aligned_bisection_and_missing_scipy_dependency_error.py
"""
import sys

from steeljoints import BoltGroupICR, rectangular_pattern
from steeljoints.exceptions import DependencyError


def main() -> None:
    pos = rectangular_pattern(nx=2, ny=4, sx=90.0, sy=75.0)
    try:
        import scipy  # noqa: F401
        tiene_scipy = True
    except ImportError:
        tiene_scipy = False
    print(f"Grupo 2 × 4 (90 × 75 mm), excentricidad 150 mm, Rult = 1 → C. scipy instalado: {tiene_scipy}\n")
    print("  Ángulo medido desde el eje +Y: 0° es carga vertical, paralela al lado largo del grupo (225 mm); 90° es horizontal.")
    print(f"  {'ángulo':>6} {'C':>7} {'IC x [mm]':>9} {'IC y [mm]':>9} {'solver':>18}")
    Cs = {}
    for ang in (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0):
        try:
            r = BoltGroupICR(positions=pos, Pu_N=1.0, ex_mm=150.0, load_angle_deg=ang, Rult_N=1.0).solve()
            Cs[ang] = r["C_coefficient"]
            print(f"  {ang:6.0f} {r['C_coefficient']:7.3f} {r['IC_x_mm']:9.1f} {r['IC_y_mm']:9.1f} {r['solver']:>18}")
        except DependencyError as exc:
            print(f"  {ang:6.0f} DependencyError: {exc}")
    if tiene_scipy:
        a = BoltGroupICR(positions=pos, Pu_N=1.0, ex_mm=150.0, load_angle_deg=0.0, Rult_N=1.0).solve(solver="bisection")
        b = BoltGroupICR(positions=pos, Pu_N=1.0, ex_mm=150.0, load_angle_deg=0.0, Rult_N=1.0).solve(solver="newton2d")
        print(f"\nCarga vertical: bisección C = {a['C_coefficient']:.4f}, Newton 2D C = {b['C_coefficient']:.4f} ({(b['C_coefficient'] / a['C_coefficient'] - 1) * 100:+.3f} %)")
    real = sys.modules.get("scipy.optimize")
    sys.modules["scipy.optimize"] = None
    try:
        BoltGroupICR(positions=pos, Pu_N=1.0, ex_mm=150.0, load_angle_deg=30.0, Rult_N=1.0).solve()
    except DependencyError as exc:
        print(f"\nSimulando un entorno sin scipy, carga a 30° → {type(exc).__name__}: {exc}")
    finally:
        if real is not None:
            sys.modules["scipy.optimize"] = real
        else:
            sys.modules.pop("scipy.optimize", None)
    r0 = BoltGroupICR(positions=pos, Pu_N=1.0, ex_mm=0.0, load_angle_deg=30.0, Rult_N=1.0).solve()
    print(f"Carga centrada (e = 0): C = {r0['C_coefficient']:.0f} = número de pernos, sin solver ({r0['solver']}).")
    if Cs:
        a_min, a_max = min(Cs, key=Cs.get), max(Cs, key=Cs.get)
        print(f"\nEn este grupo C va de {Cs[a_min]:.3f} a {a_min:.0f}° a {Cs[a_max]:.3f} a {a_max:.0f}° ({(Cs[a_max] / Cs[a_min] - 1) * 100:.1f} % de diferencia): "
              "con la misma excentricidad, la carga paralela al lado largo es la favorable.")
    print("La bisección solo es exacta con la carga paralela a un eje de simetría: por eso con carga oblicua se exige scipy en vez de caer en silencio a un método inexacto.")


if __name__ == "__main__":
    main()
