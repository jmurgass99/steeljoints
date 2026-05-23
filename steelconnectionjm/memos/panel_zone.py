"""
Memoria handcalcs — Panel Zone (zona de panel nodal) AISC 341-22 §E3.6e.

Verifica:
    R_v = 0.6·Fy·d_c·t_p · (1 + 3·b_cf·t_cf² / (d_b·d_c·t_p))    (con axial bajo)

vs demanda 0.8·(M_f1 + M_f2)/d_b - V_c (cortante neto en el panel).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PanelZoneInput:
    M_f1_kNm: float          # momento en cara 1 de columna
    M_f2_kNm: float
    d_beam_mm: float
    d_column_mm: float
    t_web_column_mm: float
    b_flange_column_mm: float
    t_flange_column_mm: float
    t_doubler_mm: float = 0.0
    Fy_MPa: float = 345.0
    V_column_kN: float = 0.0


@dataclass(frozen=True)
class PanelZoneResult:
    V_demand_kN: float
    V_capacity_kN: float
    DCR: float
    needs_doubler: bool
    markdown: str


def render_panel_zone_memo(inp: PanelZoneInput) -> PanelZoneResult:
    db, dc = inp.d_beam_mm, inp.d_column_mm
    bcf, tcf = inp.b_flange_column_mm, inp.t_flange_column_mm
    tp = inp.t_web_column_mm + inp.t_doubler_mm

    # V_demand AISC 341-22 §E3.6e.1
    V_demand_kN = 0.8 * (inp.M_f1_kNm + inp.M_f2_kNm) / (db / 1000.0) \
                   - inp.V_column_kN

    # V_capacity §E3.6e.2 (sin axial significativo)
    V_capacity_N = 0.6 * inp.Fy_MPa * dc * tp * (
        1.0 + (3.0 * bcf * tcf ** 2) / (db * dc * tp + 1e-9)
    )
    V_capacity_kN = V_capacity_N / 1000.0

    DCR = V_demand_kN / max(V_capacity_kN, 1e-9)
    needs = DCR > 1.0

    md = (
        "# Memoria — Panel Zone AISC 341-22 §E3.6e\n\n"
        f"## Demanda\n"
        f"V_pz = 0.8·(M_f1+M_f2)/d_b - V_c = "
        f"{V_demand_kN:.1f} kN\n\n"
        f"## Capacidad\n"
        f"R_v = 0.6·Fy·d_c·t_p·(1 + 3·b_cf·t_cf² / (d_b·d_c·t_p)) "
        f"= **{V_capacity_kN:.1f} kN**\n\n"
        f"## Resultado\n"
        f"DCR = {DCR:.2f} → {'❌ requiere doubler' if needs else '✅'}\n"
    )

    return PanelZoneResult(
        V_demand_kN=V_demand_kN, V_capacity_kN=V_capacity_kN,
        DCR=DCR, needs_doubler=needs, markdown=md,
    )


__all__ = ["PanelZoneInput", "PanelZoneResult", "render_panel_zone_memo"]
