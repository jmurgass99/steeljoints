"""Servicio: panel zone (delega al modulo existente)."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PanelZoneServiceInput:
    d_c_mm: float
    t_w_mm: float
    d_b_mm: float
    b_f_c_mm: float
    t_f_c_mm: float
    Fy_c_MPa: float = 345.0
    Pu_kN: float = 0.0
    Py_kN: float = 1000.0
    V_demand_kN: float = 0.0
    consider_plastification: bool = True


@dataclass(frozen=True)
class PanelZoneServiceResult:
    Vn_kN: float
    DCR: float
    governs: str
    notes: list[str]


def design_panel_zone(inp: PanelZoneServiceInput) -> PanelZoneServiceResult:
    """Wrap del modulo panel_zone existente."""
    from steelconnectionjm.panel_zone import (
        PanelZoneInput, shear_capacity,
    )
    pz_inp = PanelZoneInput(
        d_c=inp.d_c_mm / 1000,
        t_w=inp.t_w_mm / 1000,
        d_b=inp.d_b_mm / 1000,
        b_f_c=inp.b_f_c_mm / 1000,
        t_f_c=inp.t_f_c_mm / 1000,
        Fy_c=inp.Fy_c_MPa * 1e6,
        P_u=inp.Pu_kN * 1e3,
        P_y=inp.Py_kN * 1e3,
        consider_plastification=inp.consider_plastification,
    )
    res = shear_capacity(pz_inp, V_demand=inp.V_demand_kN * 1e3)
    return PanelZoneServiceResult(
        Vn_kN=res.Vn / 1e3,
        DCR=res.DCR,
        governs=res.governs,
        notes=list(res.notes),
    )
