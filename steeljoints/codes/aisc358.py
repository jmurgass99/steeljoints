"""
aisc358.py — AISC 358-22 Prequalified Connections for Seismic Applications.

Esta versión cubre los parámetros clave para:

  §5  RBS (Reduced Beam Section)         — geometría a, b, c
  §6  Bolted Unstiffened End Plate (BUEEP / 4ES / 8ES) — geometría y Mpr
  §7  Bolted Stiffened Extended End Plate (BSEEP)
  §8  Bolted Flange Plate (BFP)

Funciones devuelven:
  - Mpr (momento probable en la rótula plástica) [N·mm]:
        Mpr = Cpr · Ry · Fy · Zx
        Cpr = (Fy + Fu) / (2·Fy) ≤ 1.2
  - Sh (distancia desde la cara de la columna a la rótula) [mm]
  - Vu en la rótula (estimación con cargas gravitacionales)
"""
from __future__ import annotations
from math import sqrt


# Factor Ry (esperado a fluencia) Tabla A3.1 AISC 341
RY: dict[str, float] = {
    "A36": 1.5,
    "A572-50": 1.1,
    "A992": 1.1,
    "A913-50": 1.1,
    "A913-65": 1.1,
    "A913-70": 1.1,
}
RT: dict[str, float] = {
    "A36": 1.2, "A572-50": 1.1, "A992": 1.1,
}


def Cpr(Fy_MPa: float, Fu_MPa: float) -> float:
    """Factor de sobre-resistencia probable. AISC 358 §2.4.3."""
    return min((Fy_MPa + Fu_MPa) / (2.0 * Fy_MPa), 1.2)


def Mpr(Z_mm3: float, Fy_MPa: float, Fu_MPa: float, Ry: float = 1.1) -> float:
    """
    Mpr = Cpr · Ry · Fy · Zx     [N·mm]
    AISC 358 Eq. 2.4.3-1.
    """
    return Cpr(Fy_MPa, Fu_MPa) * Ry * Fy_MPa * Z_mm3


# ---------------------------------------------------------------------------
# §5 — RBS (Reduced Beam Section)
# ---------------------------------------------------------------------------
def rbs_geometry(bf_mm: float, d_mm: float) -> dict:
    """
    Límites geométricos AISC 358 §5.8:
      0.50·bf ≤ a ≤ 0.75·bf
      0.65·d  ≤ b ≤ 0.85·d
      0.10·bf ≤ c ≤ 0.25·bf
    Devuelve valores típicos centrales del rango.
    """
    a = 0.625 * bf_mm   # central a
    b = 0.75  * d_mm
    c = 0.20  * bf_mm
    return {
        "a_mm": round(a, 1),
        "b_mm": round(b, 1),
        "c_mm": round(c, 1),
        "bf_reduced_mm": round(bf_mm - 2 * c, 1),
        "Sh_mm": round(a + b / 2.0, 1),   # dist. centro de RBS desde cara columna
        "limits": {
            "a_range_mm": (0.5 * bf_mm, 0.75 * bf_mm),
            "b_range_mm": (0.65 * d_mm, 0.85 * d_mm),
            "c_range_mm": (0.10 * bf_mm, 0.25 * bf_mm),
        }
    }


def rbs_Z_reduced(Zx_mm3: float, c_mm: float, tf_mm: float, d_mm: float) -> float:
    """
    Módulo plástico reducido en el RBS:
      Z_RBS = Zx − 2·c·tf·(d − tf)     AISC 358 Eq. 5.8-4
    """
    return Zx_mm3 - 2.0 * c_mm * tf_mm * (d_mm - tf_mm)


def rbs_Mpr(Zx_mm3: float, c_mm: float, tf_mm: float, d_mm: float,
            Fy_MPa: float, Fu_MPa: float, Ry: float = 1.1) -> float:
    """Mpr basado en Z_RBS."""
    Z_rbs = rbs_Z_reduced(Zx_mm3, c_mm, tf_mm, d_mm)
    return Mpr(Z_rbs, Fy_MPa, Fu_MPa, Ry)


# ---------------------------------------------------------------------------
# §6/§7 — Extended End Plate (4E, 4ES, 8ES)
# ---------------------------------------------------------------------------
def end_plate_thickness_required(Mu_Nmm: float, bp_mm: float,
                                  Fy_plate_MPa: float, Yp: float,
                                  phi: float = 0.90) -> float:
    """
    Espesor requerido de placa extrema (Yield-line analysis, AISC 358 §6.9.4):
      tp,req = √( 1.11 · Mu / (φ · Fy · Yp) )
    Yp = parámetro de mecanismo de líneas de fluencia (depende de geometría).
    """
    return sqrt(1.11 * Mu_Nmm / (phi * Fy_plate_MPa * Yp))


def Yp_4E_unstiffened(bp: float, g: float, pfo: float, pfi: float,
                       h0: float, h1: float, s: float) -> float:
    """
    Parámetro Yp para 4-bolt extended unstiffened (4E), AISC 358 Tabla 6.2.
    bp = ancho placa; g = gage horizontal; pfo,pfi = dist. de las filas
    al ala; h0,h1 = dist. de las filas al eje del ala COMPRIMIDA; s = √(bp·g)/2.

    SIN CONTRASTAR (1.2.0): la expresión lleva los términos h0/(2s) y h0·(pfo + s) que la forma
    de 4E que suele reproducirse no tiene, y que se parecen a la del caso rigidizado (4ES). No se
    ha podido verificar contra la Tabla 6.2 de AISC 358, así que no se cambia; con las cotas por
    defecto de ``EndPlate`` da un Yp un 30–40 % mayor que la forma reducida
    bp/2·[h1(1/pfi + 1/s) + h0/pfo − 1/2] + 2/g·h1(pfi + s). Compruébalo antes de usar φMn.
    """
    if s <= 0:
        s = sqrt(bp * g) / 2.0
    Yp = (bp / 2.0) * (
        h1 * (1.0 / pfi + 1.0 / s)
        + h0 * (1.0 / pfo + 1.0 / (2.0 * s))
        - 0.5
    ) + (2.0 / g) * (h1 * (pfi + s) + h0 * (pfo + s))
    return Yp


# ---------------------------------------------------------------------------
# §8 — Bolted Flange Plate (BFP)
# ---------------------------------------------------------------------------
def bfp_flange_plate_force(Mpr_Nmm: float, d_mm: float, tfp_mm: float) -> float:
    """
    Fuerza en la placa de ala: Fpr = Mpr / (d + tfp)       AISC 358 §8.6.
    """
    return Mpr_Nmm / (d_mm + tfp_mm)


# ---------------------------------------------------------------------------
# Cortante en la rótula plástica (cargas gravitacionales + Mpr)
# ---------------------------------------------------------------------------
def Vh_at_hinge(Mpr_Nmm: float, Lh_mm: float, wu_N_per_mm: float = 0.0) -> float:
    """
    Vh = 2·Mpr / Lh + wu·Lh / 2     [N]
    Lh = distancia entre rótulas plásticas (de cara a cara aprox.).
    wu = carga gravitacional factorada por unidad de longitud sobre la viga [N/mm].
    """
    return 2.0 * Mpr_Nmm / Lh_mm + wu_N_per_mm * Lh_mm / 2.0
