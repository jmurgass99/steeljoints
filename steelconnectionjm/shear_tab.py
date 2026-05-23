"""
shear_tab.py — Single-plate shear connection (shear tab) design.
AISC 360-22 §J + AISC Manual Part 10 (Table 10-9).
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt
from .bolts import Bolt
from .block_shear import block_shear_strength


@dataclass
class ShearTab:
    """
    Single-plate (shear tab) simple shear connection.

    Parameters
    ----------
    Vu : float  required shear [kN]
    bolt_diameter : float  [mm]
    bolt_grade : str  e.g. 'A325'
    n_bolts : int  number of bolts in vertical line
    bolt_spacing : float  vertical spacing between bolts [mm] (default 75)
    edge_dist : float  vertical edge distance [mm] (default 38)
    plate_thickness : float  plate thickness [mm]
    plate_width : float  plate width (horizontal) [mm]
    Fy_plate : float  plate yield stress [MPa]
    Fu_plate : float  plate ultimate stress [MPa]
    code : str  'AISC'
    phi : float  resistance factor (AISC = 0.75 shear, 0.90 gross yielding)

    Examples
    --------
    >>> tab = ShearTab(Vu=120.0, bolt_diameter=19.05, bolt_grade='A325',
    ...                n_bolts=3, plate_thickness=9.5, plate_width=75.0)
    >>> r = tab.design()
    >>> print(r['summary'])
    """
    Vu: float                    # required shear [kN]
    bolt_diameter: float = 19.05 # 3/4"
    bolt_grade: str = "A325"
    n_bolts: int = 3
    bolt_spacing: float = 75.0   # [mm]
    edge_dist_v: float = 38.0    # vertical edge dist [mm]
    edge_dist_h: float = 38.0    # horizontal edge dist [mm]
    plate_thickness: float = 9.5
    plate_width: float = 75.0
    Fy_plate: float = 345.0      # A36 Fy [MPa]
    Fu_plate: float = 450.0      # A36 Fu [MPa]
    code: str = "AISC"

    def __post_init__(self) -> None:
        self.Vu_N = self.Vu * 1000
        self.bolt = Bolt(
            diameter=self.bolt_diameter,
            grade=self.bolt_grade,
            code=self.code,
            threads_in_shear_plane=True,
            n_shear_planes=1,
        )
        self.plate_height = (self.n_bolts - 1) * self.bolt_spacing + 2 * self.edge_dist_v

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------
    def bolt_shear(self) -> dict:
        phi_Rn_bolt = self.bolt.aisc_shear_strength()
        phi_Rn_group = phi_Rn_bolt * self.n_bolts
        util = self.Vu_N / phi_Rn_group
        return {
            "check": "Bolt group shear",
            "phi_Rn_kN": round(phi_Rn_group / 1000, 2),
            "Vu_kN": self.Vu,
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }

    def bolt_bearing(self) -> dict:
        # Clear distance = spacing - hole diameter (hole = d + 2mm per AISC)
        dh = self.bolt_diameter + 2.0
        lc_interior = self.bolt_spacing - dh
        lc_edge = self.edge_dist_v - dh / 2

        Rn_int  = self.bolt.aisc_bearing_strength(
            self.plate_thickness, self.Fu_plate, lc_interior) * (self.n_bolts - 1)
        Rn_edge = self.bolt.aisc_bearing_strength(
            self.plate_thickness, self.Fu_plate, lc_edge)
        phi_Rn = Rn_int + Rn_edge
        util = self.Vu_N / phi_Rn
        return {
            "check": "Bolt bearing on plate",
            "phi_Rn_kN": round(phi_Rn / 1000, 2),
            "Vu_kN": self.Vu,
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }

    def plate_shear_yielding(self) -> dict:
        """Plate shear yielding: φRn = φ·0.60·Fy·Ag  (φ=1.0)"""
        Ag = self.plate_thickness * self.plate_height
        phi_Rn = 1.0 * 0.60 * self.Fy_plate * Ag
        util = self.Vu_N / phi_Rn
        return {
            "check": "Plate shear yielding",
            "phi_Rn_kN": round(phi_Rn / 1000, 2),
            "Vu_kN": self.Vu,
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }

    def plate_shear_rupture(self) -> dict:
        """Plate shear rupture: φRn = φ·0.60·Fu·Anv  (φ=0.75)"""
        dh = self.bolt_diameter + 2.0
        Anv = (self.plate_height - self.n_bolts * dh) * self.plate_thickness
        phi_Rn = 0.75 * 0.60 * self.Fu_plate * Anv
        util = self.Vu_N / phi_Rn
        return {
            "check": "Plate shear rupture",
            "phi_Rn_kN": round(phi_Rn / 1000, 2),
            "Vu_kN": self.Vu,
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }

    def plate_block_shear(self) -> dict:
        dh = self.bolt_diameter + 2.0
        tp = self.plate_thickness
        # Shear paths
        Agv = (self.plate_height - self.edge_dist_v) * tp
        Anv = Agv - (self.n_bolts - 0.5) * dh * tp
        # Tension path
        Ant = (self.plate_width - self.edge_dist_h - dh / 2) * tp
        result = block_shear_strength(
            Agv, Anv, Ant,
            self.Fy_plate, self.Fu_plate,
            Ubs=1.0, code="AISC"
        )
        util = self.Vu_N / result["phi_Rn_N"]
        return {
            "check": "Block shear",
            **result,
            "Vu_kN": self.Vu,
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }

    # ------------------------------------------------------------------
    # Full design
    # ------------------------------------------------------------------
    def design(self) -> dict:
        """
        Run all checks and return complete design report.

        Returns
        -------
        dict with all checks, governing utilization, and pass/fail.
        """
        checks = [
            self.bolt_shear(),
            self.bolt_bearing(),
            self.plate_shear_yielding(),
            self.plate_shear_rupture(),
            self.plate_block_shear(),
        ]

        governing = max(checks, key=lambda c: c["utilization"])
        all_ok = all(c["is_ok"] for c in checks)

        return {
            "connection_type": "Single-Plate Shear Tab",
            "code": self.code,
            "Vu_kN": self.Vu,
            "n_bolts": self.n_bolts,
            "bolt_diameter_mm": self.bolt_diameter,
            "bolt_grade": self.bolt_grade,
            "plate_t_mm": self.plate_thickness,
            "plate_h_mm": round(self.plate_height, 1),
            "checks": checks,
            "governing_check": governing["check"],
            "governing_utilization": governing["utilization"],
            "all_checks_ok": all_ok,
            "summary": "✅ OK" if all_ok else "❌ FAILED",
        }
