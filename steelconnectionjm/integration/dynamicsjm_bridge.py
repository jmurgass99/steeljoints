"""Bridge steelconnectionjm -> dynamicsjm: verifica conexiones contra demanda dinamica.

Recibe lista de demandas (M_Ed, V_Ed) por viga (tipicamente del envelope
de un pushover N2 o IDA), itera sobre las conexiones RBS definidas y verifica
que la capacidad probable de la rotula plastica cumpla con la demanda
amplificada por capacity design.

Cliente dynamicsjm duck-typed: la demanda llega como dataclass simple,
no se importa dynamicsjm directamente.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field

from ..memos.rbs_aisc358 import rbs_aisc358_memo, RBSDesignResult

log = logging.getLogger("steelconnectionjm.dynamicsjm_bridge")


@dataclass(frozen=True)
class BeamDynamicDemand:
    """Demanda dinamica en una viga (envelope de un analisis dinamico)."""
    beam_id: str
    M_Ed_kNm: float            # momento solicitante max (kN.m)
    V_Ed_kN: float              # cortante max (kN)
    analysis_label: str = ""    # 'pushover' | 'IDA' | etc.


@dataclass(frozen=True)
class RBSConnectionDefinition:
    """Definicion geometrica de una conexion RBS para una viga."""
    beam_id: str                # debe coincidir con BeamDynamicDemand.beam_id
    beam_d: float               # mm
    beam_bf: float              # mm
    beam_tf: float              # mm
    beam_Z_x: float             # mm3
    a: float                    # mm
    b: float                    # mm
    c: float                    # mm
    L_clear: float              # m
    wu: float                   # kN/m (carga gravitacional)
    Fy: float = 345.0           # MPa
    Ry: float = 1.1
    Cpr: float = 1.15


@dataclass
class ConnectionCheckRow:
    """Una fila del reporte: una conexion vs su demanda."""
    beam_id: str
    M_demand_kNm: float
    M_pr_capacity_kNm: float
    utilization_ratio: float     # M_demand / M_pr (<=1.0 OK)
    is_safe: bool
    geometry_ok: bool
    notes: list[str] = field(default_factory=list)


@dataclass
class BridgeReport:
    """Reporte global de verificacion."""
    n_total: int
    n_safe: int
    n_unsafe: int
    n_geometry_violations: int
    rows: list[ConnectionCheckRow] = field(default_factory=list)
    max_utilization: float = 0.0
    critical_beam: str = ""


def verify_connections_vs_demand(connections: list[RBSConnectionDefinition], demands: list[BeamDynamicDemand],
                                     safety_margin: float = 1.0):
    """Verifica una lista de conexiones contra una lista de demandas.

    Args:
        connections: iterable[RBSConnectionDefinition]
        demands: iterable[BeamDynamicDemand]
        safety_margin: multiplicador adicional sobre la capacidad (1.0 = solo
            el factor de Cpr*Ry del calculo RBS).

    Returns:
        BridgeReport con detalle fila a fila y resumen.

    Raises:
        ValueError si hay duplicados o beam_id no encontrados.
    """
    connections = list(connections)
    demands = list(demands)
    if not connections:
        raise ValueError("connections no puede estar vacio")
    if not demands:
        raise ValueError("demands no puede estar vacio")
    if safety_margin <= 0:
        raise ValueError("safety_margin debe ser > 0")

    conn_by_id = {c.beam_id: c for c in connections}
    if len(conn_by_id) != len(connections):
        raise ValueError("beam_id duplicado en connections")

    report = BridgeReport(n_total=0, n_safe=0, n_unsafe=0, n_geometry_violations=0)

    for d in demands:
        conn = conn_by_id.get(d.beam_id)
        if conn is None:
            raise ValueError(f"demand para beam_id='{d.beam_id}' sin conexion definida")

        _, rbs = rbs_aisc358_memo(
            beam_d=conn.beam_d, beam_bf=conn.beam_bf, beam_tf=conn.beam_tf,
            beam_Z_x=conn.beam_Z_x, a=conn.a, b=conn.b, c=conn.c,
            L_clear=conn.L_clear, wu=conn.wu,
            Fy=conn.Fy, Ry=conn.Ry, Cpr=conn.Cpr,
        )

        capacity_with_margin = rbs.M_pr_kNm / safety_margin
        util = d.M_Ed_kNm / capacity_with_margin if capacity_with_margin > 0 else float("inf")
        is_safe = util <= 1.0 and rbs.is_geometry_ok

        row = ConnectionCheckRow(
            beam_id=d.beam_id,
            M_demand_kNm=d.M_Ed_kNm,
            M_pr_capacity_kNm=rbs.M_pr_kNm,
            utilization_ratio=util,
            is_safe=is_safe,
            geometry_ok=rbs.is_geometry_ok,
            notes=[
                f"M_Ed = {d.M_Ed_kNm:.1f} vs M_pr = {rbs.M_pr_kNm:.1f} kN.m",
                f"Utilization = {util*100:.1f}% ({'OK' if is_safe else 'NO CUMPLE'})",
                f"safety_margin extra aplicado = {safety_margin}",
            ],
        )
        report.rows.append(row)
        report.n_total += 1
        if is_safe:
            report.n_safe += 1
        else:
            report.n_unsafe += 1
        if not rbs.is_geometry_ok:
            report.n_geometry_violations += 1
        if util > report.max_utilization:
            report.max_utilization = util
            report.critical_beam = d.beam_id

    log.info(
        "verify_connections: %d/%d safe (max util = %.2f en %s)",
        report.n_safe, report.n_total, report.max_utilization, report.critical_beam,
    )
    return report
