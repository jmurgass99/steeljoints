"""Servicio: placa base de columna (delega en ``steeljoints.base_plate.BasePlate``)."""
from __future__ import annotations
from dataclasses import dataclass
from math import pi, sqrt


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
    n_anchors: int = 4
    anchor_diameter_mm: float = 25.4
    anchor_Fut_MPa: float = 827.0
    anchor_edge_distance_mm: float = 50.0


@dataclass(frozen=True)
class BasePlateResult:
    fp_actual_MPa: float
    fp_allow_MPa: float
    tp_required_mm: float
    DCR: float
    notes: list[str]
    T_anchor_per_bolt_kN: float = 0.0
    Y_bearing_mm: float | None = None


def design_base_plate(inp: BasePlateInput) -> BasePlateResult:
    """AISC Design Guide 1 para compresión centrada o flexocompresión.

    Delega en ``BasePlate``:
    - Cuando ``Mu_kNm == 0``: fp = Pu/A1 frente a φc·0,85·f'c (φc = 0,65, A2/A1 = 1) y
      tp,req = l·√(2·fp/(0,9·Fy)) con l = máx(m, n, λn'). ``DCR`` es el mayor de fp/φFp y tp,req/tp.
    - Cuando ``Mu_kNm != 0``: evalúa excentricidad e = Mu/Pu según AISC DG1 §3.4/§3.5
      (bloque equivalente de longitud Y, presión máxima fp y tracción en anclajes Tu).
    """
    from ..base_plate import BasePlate
    if inp.tp_mm <= 0:
        raise ValueError("tp_mm debe ser > 0")
    bp = BasePlate(
        Pu=inp.Pu_kN,
        Mu=inp.Mu_kNm,
        column_d=inp.d_col_mm,
        column_bf=inp.bf_col_mm,
        plate_B=inp.Bp_mm,
        plate_N=inp.Np_mm,
        plate_Fy=inp.fy_plate_MPa,
        fc_concrete=inp.fc_MPa,
        n_anchors=inp.n_anchors,
        anchor_diameter=inp.anchor_diameter_mm,
        anchor_Fut=inp.anchor_Fut_MPa,
    )
    bearing = bp.bearing_check()
    thick = bp.required_thickness()
    tp_req = thick["tp_required_mm"]
    if tp_req is None:
        raise ValueError("Pu <= 0: la placa no está comprimida; usa BasePlate para el caso con tracción")

    if inp.Mu_kNm == 0.0:
        dcr = max(bearing["utilization"], tp_req / inp.tp_mm)
        notes = [
            f"fp = {bearing['fp_MPa']:.2f} MPa, φFp = {bearing['phi_Fp_MPa']:.2f} MPa",
            f"m = {thick['m_mm']:.1f}, n = {thick['n_mm']:.1f}, λn' = {thick['lambda_n_prime_mm']:.1f} mm → tp,req = {tp_req:.1f} mm frente a tp = {inp.tp_mm:.1f} mm",
            f"DCR = {dcr:.2f}",
        ]
        return BasePlateResult(
            fp_actual_MPa=bearing["fp_MPa"],
            fp_allow_MPa=bearing["phi_Fp_MPa"],
            tp_required_mm=tp_req,
            DCR=dcr,
            notes=notes,
            T_anchor_per_bolt_kN=0.0,
            Y_bearing_mm=inp.Np_mm,
        )

    ecc = bp.dg1_eccentric_pressure(edge_dist_f_mm=inp.anchor_edge_distance_mm)
    fp_ecc = ecc["fp_MPa"]
    phi_Fp = bearing["phi_Fp_MPa"]
    Y_mm = ecc["Y_mm"]
    m_mm = (inp.Np_mm - 0.95 * inp.d_col_mm) / 2.0
    n_mm = (inp.Bp_mm - 0.80 * inp.bf_col_mm) / 2.0
    l_cant = max(abs(m_mm), abs(n_mm))
    tp_req_ecc = max(tp_req, l_cant * sqrt(2.0 * fp_ecc / (0.9 * inp.fy_plate_MPa)))
    Ab = pi * inp.anchor_diameter_mm**2 / 4.0
    phi_Rnt_kN = 0.75 * 0.75 * inp.anchor_Fut_MPa * Ab / 1000.0
    T_bolt_kN = ecc["Tu_per_bolt_kN"]
    dcr_anchor = T_bolt_kN / phi_Rnt_kN if phi_Rnt_kN > 0 else 0.0
    dcr_bearing = (fp_ecc / phi_Fp) if ecc["is_bearing_ok"] else max(fp_ecc / phi_Fp, 1.05)
    dcr = max(dcr_bearing, tp_req_ecc / inp.tp_mm, dcr_anchor)
    notes = [
        f"DG1 ({ecc['regime']}): e = {ecc['e_mm']:.1f} mm (e_crit = {ecc['e_crit_mm']:.1f} mm), Y = {Y_mm:.1f} mm",
        f"fp = {fp_ecc:.2f} MPa, φFp = {phi_Fp:.2f} MPa, tp,req = {tp_req_ecc:.1f} mm",
        f"Tu/perno = {T_bolt_kN:.2f} kN vs φRnt = {phi_Rnt_kN:.2f} kN → DCR = {dcr:.2f}",
    ]
    return BasePlateResult(
        fp_actual_MPa=fp_ecc,
        fp_allow_MPa=phi_Fp,
        tp_required_mm=round(tp_req_ecc, 2),
        DCR=dcr,
        notes=notes,
        T_anchor_per_bolt_kN=T_bolt_kN,
        Y_bearing_mm=Y_mm,
    )
