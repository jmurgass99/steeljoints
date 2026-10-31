# -*- coding: utf-8 -*-
"""Soldaduras de ranura — penetracion completa (CJP) y parcial (PJP).

AISC 360-22 §J2.1 (garganta efectiva) y Tabla J2.5 (resistencia):

  CJP  : la soldadura DESARROLLA el metal base. La resistencia la gobierna el
         metal base (fluencia phi=0.90 Fy·A o rotura phi=0.75 Fu·A).
  PJP  : resistencia por la garganta efectiva E. Traccion/cortante normal al eje:
         Rn = 0.60·FEXX·(E·L); ademas se acota por el metal base.

Garganta efectiva PJP (Tabla J2.1): segun tipo de ranura, angulo y proceso.
"""
from __future__ import annotations

from dataclasses import dataclass

from .exceptions import GeometryError

PHI_Y, PHI_R, PHI_W = 0.90, 0.75, 0.75   # fluencia, rotura, soldadura
_ELECTRODE = {"E60": 415.0, "E70": 485.0, "E80": 550.0}  # FEXX (MPa)


def _fexx(electrode: str) -> float:
    v = _ELECTRODE.get(electrode.upper())
    return v if v is not None else float(electrode)


@dataclass(frozen=True)
class GrooveWeldResult:
    Rn_kN: float
    Rd_kN: float          # phi·Rn
    governs: str          # 'metal_base' o 'soldadura'


def cjp_strength(Fy_MPa: float, Fu_MPa: float, area_mm2: float,
                 load: str = "tension") -> GrooveWeldResult:
    """CJP: resistencia gobernada por el metal base (la soldadura desarrolla el metal)."""
    if min(Fy_MPa, Fu_MPa, area_mm2) <= 0:
        raise GeometryError("Fy, Fu, area deben ser > 0")
    if load in ("tension", "compression"):
        Rn_y = Fy_MPa * area_mm2          # fluencia
        Rn_r = Fu_MPa * area_mm2          # rotura
        Rd = min(PHI_Y * Rn_y, PHI_R * Rn_r)
        Rn = min(Rn_y, Rn_r)
    elif load == "shear":
        Rn = 0.6 * Fy_MPa * area_mm2
        Rd = PHI_Y * Rn
    else:
        raise GeometryError("load debe ser tension/compression/shear")
    return GrooveWeldResult(Rn_kN=Rn / 1e3, Rd_kN=Rd / 1e3, governs="metal_base")


def pjp_effective_throat(groove_depth_mm: float, groove_angle_deg: float = 60.0,
                         process: str = "SMAW") -> float:
    """Garganta efectiva E de una soldadura PJP (AISC Tabla J2.1, aprox.).

    Ranura en V/bisel: si angulo >= 60deg, E = profundidad; si 45<=angulo<60,
    E = profundidad − 3 mm (procesos SMAW/GMAW). Otros casos: E = profundidad.
    """
    if groove_depth_mm <= 0:
        raise GeometryError("profundidad de ranura debe ser > 0")
    if groove_angle_deg < 45.0:
        raise GeometryError("angulo de ranura PJP < 45deg no recomendado")
    if 45.0 <= groove_angle_deg < 60.0 and process.upper() in ("SMAW", "GMAW", "FCAW"):
        return max(groove_depth_mm - 3.0, 0.0)
    return groove_depth_mm


def pjp_strength(electrode: str, throat_mm: float, length_mm: float,
                 Fy_base_MPa: float, t_base_mm: float, load: str = "tension") -> GrooveWeldResult:
    """PJP: resistencia por garganta efectiva, acotada por el metal base."""
    if min(throat_mm, length_mm, Fy_base_MPa, t_base_mm) <= 0:
        raise GeometryError("throat, length, Fy_base, t_base deben ser > 0")
    FEXX = _fexx(electrode)
    Awe = throat_mm * length_mm
    Rn_weld = 0.60 * FEXX * Awe                     # N (traccion/cortante en garganta)
    Rd_weld = PHI_W * Rn_weld
    # Metal base (fluencia del area conectada t_base·L).
    Rn_base = (0.6 if load == "shear" else 1.0) * Fy_base_MPa * t_base_mm * length_mm
    Rd_base = PHI_Y * Rn_base
    if Rd_weld <= Rd_base:
        return GrooveWeldResult(Rn_kN=Rn_weld / 1e3, Rd_kN=Rd_weld / 1e3, governs="soldadura")
    return GrooveWeldResult(Rn_kN=Rn_base / 1e3, Rd_kN=Rd_base / 1e3, governs="metal_base")


__all__ = ["GrooveWeldResult", "cjp_strength", "pjp_effective_throat", "pjp_strength"]
