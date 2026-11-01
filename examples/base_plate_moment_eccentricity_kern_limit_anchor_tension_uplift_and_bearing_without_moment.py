"""Placa base de 450 × 550 mm con 800 kN de compresión y momento creciente: límite del núcleo central (e = N/6), tracción en los anclajes, levantamiento con axil de tracción, y la limitación del módulo, que calcula el aplastamiento y el espesor sin el momento.

`BasePlate(Pu, Mu, ...).anchor_tension()` usa un modelo lineal propio: T = (|Mu| − (N/6)·Pu)/(N/2 − N/6) repartido
entre `n_anchors`, φRnt = 0,75·0,75·Fut·Ab. `bearing_check` y `required_thickness` usan Pu/(B·N) uniforme.
Para comparar, el caso aplica Design Guide 1 §3.4 con bloque rectangular: fp,max = 0,65·0,85·f′c, q = fp,max·B,
e_crit = N/2 − Pu/(2q); si e ≤ e_crit, Y = N − 2e y fp = Pu/(B·Y) sin tracción; si no, fp = fp,max,
Y = (f + N/2) − √((f + N/2)² − 2·Pu·(e + f)/q) y T = q·Y − Pu, con f la distancia de los anclajes al eje.

Ejecutar:  python examples/base_plate_moment_eccentricity_kern_limit_anchor_tension_uplift_and_bearing_without_moment.py
"""
from steeljoints import BasePlate

GEOM = dict(column_d=310.0, column_bf=305.0, plate_B=450.0, plate_N=550.0, plate_Fy=250.0, fc_concrete=28.0, n_anchors=2, anchor_diameter=25.4, anchor_Fut=400.0)


def dg1_rectangular(Pu_kN: float, Mu_kNm: float, B: float, N: float, fc: float, f: float) -> tuple[float, float]:
    """Design Guide 1 (3.ª ed.) §3.4, bloque rectangular: (fp [MPa], T total en anclajes [kN])."""
    from math import sqrt
    fpmax = 0.65 * 0.85 * fc
    q = fpmax * B
    P = Pu_kN * 1e3
    e = Mu_kNm * 1e6 / P
    e_crit = N / 2 - P / (2 * q)
    if e <= e_crit:
        return P / (B * (N - 2 * e)), 0.0
    disc = (f + N / 2) ** 2 - 2 * P * (e + f) / q
    if disc < 0:
        return float("nan"), float("nan")   # la placa no puede equilibrar: agrandarla
    Y = (f + N / 2) - sqrt(disc)
    return fpmax, (q * Y - P) / 1e3


def main() -> None:
    Pu, N, B = 800.0, 550.0, 450.0
    print(f"Pu = {Pu:.0f} kN, placa {B:.0f} × {N:.0f} mm, 2 anclajes F1554 Gr. 36 de 1\" por lado (Fut 400 MPa). Núcleo central: e ≤ N/6 = {N / 6:.0f} mm\n")
    f_anc = N / 2 - 50.0   # anclajes a 50 mm del borde
    e_crit = N / 2 - Pu * 1e3 / (2 * 0.65 * 0.85 * 28.0 * B)
    print(f"DG1: fp,max = 0,65·0,85·28 = {0.65 * 0.85 * 28:.2f} MPa, e_crit = {e_crit:.0f} mm; anclajes a f = {f_anc:.0f} mm del eje.\n")
    print(f"  {'Mu':>5} {'e [mm]':>6} {'fp módulo':>9} {'fp DG1':>7} {'T/ancl. módulo':>14} {'T/ancl. DG1':>11} {'φRnt':>6}")
    filas = []
    for Mu in (0.0, 40.0, 73.0, 120.0, 175.0, 200.0, 280.0):
        bp = BasePlate(Pu=Pu, Mu=Mu, **GEOM)
        e = Mu * 1e3 / Pu
        fp_mod = bp.bearing_check()["fp_MPa"]
        fp_dg1, T_dg1 = dg1_rectangular(Pu, Mu, B, N, 28.0, f_anc)
        a = bp.anchor_tension()
        filas.append((e, fp_mod, fp_dg1, a["T_per_bolt_kN"], T_dg1 / 2))
        phi = "—" if a["phi_Rnt_kN"] is None else f"{a['phi_Rnt_kN']:.1f}"
        print(f"  {Mu:5.0f} {e:6.0f} {fp_mod:9.2f} {fp_dg1:7.2f} {a['T_per_bolt_kN']:14.1f} {T_dg1 / 2:11.1f} {phi:>6}")
    lev = BasePlate(Pu=-150.0, Mu=60.0, **GEOM)
    a = lev.anchor_tension()
    t = lev.required_thickness()
    r = lev.design()
    print(f"\nLevantamiento (Pu = −150 kN, Mu = 60 kN·m): T = {a['T_per_bolt_kN']:.1f} kN por anclaje ({a['note']}), utilización {a['utilization']:.2f}")
    print(f"  Espesor: {t['tp_required_mm']} — {t['motivo_no_evaluado']}")
    print(f"  Informe: {r['summary']} (gobierna {r['governing_check']})")
    e150 = next(r for r in filas if abs(r[0] - 150) < 1)
    e350 = filas[-1]
    print(f"\nCon momento el módulo deja fp en Pu/(B·N): con e = 150 mm la presión de DG1 es un {(e150[2] / e150[1] - 1) * 100:.0f} % mayor (del lado inseguro). "
          f"Su modelo de anclajes va al revés: con e = 150 mm pide {e150[3]:.0f} kN por anclaje donde DG1 no pide ninguno, y con e = 350 mm pide {e350[3]:.0f} kN frente a {e350[4]:.0f} kN. "
          "Úsalo con compresión centrada; con momento calcula aplastamiento, espesor y anclajes con DG1 §3.4.")


if __name__ == "__main__":
    main()
