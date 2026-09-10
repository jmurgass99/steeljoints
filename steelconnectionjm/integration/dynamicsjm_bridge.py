"""Bridge steelconnectionjm -> dynamicsjm: verifica conexiones contra demanda dinamica.

Recibe lista de demandas (M_Ed, V_Ed) por viga (tipicamente del envelope
de un pushover N2 o IDA), itera sobre las conexiones RBS definidas y verifica
que la capacidad probable de la rotula plastica cumpla con la demanda
amplificada por capacity design.

Cliente dynamicsjm duck-typed: la demanda llega como dataclass simple,
no se importa dynamicsjm directamente.

Contrato de la demanda (AC-03): `M_Ed_kNm` se clasifica junto al calculo como
MISSING / ZERO / INVALID / POSITIVE (ver `services._demanda`). Antes
`util = M_Ed / M_pr` y `is_safe = util <= 1.0`, asi que un momento NEGATIVO de
cualquier magnitud daba `util < 0` y firmaba, un cero firmaba, y un NaN contaba
como incumplimiento. Ahora `is_safe` es exactamente `calculation_status is
CALCULADO_CUMPLE`, el signo se descarta con nota (la RBS es simetrica) y lo que no
tiene veredicto se cuenta aparte (`n_sin_veredicto`), ni como seguro ni como
inseguro.
"""
from __future__ import annotations
import logging
import math
from dataclasses import dataclass, field

from jmstructural_common.audit_status import CalculationStatus, resolve_status

from ..memos.rbs_aisc358 import rbs_aisc358_memo, RBSDesignResult
from ..services._demanda import clasificar_momento, nota_de_signo

log = logging.getLogger("steelconnectionjm.dynamicsjm_bridge")


@dataclass(frozen=True)
class BeamDynamicDemand:
    """Demanda dinamica en una viga (envelope de un analisis dinamico)."""
    beam_id: str
    M_Ed_kNm: float            # momento solicitante max (kN.m); se evalua |M_Ed|
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
    utilization_ratio: float | None   # |M_demand| / M_pr; None sin demanda evaluable
    is_safe: bool                     # == calculation_status is CALCULADO_CUMPLE
    geometry_ok: bool
    notes: list[str] = field(default_factory=list)
    # Veredicto canonico (closed-by-default). Nace NO_CALCULADO.
    calculation_status: CalculationStatus = CalculationStatus.NO_CALCULADO
    missing_inputs: list[str] = field(default_factory=list)


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
    # Filas sin veredicto (NO_CALCULADO / REQUIERE_REVISION): ni seguras ni
    # inseguras. n_safe + n_unsafe + n_sin_veredicto == n_total.
    n_sin_veredicto: int = 0


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
        capacidad_ok = capacity_with_margin > 0
        dem = clasificar_momento(d.M_Ed_kNm, nombre=f"M_Ed_kNm[{d.beam_id}]")
        missing_inputs: list[str] = [] if dem.presente else [dem.motivo]
        if not capacidad_ok:
            missing_inputs.append(
                f"M_pr = {rbs.M_pr_kNm:.1f} kN.m no es una capacidad positiva")

        if dem.es_evaluable and capacidad_ok:
            util: float | None = dem.magnitud / capacity_with_margin
        elif dem.estado == "INVALID":
            util = float("nan")                 # no finito -> REQUIERE_REVISION
        else:
            util = None

        # Proof Obligation closed-by-default. `analysis_executed`: la evaluacion RBS
        # (`rbs_aisc358_memo`) acaba de ejecutarse en esta misma llamada.
        # `reinforcement_present=True` documentado: conexion de acero, sin armadura.
        # La geometria fuera de AISC 358 s5.8.1 deja la conexion fuera del alcance
        # de la precalificacion: REQUIERE_REVISION, no "OK con aviso".
        status = resolve_status(
            util,
            missing_inputs=missing_inputs,
            demand_present=dem.presente,
            capacity_present=capacidad_ok,
            analysis_executed=True,
            geometry_present=True,
            material_present=conn.Fy > 0,
            reinforcement_present=True,
            unsupported_calc=not rbs.is_geometry_ok,
        )
        is_safe = status is CalculationStatus.CALCULADO_CUMPLE
        util_publicado = util if (util is not None and math.isfinite(util)) else None

        if status is CalculationStatus.CALCULADO_CUMPLE:
            veredicto_txt = "OK"
        elif status is CalculationStatus.CALCULADO_FALLA:
            veredicto_txt = "NO CUMPLE"
        else:
            veredicto_txt = f"SIN VEREDICTO ({status})"
        notes = [
            f"M_Ed = {d.M_Ed_kNm!r} vs M_pr = {rbs.M_pr_kNm:.1f} kN.m",
            (f"Utilization = {util_publicado * 100:.1f}% ({veredicto_txt})"
             if util_publicado is not None else f"Utilization = n/a ({veredicto_txt})"),
            f"safety_margin extra aplicado = {safety_margin}",
            *nota_de_signo(dem, nombre="M_Ed_kNm"),
            *[f"Sin veredicto: {m}" for m in missing_inputs],
            *([f"Sin veredicto: {dem.motivo}"] if dem.estado == "INVALID" else []),
            *([] if rbs.is_geometry_ok else
              ["Geometria fuera de AISC 358 s5.8.1: fuera del alcance de la precalificacion"]),
        ]

        row = ConnectionCheckRow(
            beam_id=d.beam_id,
            M_demand_kNm=d.M_Ed_kNm,
            M_pr_capacity_kNm=rbs.M_pr_kNm,
            utilization_ratio=util_publicado,
            is_safe=is_safe,
            geometry_ok=rbs.is_geometry_ok,
            notes=notes,
            calculation_status=status,
            missing_inputs=missing_inputs,
        )
        report.rows.append(row)
        report.n_total += 1
        if status is CalculationStatus.CALCULADO_CUMPLE:
            report.n_safe += 1
        elif status is CalculationStatus.CALCULADO_FALLA:
            report.n_unsafe += 1
        else:
            report.n_sin_veredicto += 1
        if not rbs.is_geometry_ok:
            report.n_geometry_violations += 1
        if util_publicado is not None and util_publicado > report.max_utilization:
            report.max_utilization = util_publicado
            report.critical_beam = d.beam_id

    log.info(
        "verify_connections: %d/%d safe, %d sin veredicto (max util = %.2f en %s)",
        report.n_safe, report.n_total, report.n_sin_veredicto,
        report.max_utilization, report.critical_beam,
    )
    return report
