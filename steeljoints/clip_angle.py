"""
clip_angle.py — Double-angle (clip angle) shear connection.

Conexión simple a cortante donde dos ángulos conectan el alma de la viga al
elemento soportante (columna o viga). Pernos en el alma de la viga (corte
doble) y en el ala saliente del soportante (corte simple o tensión a
prying si hay momento accidental).

Verificaciones (AISC 360-22 Chapter J + AISC Manual Part 10 Table 10-1):
  1. Cortante de pernos del alma  (doble corte, 2 ángulos)
  2. Aplastamiento de pernos en el alma de la viga
  3. Aplastamiento de pernos en el ala del ángulo
  4. Cortante de pernos del soporte (corte simple)
  5. Fluencia bruta del ángulo a cortante (φ=1.00·0.60·Fy·Agv)
  6. Rotura neta del ángulo a cortante     (φ=0.75·0.60·Fu·Anv)
  7. Block shear del ángulo
  8. Block shear del alma de la viga acoplada (AISC J4.3)
Unidades: kN para fuerzas externas, mm/MPa/N internamente.
"""
from __future__ import annotations
from dataclasses import dataclass
from .bolts import Bolt
from .block_shear import block_shear_strength


@dataclass
class ClipAngle:
    """
    Conexión de doble ángulo a cortante.

    Parameters
    ----------
    Vu : float                 cortante requerido [kN]
    n_bolts : int              número de pernos en línea vertical (alma)
    bolt_diameter : float      [mm]
    bolt_grade : str           e.g. 'A325'
    bolt_spacing : float       espaciamiento vertical [mm] (típ. 75)
    edge_dist_v : float        distancia al borde vertical del ángulo [mm]
    edge_dist_h : float        distancia al borde horizontal (gage) [mm]
    angle_thickness : float    t del ángulo [mm]
    angle_leg : float          longitud del lado del ángulo [mm]
    beam_tw : float            espesor del alma de la viga [mm]
    Fy_angle : float, Fu_angle : float
    Fy_beam  : float, Fu_beam  : float
    code : str  'AISC'
    """
    Vu: float
    n_bolts: int = 3
    bolt_diameter: float = 19.05
    bolt_grade: str = "A325"
    bolt_spacing: float = 75.0
    edge_dist_v: float = 38.0
    edge_dist_h: float = 38.0
    angle_thickness: float = 9.5
    angle_leg: float = 100.0
    beam_tw: float = 8.0
    Fy_angle: float = 248.0   # A36
    Fu_angle: float = 400.0
    Fy_beam: float = 345.0    # A572-50
    Fu_beam: float = 450.0
    # Distancia transversal del eje de pernos al borde del alma de la viga
    # acoplada (típ. coped beam: gage_to_edge ≈ end-coping clearance).
    # Default ≈ 1.5·d_bolt ≈ 30 mm si no se especifica.
    beam_gage_to_edge: float = 35.0
    code: str = "AISC"

    def __post_init__(self) -> None:
        self.Vu_N = self.Vu * 1000.0
        self.angle_height = (self.n_bolts - 1) * self.bolt_spacing + 2 * self.edge_dist_v
        # Pernos del alma: corte doble (atraviesan dos ángulos + alma)
        self.bolt_web = Bolt(diameter=self.bolt_diameter, grade=self.bolt_grade,
                             code=self.code, threads_in_shear_plane=True,
                             n_shear_planes=2)
        # Pernos del soporte: corte simple, pero hay 2 ángulos ⇒ 2 pernos por fila
        # actuando juntos. Cada perno es corte simple.
        self.bolt_sup = Bolt(diameter=self.bolt_diameter, grade=self.bolt_grade,
                             code=self.code, threads_in_shear_plane=True,
                             n_shear_planes=1)

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------
    def bolt_shear_web(self) -> dict:
        """Pernos del alma: n pernos × 2 planos de corte."""
        phi_Rn = self.bolt_web.aisc_shear_strength() * self.n_bolts
        util = self.Vu_N / phi_Rn
        return {"check": "Bolt shear (web, double shear)",
                "phi_Rn_kN": round(phi_Rn / 1000, 2),
                "Vu_kN": self.Vu, "utilization": round(util, 4),
                "is_ok": util <= 1.0}

    def bolt_shear_support(self) -> dict:
        """Pernos del soporte: 2 ángulos × n pernos, cada uno en corte simple.
        Cada fila tiene 2 pernos (uno por ángulo); total = 2·n pernos."""
        phi_Rn = self.bolt_sup.aisc_shear_strength() * (2 * self.n_bolts)
        util = self.Vu_N / phi_Rn
        return {"check": "Bolt shear (support, single shear ×2 angles)",
                "phi_Rn_kN": round(phi_Rn / 1000, 2),
                "Vu_kN": self.Vu, "utilization": round(util, 4),
                "is_ok": util <= 1.0}

    def bearing_beam_web(self) -> dict:
        """Aplastamiento de los pernos del alma sobre el alma de la viga."""
        dh = self.bolt_diameter + 2.0
        lc_int = self.bolt_spacing - dh
        lc_edge = self.edge_dist_v - dh / 2
        # n-1 pernos interiores + 1 perno extremo
        Rn = (self.bolt_web.aisc_bearing_strength(self.beam_tw, self.Fu_beam, lc_int)
              * (self.n_bolts - 1)
              + self.bolt_web.aisc_bearing_strength(self.beam_tw, self.Fu_beam, lc_edge))
        util = self.Vu_N / Rn
        return {"check": "Bearing on beam web",
                "phi_Rn_kN": round(Rn / 1000, 2),
                "Vu_kN": self.Vu, "utilization": round(util, 4),
                "is_ok": util <= 1.0}

    def bearing_angle_leg(self) -> dict:
        """Aplastamiento sobre cada ángulo (resiste mitad de Vu por ángulo)."""
        dh = self.bolt_diameter + 2.0
        lc_int = self.bolt_spacing - dh
        lc_edge = self.edge_dist_v - dh / 2
        # Para el alma: cada perno transfiere por aplastamiento en 2 ángulos,
        # mitad de carga cada uno → comparamos Rn_total (2 ángulos juntos) vs Vu.
        Rn_per_angle = (self.bolt_web.aisc_bearing_strength(
                            self.angle_thickness, self.Fu_angle, lc_int) * (self.n_bolts - 1)
                        + self.bolt_web.aisc_bearing_strength(
                            self.angle_thickness, self.Fu_angle, lc_edge))
        Rn_total = 2 * Rn_per_angle
        util = self.Vu_N / Rn_total
        return {"check": "Bearing on angle legs (2 angles)",
                "phi_Rn_kN": round(Rn_total / 1000, 2),
                "Vu_kN": self.Vu, "utilization": round(util, 4),
                "is_ok": util <= 1.0}

    def angle_shear_yielding(self) -> dict:
        """Fluencia bruta a cortante de los 2 ángulos: φRn = 1.00·0.6·Fy·Agv (AISC J4.2)."""
        Ag = self.angle_thickness * self.angle_height
        phi_Rn = 2 * 1.00 * 0.60 * self.Fy_angle * Ag
        util = self.Vu_N / phi_Rn
        return {"check": "Angle shear yielding (2 angles)",
                "phi_Rn_kN": round(phi_Rn / 1000, 2),
                "Vu_kN": self.Vu, "utilization": round(util, 4),
                "is_ok": util <= 1.0}

    def angle_shear_rupture(self) -> dict:
        """Rotura a cortante de los ángulos: φRn = 0.75·0.6·Fu·Anv (AISC J4.2)."""
        dh = self.bolt_diameter + 2.0
        Anv = (self.angle_height - self.n_bolts * dh) * self.angle_thickness
        phi_Rn = 2 * 0.75 * 0.60 * self.Fu_angle * Anv
        util = self.Vu_N / phi_Rn
        return {"check": "Angle shear rupture (2 angles)",
                "phi_Rn_kN": round(phi_Rn / 1000, 2),
                "Vu_kN": self.Vu, "utilization": round(util, 4),
                "is_ok": util <= 1.0}

    def angle_block_shear(self) -> dict:
        """Block shear en cada ángulo (suma de los 2)."""
        dh = self.bolt_diameter + 2.0
        t = self.angle_thickness
        Agv = (self.angle_height - self.edge_dist_v) * t
        Anv = Agv - (self.n_bolts - 0.5) * dh * t
        Ant = (self.angle_leg - self.edge_dist_h - dh / 2) * t
        r = block_shear_strength(Agv, Anv, Ant, self.Fy_angle, self.Fu_angle,
                                 Ubs=1.0, code="AISC")
        phi_Rn = 2 * r["phi_Rn_N"]
        util = self.Vu_N / phi_Rn
        return {"check": "Block shear (2 angles)",
                "phi_Rn_kN": round(phi_Rn / 1000, 2),
                "Vu_kN": self.Vu, "utilization": round(util, 4),
                "is_ok": util <= 1.0,
                "governs_path": r["governs"]}

    def beam_web_block_shear(self) -> dict:
        """Block shear en el alma de la viga acoplada (AISC 360-22 §J4.3).

        Geometría: una sola línea vertical de pernos atraviesa el alma. El
        bloque rompe a cortante a lo largo de la línea de pernos y a tensión
        transversal hacia el borde libre del alma (coped beam).

            Agv = (n-1)·s·tw + end_distance·tw
            Anv = Agv − (n − 0.5)·dh·tw
            Ant = (gage_to_edge − 0.5·dh)·tw
            Rn  = min[0.6·Fu·Anv, 0.6·Fy·Agv] + Ubs·Fu·Ant
            Ubs = 1.0 (tensión uniforme)
            φ   = 0.75
        """
        dh = self.bolt_diameter + 2.0
        tw = self.beam_tw
        Agv = ((self.n_bolts - 1) * self.bolt_spacing + self.edge_dist_v) * tw
        Anv = Agv - (self.n_bolts - 0.5) * dh * tw
        Ant = max(0.0, (self.beam_gage_to_edge - 0.5 * dh)) * tw
        r = block_shear_strength(Agv, Anv, Ant, self.Fy_beam, self.Fu_beam,
                                 Ubs=1.0, code="AISC")
        phi_Rn = r["phi_Rn_N"]
        util = self.Vu_N / phi_Rn if phi_Rn > 0 else float("inf")
        return {"check": "Block shear (beam web)",
                "phi_Rn_kN": round(phi_Rn / 1000, 2),
                "Vu_kN": self.Vu, "utilization": round(util, 4),
                "is_ok": util <= 1.0,
                "governs_path": r["governs"]}

    # ------------------------------------------------------------------
    def design(self) -> dict:
        checks = [
            self.bolt_shear_web(),
            self.bolt_shear_support(),
            self.bearing_beam_web(),
            self.bearing_angle_leg(),
            self.angle_shear_yielding(),
            self.angle_shear_rupture(),
            self.angle_block_shear(),
            self.beam_web_block_shear(),
        ]
        gov = max(checks, key=lambda c: c["utilization"])
        all_ok = all(c["is_ok"] for c in checks)
        return {
            "connection_type": "Double-Angle (Clip Angle) Shear",
            "code": "AISC 360-22 + Manual Part 10",
            "Vu_kN": self.Vu,
            "n_bolts": self.n_bolts,
            "bolt": f"{self.bolt_grade} Ø{self.bolt_diameter}mm",
            "angle_t_mm": self.angle_thickness,
            "angle_h_mm": round(self.angle_height, 1),
            "checks": checks,
            "governing_check": gov["check"],
            "governing_utilization": gov["utilization"],
            "all_checks_ok": all_ok,
        }
