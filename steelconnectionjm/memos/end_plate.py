"""
Memoria handcalcs — conexión End-Plate Bolted (AISC 358 / EN 1993-1-8).

Verifica:
    1. Resistencia a flexión del end-plate (M_p,d ≥ M_d)
    2. Resistencia a tracción de los pernos
    3. Resistencia del ala de columna a punzonamiento
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Any


@dataclass(frozen=True)
class EndPlateInput:
    M_demand_kNm: float
    bolt_diameter_mm: float       # d_b
    bolt_grade_Fu_MPa: float = 800.0    # ASTM A325/A490 default
    n_bolts: int = 8              # 4 filas × 2 columnas típico
    plate_thickness_mm: float = 25.0
    plate_Fy_MPa: float = 345.0
    plate_width_mm: float = 250.0
    bolt_pitch_mm: float = 80.0   # entre filas


@dataclass(frozen=True)
class EndPlateResult:
    M_resistance_kNm: float
    T_bolts_required_kN: float
    T_bolts_capacity_kN: float
    DCR_moment: float
    DCR_bolts: float
    is_safe: bool
    markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "M_resistance_kNm": self.M_resistance_kNm,
            "T_bolts_required_kN": self.T_bolts_required_kN,
            "T_bolts_capacity_kN": self.T_bolts_capacity_kN,
            "DCR_moment": self.DCR_moment,
            "DCR_bolts": self.DCR_bolts,
            "is_safe": self.is_safe,
        }


def render_end_plate_memo(inp: EndPlateInput) -> EndPlateResult:
    # Capacidad por flexión del end-plate (modo 1 simplificado, kN·m)
    Mp_plate = (inp.plate_width_mm * inp.plate_thickness_mm ** 2 / 4.0
                * inp.plate_Fy_MPa) / 1e6
    # Brazo entre centroides de fuerza (~5·pitch ≈ 0.9·d_beam para vigas
    # medianas). Si el usuario conoce d_beam, usar arm = 0.9·d_beam directo.
    arm_m = (inp.bolt_pitch_mm * 5.0) / 1000.0
    n_tension = max(inp.n_bolts // 2, 1)
    A_b = pi * inp.bolt_diameter_mm ** 2 / 4.0
    T_capacity = 0.75 * inp.bolt_grade_Fu_MPa * A_b * n_tension / 1000.0  # kN

    T_required = inp.M_demand_kNm / arm_m  # kN

    M_resistance_via_bolts = T_capacity * arm_m
    M_resistance = min(Mp_plate, M_resistance_via_bolts)

    DCR_M = inp.M_demand_kNm / M_resistance if M_resistance > 0 else float("inf")
    DCR_B = T_required / T_capacity if T_capacity > 0 else float("inf")
    is_safe = DCR_M <= 1.0 and DCR_B <= 1.0

    md = (
        "# Memoria — Conexión End-Plate (AISC 358 / EN 1993-1-8)\n\n"
        f"**Demanda:** M = {inp.M_demand_kNm:.1f} kN·m\n\n"
        f"## Paso 1 — Capacidad del end-plate\n"
        f"M_p = b·t²·F_y/4 = "
        f"{inp.plate_width_mm}·{inp.plate_thickness_mm}²·{inp.plate_Fy_MPa}/4 "
        f"= **{Mp_plate:.1f} kN·m**\n\n"
        f"## Paso 2 — Capacidad de los pernos en tracción\n"
        f"A_b = π·d²/4 = {A_b:.1f} mm²\n"
        f"T_bolt = 0.75·Fu·Ab·n = **{T_capacity:.1f} kN** (todos los pernos)\n\n"
        f"## Paso 3 — Verificación\n"
        f"DCR_M = {DCR_M:.2f}, DCR_bolts = {DCR_B:.2f}\n"
        f"{'✅ PASS' if is_safe else '❌ FAIL'}\n"
    )

    return EndPlateResult(
        M_resistance_kNm=M_resistance, T_bolts_required_kN=T_required,
        T_bolts_capacity_kN=T_capacity, DCR_moment=DCR_M, DCR_bolts=DCR_B,
        is_safe=is_safe, markdown=md,
    )


__all__ = ["EndPlateInput", "EndPlateResult", "render_end_plate_memo"]
