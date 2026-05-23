"""
Conexión WUF-W (Welded Unreinforced Flange-Welded web) — AISC 358-22 §8.

Conexión sísmica precalificada para SMF/IMF. Características:
    - Soldadura completa pen. en alas viga-columna (CJP welds)
    - Alma soldada con filete a un plato de cortante
    - Sin reforzamiento (a diferencia de RBS, WUF-B)
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Any


@dataclass(frozen=True)
class WUFWInput:
    beam_Zx_mm3: float
    beam_Fy_MPa: float = 345
    beam_db_mm: float = 500           # peralte viga
    beam_bf_mm: float = 200
    beam_tf_mm: float = 16
    beam_tw_mm: float = 10
    column_Zx_mm3: float = 4_000_000  # para SCWB check
    column_Fy_MPa: float = 345
    n_panel_zone_doublers: int = 0
    # Optional parameters for advanced AISC 341 SCWB checks
    column_Pu_kN: float = 0.0
    column_Ag_mm2: float = 10000.0     # default area
    column_dc_mm: float = 300.0        # column depth


@dataclass(frozen=True)
class WUFWResult:
    Mpr_kNm: float                    # momento probable
    Vu_kN: float                      # cortante esperado a 0.5·L
    is_compact_per_AISC341: bool      # §D1
    scwb_ratio: float                 # ΣMpc/ΣMpb
    notes: list[str]


def design_wuf_w(inp: WUFWInput, beam_length_m: float = 6.0,
                  Lp_distance_m: float | None = None) -> WUFWResult:
    """Diseño WUF-W según AISC 358 §8 + AISC 341 §E3.

    Mpr = C_pr · R_y · Z_x · F_y    con C_pr = 1.15, R_y = 1.1 (A992)
    """
    Cpr = 1.15
    Ry = 1.10
    Mpr = Cpr * Ry * inp.beam_Zx_mm3 * inp.beam_Fy_MPa / 1e6  # kN·m

    # Lp típico para WUF-W: d_b (distancia al centro de la zona PZ)
    Lp = Lp_distance_m if Lp_distance_m else inp.beam_db_mm / 1000.0
    L_clear = beam_length_m - 2 * Lp
    Vu = 2 * Mpr / max(L_clear, 0.5)   # cortante en la rótula

    # Compactness §D1 highly ductile beam
    lam_p_flange = 0.30 * (200_000 / inp.beam_Fy_MPa) ** 0.5
    flange_ratio = (inp.beam_bf_mm / 2.0) / inp.beam_tf_mm
    flange_ok = flange_ratio <= lam_p_flange
    h = inp.beam_db_mm - 2 * inp.beam_tf_mm
    web_ratio = h / inp.beam_tw_mm
    Ca = 0.0  # asumir P/Pu pequeño
    lam_p_web = 2.45 * (200_000 / inp.beam_Fy_MPa) ** 0.5 * (1 - 0.93 * Ca)
    web_ok = web_ratio <= lam_p_web

    # Strong-column weak-beam (AISC 341 §E3.4a)
    # Column plastic moment reduced by axial stress
    Fyc_reduced = inp.column_Fy_MPa - (abs(inp.column_Pu_kN) * 1000.0) / max(inp.column_Ag_mm2, 1.0)
    Fyc_reduced = max(Fyc_reduced, 0.0)
    M_pc = inp.column_Zx_mm3 * Fyc_reduced / 1e6

    # Beam probable moment projected to column centerline: M*_pb = Mpr + Vu * (d_c / 2)
    dc_m = inp.column_dc_mm / 1000.0
    M_pb_projected = Mpr + Vu * (dc_m / 2.0)
    scwb = M_pc / max(M_pb_projected, 1e-9)


    notes = []
    if not flange_ok:
        notes.append(f"Ala viga b/2tf={flange_ratio:.1f} > λp={lam_p_flange:.1f}")
    if not web_ok:
        notes.append(f"Alma viga h/tw={web_ratio:.1f} > λp={lam_p_web:.1f}")
    if scwb < 1.0:
        notes.append(f"SCWB = {scwb:.2f} < 1.0")

    return WUFWResult(
        Mpr_kNm=Mpr, Vu_kN=Vu,
        is_compact_per_AISC341=flange_ok and web_ok,
        scwb_ratio=scwb, notes=notes,
    )


__all__ = ["WUFWInput", "WUFWResult", "design_wuf_w"]
