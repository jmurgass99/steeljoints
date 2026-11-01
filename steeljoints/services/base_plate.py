"""Servicio: placa base de columna (delega en ``steeljoints.base_plate.BasePlate``)."""
from __future__ import annotations
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
    """AISC Design Guide 1 para compresión centrada: aplastamiento y espesor.

    Delega en ``BasePlate``: fp = Pu/A1 frente a φc·0,85·f'c (φc = 0,65, A2/A1 = 1) y
    tp,req = l·√(2·fp/(0,9·Fy)) con l = máx(m, n, λn'). ``DCR`` es el mayor de fp/φFp y tp,req/tp.
    Hasta la versión 1.1 el espesor usaba solo m y sin el 0,9, y el DCR ignoraba el espesor dado.
    El momento no se evalúa aquí (la presión no es uniforme y faltan los anclajes): usa la clase.
    """
    from ..base_plate import BasePlate
    if inp.tp_mm <= 0:
        raise ValueError("tp_mm debe ser > 0")
    bp = BasePlate(Pu=inp.Pu_kN, Mu=0.0, column_d=inp.d_col_mm, column_bf=inp.bf_col_mm,
                   plate_B=inp.Bp_mm, plate_N=inp.Np_mm, plate_Fy=inp.fy_plate_MPa,
                   fc_concrete=inp.fc_MPa)
    bearing = bp.bearing_check()
    thick = bp.required_thickness()
    tp_req = thick["tp_required_mm"]
    if tp_req is None:
        raise ValueError("Pu <= 0: la placa no está comprimida; usa BasePlate para el caso con tracción")
    dcr = max(bearing["utilization"], tp_req / inp.tp_mm)
    notes = [
        f"fp = {bearing['fp_MPa']:.2f} MPa, φFp = {bearing['phi_Fp_MPa']:.2f} MPa",
        f"m = {thick['m_mm']:.1f}, n = {thick['n_mm']:.1f}, λn' = {thick['lambda_n_prime_mm']:.1f} mm → tp,req = {tp_req:.1f} mm frente a tp = {inp.tp_mm:.1f} mm",
        f"DCR = {dcr:.2f}",
    ]
    if inp.Mu_kNm:
        notes.append(f"Mu = {inp.Mu_kNm} kN·m NO evaluado por este servicio (usa BasePlate con anclajes)")
    return BasePlateResult(
        fp_actual_MPa=bearing["fp_MPa"], fp_allow_MPa=bearing["phi_Fp_MPa"],
        tp_required_mm=tp_req, DCR=dcr, notes=notes,
    )
