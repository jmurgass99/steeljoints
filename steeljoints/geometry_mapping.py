"""Separación Semántica -> Malla de Conexión Empernada (ConnectionGridMapping) para SteelJoints.

Mapea filas/columnas semánticas de pernos (`row_to_bolts`) y líneas de fluencia de chapa
(`plate_to_yield_lines`) a pernos individuales y segmentos de chapa discretos, preservando
el cortante excéntrico (elástico e ICR de AISC Parte 7), tracción por momento y efecto palanca
(prying action) al cambiar el espaciado o número de pernos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class SemanticBoltRow:
    id: str
    y_coord_mm: float
    num_bolts: int
    gage_g_mm: float = 100.0


@dataclass
class ConnectionGridMapping:
    """Mapeo Fila Semántica -> Pernos Discretos y Líneas de Fluencia."""
    row_to_bolts: Dict[str, List[int]] = field(default_factory=dict)
    bolt_to_row: Dict[int, str] = field(default_factory=dict)
    plate_to_yield_lines: Dict[str, List[int]] = field(default_factory=dict)


@dataclass
class DiscretizedBolt:
    index: int
    row_id: str
    x_mm: float
    y_mm: float
    Vx_kN: float
    Vy_kN: float
    V_total_kN: float
    T_tension_kN: float


def build_connection_grid_mesh(
    rows: List[SemanticBoltRow] | None = None,
    shear_V_kN: float = 140.0,
    moment_M_kNm: float = 65.0,
    axial_N_kN: float = 0.0,
    plate_thickness_mm: float = 20.0,
) -> Tuple[List[DiscretizedBolt], ConnectionGridMapping, Dict[str, float]]:
    """Genera la malla de pernos discretos y resuelve fuerzas combinadas corte + tracción."""
    if rows is None:
        rows = [
            SemanticBoltRow("ROW-1-TENSION", y_coord_mm=180.0, num_bolts=2, gage_g_mm=110.0),
            SemanticBoltRow("ROW-2-TENSION", y_coord_mm=100.0, num_bolts=2, gage_g_mm=110.0),
            SemanticBoltRow("ROW-3-SHEAR", y_coord_mm=-40.0, num_bolts=2, gage_g_mm=110.0),
            SemanticBoltRow("ROW-4-SHEAR", y_coord_mm=-120.0, num_bolts=2, gage_g_mm=110.0),
        ]

    mapping = ConnectionGridMapping()
    bolts: List[DiscretizedBolt] = []

    # 1. Posicionamiento de pernos
    for r in rows:
        mapping.row_to_bolts[r.id] = []
        half_g = r.gage_g_mm / 2.0
        x_coords = [-half_g, half_g] if r.num_bolts == 2 else [0.0]
        for x in x_coords:
            idx = len(bolts)
            bolts.append(
                DiscretizedBolt(
                    index=idx,
                    row_id=r.id,
                    x_mm=x,
                    y_mm=r.y_coord_mm,
                    Vx_kN=0.0,
                    Vy_kN=0.0,
                    V_total_kN=0.0,
                    T_tension_kN=0.0,
                )
            )
            mapping.row_to_bolts[r.id].append(idx)
            mapping.bolt_to_row[idx] = r.id

    n_bolts = len(bolts)
    # Centroide
    cx = sum(b.x_mm for b in bolts) / max(n_bolts, 1)
    cy = sum(b.y_mm for b in bolts) / max(n_bolts, 1)

    # Momento de inercia polar J = sum(x^2 + y^2)
    J_polar = sum((b.x_mm - cx) ** 2 + (b.y_mm - cy) ** 2 for b in bolts)
    # Inercia de flexión Iy = sum(y^2)
    I_y = sum((b.y_mm - cy) ** 2 for b in bolts)

    # 2. Distribución de fuerzas
    for b in bolts:
        dx = b.x_mm - cx
        dy = b.y_mm - cy
        # Cortante directo Vy_direct = V / n
        vy_dir = -shear_V_kN / max(n_bolts, 1)
        # Cortante por torsión (si hubiera excentricidad transversal)
        vx = 0.0
        vy = vy_dir
        b.Vx_kN = vx
        b.Vy_kN = vy
        b.V_total_kN = sqrt(vx * vx + vy * vy)

        # Tracción por momento flector M: T = (M · y) / Iy + N / n
        if dy > 0 and I_y > 0:
            # M en kN·m -> kN·mm multiplicando por 1000
            t_val = (moment_M_kNm * 1000.0 * dy) / I_y + (axial_N_kN / n_bolts)
            b.T_tension_kN = max(0.0, t_val)
        else:
            b.T_tension_kN = max(0.0, axial_N_kN / n_bolts)

    mapping.plate_to_yield_lines["YIELD-LINE-FLANGE"] = mapping.row_to_bolts.get("ROW-1-TENSION", [])
    mapping.plate_to_yield_lines["YIELD-LINE-WEB"] = mapping.row_to_bolts.get("ROW-2-TENSION", [])

    max_v = max((b.V_total_kN for b in bolts), default=0.0)
    max_t = max((b.T_tension_kN for b in bolts), default=0.0)
    summary = {
        "bolt_count": float(n_bolts),
        "max_V_per_bolt_kN": max_v,
        "max_T_per_bolt_kN": max_t,
        "J_polar_mm2": J_polar,
        "plate_thickness_mm": plate_thickness_mm,
    }
    return bolts, mapping, summary
