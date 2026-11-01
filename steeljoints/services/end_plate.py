"""Servicio: chapa frontal extendida (delega en ``steeljoints.end_plate.EndPlate``)."""
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
    """Flexión de la chapa frontal por líneas de rotura: φMn = φ·Fy·tp²·Yp (φ = 0,90).

    Delega en ``EndPlate.plate_flexure_check`` con las cotas por defecto de la clase (pfo = pfi =
    38 mm, g = 140 mm). ``Mn_kNm`` es la resistencia de DISEÑO φMn y ``plate_thickness_required_mm``
    el espesor que da φMn = Mu. Hasta la versión 1.1 este servicio calculaba 4·(Fy·bp·tp²/4)·(db/2),
    una expresión dimensionalmente inconsistente (≈ 6 kN·m para una chapa de 20 mm).
    El Yp que usa ``EndPlate`` está marcado como SIN CONTRASTAR (ver ``codes.aisc358``).
    """
    import math
    from ..end_plate import EndPlate
    ep = EndPlate(Mu=inp.Mu_kNm, Vu=0.0, beam_depth=inp.db_mm, beam_tf=inp.tf_mm, beam_bf=inp.bf_mm,
                  bolt_diameter=inp.bolt_diameter_mm, bolt_grade=inp.bolt_grade,
                  plate_thickness=inp.tp_mm, plate_Fy=inp.fy_plate_MPa, plate_width=inp.bp_mm)
    chk = ep.plate_flexure_check()
    phi_Mn = chk["phi_Mn_kNm"]
    Yp = chk["Yp_mm"]
    dcr = inp.Mu_kNm / phi_Mn if phi_Mn > 0 else float("inf")
    tp_req = math.sqrt(inp.Mu_kNm * 1e6 / (0.90 * inp.fy_plate_MPa * Yp)) if Yp > 0 else float("inf")
    return EndPlateResult(
        Mn_kNm=phi_Mn, DCR=dcr,
        plate_thickness_required_mm=tp_req,
        notes=[
            f"Yp = {Yp:.0f} mm (líneas de rotura 4E, SIN CONTRASTAR con AISC 358 Tabla 6.2)",
            f"φMn = 0.90·Fy·tp²·Yp = {phi_Mn:.1f} kN*m, DCR = {dcr:.2f}",
            f"tp requerido (DCR=1): {tp_req:.1f} mm",
        ],
    )
