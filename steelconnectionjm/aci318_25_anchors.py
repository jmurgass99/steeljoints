"""ACI 318-25 Chapter 17 Uncoupled Anchor Interaction & Deep Footing Shear Size/Arching Effects.

Implements the structural code updates introduced in ACI 318-25:
  1. Uncoupled tension-shear anchor interaction (ACI 318-25 Ch. 17):
     - Steel failure interaction with exponent 2.0:
       ``(N_ua / phi_N_sa)^2 + (V_ua / phi_V_sa)^2 <= 1.0``
     - Concrete failure interaction (breakout/pullout/pryout) with exponent 5/3:
       ``(N_ua / phi_N_nc)^(5/3) + (V_ua / phi_V_nc)^(5/3) <= 1.0``
     Compared against the legacy coupled ACI 318-19 interaction where the minimum across
     steel and concrete modes was combined in a single equation.
  2. One-way shear with size-effect factor ``lambda_s`` and arching-action multiplier for
     deep footings / pile caps (shear span ``a_v / d < 2.0``).

All public dataclasses declare ``units`` explicitly and avoid unit-suffixed field names.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Aci318Anchor2025Input:
    """Input for ACI 318-25 Chapter 17 uncoupled anchor tension-shear interaction check.

    Units: forces in kN.
    """

    n_ua: float
    v_ua: float
    phi_n_sa: float
    phi_v_sa: float
    phi_n_nc: float
    phi_v_nc: float
    units: str = "SI_kN"


@dataclass(frozen=True)
class Aci318Anchor2025Result:
    """Result of ACI 318-25 Chapter 17 uncoupled anchor interaction vs ACI 318-19 coupled check."""

    steel_interaction: float
    concrete_interaction: float
    governing_utilization_2025: float
    legacy_coupled_utilization_2019: float
    governing_mode: str
    passes: bool
    status: str = "CALCULADO"
    clause: str = "ACI 318-25 Ch. 17 (Uncoupled Steel/Concrete Interaction)"
    units: str = "SI_kN"


def verify_anchor_interaction_aci318_25(inp: Aci318Anchor2025Input) -> Aci318Anchor2025Result:
    """Evaluate ACI 318-25 uncoupled anchor interaction and compare with ACI 318-19."""
    if inp.phi_n_sa <= 0.0 or inp.phi_v_sa <= 0.0 or inp.phi_n_nc <= 0.0 or inp.phi_v_nc <= 0.0:
        raise ValueError("All design capacities (phi * Nn, phi * Vn) must be strictly positive.")

    n_u = max(0.0, float(inp.n_ua))
    v_u = abs(float(inp.v_ua))

    # 1. Steel failure mode interaction (elliptical exponent = 2.0)
    ratio_ns = n_u / inp.phi_n_sa
    ratio_vs = v_u / inp.phi_v_sa
    eta_steel = (ratio_ns**2) + (ratio_vs**2)

    # 2. Concrete failure mode interaction (exponent = 5/3)
    ratio_nc = n_u / inp.phi_n_nc
    ratio_vc = v_u / inp.phi_v_nc
    eta_concrete = (ratio_nc ** (5.0 / 3.0)) + (ratio_vc ** (5.0 / 3.0))

    gov_2025 = max(eta_steel, eta_concrete)
    gov_mode = "steel" if eta_steel >= eta_concrete else "concrete"

    # Legacy ACI 318-19 coupled interaction (minimum N capacity paired with minimum V capacity)
    phi_n_min = min(inp.phi_n_sa, inp.phi_n_nc)
    phi_v_min = min(inp.phi_v_sa, inp.phi_v_nc)
    eta_2019 = ((n_u / phi_n_min) ** (5.0 / 3.0)) + ((v_u / phi_v_min) ** (5.0 / 3.0))

    return Aci318Anchor2025Result(
        steel_interaction=round(eta_steel, 4),
        concrete_interaction=round(eta_concrete, 4),
        governing_utilization_2025=round(gov_2025, 4),
        legacy_coupled_utilization_2019=round(eta_2019, 4),
        governing_mode=gov_mode,
        passes=gov_2025 <= 1.0,
        status="CALCULADO",
        clause="ACI 318-25 Ch. 17 (Uncoupled Steel/Concrete Interaction)",
        units=inp.units,
    )


def compute_size_effect_lambda_s(d: float) -> float:
    """Compute ACI 318-25 size effect modification factor ``lambda_s = sqrt(2 / (1 + 0.004*d)) <= 1.0`` [mm]."""
    if d <= 0.0:
        raise ValueError(f"Effective depth d must be positive, got {d}")
    return min(1.0, math.sqrt(2.0 / (1.0 + 0.004 * d)))


@dataclass(frozen=True)
class Aci318DeepShear2025Input:
    """Input for ACI 318-25 one-way shear in deep footings / pile caps with size and arching effects.

    Units: forces in kN, lengths in mm, stresses in MPa.
    """

    bw: float
    d: float
    fc: float
    v_u: float
    a_v: float | None = None
    rho_w: float = 0.005
    lambda_lightweight: float = 1.0
    phi_shear: float = 0.75
    units: str = "SI_kN_mm_MPa"


@dataclass(frozen=True)
class Aci318DeepShear2025Result:
    """Result of ACI 318-25 one-way shear check including size effect and arching multiplier."""

    lambda_s: float
    arching_multiplier: float
    vc_nominal: float
    phi_vc: float
    v_u: float
    utilization: float
    passes: bool
    status: str = "CALCULADO"
    clause: str = "ACI 318-25 §22.5.5 & §13.4 (Size Effect & Arching)"
    units: str = "SI_kN_mm_MPa"


def verify_deep_shear_aci318_25(inp: Aci318DeepShear2025Input) -> Aci318DeepShear2025Result:
    """Evaluate ACI 318-25 one-way concrete shear strength with size effect and deep arching multiplier."""
    if inp.bw <= 0.0 or inp.d <= 0.0 or inp.fc <= 0.0:
        raise ValueError("bw, d, and fc must be strictly positive.")

    lam_s = compute_size_effect_lambda_s(inp.d)
    sqrt_fc = min(math.sqrt(inp.fc), 8.3)
    rho_eff = max(inp.rho_w, 0.001)

    # Arching multiplier for short shear spans (a_v / d < 2.0 in pile caps / deep footings)
    arch_mult = 1.0
    if inp.a_v is not None and inp.a_v > 0.0:
        ratio_av_d = inp.a_v / inp.d
        if ratio_av_d < 2.0:
            arch_mult = min(2.5, max(1.0, 2.0 / max(ratio_av_d, 0.5)))

    # ACI 318-25 §22.5.5.1 basic shear stress (MPa)
    tau_basic = 0.66 * inp.lambda_lightweight * lam_s * (rho_eff ** (1.0 / 3.0)) * sqrt_fc
    tau_min = 0.083 * inp.lambda_lightweight * lam_s * sqrt_fc
    tau_c = max(tau_basic, tau_min) * arch_mult

    vc_nom = (tau_c * inp.bw * inp.d) / 1000.0  # N -> kN
    phi_vc = inp.phi_shear * vc_nom
    v_u_abs = abs(inp.v_u)
    util = v_u_abs / phi_vc if phi_vc > 0.0 else float("inf")

    return Aci318DeepShear2025Result(
        lambda_s=round(lam_s, 4),
        arching_multiplier=round(arch_mult, 4),
        vc_nominal=round(vc_nom, 3),
        phi_vc=round(phi_vc, 3),
        v_u=round(v_u_abs, 3),
        utilization=round(util, 4),
        passes=util <= 1.0,
        status="CALCULADO",
        clause="ACI 318-25 §22.5.5 & §13.4 (Size Effect & Arching)",
        units=inp.units,
    )


__all__ = [
    "Aci318Anchor2025Input",
    "Aci318Anchor2025Result",
    "Aci318DeepShear2025Input",
    "Aci318DeepShear2025Result",
    "compute_size_effect_lambda_s",
    "verify_anchor_interaction_aci318_25",
    "verify_deep_shear_aci318_25",
]
