"""T-stub equivalente de EN 1993-1-8 §6.2.4 (Tabla 6.2) con dos tornillos M20 10.9: modo 1 (rotura completa del ala), modo 2 (ala más tornillos) y modo 3 (tornillos), barrido del espesor del ala y transición entre modos; con el deslizamiento (§3.9) y el punzonamiento (§3.6) de los mismos tornillos.

`codes.ec3_1_8.t_stub_FT_Rd(leff, tp, fy, ΣFt,Rd, n, m)`: Mpl = 0,25·leff·tp²·fy/γM0, F1 = 4·Mpl/m,
F2 = (2·Mpl + n·ΣFt,Rd)/(m + n), F3 = ΣFt,Rd. `slip_resistance_Rd(ks, μ, n, Fp,C)` y `bolt_punching_Rd(dm, tp, fu)`.

Ejecutar:  python examples/ec3_t_stub_three_failure_modes_flange_thickness_sweep_mode_transition_and_slip_punching.py
"""
from math import sqrt

from steeljoints.bolts import bolt_tensile_stress_area
from steeljoints.codes.ec3_1_8 import bolt_punching_Rd, slip_resistance_Rd, t_stub_FT_Rd


def main() -> None:
    As = bolt_tensile_stress_area(20.0)
    Ft = 0.9 * 1000.0 * As / 1.25
    sumFt = 2 * Ft
    leff, m, n, fy = 160.0, 35.0, 43.75, 275.0
    print(f"T-stub de leff = {leff:.0f} mm, m = {m:.0f}, n = {n:.2f} mm (≤ 1,25·m), S275; 2 × M20 10.9: ΣFt,Rd = 2·0,9·1000·{As:.0f}/1,25 = {sumFt / 1e3:.1f} kN\n")
    print(f"  {'tp':>4} {'F1 [kN]':>8} {'F2 [kN]':>8} {'F3 [kN]':>8} {'FT,Rd':>7} {'modo':>7}")
    modos = {}
    for tp in (8.0, 10.0, 12.0, 15.0, 18.0, 20.0, 25.0, 30.0):
        r = t_stub_FT_Rd(leff, tp, fy, sumFt, n, m)
        FT = min(r["F1_Nmm"], r["F2_N"], r["F3_N"])
        modos[tp] = r["governing_mode"]
        print(f"  {tp:4.0f} {r['F1_Nmm'] / 1e3:8.1f} {r['F2_N'] / 1e3:8.1f} {r['F3_N'] / 1e3:8.1f} {FT / 1e3:7.1f} {r['governing_mode']:>7}")
    # Espesores frontera: F1 = F2 y F2 = F3
    t12 = sqrt(m * n * sumFt / ((2 * m + 4 * n) * 0.25 * leff * fy))       # 4Mpl/m = (2Mpl + nΣFt)/(m+n)
    t23 = sqrt((sumFt * (m + n) - n * sumFt) / (2 * 0.25 * leff * fy))     # (2Mpl + nΣFt)/(m+n) = ΣFt
    print(f"\nFronteras: modo 1 → 2 con tp = {t12:.1f} mm; modo 2 → 3 con tp = {t23:.1f} mm.")
    r = t_stub_FT_Rd(leff, 15.0, fy, sumFt, n, m)
    mpl = 0.25 * leff * 15.0 ** 2 * fy
    print(f"A mano con tp = 15: Mpl = 0,25·{leff:.0f}·15²·{fy:.0f} = {mpl / 1e6:.3f} kN·m; F2 = (2·Mpl + {n:.2f}·ΣFt)/({m:.0f} + {n:.2f}) = {(2 * mpl + n * sumFt) / (m + n) / 1e3:.1f} kN (función {r['F2_N'] / 1e3:.1f})")
    FpC = 0.7 * 1000.0 * As
    print("\nLos mismos tornillos pretensados (Fp,C = 0,7·fub·As):")
    for clase, mu in (("A", 0.5), ("B", 0.4), ("C", 0.3), ("D", 0.2)):
        print(f"  superficie clase {clase} (μ = {mu}): Fs,Rd = {slip_resistance_Rd(1.0, mu, 1, FpC) / 1e3:5.1f} kN por tornillo y plano")
    print(f"  Punzonamiento de una chapa de 12 mm (fu 430 MPa) bajo cabeza de M20 (dm ≈ 32,4 mm): Bp,Rd = {bolt_punching_Rd(32.4, 12.0, 430.0) / 1e3:.1f} kN frente a Ft,Rd = {Ft / 1e3:.1f} kN")
    print("\nCon alas finas manda el modo 1 (plastificación completa del ala); al engrosar el ala la rotura pasa a los tornillos con palanca (modo 2) y, con ala gruesa, a los tornillos solos (modo 3). "
          "La clave del modo 1 se llama F1_Nmm pero su valor está en N.")


if __name__ == "__main__":
    main()
