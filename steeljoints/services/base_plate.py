"""Servicio: base plate de columna."""
from __future__ import annotations
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class BasePlateInput:
    Bp_mm: float
    Np_mm: float
    tp_mm: float
    d_col_mm: float
    bf_col_mm: float
    fc_MPa: float = 25.0
    fy_plate_MPa: float = 250.0
    Pu_kN: float = 500.0
    Mu_kNm: float = 0.0


@dataclass(frozen=True)
class BasePlateResult:
    fp_actual_MPa: float
    fp_allow_MPa: float
    tp_required_mm: float
    DCR: float
    notes: list[str]


def design_base_plate(inp: BasePlateInput) -> BasePlateResult:
    """AISC DG-1 simplificado para axial + momento bajo."""
    Ag = (inp.Bp_mm / 1000) * (inp.Np_mm / 1000)
    Pu = inp.Pu_kN * 1e3
    fp_actual = Pu / Ag
    fc = inp.fc_MPa * 1e6
    phi_c = 0.65
    fp_allow = phi_c * 0.85 * fc
    m = (inp.Np_mm - 0.95 * inp.d_col_mm) / 2
    fy = inp.fy_plate_MPa * 1e6
    tp_req = m * math.sqrt(2 * fp_actual / fy)
    dcr = fp_actual / fp_allow if fp_allow > 0 else 99
    return BasePlateResult(
        fp_actual_MPa=fp_actual / 1e6,
        fp_allow_MPa=fp_allow / 1e6,
        tp_required_mm=tp_req,
        DCR=dcr,
        notes=[
            f"fp = {fp_actual/1e6:.2f} MPa, fp_allow = {fp_allow/1e6:.2f} MPa",
            f"DCR = {dcr:.2f}, tp_req = {tp_req:.1f} mm",
        ],
    )
