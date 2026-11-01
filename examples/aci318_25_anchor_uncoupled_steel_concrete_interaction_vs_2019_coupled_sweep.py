"""Anclaje a hormigón con tracción y cortante combinados: interacción desacoplada acero/hormigón tal como la implementa el módulo de ACI 318-25 (exponente 2 para acero, 5/3 para hormigón) frente a la interacción acoplada de ACI 318-19 (mínimas capacidades con exponente 5/3), barriendo la dirección de la carga.

`aci318_25_anchors.verify_anchor_interaction_aci318_25(Aci318Anchor2025Input(n_ua, v_ua, φNsa, φVsa, φNnc, φVnc))`.
SIN CONTRASTAR con el texto de ACI 318-25: los exponentes son la interpretación del módulo.

Ejecutar:  python examples/aci318_25_anchor_uncoupled_steel_concrete_interaction_vs_2019_coupled_sweep.py
"""
from math import cos, radians, sin

from steeljoints.aci318_25_anchors import Aci318Anchor2025Input, verify_anchor_interaction_aci318_25


def main() -> None:
    cap = dict(phi_n_sa=150.0, phi_v_sa=90.0, phi_n_nc=110.0, phi_v_nc=120.0)
    print("Capacidades de diseño [kN]: acero φNsa 150, φVsa 90; hormigón φNnc 110 (arrancamiento), φVnc 120 (rotura del borde)")
    print("Carga resultante de 80 kN con ángulo θ respecto al eje del anclaje:\n")
    print(f"  {'θ':>3} {'Nua':>6} {'Vua':>6} {'acero':>6} {'hormigón':>8} {'2025':>6} {'modo':>8} {'2019':>6} {'2019/2025':>9}")
    ratios = []
    for th in (0, 15, 30, 45, 60, 75, 90):
        N, V = 80.0 * cos(radians(th)), 80.0 * sin(radians(th))
        r = verify_anchor_interaction_aci318_25(Aci318Anchor2025Input(n_ua=N, v_ua=V, **cap))
        ratios.append(r.legacy_coupled_utilization_2019 / r.governing_utilization_2025)
        print(f"  {th:3d} {N:6.1f} {V:6.1f} {r.steel_interaction:6.3f} {r.concrete_interaction:8.3f} {r.governing_utilization_2025:6.3f} {r.governing_mode:>8} "
              f"{r.legacy_coupled_utilization_2019:6.3f} {r.legacy_coupled_utilization_2019 / r.governing_utilization_2025:9.2f}")
    r = verify_anchor_interaction_aci318_25(Aci318Anchor2025Input(n_ua=-30.0, v_ua=-40.0, **cap))
    print(f"\nCompresión (Nua = −30) y cortante negativo: la tracción se toma como 0 y el cortante en valor absoluto → {r.governing_utilization_2025:.3f} ({r.governing_mode})")
    try:
        verify_anchor_interaction_aci318_25(Aci318Anchor2025Input(n_ua=50.0, v_ua=20.0, phi_n_sa=150.0, phi_v_sa=0.0, phi_n_nc=110.0, phi_v_nc=120.0))
    except ValueError as exc:
        print(f"Capacidad nula → ValueError: {exc}")
    print("\nLa interacción acoplada de 2019 empareja la peor capacidad a tracción con la peor a cortante aunque sean de modos distintos; "
          f"en este barrido da entre {min(ratios):.2f} y {max(ratios):.2f} veces la desacoplada. Comprueba los exponentes con ACI 318-25 §17.8 antes de usarla en proyecto.")


if __name__ == "__main__":
    main()
