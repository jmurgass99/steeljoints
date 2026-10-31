"""Servicio: diseno de pernos y grupos de pernos."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SingleBoltInput:
    grade: str            # "A325", "A490", "A307" (AISC) | "8.8", "10.9" (EC3)
    diameter_mm: float    # diametro nominal del perno
    thread_condition: str = "N"   # "N" (rosca incluida) | "X" (rosca excluida)
    standard: str = "AISC"        # "AISC" | "EC3"
    plate_thickness_mm: float = 10.0
    plate_fu_MPa: float = 400.0   # resistencia a traccion de la placa
    edge_distance_mm: float = 30.0


@dataclass(frozen=True)
class BoltDesignResult:
    Rn_shear_kN: float            # resistencia al cortante (nominal)
    Rn_tension_kN: float
    Rn_bearing_kN: float           # bearing en la placa
    Rd_shear_kN: float             # phi*Rn (AISC) o Rn/gamma (EC3)
    governs: str
    notes: list[str]


def design_single_bolt(inp: SingleBoltInput) -> BoltDesignResult:
    """Diseno de un perno individual: cortante, tension, aplastamiento.

    Aplica formulas AISC J3 / EC3 3.6 directamente.
    """
    import math
    Ab = math.pi * (inp.diameter_mm / 1000) ** 2 / 4  # m^2

    fu_table = {
        "A307": 414e6, "A325": 825e6, "A490": 1035e6,
        "4.6": 400e6, "5.6": 500e6, "8.8": 800e6, "10.9": 1000e6,
    }
    fu = fu_table.get(inp.grade, 825e6)

    if inp.standard.upper() == "AISC":
        Fnv = 0.45 * fu if inp.thread_condition.upper() == "N" else 0.563 * fu
        Fnt = 0.75 * fu
        phi_shear = 0.75
        phi_tension = 0.75
        gamma = 1.0
    else:
        alpha_v = 0.6 if inp.thread_condition.upper() == "X" else 0.5
        Fnv = alpha_v * fu
        Fnt = 0.9 * fu
        phi_shear = 1.0
        phi_tension = 1.0
        gamma = 1.25

    Rn_shear = Fnv * Ab
    Rn_tension = Fnt * Ab
    db = inp.diameter_mm / 1000
    tp = inp.plate_thickness_mm / 1000
    fu_p = inp.plate_fu_MPa * 1e6
    Rn_bearing = 2.4 * db * tp * fu_p
    if inp.standard.upper() == "AISC":
        Rd_shear = phi_shear * Rn_shear
    else:
        Rd_shear = Rn_shear / gamma
    governs = "shear" if Rn_shear < Rn_bearing else "bearing"
    return BoltDesignResult(
        Rn_shear_kN=Rn_shear / 1e3,
        Rn_tension_kN=Rn_tension / 1e3,
        Rn_bearing_kN=Rn_bearing / 1e3,
        Rd_shear_kN=Rd_shear / 1e3,
        governs=governs,
        notes=[
            f"Grade {inp.grade}, dia={inp.diameter_mm:.0f} mm, std={inp.standard}",
            f"Rn shear = {Rn_shear/1e3:.1f} kN | bearing = {Rn_bearing/1e3:.1f} kN",
            f"Gobierna: {governs}",
        ],
    )


@dataclass(frozen=True)
class BoltGroupInput:
    n_bolts: int
    diameter_mm: float
    grade: str = "A325"
    spacing_mm: float = 76.0
    layout: str = "linear"
    Vu_kN: float = 0.0
    Mu_kNm: float = 0.0


@dataclass(frozen=True)
class BoltGroupResult:
    Rn_group_kN: float
    DCR_shear: float
    notes: list[str]


def design_bolt_group(inp: BoltGroupInput) -> BoltGroupResult:
    """Capacidad de grupo de pernos en cortante puro o con eccentricidad."""
    single = design_single_bolt(SingleBoltInput(
        grade=inp.grade, diameter_mm=inp.diameter_mm,
    ))
    if inp.Mu_kNm == 0:
        Rn_group = single.Rn_shear_kN * inp.n_bolts
    else:
        Rn_group = single.Rn_shear_kN * inp.n_bolts * 0.6
    dcr = inp.Vu_kN / Rn_group if Rn_group > 0 else 99.0
    return BoltGroupResult(
        Rn_group_kN=Rn_group, DCR_shear=dcr,
        notes=[
            f"Grupo {inp.n_bolts}dia{inp.diameter_mm:.0f} {inp.grade}",
            f"Rn = {Rn_group:.1f} kN, DCR = {dcr:.2f}",
        ],
    )
