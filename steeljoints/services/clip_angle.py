"""Servicio: clip angle (single/double) con opción de chequeo AISC 360 completo."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ClipAngleInput:
    leg_a_mm: float
    leg_b_mm: float
    thickness_mm: float
    Vu_kN: float
    angle_type: str = "double"
    full_aisc_checks: bool = False
    n_bolts: int = 3
    bolt_diameter_mm: float = 19.05
    bolt_grade: str = "A325"
    beam_tw_mm: float = 8.0


@dataclass(frozen=True)
class ClipAngleResult:
    Rn_kN: float
    DCR: float
    notes: list[str]
    governing_check: str = "Gross shear yield"


def design_clip_angle(inp: ClipAngleInput) -> ClipAngleResult:
    """Capacidad de clip angle por fluencia del ala vertical o chequeo completo con ``ClipAngle``."""
    if not inp.full_aisc_checks:
        Fy = 345e6
        A_v = (inp.thickness_mm * inp.leg_a_mm) / 1e6
        Rn = 0.6 * Fy * A_v
        if inp.angle_type == "double":
            Rn *= 2
        dcr = (inp.Vu_kN * 1e3) / Rn if Rn > 0 else 99
        return ClipAngleResult(
            Rn_kN=Rn / 1e3,
            DCR=dcr,
            notes=[
                f"Rn = {Rn/1e3:.1f} kN ({inp.angle_type}), DCR = {dcr:.2f}",
                "Fluencia por cortante bruto con Fy = 345 MPa; activa full_aisc_checks=True para pernos, aplastamiento y bloque de cortante",
            ],
            governing_check="Gross shear yield",
        )

    from ..clip_angle import ClipAngle

    scale = 1.0 if inp.angle_type == "double" else 0.5
    Vu_equiv = inp.Vu_kN / scale
    ca = ClipAngle(
        Vu=Vu_equiv,
        n_bolts=inp.n_bolts,
        bolt_diameter=inp.bolt_diameter_mm,
        bolt_grade=inp.bolt_grade,
        angle_thickness=inp.thickness_mm,
        angle_leg=inp.leg_a_mm,
        beam_tw=inp.beam_tw_mm,
    )
    rep = ca.design()
    gov_check = rep["governing_check"]
    gov_util = rep["governing_utilization"]
    # Effective design capacity Rn_kN corresponding to governing check
    Rn_eff = (inp.Vu_kN / gov_util) if gov_util > 0 else 0.0
    notes = [
        f"AISC 360 ClipAngle ({inp.angle_type}): modo gobernante = {gov_check}, DCR = {gov_util:.3f}",
        f"Capacidad gobernante efectiva φRn = {Rn_eff:.1f} kN",
    ]
    return ClipAngleResult(
        Rn_kN=round(Rn_eff, 2),
        DCR=gov_util,
        notes=notes,
        governing_check=gov_check,
    )
