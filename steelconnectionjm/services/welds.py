"""Servicio: soldaduras de filete (AISC J2.4 directional)."""
from __future__ import annotations
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class FilletWeldInput:
    leg_size_mm: float
    length_mm: float
    electrode_FEXX_MPa: float = 482.0
    angle_load_deg: float = 0.0


@dataclass(frozen=True)
class FilletWeldResult:
    throat_mm: float
    Rn_kN: float
    Rd_kN: float
    directional_factor: float
    notes: list[str]


def design_fillet_weld(inp: FilletWeldInput) -> FilletWeldResult:
    """AISC J2.4: Rn = 0.6*FEXX*(1 + 0.5*sin^1.5(theta))*tw*L."""
    throat = 0.707 * inp.leg_size_mm / 1000
    theta = math.radians(inp.angle_load_deg)
    direc = 1.0 + 0.5 * math.sin(theta) ** 1.5
    L = inp.length_mm / 1000
    fexx = inp.electrode_FEXX_MPa * 1e6
    Rn = 0.6 * fexx * direc * throat * L
    phi = 0.75
    Rd = phi * Rn
    return FilletWeldResult(
        throat_mm=throat * 1000,
        Rn_kN=Rn / 1e3, Rd_kN=Rd / 1e3,
        directional_factor=direc,
        notes=[
            f"Throat = {throat*1000:.2f} mm",
            f"Factor direccional = {direc:.3f} (theta={inp.angle_load_deg} deg)",
            f"Rn = {Rn/1e3:.1f} kN, phiRn = {Rd/1e3:.1f} kN",
        ],
    )
