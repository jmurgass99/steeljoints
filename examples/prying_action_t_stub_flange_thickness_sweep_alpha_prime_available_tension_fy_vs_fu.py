"""Efecto palanca en un T-stub atornillado (AISC Manual Parte 9): barrido del espesor del ala, espesor t_c sin palanca, α′ y tracción disponible por perno, con Fy (conservador) y con Fu (Manual 13.ª ed. en adelante).

`prying_capacity(PryingInput(B_kN, b, a, p, t, d, Fy, Fu=None))`: b′ = b − d/2, a′ = mín(a, 1,25b) + d/2,
ρ = b′/a′, δ = 1 − d′/p, t_c = √(4·B·b′/(φ·p·F)) con φ = 0,90, α′ = ((t_c/t)² − 1)/(δ(1 + ρ)) acotado a
[0, 1] y T_disp = B·(t/t_c)²·(1 + δ·α′) ≤ B.

Ejecutar:  python examples/prying_action_t_stub_flange_thickness_sweep_alpha_prime_available_tension_fy_vs_fu.py
"""
import math

from steeljoints import Bolt
from steeljoints.prying import PryingInput, prying_capacity


def main() -> None:
    B = Bolt(22.225, "A325", "AISC").aisc_tension_strength() / 1e3
    base = dict(B_kN=B, b_mm=45.0, a_mm=40.0, p_mm=90.0, d_mm=22.225, Fy_MPa=345.0)
    print(f"Perno A325 de 7/8\": B = φRnt = {B:.1f} kN; ala con b = 45 mm, a = 40 mm, p = 90 mm por perno, Fy = 345 / Fu = 450 MPa")
    r0 = prying_capacity(PryingInput(t_mm=20.0, **base))
    bp = 45.0 - 22.225 / 2
    print(f"  b′ = {bp:.2f} mm, ρ = {r0.rho:.3f}, δ = {r0.delta:.3f}; t_c(Fy) = √(4·{B:.1f}e3·{bp:.2f}/(0,9·90·345)) = {math.sqrt(4 * B * 1e3 * bp / (0.9 * 90 * 345)):.1f} mm\n")
    print(f"  {'t [mm]':>6} {'t_c Fy':>7} {'α′':>6} {'T_disp Fy':>9} {'t_c Fu':>7} {'α′':>6} {'T_disp Fu':>9} {'palanca':>8}")
    for t in (10.0, 12.0, 14.0, 16.0, 19.0, 22.0, 25.0, 28.0):
        a = prying_capacity(PryingInput(t_mm=t, **base))
        b = prying_capacity(PryingInput(t_mm=t, Fu_MPa=450.0, **base))
        print(f"  {t:6.1f} {a.t_c_mm:7.1f} {a.alpha_prime:6.3f} {a.T_avail_kN:9.1f} {b.t_c_mm:7.1f} {b.alpha_prime:6.3f} {b.T_avail_kN:9.1f} {'sí' if b.prying_governs else 'no':>8}")
    t_ok = next(t for t in [x * 0.5 for x in range(10, 80)] if prying_capacity(PryingInput(t_mm=t, Fu_MPa=450.0, **base)).T_avail_kN >= 0.999 * B)
    print(f"\nCon Fu, el ala de {t_ok:.1f} mm ya deja al perno trabajar a su resistencia completa (t ≥ t_c = {prying_capacity(PryingInput(t_mm=20, Fu_MPa=450.0, **base)).t_c_mm:.1f} mm).")
    tc_fy = prying_capacity(PryingInput(t_mm=20.0, **base)).t_c_mm
    tc_fu = prying_capacity(PryingInput(t_mm=20.0, Fu_MPa=450.0, **base)).t_c_mm
    print("Por debajo de t_c la palanca reduce la tracción útil del perno; con alas finas α′ = 1 y la reducción es la de flexión del ala. "
          f"El Manual usa Fu en t_c desde la 13.ª edición; sin Fu_MPa el módulo usa Fy y sale conservador (t_c un {(tc_fy / tc_fu - 1) * 100:.0f} % mayor).")


if __name__ == "__main__":
    main()
