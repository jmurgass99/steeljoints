"""
ec3_1_8.py — EN 1993-1-8:2005 (Eurocódigo 3, Diseño de uniones).

Funciones puras: devuelven resistencias de diseño Rd [N] aplicando γMi
correspondientes (γM0=1.0, γM2=1.25 valores recomendados; el usuario
puede sobreescribir según NA nacional).

Cubre:
  §3.6.1 Tabla 3.4 — pernos individuales (corte, tensión, aplastamiento,
                      punzonamiento, deslizamiento)
  §3.9   — uniones resistentes al deslizamiento Cat B/C
  §4.5.3 — soldadura de filete (método direccional y simplificado)
  §6.2.4 — componentes T-stub (modos 1/2/3)
"""
from __future__ import annotations
from math import sqrt, pi

GAMMA_M0 = 1.00
GAMMA_M1 = 1.00
GAMMA_M2 = 1.25
GAMMA_M3 = 1.25
GAMMA_M3_SER = 1.10

# Factor de correlación βw §4.5.3.2(7)
BETA_W: dict[str, float] = {
    "S235": 0.80, "S275": 0.85, "S355": 0.90,
    "S420": 1.00, "S460": 1.00,
}


# ---------------------------------------------------------------------------
# §3.6.1 — Pernos individuales
# ---------------------------------------------------------------------------
def bolt_shear_Rd(A_mm2: float, fub_MPa: float, alpha_v: float = 0.6,
                   gamma_M2: float = GAMMA_M2) -> float:
    """
    Fv,Rd = αv · fub · A / γM2     [N]
    αv = 0.6 (gr. 4.6, 5.6, 8.8) ; αv = 0.5 (gr. 4.8, 5.8, 6.8, 10.9)
    A = As (área de tracción) si las roscas están en el plano; A = A si no.
    """
    return alpha_v * fub_MPa * A_mm2 / gamma_M2


def bolt_tension_Rd(As_mm2: float, fub_MPa: float, k2: float = 0.9,
                     gamma_M2: float = GAMMA_M2) -> float:
    """
    Ft,Rd = k2 · fub · As / γM2    [N]
    k2 = 0.9 (general) ; k2 = 0.63 (cabeza avellanada).
    """
    return k2 * fub_MPa * As_mm2 / gamma_M2


def bolt_bearing_Rd(d_mm: float, t_mm: float, fu_plate_MPa: float, fub_MPa: float,
                     e1: float, p1: float, e2: float, p2: float,
                     direction_inner: bool = False,
                     gamma_M2: float = GAMMA_M2) -> float:
    """
    Fb,Rd = k1 · αb · fu · d · t / γM2    [N]    (Tabla 3.4)

    Para perno de borde (extremo) en dirección de carga:
        αb = min(αd, fub/fu, 1.0)   con αd = e1/(3·d)
    Para perno interior:
        αb = min(αd, fub/fu, 1.0)   con αd = p1/(3·d) − 1/4

    Perpendicular a la carga:
        Para borde:    k1 = min(2.8·e2/d − 1.7, 2.5)
        Para interior: k1 = min(1.4·p2/d − 1.7, 2.5)
    """
    if direction_inner:
        alpha_d = p1 / (3.0 * d_mm) - 0.25
        k1 = min(1.4 * p2 / d_mm - 1.7, 2.5)
    else:
        alpha_d = e1 / (3.0 * d_mm)
        k1 = min(2.8 * e2 / d_mm - 1.7, 2.5)
    alpha_b = min(alpha_d, fub_MPa / fu_plate_MPa, 1.0)
    return k1 * alpha_b * fu_plate_MPa * d_mm * t_mm / gamma_M2


def bolt_punching_Rd(dm_mm: float, tp_mm: float, fu_plate_MPa: float,
                      gamma_M2: float = GAMMA_M2) -> float:
    """
    Bp,Rd = 0.6 · π · dm · tp · fu / γM2     [N]     §3.6.1(2)
    dm = promedio entre dist. entre caras y diagonal de la cabeza/tuerca.
    """
    return 0.6 * pi * dm_mm * tp_mm * fu_plate_MPa / gamma_M2


def bolt_combined_check(Fv_Ed: float, Fv_Rd: float, Ft_Ed: float, Ft_Rd: float) -> float:
    """
    §3.6.1 Tabla 3.4, interacción tensión-corte:
        Fv,Ed/Fv,Rd + Ft,Ed/(1.4·Ft,Rd) ≤ 1.0
    Devuelve el utilization ratio (≤1.0 ok).
    """
    return Fv_Ed / Fv_Rd + Ft_Ed / (1.4 * Ft_Rd)


# ---------------------------------------------------------------------------
# §3.9 — Resistencia al deslizamiento (Categoría B/C)
# ---------------------------------------------------------------------------
def slip_resistance_Rd(ks: float, mu: float, n: int, Fp_C: float,
                        gamma_M3: float = GAMMA_M3) -> float:
    """
    Fs,Rd = ks · n · μ · Fp,C / γM3      §3.9.1
      ks = 1.0 (agujero estándar) ; 0.85 sobredimensionado ; etc.
      n  = nº de planos de fricción
      μ  = coeficiente de fricción (Clase A: 0.5, B: 0.4, C: 0.3, D: 0.2)
      Fp,C = 0.7 · fub · As   (fuerza de pretensión)
    """
    return ks * n * mu * Fp_C / gamma_M3


# ---------------------------------------------------------------------------
# §4.5.3 — Soldadura de filete
# ---------------------------------------------------------------------------
def fillet_weld_Rd_directional(a_mm: float, L_mm: float, fu_MPa: float,
                                steel_grade: str = "S275",
                                sigma_perp: float = 0.0, tau_perp: float = 0.0,
                                tau_par: float = 0.0,
                                gamma_M2: float = GAMMA_M2) -> dict:
    """
    Método direccional §4.5.3.2:
        √(σ⊥² + 3·(τ⊥² + τ∥²))  ≤ fu / (βw · γM2)
        σ⊥                       ≤ 0.9·fu / γM2
    Devuelve el ratio de utilización.
    """
    beta_w = BETA_W.get(steel_grade, 0.85)
    fvw_d = fu_MPa / (beta_w * sqrt(3.0) * gamma_M2)
    von_mises = sqrt(sigma_perp**2 + 3.0 * (tau_perp**2 + tau_par**2))
    limit_1 = fu_MPa / (beta_w * gamma_M2)
    limit_2 = 0.9 * fu_MPa / gamma_M2
    util = max(von_mises / limit_1, abs(sigma_perp) / limit_2)
    # Capacidad como esfuerzo cortante simple en garganta:
    Fw_Rd = fvw_d * a_mm * L_mm
    return {"Fw_Rd_N": Fw_Rd, "utilization": util,
            "fvw_d_MPa": fvw_d, "beta_w": beta_w}


def fillet_weld_Rd_simplified(a_mm: float, L_mm: float, fu_MPa: float,
                               steel_grade: str = "S275",
                               gamma_M2: float = GAMMA_M2) -> float:
    """
    Método simplificado §4.5.3.3 — capacidad por unidad de longitud:
      Fw,Rd = fvw,d · a       con   fvw,d = fu / (βw·√3·γM2)
    Devuelve Fw,Rd total en [N].
    """
    beta_w = BETA_W.get(steel_grade, 0.85)
    fvw_d = fu_MPa / (beta_w * sqrt(3.0) * gamma_M2)
    return fvw_d * a_mm * L_mm


# ---------------------------------------------------------------------------
# §6.2.4 — T-stub equivalente (modos de falla)
# ---------------------------------------------------------------------------
def t_stub_FT_Rd(leff_mm: float, tp_mm: float, fy_plate_MPa: float,
                  Ft_Rd_bolt_N: float, n_mm: float, m_mm: float,
                  gamma_M0: float = GAMMA_M0) -> dict:
    """
    Resistencia del T-stub equivalente a tracción (§6.2.4.1 Tabla 6.2):

      Mpl,Rd  = 0.25 · leff · tp² · fy / γM0

      Modo 1 (mecanismo de placa, sin pernos):
          FT,1,Rd = 4·Mpl,Rd / m
      Modo 2 (mecanismo combinado placa + pernos):
          FT,2,Rd = (2·Mpl,Rd + n·ΣFt,Rd) / (m + n)
      Modo 3 (fallo solo de pernos):
          FT,3,Rd = ΣFt,Rd

      FT,Rd = min(modo 1, 2, 3)

    Σ Ft,Rd_bolt_N pasarse como Ft_Rd_bolt_N (suma de los pernos de la fila).
    """
    Mpl_Rd = 0.25 * leff_mm * tp_mm**2 * fy_plate_MPa / gamma_M0
    F1 = 4.0 * Mpl_Rd / m_mm
    F2 = (2.0 * Mpl_Rd + n_mm * Ft_Rd_bolt_N) / (m_mm + n_mm)
    F3 = Ft_Rd_bolt_N
    Fmin = min(F1, F2, F3)
    governing = ["Modo 1", "Modo 2", "Modo 3"][[F1, F2, F3].index(Fmin)]
    return {"FT_Rd_N": Fmin, "Mpl_Rd_Nmm": Mpl_Rd,
            "F1_Nmm": F1, "F2_N": F2, "F3_N": F3,
            "governing_mode": governing}
