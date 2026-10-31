"""Servicio: extended end-plate moment connection."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class EndPlateInput:
    bp_mm: float
    tp_mm: float
    db_mm: float
    bf_mm: float
    tf_mm: float
    bolt_diameter_mm: float
    bolt_grade: str = "A325"
    fy_plate_MPa: float = 345.0
    Mu_kNm: float = 100.0


@dataclass(frozen=True)
class EndPlateResult:
    Mn_kNm: float
    DCR: float
    plate_thickness_required_mm: float
    notes: list[str]


def design_end_plate(inp: EndPlateInput) -> EndPlateResult:
    """End-plate 4ES (AISC 358) simplificado."""
    import math
    fy = inp.fy_plate_MPa * 1e6
    tp = inp.tp_mm / 1000
    bp = inp.bp_mm / 1000
    db = inp.db_mm / 1000
    Mp = fy * bp * tp ** 2 / 4
    Mn = 4 * Mp * (db / 2)
    Mu = inp.Mu_kNm * 1e3
    dcr = Mu / Mn if Mn > 0 else 99
    tp_req = math.sqrt(Mu / (fy * bp * db / 2)) * 1000
    return EndPlateResult(
        Mn_kNm=Mn / 1e3, DCR=dcr,
        plate_thickness_required_mm=tp_req,
        notes=[
            f"Mn = {Mn/1e3:.1f} kN*m, DCR = {dcr:.2f}",
            f"tp requerido (DCR=1): {tp_req:.1f} mm",
        ],
    )
