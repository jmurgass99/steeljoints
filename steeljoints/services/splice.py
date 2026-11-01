"""Servicio: splice (empalme) - placeholder."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SpliceInput:
    Mu_kNm: float
    Vu_kN: float
    flange_plate_t_mm: float = 10.0
    flange_plate_b_mm: float = 200.0


@dataclass(frozen=True)
class SpliceResult:
    Mn_kNm: float
    DCR: float
    notes: list[str]


def design_splice(inp: SpliceInput) -> SpliceResult:
    """v1: capacidad nominal por placa de ala - chequeo simplificado."""
    Fy = 345e6
    A = (inp.flange_plate_t_mm * inp.flange_plate_b_mm) / 1e6
    T = Fy * A
    Mn = T * 0.5
    dcr = (inp.Mu_kNm * 1e3) / Mn if Mn > 0 else 99
    return SpliceResult(Mn_kNm=Mn / 1e3, DCR=dcr,
                        notes=[f"Mn = {Mn/1e3:.1f} kN*m, DCR = {dcr:.2f}",
                               "PROVISIONAL: Fy = 345 MPa fijo y brazo fijo de 0,5 m (la entrada no trae el canto); "
                               "no comprueba pernos, alma ni cortante"])
