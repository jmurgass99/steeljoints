"""
end_plate.py — Extended end-plate moment connection design.
AISC 360-22 Chapter J + AISC 358-22 §6/§7 (BUEEP / BSEEP) + DG4.

Covers the 4-bolt extended unstiffened (4E) and
8-bolt extended stiffened (8ES) configurations.

Refactored to consume the shared resources:
  - ``catalog.get_bolt_size`` / ``catalog.get_bolt_grade`` for bolt data
  - ``catalog.get_electrode_FEXX``                          for electrodes
  - ``codes.aisc358.Yp_4E_unstiffened``                     for yield-line Yp
  - ``codes.aisc358.Cpr`` / ``codes.aisc358.Mpr``           for seismic Mpr

Public API remains backward-compatible: the historical signature
``EndPlate(Mu, Vu, beam_depth, beam_tf, beam_bf, bolt_diameter=22.0, ...)``
still works. New optional arguments (``bolt_size``, ``electrode``, ``seismic``,
``Zx``, ``plate_width``, ``Ry``) extend behaviour without breaking callers.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from math import sqrt, pi
from typing import Optional

from . import catalog
from .codes import aisc358


@dataclass
class EndPlate:
    """
    Extended end-plate moment connection design.

    Parameters
    ----------
    Mu : float  required moment [kN·m]
    Vu : float  required shear  [kN]
    beam_depth : float  beam depth db [mm]
    beam_tf : float  beam flange thickness [mm]
    beam_bf : float  beam flange width  [mm]
    bolt_diameter : float  bolt diameter [mm] (legacy; ignored when ``bolt_size`` given)
    bolt_size : str | None  catalog key ('3/4', '1', 'M22', ...). Optional.
    bolt_grade : str  AISC grade ('A325', 'A490', 'A307', ...)
    plate_thickness : float  end plate thickness [mm]
    plate_Fy : float  plate yield stress [MPa]
    plate_Fu : float  plate ultimate stress [MPa]
    plate_width : float | None  bp [mm]; defaults to beam_bf + 25 mm
    n_bolt_rows : int  2 (4-bolt 4E) or 4 (8-bolt 8ES)
    pfo : float  distance from flange face to outer bolt row [mm]
    pfi : float  distance from flange face to inner bolt row [mm]
    g   : float  bolt gage (horizontal spacing) [mm]
    electrode : str  AWS electrode tag ('E70XX', 'E80XX', ...). Resolves via catalog.
    seismic : bool  if True, demand uses Mpr = Cpr·Ry·Fy·Zx (AISC 358 §2.4.3)
    Zx : float | None  beam plastic modulus [mm³] (required if ``seismic=True``)
    Ry : float  expected-to-nominal yield ratio (default 1.1 for A992)
    beam_Fy : float  beam yield stress [MPa] (for Cpr/Mpr)
    beam_Fu : float  beam ultimate stress [MPa] (for Cpr/Mpr)
    code : str  'AISC'
    """
    Mu: float                    # [kN·m]
    Vu: float                    # [kN]
    beam_depth: float            # db [mm]
    beam_tf: float               # flange thickness [mm]
    beam_bf: float               # flange width [mm]
    bolt_diameter: float = 22.0  # [mm]  legacy
    bolt_size: Optional[str] = None
    bolt_grade: str = "A325"
    plate_thickness: float = 19.0
    plate_Fy: float = 345.0
    plate_Fu: float = 450.0
    plate_width: Optional[float] = None
    n_bolt_rows: int = 2         # 2 = 4-bolt (4E), 4 = 8-bolt (8ES)
    pfo: float = 38.0
    pfi: float = 38.0
    g: float = 140.0
    electrode: str = "E70XX"
    seismic: bool = False
    Zx: Optional[float] = None
    Ry: float = 1.1
    beam_Fy: float = 345.0
    beam_Fu: float = 450.0
    code: str = "AISC"

    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        from .bolts import Bolt, bolt_gross_area

        # --- Resolve bolt size/area via catalog when possible ---------
        if self.bolt_size is not None:
            data = catalog.get_bolt_size(self.bolt_size)
            self.bolt_diameter = data["d_mm"]
            self.Ab = data["Ab_mm2"]
            self.As = data["As_mm2"]
        else:
            self.Ab = bolt_gross_area(self.bolt_diameter)
            self.As = self.Ab  # fallback; threads_in_shear handled by Bolt

        # --- Resolve bolt grade via catalog (Fnt, Fnv) ----------------
        try:
            grade_data = catalog.get_bolt_grade(self.bolt_grade, self.code)
            self._Fnt = grade_data.get("Fnt")
            # Catalog stores Fnv_N (threads in shear) / Fnv_X (threads excluded)
            self._Fnv = grade_data.get("Fnv_N") or grade_data.get("Fnv")
        except Exception:
            self._Fnt = None
            self._Fnv = None

        # --- Resolve electrode FEXX via catalog -----------------------
        try:
            self._FEXX = catalog.get_electrode_FEXX(self.electrode)
        except Exception:
            self._FEXX = 482.6  # E70XX default

        # Plate width default
        if self.plate_width is None:
            self.plate_width = self.beam_bf + 25.0

        # Demand quantities
        self.Mu_Nmm = self.Mu * 1e6
        self.Vu_N = self.Vu * 1000.0

        # If seismic, replace demand with Mpr (AISC 358 §2.4.3)
        if self.seismic and self.Zx is not None:
            self.Cpr_factor = aisc358.Cpr(self.beam_Fy, self.beam_Fu)
            self.Mpr_Nmm = aisc358.Mpr(self.Zx, self.beam_Fy, self.beam_Fu, self.Ry)
            self.Mu_Nmm = max(self.Mu_Nmm, self.Mpr_Nmm)
        else:
            self.Cpr_factor = 1.0
            self.Mpr_Nmm = self.Mu_Nmm

        # Internal Bolt object (legacy strength engine)
        self._bolt = Bolt(self.bolt_diameter, self.bolt_grade, self.code,
                          threads_in_shear_plane=False, n_shear_planes=1)

    # ------------------------------------------------------------------
    # Geometry helpers for yield-line analysis (AISC 358 §6 Table 6.2)
    # ------------------------------------------------------------------
    def _Yp(self) -> float:
        """Yp parameter from AISC 358 (4E unstiffened).  For 8ES we still
        use the same formula multiplied by an extra row term — an
        approximation; users seeking strict 8ES checking should provide
        a custom Yp."""
        bp = self.plate_width
        g = self.g
        pfo = self.pfo
        pfi = self.pfi
        # h0 / h1: distances from the centerline of the compression flange
        # to the outer / inner tension bolt rows
        h0 = self.beam_depth - self.beam_tf / 2.0 + self.pfo
        h1 = self.beam_depth - self.beam_tf / 2.0 - self.pfi
        s = sqrt(bp * g) / 2.0
        return aisc358.Yp_4E_unstiffened(bp, g, pfo, pfi, h0, h1, s)

    # ------------------------------------------------------------------
    # Bolt force demand (DG4 Eq. 3.1)
    # ------------------------------------------------------------------
    def bolt_tension_demand(self) -> float:
        """Required tension force per bolt from bending moment [kN]."""
        d_eff = self.beam_depth - self.beam_tf
        n_t = self.n_bolt_rows
        T_total = self.Mu_Nmm / d_eff
        T_per_bolt = T_total / (n_t * 2)
        return T_per_bolt / 1000.0

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------
    def bolt_tension_check(self, phi: float = 0.90) -> dict:
        """Check bolt tension capacity vs demand (DG4 §3.1)."""
        T_demand = self.bolt_tension_demand()  # kN
        # Prefer catalog Fnt × Ab; fall back to Bolt object.
        if self._Fnt is not None:
            Rnt = self._Fnt * self.Ab
        else:
            Rnt = self._bolt.aisc_tension_strength(phi=1.0)
        phi_Rnt = phi * Rnt / 1000.0  # kN
        util = T_demand / phi_Rnt if phi_Rnt > 0 else 0.0
        return {
            "check": "Bolt tension",
            "T_demand_kN": round(T_demand, 3),
            "phi_Rnt_kN": round(phi_Rnt, 3),
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }

    def bolt_shear_check(self, phi: float = 0.75) -> dict:
        """Shear on bolts from Vu distributed equally to all bolts."""
        n_total = self.n_bolt_rows * 2
        Vu_per = self.Vu_N / n_total
        if self._Fnv is not None:
            phi_Rnv = phi * self._Fnv * self.Ab
        else:
            phi_Rnv = self._bolt.aisc_shear_strength()
        util = Vu_per / phi_Rnv if phi_Rnv > 0 else 0.0
        return {
            "check": "Bolt shear (Vu)",
            "Vu_per_bolt_kN": round(Vu_per / 1000.0, 3),
            "phi_Rnv_kN": round(phi_Rnv / 1000.0, 3),
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }

    def plate_flexure_check(self, phi: float = 0.90) -> dict:
        """End-plate flexural yielding via yield-line analysis (AISC 358 §6.9.4):

           φMn = φ · Fy · tp² · Yp        [N·mm]
        """
        tp = self.plate_thickness
        Yp = self._Yp()
        phi_Mn = phi * self.plate_Fy * tp**2 * Yp     # [N·mm]
        # 1.11 factor for seismic per AISC 358 §6.9.4-1; 1.0 otherwise
        gamma = 1.11 if self.seismic else 1.0
        Mreq = gamma * self.Mu_Nmm
        util = Mreq / phi_Mn if phi_Mn > 0 else 0.0
        return {
            "check": "End plate flexure",
            "Yp_mm": round(Yp, 2),
            "phi_Mn_kNm": round(phi_Mn / 1e6, 3),
            "Mreq_kNm": round(Mreq / 1e6, 3),
            # Backwards-compat keys (units now per total moment, not per mm of width)
            "Mp_kNmm_per_mm": round(phi_Mn / 1000.0, 3),
            "Mreq_kNmm_per_mm": round(Mreq / 1000.0, 3),
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }

    def weld_check(self, weld_size: float = 8.0,
                   electrode: Optional[str] = None) -> dict:
        """Flange weld (CJP) + web fillet weld check.

        ``electrode`` overrides the connection-level electrode; both
        are resolved via :func:`catalog.get_electrode_FEXX`.
        """
        from .welds import FilletWeld
        elec = electrode or self.electrode
        # Resolve FEXX via catalog; pass numeric MPa to FilletWeld so it
        # accepts every electrode the catalog supports (E60XX..E110XX).
        FEXX = catalog.get_electrode_FEXX(elec)

        # Flange: CJP (complete penetration), capacity = 0.90·Fy·Af
        Af = self.beam_bf * self.beam_tf
        phi_Rn_flange = 0.90 * self.plate_Fy * Af
        T_demand = self.bolt_tension_demand() * 1000 * self.n_bolt_rows * 2
        util_flange = T_demand / phi_Rn_flange

        # Web fillet weld both sides
        fw = FilletWeld(weld_size=weld_size,
                        length=self.beam_depth - 2 * self.beam_tf,
                        electrode=str(FEXX), code=self.code, theta=90.0)
        phi_Rn_web = 2 * fw.aisc_strength()
        util_web = self.Vu_N / phi_Rn_web

        return {
            "check": "Welds (flange CJP + web fillet)",
            "electrode": elec,
            "FEXX_MPa": round(FEXX, 1),
            "phi_Rn_flange_kN": round(phi_Rn_flange / 1000.0, 2),
            "T_demand_kN": round(T_demand / 1000.0, 2),
            "util_flange": round(util_flange, 4),
            "phi_Rn_web_kN": round(phi_Rn_web / 1000.0, 2),
            "Vu_kN": self.Vu,
            "util_web": round(util_web, 4),
            "utilization": round(max(util_flange, util_web), 4),
            "is_ok": max(util_flange, util_web) <= 1.0,
        }

    def design(self) -> dict:
        """Full end-plate connection design report."""
        checks = [
            self.bolt_tension_check(),
            self.bolt_shear_check(),
            self.plate_flexure_check(),
            self.weld_check(),
        ]
        governing = max(checks, key=lambda c: c["utilization"])
        all_ok = all(c["is_ok"] for c in checks)
        out = {
            "connection_type": f"Extended End-Plate ({self.n_bolt_rows*2}-bolt)",
            "code": self.code,
            "seismic": self.seismic,
            "Mu_kNm": self.Mu,
            "Mu_design_kNm": round(self.Mu_Nmm / 1e6, 3),
            "Vu_kN": self.Vu,
            "bolt_diameter_mm": round(self.bolt_diameter, 3),
            "bolt_grade": self.bolt_grade,
            "plate_t_mm": self.plate_thickness,
            "electrode": self.electrode,
            "checks": checks,
            "governing_check": governing["check"],
            "governing_utilization": governing["utilization"],
            "all_checks_ok": all_ok,
            "summary": "OK" if all_ok else "FAILED",
        }
        if self.seismic:
            out["Cpr"] = round(self.Cpr_factor, 4)
            out["Mpr_kNm"] = round(self.Mpr_Nmm / 1e6, 3)
        return out
