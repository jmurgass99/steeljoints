"""
bolts.py — Bolt strength calculations per AISC 360-22 Chapter J and EN 1993-1-8.

Covers:
  - Single bolt shear capacity (Rn shear, bearing, tension)
  - Slip-critical connections (AISC §J3.8)
  - Bolt group eccentric shear (ICR method — elastic approximation)
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from math import pi, sqrt


# ---------------------------------------------------------------------------
# Bolt material data
# ---------------------------------------------------------------------------
# AISC 360-22 Tabla J3.2 en ksi convertidos exactamente (1 ksi = 6.894757 MPa):
#   A307: Fnt 45, Fnv 27 · Grupo 120 (A325, F1852): Fnt 90, Fnv-N 54, Fnv-X 68
#   Grupo 150 (A490, F2280): Fnt 113, Fnv-N 68, Fnv-X 84
# "Fnv" (sin sufijo) es el valor -N, por compatibilidad. Hasta la versión 1.1, A307 llevaba 24 ksi
# (valor antiguo) y A490-N 66 ksi.
_AISC_BOLT_DATA: dict[str, dict] = {
    "A307": {"Fnt": 310.3, "Fnv": 186.2, "Fnv_X": 186.2, "Fu": 413.7},
    "A325": {"Fnt": 620.5, "Fnv": 372.3, "Fnv_X": 468.8, "Fu": 827.4},
    "A490": {"Fnt": 779.1, "Fnv": 468.8, "Fnv_X": 579.2, "Fu": 1034.3},
    "F1852": {"Fnt": 620.5, "Fnv": 372.3, "Fnv_X": 468.8, "Fu": 827.4},  # equiv A325
    "F2280": {"Fnt": 779.1, "Fnv": 468.8, "Fnv_X": 579.2, "Fu": 1034.3},  # equiv A490
}

_EC3_BOLT_DATA: dict[str, dict] = {
    # Grade: fub (MPa), fyb (MPa)
    "4.6": {"fub": 400.0,  "fyb": 240.0},
    "5.6": {"fub": 500.0,  "fyb": 300.0},
    "6.8": {"fub": 600.0,  "fyb": 480.0},
    "8.8": {"fub": 800.0,  "fyb": 640.0},
    "10.9": {"fub": 1000.0, "fyb": 900.0},
}

# ---------------------------------------------------------------------------
# Bolt areas from nominal diameter
# ---------------------------------------------------------------------------
_BOLT_AREA_CM2: dict[float, float] = {
    # diameter mm → gross area cm² (pi*d²/4)
    12.0: 1.131, 14.0: 1.539, 16.0: 2.011, 18.0: 2.545,
    20.0: 3.142, 22.0: 3.801, 24.0: 4.524, 27.0: 5.726,
    30.0: 7.069, 36.0: 10.18,
    # AISC inches → mm conversion
    12.7: 1.267,   # 1/2"
    15.875: 1.979, # 5/8"
    19.05: 2.850,  # 3/4"
    22.225: 3.879, # 7/8"
    25.4: 5.067,   # 1"
    28.575: 6.413, # 1-1/8"
    31.75: 7.917,  # 1-1/4"
}

SHEAR_AREA_FACTOR = 0.75  # OBSOLETO desde 1.2.0: ya no interviene en ninguna resistencia

# Paso grueso ISO 261 [mm] para el área resistente a tracción As = π/4·(d − 0.9382·P)² (ISO 898-1)
_ISO_COARSE_PITCH: dict[float, float] = {
    12.0: 1.75, 14.0: 2.0, 16.0: 2.0, 18.0: 2.5, 20.0: 2.5, 22.0: 2.5,
    24.0: 3.0, 27.0: 3.0, 30.0: 3.5, 33.0: 3.5, 36.0: 4.0,
}


def bolt_tensile_stress_area(d_mm: float) -> float:
    """Área resistente a tracción As [mm²] (ISO 898-1 / ASME B1.1).

    Usa el catálogo (métrico o imperial) cuando el diámetro coincide a menos de 0,5 mm; si no,
    As = π/4·(d − 0.9382·P)² con el paso grueso ISO más próximo.
    """
    from .catalog import BOLT_SIZES_IMPERIAL, BOLT_SIZES_METRIC
    for table in (BOLT_SIZES_METRIC, BOLT_SIZES_IMPERIAL):
        for data in table.values():
            if abs(data["d_mm"] - d_mm) < 0.5:
                return float(data["As_mm2"])
    pitch = _ISO_COARSE_PITCH[min(_ISO_COARSE_PITCH, key=lambda k: abs(k - d_mm))]
    return pi / 4.0 * (d_mm - 0.9382 * pitch) ** 2


def ec3_normal_hole_clearance(d_mm: float) -> float:
    """Holgura nominal de agujero normal [mm] (EN 1090-2, Tabla 11): M12–M14 1 mm, M16–M24 2 mm, ≥ M27 3 mm."""
    if d_mm <= 14.0:
        return 1.0
    if d_mm <= 24.0:
        return 2.0
    return 3.0


def bolt_gross_area(d_mm: float) -> float:
    """Cross-sectional area of bolt from nominal diameter [mm² → mm²]."""
    # Find closest entry or compute
    closest = min(_BOLT_AREA_CM2.keys(), key=lambda k: abs(k - d_mm))
    if abs(closest - d_mm) < 0.5:
        return _BOLT_AREA_CM2[closest] * 100  # cm² → mm²
    return pi * d_mm**2 / 4


@dataclass
class Bolt:
    """
    Single structural bolt.

    Parameters
    ----------
    diameter : float  nominal diameter [mm]
    grade    : str    'A325', 'A490', 'A307' (AISC) or '8.8', '10.9' (EC3)
    code     : str    'AISC' or 'EC3'
    threads_in_shear_plane : bool  True = threads in shear plane (conservative)
    n_shear_planes : int  1 (single shear) or 2 (double shear)
    """
    diameter: float
    grade: str
    code: str = "AISC"
    threads_in_shear_plane: bool = True
    n_shear_planes: int = 1

    def __post_init__(self) -> None:
        self.code = self.code.upper()
        self.Ab = bolt_gross_area(self.diameter)  # mm²

    # ------------------------------------------------------------------
    # AISC 360-22 Chapter J
    # ------------------------------------------------------------------
    @property
    def _aisc_data(self) -> dict:
        if self.grade not in _AISC_BOLT_DATA:
            raise ValueError(f"Unknown AISC bolt grade '{self.grade}'. "
                             f"Valid: {list(_AISC_BOLT_DATA)}")
        return _AISC_BOLT_DATA[self.grade]

    def _aisc_Fnv(self) -> float:
        """Fnv de AISC 360-22 Tabla J3.2: «-N» (rosca en el plano de corte) o «-X» (excluida)."""
        g = self._aisc_data  # valida el grado
        return g["Fnv"] if self.threads_in_shear_plane else g["Fnv_X"]

    def aisc_shear_strength(self, phi: float = 0.75) -> float:
        """
        φRn (shear) per AISC §J3.6 [N].
        Rn = Fnv · Ab · n_planos, con Ab el área NOMINAL (bruta) y Fnv de la Tabla J3.2:
        «-N» si la rosca está en el plano de corte, «-X» si está excluida.

        La tabla ya incorpora la reducción por rosca (A325-N 372 MPa frente a A325-X 469 MPa).
        Hasta la versión 1.1 se usaba Fnv «-N» y ADEMÁS 0,75·Ab: el cortante de un perno
        A325-N de 3/4" salía 59,7 kN en vez de 79,5 kN, y con la rosca excluida no subía a «-X».
        """
        Rn = self._aisc_Fnv() * self.Ab * self.n_shear_planes
        return phi * Rn  # [N]

    def aisc_tension_strength(self, phi: float = 0.75) -> float:
        """φRn (tension) per AISC §J3.6 [N]."""
        Fnt = self._aisc_data["Fnt"]
        return phi * Fnt * self.Ab

    def aisc_bearing_strength(self, t: float, Fu_plate: float,
                               clear_dist: float,
                               phi: float = 0.75) -> float:
        """
        φRn (bearing on connected material) per AISC §J3.10 [N].

        Parameters
        ----------
        t : float  thickness of connected part [mm]
        Fu_plate : float  ultimate strength of connected material [MPa]
        clear_dist : float  clear distance from edge/adjacent hole to bolt [mm]
        """
        # Rn = 1.2 · lc · t · Fu ≤ 2.4 · d · t · Fu  (deformation considered)
        lc = clear_dist
        Rn = min(1.2 * lc * t * Fu_plate, 2.4 * self.diameter * t * Fu_plate)
        return phi * Rn

    def aisc_combined_tension_shear(self, Vuv: float, phi: float = 0.75) -> float:
        """
        Modified tensile strength under combined T+V (AISC §J3.7) [N].
        Fnt' = 1.3*Fnt - Fnt/(phi*Fnv) * (Vuv/Ab) ≤ Fnt

        Parameters
        ----------
        Vuv : float  required shear strength per bolt [N]
        """
        data = self._aisc_data
        Fnt, Fnv = data["Fnt"], self._aisc_Fnv()
        frv = Vuv / self.Ab  # shear stress on bolt
        Fnt_prime = max(0.0, min(1.3 * Fnt - (Fnt / (phi * Fnv)) * frv, Fnt))
        return phi * Fnt_prime * self.Ab

    # ------------------------------------------------------------------
    # EN 1993-1-8 §3.6 bolt design resistance
    # ------------------------------------------------------------------
    @property
    def _ec3_data(self) -> dict:
        if self.grade not in _EC3_BOLT_DATA:
            raise ValueError(f"Unknown EC3 bolt grade '{self.grade}'. "
                             f"Valid: {list(_EC3_BOLT_DATA)}")
        return _EC3_BOLT_DATA[self.grade]

    def ec3_shear_strength(self, gamma_M2: float = 1.25) -> float:
        """
        Fv,Rd (shear) per EC3-1-8 §3.6.1 Table 3.4 [N].
        Fv,Rd = 0.6 · fub · A / γM2  (grades 4.6, 5.6, 8.8)
        Fv,Rd = 0.5 · fub · A / γM2  (grades 6.8, 10.9)
        A = As (área resistente a tracción) si la rosca está en el plano de corte; A = área bruta si no.
        Delega en la primitiva canónica bolt_shear_Rd. Hasta la versión 1.1 se tomaba 0,75·Ab en lugar
        de As (M20 8.8: 90,5 kN en vez de 94,1 kN).
        """
        from .codes.ec3_1_8 import bolt_shear_Rd
        fub = self._ec3_data["fub"]
        alpha_v = 0.5 if self.grade in ("6.8", "10.9") else 0.6
        A = bolt_tensile_stress_area(self.diameter) if self.threads_in_shear_plane else self.Ab
        return bolt_shear_Rd(A_mm2=A, fub_MPa=fub, alpha_v=alpha_v, gamma_M2=gamma_M2) * self.n_shear_planes

    def ec3_tension_strength(self, gamma_M2: float = 1.25) -> float:
        """Ft,Rd = k2 · fub · As / γM2 (EC3-1-8 §3.6.1 Tabla 3.4, k2 = 0,9) [N].

        Con el área resistente As, no con la bruta: hasta la versión 1.1 se usaba Ab y la
        resistencia de un M20 salía un 28 % alta (181 kN en vez de 141 kN para 8.8).
        """
        from .codes.ec3_1_8 import bolt_tension_Rd
        fub = self._ec3_data["fub"]
        return bolt_tension_Rd(As_mm2=bolt_tensile_stress_area(self.diameter), fub_MPa=fub, gamma_M2=gamma_M2)

    def ec3_bearing_strength(self, t: float, fu_plate: float,
                              e1: float, p1: float,
                              e2: float, p2: float,
                              direction: str = "parallel",
                              gamma_M2: float = 1.25,
                              d0: float | None = None) -> float:
        """
        Fb,Rd (bearing) per EC3-1-8 §3.6.1 Table 3.4 [N].

        Parameters
        ----------
        t : float  plate thickness [mm]
        fu_plate : float  plate ultimate strength [MPa]
        e1, p1 : float  end/pitch distance in load direction [mm]
        e2, p2 : float  end/pitch distance perpendicular [mm]
        d0 : float  diámetro del agujero [mm]; por defecto d + holgura normal de EN 1090-2 Tabla 11.

        Los cocientes de posición (αd, k1) van con d0 y el área de aplastamiento con d (Tabla 3.4).
        Se toma el perno más desfavorable de la fila: αd = mín(e1/3d0, p1/3d0 − 1/4) y
        k1 = mín(2,8·e2/d0 − 1,7, 1,4·p2/d0 − 1,7, 2,5), una envolvente conservadora de los casos de
        borde e interior. Hasta la versión 1.1 los cocientes usaban d en vez de d0 (+10 % en M20).
        """
        d = self.diameter
        d0 = d + ec3_normal_hole_clearance(d) if d0 is None else d0
        fub = self._ec3_data["fub"]
        # alpha_d in load direction
        alpha_d = min(e1 / (3 * d0), p1 / (3 * d0) - 0.25, fub / fu_plate, 1.0)
        # k1 perpendicular
        k1 = min(2.8 * e2 / d0 - 1.7, 1.4 * p2 / d0 - 1.7, 2.5)
        Fb_Rd = k1 * alpha_d * fu_plate * d * t / gamma_M2
        return Fb_Rd


@dataclass
class BoltGroup:
    """
    Group of bolts under eccentric shear (elastic method).

    Parameters
    ----------
    bolt : Bolt
        Single bolt object defining bolt grade and size.
    positions : list[tuple[float, float]]
        (x, y) positions of each bolt relative to centroid [mm].
    phi_Rn_single : float
        Design shear strength of one bolt [N].

    Notes
    -----
    Full ICR (Instantaneous Center of Rotation) method is complex.
    This implements the elastic vector method (conservative) per
    AISC Manual Part 7.
    """
    bolt: Bolt
    positions: list[tuple[float, float]]
    phi_Rn_single: float  # per bolt [N]

    def __post_init__(self) -> None:
        self.n = len(self.positions)
        xs = [p[0] for p in self.positions]
        ys = [p[1] for p in self.positions]
        self.cx = sum(xs) / self.n
        self.cy = sum(ys) / self.n
        # Relative positions from centroid
        self.ri = [(p[0] - self.cx, p[1] - self.cy) for p in self.positions]

    def elastic_critical_bolt(self, Vu: float, Mu: float) -> dict:
        """
        Find maximum bolt resultant force using elastic vector method.

        Parameters
        ----------
        Vu : float  total applied shear [N]
        Mu : float  moment about bolt group centroid [N·mm]

        Returns
        -------
        dict with: Vmax_N, bolt_index, utilization
        """
        n = self.n
        # Direct shear per bolt
        V_direct = Vu / n

        # Polar moment of inertia
        Ip = sum(rx**2 + ry**2 for rx, ry in self.ri)

        Vmax = 0.0
        crit_idx = 0
        for i, (rx, ry) in enumerate(self.ri):
            r2 = rx**2 + ry**2
            # Torsional components
            Vx_t = -Mu * ry / Ip if Ip > 0 else 0
            Vy_t = +Mu * rx / Ip if Ip > 0 else 0
            # Total per bolt
            Vx_total = Vx_t
            Vy_total = V_direct + Vy_t
            V_total = sqrt(Vx_total**2 + Vy_total**2)
            if V_total > Vmax:
                Vmax = V_total
                crit_idx = i

        utilization = Vmax / self.phi_Rn_single
        return {
            "Vmax_N": round(Vmax, 1),
            "Vmax_kN": round(Vmax / 1000, 3),
            "phi_Rn_N": round(self.phi_Rn_single, 1),
            "utilization": round(utilization, 4),
            "is_ok": utilization <= 1.0,
            "critical_bolt_index": crit_idx,
        }

    def capacity_concentric(self) -> float:
        """Total group capacity for concentric shear [N]."""
        return self.n * self.phi_Rn_single
