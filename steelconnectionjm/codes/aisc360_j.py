"""
aisc360_j.py — AISC 360-22 Chapter J (Conexiones).

Funciones puras: cada una recibe parámetros físicos y devuelve Rn [N]. El
diseñador multiplica por φ (LRFD) o divide por Ω (ASD).

Cubre:
  §J2.4   Soldadura de filete (Fnw direccional)
  §J3.6   Pernos: cortante y tensión (Rn = Fn·Ab)
  §J3.7   Combinación tensión-cortante (Fnt')
  §J3.8   Conexiones críticas al deslizamiento (slip-critical)
  §J3.10  Aplastamiento en pernos
  §J4.1   Resistencia de elementos a tensión (fluencia / rotura)
  §J4.2   Resistencia de elementos a cortante (fluencia / rotura)
  §J4.3   Block shear (también en módulo block_shear.py)
  §J10.6  Panel zone (también en panel_zone.py)
"""
from __future__ import annotations
from math import sin, sqrt, radians

PHI_SHEAR = 0.75
PHI_TENSION = 0.75
PHI_BEARING = 0.75
PHI_GROSS_YIELDING = 0.90
PHI_NET_RUPTURE = 0.75
PHI_SLIP = 1.00            # standard holes; 0.85 oversized; 0.70 LSlots transverse
PHI_PANEL_ZONE = 0.90
PHI_WELD = 0.75

# ---------------------------------------------------------------------------
# §J2.4 — Fillet weld
# ---------------------------------------------------------------------------
def fillet_weld_Rn(a_mm: float, L_mm: float, FEXX_MPa: float,
                   theta_deg: float = 0.0) -> float:
    """
    Rn = Fnw · Awe   con   Fnw = 0.60·FEXX·(1.0 + 0.50·sin^1.5 θ)   [N]
    a = garganta efectiva (= w/√2 para fillet equilátero), L = longitud útil.
    θ = 0 (longitudinal) … 90 (transversal).
    """
    Fnw = 0.60 * FEXX_MPa * (1.0 + 0.50 * sin(radians(theta_deg))**1.5)
    return Fnw * a_mm * L_mm


# ---------------------------------------------------------------------------
# §J3.6 — Bolt shear / tension
# ---------------------------------------------------------------------------
def bolt_shear_Rn(Ab_mm2: float, Fnv_MPa: float, n_planes: int = 1,
                  threads_in_plane: bool = True) -> float:
    """
    Rn = Fnv · Ab · n_planes
    Si las roscas están en el plano de corte se usa el Fnv "-N" (ya descontado).
    Si están excluidas se usa "-X" (mayor). Esta función toma Fnv tal cual.
    """
    # AISC ya reduce Fnv en la tabla J3.2 cuando "-N" (e.g. A325: 372 MPa).
    return Fnv_MPa * Ab_mm2 * n_planes


def bolt_tension_Rn(Ab_mm2: float, Fnt_MPa: float) -> float:
    """Rn = Fnt · Ab."""
    return Fnt_MPa * Ab_mm2


# ---------------------------------------------------------------------------
# §J3.7 — Combined tension + shear in bearing-type connections
# ---------------------------------------------------------------------------
def bolt_combined_Fnt_prime(Fnt_MPa: float, Fnv_MPa: float, frv_MPa: float,
                            phi: float = PHI_SHEAR) -> float:
    """
    Fnt' = 1.3·Fnt − (Fnt / (φ·Fnv)) · frv ≤ Fnt
    frv = esfuerzo de corte requerido = Vu/Ab.
    """
    Fnt_p = 1.3 * Fnt_MPa - (Fnt_MPa / (phi * Fnv_MPa)) * frv_MPa
    return min(Fnt_p, Fnt_MPa)


# ---------------------------------------------------------------------------
# §J3.8 — Slip-critical
# ---------------------------------------------------------------------------
def slip_critical_Rn(mu: float, Du: float, hf: float, Tb_N: float,
                     ns: int = 1) -> float:
    """
    Rn = μ · Du · hf · Tb · ns
      μ  = 0.30 (Class A), 0.50 (Class B)
      Du = 1.13 (factor multiplicador de Tb)
      hf = factor por relleno (1.0 sin relleno)
      Tb = pretensión mínima [N] (Tabla J3.1)
      ns = número de planos deslizantes
    """
    return mu * Du * hf * Tb_N * ns


# ---------------------------------------------------------------------------
# §J3.10 — Bearing/tearout at bolt holes
# ---------------------------------------------------------------------------
def bolt_bearing_Rn(d_mm: float, t_mm: float, Fu_MPa: float,
                    lc_mm: float, deformation_considered: bool = True) -> float:
    """
    Aplastamiento + desgarro (governs the smaller):

      Si la deformación al agujero ES una consideración de servicio:
        Rn = min(1.2·lc·t·Fu,  2.4·d·t·Fu)
      Si NO:
        Rn = min(1.5·lc·t·Fu,  3.0·d·t·Fu)
    """
    if deformation_considered:
        return min(1.2 * lc_mm * t_mm * Fu_MPa, 2.4 * d_mm * t_mm * Fu_MPa)
    else:
        return min(1.5 * lc_mm * t_mm * Fu_MPa, 3.0 * d_mm * t_mm * Fu_MPa)


# ---------------------------------------------------------------------------
# §J4.1 — Tensile strength of connecting elements
# ---------------------------------------------------------------------------
def tension_yielding_Rn(Ag_mm2: float, Fy_MPa: float) -> float:
    """Fluencia bruta (φ=0.90): Rn = Fy · Ag."""
    return Fy_MPa * Ag_mm2

def tension_rupture_Rn(Ae_mm2: float, Fu_MPa: float) -> float:
    """Rotura neta efectiva (φ=0.75): Rn = Fu · Ae."""
    return Fu_MPa * Ae_mm2


# ---------------------------------------------------------------------------
# §J4.2 — Shear strength of connecting elements
# ---------------------------------------------------------------------------
def shear_yielding_Rn(Agv_mm2: float, Fy_MPa: float) -> float:
    """Cortante en fluencia (φ=1.00): Rn = 0.60·Fy·Agv."""
    return 0.60 * Fy_MPa * Agv_mm2

def shear_rupture_Rn(Anv_mm2: float, Fu_MPa: float) -> float:
    """Cortante en rotura (φ=0.75): Rn = 0.60·Fu·Anv."""
    return 0.60 * Fu_MPa * Anv_mm2


# ---------------------------------------------------------------------------
# §J7 — Connecting elements in compression (column base plates etc.)
# ---------------------------------------------------------------------------
def concrete_bearing_Rn(A1_mm2: float, A2_mm2: float, fc_MPa: float) -> float:
    """
    Presión sobre concreto (AISC §J8): Pp = 0.85·fc·A1·√(A2/A1) ≤ 1.7·fc·A1.
    A1 = área de la placa, A2 = área del soporte (concretamente, área dilatada
    a 2:1 hasta el borde).
    """
    if A1_mm2 <= 0:
        return 0.0
    ratio = min(sqrt(A2_mm2 / A1_mm2), 2.0)
    Pp = 0.85 * fc_MPa * A1_mm2 * ratio
    return min(Pp, 1.7 * fc_MPa * A1_mm2)
