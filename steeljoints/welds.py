"""
welds.py — Fillet weld strength per AISC 360-22 §J2 and EN 1993-1-8 §4.5.

Covers:
  - Single fillet weld: longitudinal, transversal, and directional
  - Weld group elastic vector method
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from math import sqrt, sin, cos, pi, radians

from steeljoints._common.audit_status import CalculationStatus, resolve_status


# Electrode strengths [MPa]
_ELECTRODE_FExx: dict[str, float] = {
    "E60": 413.7,   "E70": 482.6,   "E80": 551.6,
    "E90": 620.5,   "E100": 689.5,  "E110": 758.4,
}

# EC3 correlation factor β_w
_EC3_BETA_W: dict[str, float] = {
    "S235": 0.80, "S275": 0.85, "S355": 0.90, "S420": 1.00, "S460": 1.00,
}


@dataclass
class FilletWeld:
    """
    Single fillet weld.

    Parameters
    ----------
    weld_size : float  weld leg size [mm]
    length    : float  weld length [mm]
    electrode : str    electrode classification ('E70', '8.8', etc.)
    code      : str    'AISC' or 'EC3'
    theta     : float  angle of load to weld axis [deg] (0=longitudinal, 90=transverse)
    steel_grade : str  base metal grade for EC3 (e.g. 'S355')
    """
    weld_size: float
    length: float
    electrode: str = "E70"
    code: str = "AISC"
    theta: float = 0.0      # angle of resultant force to weld longitudinal axis [deg]
    steel_grade: str = "S275"  # for EC3

    def __post_init__(self) -> None:
        self.code = self.code.upper()
        self.a = self.weld_size / sqrt(2)  # effective throat [mm]
        self.Aw = self.a * self.length     # effective weld area [mm²]

    # ------------------------------------------------------------------
    # AISC 360-22 §J2.4
    # ------------------------------------------------------------------
    def aisc_strength(self, phi: float = 0.75) -> float:
        """
        φRn for fillet weld (AISC §J2.4) with directional strength increase [N].

        Rn = Fnw · Aw  where:
          Fnw = 0.60 · FEXX · (1.0 + 0.50 · sin^1.5(θ))  (directional)
        """
        FEXX = _ELECTRODE_FExx.get(self.electrode.upper())
        if FEXX is None:
            # Try numeric: user passed e.g. "480"
            FEXX = float(self.electrode)
        theta_rad = radians(self.theta)
        dir_factor = 1.0 + 0.50 * (sin(theta_rad) ** 1.5)
        Fnw = 0.60 * FEXX * dir_factor
        Rn = Fnw * self.Aw
        return phi * Rn

    # ------------------------------------------------------------------
    # EN 1993-1-8 §4.5.3 — Directional method
    # ------------------------------------------------------------------
    def ec3_strength(self, fu: float, gamma_M2: float = 1.25) -> float:
        """
        Fw,Rd (design weld strength) per EC3-1-8 §4.5.3.2 [N].

        Parameters
        ----------
        fu : float  ultimate strength of weaker connected part [MPa]
        gamma_M2 : float  partial factor (default 1.25)

        Raises
        ------
        ValueError
            If ``steel_grade`` is absent or not in EN 1993-1-8:2005 Table 4.1.
            β_w has no normative default: assuming one silently inflates
            Fw,Rd (assuming S275's 0.85 for an S460 joint overstates the
            design resistance by 1.00/0.85 = +17.6 %).
        """
        grade = "" if self.steel_grade is None else str(self.steel_grade).strip().upper()
        beta_w = _EC3_BETA_W.get(grade)
        if beta_w is None:
            raise ValueError(
                f"Grado de acero desconocido para beta_w (EN 1993-1-8:2005 "
                f"Tabla 4.1): {self.steel_grade!r}. "
                f"Conocidos: {sorted(_EC3_BETA_W)}"
            )
        Fw_Rd = fu / (beta_w * sqrt(3) * gamma_M2) * self.a * self.length
        return Fw_Rd

    def min_size(self, t_thinner: float | None = None, t_thicker: float | None = None) -> float:
        """
        Minimum fillet weld size per AISC 360-22 Table J2.4 [mm].

        Parameters
        ----------
        t_thinner : float
            Material thickness of thinner part joined [mm] (AISC 360-22 Table J2.4
            is indexed by the thinner connected part).
        t_thicker : float, optional
            Deprecated alias for backward compatibility.
        """
        t = t_thinner if t_thinner is not None else t_thicker
        if t is None:
            raise ValueError("Must provide material thickness of thinner part joined")
        # AISC Table J2.4
        if t <= 6.35:
            return 3.175   # 1/8"
        elif t <= 12.7:
            return 4.762   # 3/16"
        elif t <= 19.05:
            return 6.35    # 1/4"
        else:
            return 8.0     # 5/16"

    def max_size(self, t_edge: float) -> float:
        """
        Maximum fillet weld size per AISC §J2.2b [mm].
        For plates < 6 mm: weld size ≤ plate thickness
        For plates ≥ 6 mm: weld size ≤ plate thickness - 2 mm
        """
        if t_edge < 6.35:
            return t_edge
        return t_edge - 2.0


@dataclass
class WeldGroup:
    """
    Group of fillet welds under eccentric shear (elastic vector method).

    Segments are defined as rectangles with centroid (x, y), length, orientation.
    """
    welds: list[FilletWeld]
    positions: list[tuple[float, float]]  # centroid (x,y) of each weld [mm]
    angles: list[float] = None  # orientation angle of each weld [deg]

    def __post_init__(self) -> None:
        n = len(self.welds)
        if self.angles is None:
            self.angles = [0.0] * n
        # Effective throat areas
        self.Aw_list = [w.Aw for w in self.welds]
        total_Aw = sum(self.Aw_list)
        # Centroid of group
        self.cx = sum(Aw * x for Aw, (x, _) in zip(self.Aw_list, self.positions)) / total_Aw
        self.cy = sum(Aw * y for Aw, (_, y) in zip(self.Aw_list, self.positions)) / total_Aw

    def polar_moment(self) -> float:
        """Ip of the weld group about its centroid [mm⁴ — as line element]."""
        Ip = 0.0
        for w, Aw, (x, y), ang in zip(self.welds, self.Aw_list, self.positions, self.angles):
            rx = x - self.cx
            ry = y - self.cy
            ang_r = radians(ang)
            # Length and throat of this specific weld segment
            L = w.length
            a = w.a
            # Ip contribution of segment (thin rect about its centroid + parallel axis)
            Ip_self = a * (L**3) / 12.0 * ((sin(ang_r))**2 + (cos(ang_r))**2)
            Ip += Ip_self + Aw * (rx**2 + ry**2)
        return Ip

    def utilization(self, Vu: float, Mu: float,
                     phi_Rn_per_unit: float) -> dict:
        """
        Elastic vector method — max stress in weld group.

        Parameters
        ----------
        Vu : float  applied shear [N]
        Mu : float  moment [N·mm]
        phi_Rn_per_unit : float  design strength per mm of weld [N/mm]

        Notes
        -----
        La ausencia se propaga como ausencia. Si falta la capacidad de diseño
        (``phi_Rn_per_unit <= 0`` o garganta nula) o el momento aplicado no es
        distribuible (``Ip <= 0`` con ``Mu != 0``), la comprobación NO se hizo:
        se emite ``utilization = inf`` / ``NO_CALCULADO`` / ``is_ok = False``,
        nunca un ``0`` que se lee como holgura. Mismo idioma que
        ``weld_group.WeldGroupElastic.utilization`` para esta misma magnitud.
        """
        total_Aw = sum(self.Aw_list)
        Ip = self.polar_moment()
        a0 = self.welds[0].a  # garganta de referencia [mm]

        missing_inputs: list[str] = []
        if not (phi_Rn_per_unit > 0):
            missing_inputs.append("phi_Rn_per_unit")
        if not (a0 > 0):
            missing_inputs.append("weld_throat_a")
        if Mu != 0.0 and not (Ip > 0):
            missing_inputs.append("polar_moment_Ip")

        fv_direct = Vu / total_Aw  # direct shear stress [N/mm²]

        max_f = 0.0
        for Aw, (x, y) in zip(self.Aw_list, self.positions):
            rx = x - self.cx
            ry = y - self.cy
            r = sqrt(rx**2 + ry**2)
            # Ip <= 0 solo llega aquí con Mu == 0 (si no, ya está en missing).
            ft = Mu * r / Ip if Ip > 0 else 0.0
            # r == 0 es el centroide: ahí ft == 0 y el término cruzado se
            # anula de veras — coseno director legítimamente nulo.
            f_total = sqrt(fv_direct**2 + ft**2 + 2 * fv_direct * ft * (ry / r if r > 0 else 0.0))
            max_f = max(max_f, f_total)

        if missing_inputs:
            util = float("inf")
        else:
            util = max_f / (phi_Rn_per_unit / a0)
        # Proof Obligation closed-by-default: este calculo declara, condicion por
        # condicion, que verifico. Nada de `True` de cortesia -- cada una sale de un
        # predicado real sobre los datos de la soldadura.
        #
        # `reinforcement_present` es True y esta documentado: una comprobacion de
        # cordon de soldadura no toma armadura como input, asi que no puede faltar
        # aqui. `material_present` es la resistencia de calculo del cordon
        # (`phi_Rn_per_unit`), que es el dato derivado del material en este modulo.
        status = resolve_status(
            util,
            missing_inputs=missing_inputs,
            demand_present=(Vu != 0.0 or Mu != 0.0),
            capacity_present=phi_Rn_per_unit > 0,
            material_present=phi_Rn_per_unit > 0,
            analysis_executed=bool(self.welds) and total_Aw > 0,
            geometry_present=a0 > 0 and total_Aw > 0,
            reinforcement_present=True,
        )
        return {
            "max_stress_N_mm2": round(max_f, 3),
            "utilization": round(util, 4),
            "is_ok": status is CalculationStatus.CALCULADO_CUMPLE,
            "status": status,
            "missing_inputs": missing_inputs,
        }
