"""Servicio: splice (empalme de viga/columna con cubrejuntas de ala y grupo de pernos en alma)."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SpliceInput:
    Mu_kNm: float
    Vu_kN: float
    flange_plate_t_mm: float = 10.0
    flange_plate_b_mm: float = 200.0
    beam_depth_mm: float = 500.0
    Fy_MPa: float = 345.0
    n_bolts_web: int = 0
    pitch_mm: float = 75.0
    gauge_mm: float = 100.0
    bolt_capacity_kN: float = 80.0


@dataclass(frozen=True)
class SpliceResult:
    Mn_kNm: float
    DCR: float
    notes: list[str]
    bolt_demand_max_kN: float = 0.0
    bolt_dcr: float = 0.0


def design_splice(inp: SpliceInput) -> SpliceResult:
    """Capacidad de empalme por placas de ala y, opcionalmente, grupo de pernos mediante ``SpliceConnection``."""
    from ..splice_design import SpliceConnection

    Fy = inp.Fy_MPa * 1e6
    A = (inp.flange_plate_t_mm * inp.flange_plate_b_mm) / 1e6
    T = Fy * A
    lever_m = inp.beam_depth_mm / 1000.0
    Mn = T * lever_m
    dcr_flange = (inp.Mu_kNm * 1e3) / Mn if Mn > 0 else 99.0

    if inp.n_bolts_web <= 0:
        return SpliceResult(
            Mn_kNm=Mn / 1e3,
            DCR=dcr_flange,
            notes=[
                f"Mn = {Mn/1e3:.1f} kN*m (brazo d = {inp.beam_depth_mm:.0f} mm, Fy = {inp.Fy_MPa:.0f} MPa), DCR = {dcr_flange:.2f}",
            ],
            bolt_demand_max_kN=0.0,
            bolt_dcr=0.0,
        )

    sc = SpliceConnection(M_Ed=inp.Mu_kNm, V_Ed=inp.Vu_kN, N_Ed=0.0)
    bolt_res = sc.evaluate_bolt_group(
        n_bolts_web=inp.n_bolts_web,
        pitch=inp.pitch_mm,
        gauge=inp.gauge_mm,
        bolt_capacity=inp.bolt_capacity_kN,
    )
    bolt_dcr = bolt_res["utilization"]
    dcr = max(dcr_flange, bolt_dcr)
    return SpliceResult(
        Mn_kNm=Mn / 1e3,
        DCR=dcr,
        notes=[
            f"Mn = {Mn/1e3:.1f} kN*m (dcr_flange = {dcr_flange:.2f})",
            f"Grupo de {inp.n_bolts_web} pernos: R_max = {bolt_res['critical_bolt_force_kN']:.2f} kN vs {inp.bolt_capacity_kN:.1f} kN (dcr_bolt = {bolt_dcr:.2f})",
        ],
        bolt_demand_max_kN=bolt_res["critical_bolt_force_kN"],
        bolt_dcr=bolt_dcr,
    )
