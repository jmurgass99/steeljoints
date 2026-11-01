"""Cortante en una dirección de una zapata o encepado de hormigón sin armadura de cortante: factor de efecto de tamaño λs = √(2/(1 + 0,004·d)) ≤ 1 (ACI 318-19 y 318-25, Tabla 22.5.5.1), barrido del canto, cuantía, y el multiplicador por efecto arco en vanos cortos que el módulo añade sin contrastar.

`aci318_25_anchors.compute_size_effect_lambda_s(d)` y `verify_deep_shear_aci318_25(Aci318DeepShear2025Input(bw, d, f′c, Vu, a_v, ρw))`:
τc = 0,66·λ·λs·ρw^(1/3)·√f′c (√f′c ≤ 8,3 MPa), φ = 0,75.

Ejecutar:  python examples/aci318_one_way_shear_size_effect_lambda_s_depth_sweep_and_short_span_arching_unverified.py
"""
from math import sqrt

from steeljoints.aci318_25_anchors import Aci318DeepShear2025Input, compute_size_effect_lambda_s, verify_deep_shear_aci318_25


def main() -> None:
    print("Zapata de 1000 mm de ancho, f′c = 28 MPa, ρw = 0,4 %, sin armadura de cortante:\n")
    print(f"  {'d [mm]':>6} {'λs':>6} {'τc [MPa]':>8} {'φVc [kN]':>9} {'φVc/d [kN/mm]':>13}")
    for d in (250, 500, 750, 1000, 1500, 2000):
        r = verify_deep_shear_aci318_25(Aci318DeepShear2025Input(bw=1000.0, d=float(d), fc=28.0, v_u=0.0, rho_w=0.004))
        tau = r.vc_nominal * 1e3 / (1000.0 * d)
        print(f"  {d:6d} {r.lambda_s:6.3f} {tau:8.3f} {r.phi_vc:9.1f} {r.phi_vc / d:13.3f}")
    d = 1000.0
    print(f"\nA mano con d = 1000: λs = √(2/(1 + 4)) = {sqrt(2 / 5):.3f} (función {compute_size_effect_lambda_s(d):.3f}); "
          f"τc = 0,66·{sqrt(2 / 5):.3f}·0,004^(1/3)·√28 = {0.66 * sqrt(2 / 5) * 0.004 ** (1 / 3) * sqrt(28):.3f} MPa")
    print("\nCuantía (d = 1000 mm):")
    for rho in (0.002, 0.004, 0.008, 0.015):
        r = verify_deep_shear_aci318_25(Aci318DeepShear2025Input(bw=1000.0, d=1000.0, fc=28.0, v_u=0.0, rho_w=rho))
        print(f"  ρw = {rho * 100:.1f} % → φVc = {r.phi_vc:.1f} kN")
    print("\nVano de cortante corto (a_v/d < 2), Vu = 1500 kN, d = 1000 mm:")
    for av in (None, 2500.0, 1500.0, 1000.0, 500.0):
        r = verify_deep_shear_aci318_25(Aci318DeepShear2025Input(bw=1000.0, d=1000.0, fc=28.0, v_u=1500.0, rho_w=0.004, a_v=av))
        txt = "sin a_v" if av is None else f"a_v/d = {av / 1000:.1f}"
        print(f"  {txt:12} → multiplicador {r.arching_multiplier:.2f}, φVc = {r.phi_vc:7.1f} kN, utilización {r.utilization:.2f} {'cumple' if r.passes else 'NO cumple'}")
    print("\nλs reduce la resistencia de los cantos grandes: a 2 m la tensión resistente es un "
          f"{(1 - compute_size_effect_lambda_s(2000) / compute_size_effect_lambda_s(250)) * 100:.0f} % menor que a 250 mm. "
          "El multiplicador por efecto arco (hasta 2,5) es la interpretación del módulo y no está contrastado con ACI 318-25 §13.4: no lo uses para verificar un encepado.")


if __name__ == "__main__":
    main()
