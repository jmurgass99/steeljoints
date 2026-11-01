"""Resistencia de un cordón de 8 mm según el ángulo de la carga, de 0° (longitudinal) a 90° (transversal): AISC 360-22 §J2.4 con E70 frente a EN 1993-1-8 §4.5.3 con S355, método direccional y simplificado.

AISC: φRn/mm = 0,75·0,60·FEXX·a·(1 + 0,50·sin^1,5 θ) (`FilletWeld(...).aisc_strength()`).
EC3 direccional (§4.5.3.2): con una fuerza F por mm a θ del eje, en la garganta a 45° σ⊥ = τ⊥ = F·sin θ/(a√2)
y τ∥ = F·cos θ/a; se agota cuando √(σ⊥² + 3(τ⊥² + τ∥²)) = fu/(βw·γM2) (`codes.ec3_1_8.fillet_weld_Rd_directional`).
EC3 simplificado (§4.5.3.3): fvw,d·a con fvw,d = fu/(√3·βw·γM2), independiente de θ.

Ejecutar:  python examples/fillet_weld_directional_strength_0_to_90_deg_aisc_e70_vs_ec3_s355_directional_and_simplified.py
"""
from math import cos, radians, sin, sqrt

from steeljoints import FilletWeld
from steeljoints.codes.ec3_1_8 import beta_w, fillet_weld_Rd_directional, fillet_weld_Rd_simplified


def ec3_directional_per_mm(a: float, fu: float, grade: str, theta_deg: float) -> float:
    s, c = sin(radians(theta_deg)), cos(radians(theta_deg))
    r = fillet_weld_Rd_directional(a, 1.0, fu, grade, sigma_perp=s / (a * sqrt(2)), tau_perp=s / (a * sqrt(2)), tau_par=c / a)
    return 1.0 / r["utilization"]   # fuerza por mm que agota la garganta


def main() -> None:
    w, fu, grade = 8.0, 510.0, "S355"   # fu de S355 con t ≤ 40 mm (EN 1993-1-1 Tabla 3.1)
    a = w / sqrt(2)
    simp = fillet_weld_Rd_simplified(a, 1.0, fu, grade)
    aisc0 = FilletWeld(w, 1.0, "E70", "AISC", theta=0.0).aisc_strength()
    print(f"Cordón de {w:.0f} mm, garganta a = {a:.2f} mm. AISC: E70 (FEXX 482,6 MPa), φ = 0,75. EC3: S355, fu = {fu:.0f} MPa, βw = {beta_w(grade)}, γM2 = 1,25.\n")
    print(f"  {'θ':>3} {'AISC φRn [N/mm]':>15} {'×θ=0':>6} {'EC3 direcc. [N/mm]':>18} {'×simplif.':>9} {'EC3 simplif.':>12}")
    for th in (0, 15, 30, 45, 60, 75, 90):
        aisc = FilletWeld(w, 1.0, "E70", "AISC", theta=float(th)).aisc_strength()
        dirc = ec3_directional_per_mm(a, fu, grade, th)
        print(f"  {th:3d} {aisc:15.0f} {aisc / aisc0:6.3f} {dirc:18.0f} {dirc / simp:9.3f} {simp:12.0f}")
    a90 = FilletWeld(w, 1.0, "E70", "AISC", theta=90.0).aisc_strength() / aisc0
    e90 = ec3_directional_per_mm(a, fu, grade, 90) / simp
    print(f"\nA mano a 90°: AISC 1 + 0,5·1 = 1,5 (función {a90:.3f}); EC3 √(3/2) = {sqrt(1.5):.3f} (función {e90:.3f}).")
    print(f"A 0° el EC3 simplificado y el direccional coinciden ({simp:.0f} N/mm) y quedan un {(simp / aisc0 - 1) * 100:.0f} % por encima del AISC E70 con estos materiales.")
    print(f"\nA 90° el método direccional de EC3 sube un {(e90 - 1) * 100:.0f} % y AISC un {(a90 - 1) * 100:.0f} %. "
          "AISC aplica el aumento completo a un grupo lineal de tamaño uniforme cargado por su centro de gravedad (§J2.4(b)(1)); "
          "si se mezclan cordones longitudinales y transversales, §J2.4(b)(2) limita a máx(Rnwl + Rnwt, 0,85·Rnwl + 1,5·Rnwt) por compatibilidad de deformaciones. "
          "En EC3 el simplificado es siempre seguro.")


if __name__ == "__main__":
    main()
