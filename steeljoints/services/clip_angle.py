"""Servicio: clip angle (single/double) - placeholder."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ClipAngleInput:
    leg_a_mm: float
    leg_b_mm: float
    thickness_mm: float
    Vu_kN: float
    angle_type: str = "double"


@dataclass(frozen=True)
class ClipAngleResult:
    Rn_kN: float
    DCR: float
    notes: list[str]


def design_clip_angle(inp: ClipAngleInput) -> ClipAngleResult:
    """v1 simplificado: capacidad nominal por fluencia del ala vertical."""
    Fy = 345e6
    A_v = (inp.thickness_mm * inp.leg_a_mm) / 1e6
    Rn = 0.6 * Fy * A_v
    if inp.angle_type == "double":
        Rn *= 2
    dcr = (inp.Vu_kN * 1e3) / Rn if Rn > 0 else 99
    return ClipAngleResult(
        Rn_kN=Rn / 1e3, DCR=dcr,
        notes=[f"Rn = {Rn/1e3:.1f} kN ({inp.angle_type}), DCR = {dcr:.2f}",
               "PROVISIONAL: solo fluencia por cortante bruto con Fy = 345 MPa y sin φ; "
               "para pernos, aplastamiento, rotura y bloque usa steeljoints.ClipAngle"],
    )
