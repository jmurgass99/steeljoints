"""NSR-10 Título F.2 — Estructuras de Acero (Colombia).

NSR-10 F.2 adopta AISC 360 con minor adjustments. Esta implementación
provee chequeos básicos para:
    - Resistencia a tracción/cortante de pernos (F.2.10)
    - Soldadura de filete (F.2.10.2.4)
    - Bloque de cortante (F.2.10.4.3)
    - Factores de minoración (F.2.5)

Para chequeos avanzados (panel zone, prequalified seismic) usar los
módulos AISC equivalentes — NSR-10 F.2 los referencia directamente.

Backward compat: las funciones puras Rn de aisc360_j siguen disponibles
como aliases en este módulo.
"""
from __future__ import annotations
import math
from dataclasses import dataclass

from . import aisc360_j as _aisc
from ..exceptions import CodeError, ConfigurationError


# ---------------------------------------------------------------------------
# Backward-compat re-export de funciones puras Rn (idénticas a AISC 360)
# ---------------------------------------------------------------------------
fillet_weld_Rn          = _aisc.fillet_weld_Rn
bolt_shear_Rn           = _aisc.bolt_shear_Rn
bolt_tension_Rn         = _aisc.bolt_tension_Rn
bolt_bearing_Rn         = _aisc.bolt_bearing_Rn
bolt_combined_Fnt_prime = _aisc.bolt_combined_Fnt_prime
slip_critical_Rn        = _aisc.slip_critical_Rn
tension_yielding_Rn     = _aisc.tension_yielding_Rn
tension_rupture_Rn      = _aisc.tension_rupture_Rn
shear_yielding_Rn       = _aisc.shear_yielding_Rn
shear_rupture_Rn        = _aisc.shear_rupture_Rn
concrete_bearing_Rn     = _aisc.concrete_bearing_Rn


# ---------------------------------------------------------------------------
# Factores de minoración NSR-10 F.2.5 / Tabla F.2.10.3-2 (idénticos a AISC LRFD)
# ---------------------------------------------------------------------------
PHI_TENSION         = 0.90    # Fluencia
PHI_TENSION_RUPTURE = 0.75
PHI_SHEAR           = 0.75
PHI_BOLT_SHEAR      = 0.75
PHI_BOLT_TENSION    = 0.75
PHI_WELD            = 0.75
PHI_BLOCK_SHEAR     = 0.75
# Alias en español (legacy)
PHI_CORTANTE_PERNO  = PHI_BOLT_SHEAR
PHI_TENSION_PERNO   = PHI_BOLT_TENSION
PHI_APLASTAMIENTO   = 0.75
PHI_FLUENCIA        = 0.90
PHI_ROTURA          = 0.75
PHI_DESLIZAMIENTO   = 1.00
PHI_PANEL_ZONA      = 0.90
PHI_SOLDADURA       = PHI_WELD


# ---------------------------------------------------------------------------
# Tabla de pernos NSR-10 (corresponden a AISC). Unidades SI: Pa, Pa.
# ---------------------------------------------------------------------------
BOLT_GRADES_NSR10 = {
    "A307": {"Fu": 414e6, "Fnv_N": 188e6, "Fnt": 310e6},
    "A325": {"Fu": 825e6, "Fnv_N": 372e6, "Fnt": 620e6},
    "A490": {"Fu": 1035e6, "Fnv_N": 457e6, "Fnt": 780e6},
}


# ---------------------------------------------------------------------------
# 1) Pernos individuales — F.2.10.3 (≡ AISC §J3)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NSR10BoltInput:
    grade: str             # "A307" | "A325" | "A490"
    diameter_mm: float
    thread_condition: str = "N"   # "N" (rosca incluida) | "X"


@dataclass(frozen=True)
class NSR10BoltResult:
    Rn_shear_kN: float
    Rn_tension_kN: float
    Rd_shear_kN: float
    Rd_tension_kN: float
    notes: list[str]


def design_bolt_nsr10(inp: NSR10BoltInput) -> NSR10BoltResult:
    """Resistencia de un perno individual según NSR-10 F.2.10.

    Idéntico en estructura a AISC §J3, con phi=0.75.
    """
    if inp.grade not in BOLT_GRADES_NSR10:
        raise CodeError(
            f"Grado '{inp.grade}' no en tabla F.2.5-1. "
            f"Soportados: {list(BOLT_GRADES_NSR10)}"
        )
    if inp.thread_condition.upper() not in ("N", "X"):
        raise ConfigurationError(
            f"thread_condition debe ser 'N' o 'X', no '{inp.thread_condition}'"
        )
    grade = BOLT_GRADES_NSR10[inp.grade]
    Ab = math.pi * (inp.diameter_mm / 1000) ** 2 / 4
    # Cortante NSR-10 F.2.10.3.6: Rn = Fnv * Ab
    # Para rosca excluida usar Fnv del orden 0.563·Fu (similar AISC)
    if inp.thread_condition.upper() == "N":
        Fnv = grade["Fnv_N"]
    else:
        Fnv = 0.563 * grade["Fu"]
    Fnt = grade["Fnt"]
    Rn_shear = Fnv * Ab
    Rn_tension = Fnt * Ab
    Rd_shear = PHI_BOLT_SHEAR * Rn_shear
    Rd_tension = PHI_BOLT_TENSION * Rn_tension
    return NSR10BoltResult(
        Rn_shear_kN=Rn_shear / 1e3,
        Rn_tension_kN=Rn_tension / 1e3,
        Rd_shear_kN=Rd_shear / 1e3,
        Rd_tension_kN=Rd_tension / 1e3,
        notes=[
            f"NSR-10 F.2.10.3 — perno {inp.grade} Ø{inp.diameter_mm} mm",
            f"phi·Rn cortante = {Rd_shear/1e3:.1f} kN",
            f"phi·Rn tensión = {Rd_tension/1e3:.1f} kN",
        ],
    )


# ---------------------------------------------------------------------------
# 2) Soldadura de filete — F.2.10.2.4 (≡ AISC §J2)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NSR10FilletWeldInput:
    leg_size_mm: float
    length_mm: float
    electrode_FEXX_MPa: float = 482.0    # E70XX ~482 MPa
    angle_load_deg: float = 0.0


@dataclass(frozen=True)
class NSR10FilletWeldResult:
    throat_mm: float
    Rn_kN: float
    Rd_kN: float
    notes: list[str]


def design_fillet_weld_nsr10(inp: NSR10FilletWeldInput) -> NSR10FilletWeldResult:
    """NSR-10 F.2.10.2.4 — soldadura de filete con direccional (≡ AISC J2)."""
    throat = 0.707 * inp.leg_size_mm / 1000
    direc = 1.0 + 0.5 * math.sin(math.radians(inp.angle_load_deg)) ** 1.5
    L = inp.length_mm / 1000
    fexx = inp.electrode_FEXX_MPa * 1e6
    Rn = 0.6 * fexx * direc * throat * L
    Rd = PHI_WELD * Rn
    return NSR10FilletWeldResult(
        throat_mm=throat * 1000, Rn_kN=Rn / 1e3, Rd_kN=Rd / 1e3,
        notes=[
            f"NSR-10 F.2.10.2.4 — soldadura E{int(inp.electrode_FEXX_MPa/482*70)}XX",
            f"Throat = {throat*1000:.2f} mm, ang = {inp.angle_load_deg}°",
            f"phi·Rn = {Rd/1e3:.1f} kN",
        ],
    )


# ---------------------------------------------------------------------------
# 3) Bloque de cortante — F.2.10.4.3 (≡ AISC §J4.3)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class NSR10BlockShearInput:
    Agv_mm2: float        # área bruta cortante
    Anv_mm2: float        # área neta cortante
    Ant_mm2: float        # área neta tensión
    Fy_MPa: float = 250.0
    Fu_MPa: float = 400.0
    Ubs: float = 1.0      # tracción uniforme=1.0, no uniforme=0.5


@dataclass(frozen=True)
class NSR10BlockShearResult:
    Rn_kN: float
    Rd_kN: float
    governing: str        # "shear_yield" o "shear_rupture"
    notes: list[str]


def design_block_shear_nsr10(inp: NSR10BlockShearInput) -> NSR10BlockShearResult:
    """NSR-10 F.2.10.4.3 — bloque de cortante (≡ AISC §J4.3).

    Rn = min(0.6·Fu·Anv + Ubs·Fu·Ant, 0.6·Fy·Agv + Ubs·Fu·Ant)
    """
    Fy = inp.Fy_MPa * 1e6
    Fu = inp.Fu_MPa * 1e6
    Agv = inp.Agv_mm2 / 1e6
    Anv = inp.Anv_mm2 / 1e6
    Ant = inp.Ant_mm2 / 1e6
    R1 = 0.6 * Fu * Anv + inp.Ubs * Fu * Ant     # rotura cortante
    R2 = 0.6 * Fy * Agv + inp.Ubs * Fu * Ant     # fluencia cortante
    Rn = min(R1, R2)
    governing = "shear_rupture" if R1 < R2 else "shear_yield"
    Rd = PHI_BLOCK_SHEAR * Rn
    return NSR10BlockShearResult(
        Rn_kN=Rn / 1e3, Rd_kN=Rd / 1e3, governing=governing,
        notes=[
            f"NSR-10 F.2.10.4.3 — bloque cortante",
            f"R1 (rotura) = {R1/1e3:.1f} kN",
            f"R2 (fluencia) = {R2/1e3:.1f} kN",
            f"Rn = {Rn/1e3:.1f} kN ({governing})",
            f"phi·Rn = {Rd/1e3:.1f} kN",
        ],
    )


def info() -> str:
    """Información sobre la implementación NSR-10 F.2 en este módulo."""
    return (
        "NSR-10 Título F.2 — Estructuras de Acero (Colombia)\n"
        "Implementación v1: pernos, soldaduras, bloque cortante.\n"
        "Para chequeos avanzados (panel zone, prequalified seismic)\n"
        "usar los módulos AISC equivalentes, ya que NSR-10 F.2 los\n"
        "referencia directamente."
    )


__all__ = [
    # Phi factors
    "PHI_TENSION", "PHI_TENSION_RUPTURE", "PHI_SHEAR",
    "PHI_BOLT_SHEAR", "PHI_BOLT_TENSION",
    "PHI_WELD", "PHI_BLOCK_SHEAR",
    "PHI_CORTANTE_PERNO", "PHI_TENSION_PERNO", "PHI_APLASTAMIENTO",
    "PHI_FLUENCIA", "PHI_ROTURA", "PHI_DESLIZAMIENTO",
    "PHI_PANEL_ZONA", "PHI_SOLDADURA",
    # Bolt table
    "BOLT_GRADES_NSR10",
    # Dataclasses & funciones de diseño
    "NSR10BoltInput", "NSR10BoltResult", "design_bolt_nsr10",
    "NSR10FilletWeldInput", "NSR10FilletWeldResult", "design_fillet_weld_nsr10",
    "NSR10BlockShearInput", "NSR10BlockShearResult", "design_block_shear_nsr10",
    # Backward-compat AISC aliases
    "fillet_weld_Rn", "bolt_shear_Rn", "bolt_tension_Rn", "bolt_bearing_Rn",
    "bolt_combined_Fnt_prime", "slip_critical_Rn",
    "tension_yielding_Rn", "tension_rupture_Rn",
    "shear_yielding_Rn", "shear_rupture_Rn", "concrete_bearing_Rn",
    "info",
]
