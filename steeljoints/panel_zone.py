"""
panel_zone.py — Cortante en panel zone (zona de panel viga-columna).

AISC 360-22 §J10.6 — Web panel zone shear.

Cuando el análisis del pórtico NO considera la deformación de la zona de panel:
    Si  αPr ≤ 0.4·Pc:   Rn = 0.60·Fy·dc·tw
    Si  αPr > 0.4·Pc:   Rn = 0.60·Fy·dc·tw·(1.4 − αPr/Pc)

Cuando SÍ la considera (deformación inelástica de la zona de panel):
    Si  αPr ≤ 0.75·Pc:  Rn = 0.60·Fy·dc·tw·[1 + 3·bcf·tcf² / (db·dc·tw)]
    Si  αPr > 0.75·Pc:  Rn = 0.60·Fy·dc·tw·[1 + 3·bcf·tcf² / (db·dc·tw)]·(1.9 − 1.2·αPr/Pc)

(φ = 0.90, LRFD α = 1.0, Pc = Py.) Hasta la versión 1.1 la API funcional omitía la reducción
(1.4 − Pr/Pc) del primer caso (lado inseguro con axil alto) y la clase aplicaba el umbral 0,4 y
(1.4 − Pr/Pc) también al segundo (lado seguro, hasta un 36 % de capacidad perdida).

Si Rn < Vu_panel, se requiere doubler plate de espesor tdp tal que:
    Rn(con tw_total = tw + tdp) ≥ Vu_panel

Vu_panel ≈ ΣMu/(db - tf) - Vu_col   (suma de momentos de vigas / brazo - cortante columna)
"""
from __future__ import annotations
import math
from dataclasses import dataclass


# ----------------------------------------------------------------------
# API funcional alterna (SI units, AISC §J10.6) — añadida en v1.2
# Coexiste con la clase PanelZone (más completa, en kN/mm/MPa).
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class PanelZoneInput:
    """Parámetros del panel zone (SI, sin factores).

    Atributos:
        d_c: peralte columna m
        t_w: espesor del alma columna m
        d_b: peralte viga m
        b_f_c: ancho ala columna m
        t_f_c: espesor ala columna m
        Fy_c: tensión de fluencia columna Pa
        P_u: axial demanda columna N (+ compresión)
        P_y: axial yield columna N (= A·Fy)
        consider_plastification: incluir efecto inelástico (eq J10-12)
    """
    d_c: float
    t_w: float
    d_b: float
    b_f_c: float
    t_f_c: float
    Fy_c: float
    P_u: float = 0.0
    P_y: float = 1.0
    consider_plastification: bool = True


@dataclass
class PanelZoneResult:
    Vn: float         # resistencia nominal N
    DCR: float        # demand / capacity
    governs: str      # "elastic" | "plastic"
    notes: list


def shear_capacity(p: PanelZoneInput, V_demand: float = 0.0) -> PanelZoneResult:
    """AISC §J10.6: resistencia al cortante del panel zone (API funcional SI).

    Caso 1 (sin consideración inelástica):
        Vn = 0.60·Fy·dc·tw                                        (J10-9)

    Caso 2 (con plastificación, requiere reforzar la columna):
        Vn = 0.60·Fy·dc·tw · [1 + (3·bfc·tfc²) / (db·dc·tw)]      (J10-11)
        si Pu / Py <= 0.75
        Vn = 0.60·Fy·dc·tw · [1 + (3·bfc·tfc²) / (db·dc·tw)]·(1.9 - 1.2·Pu/Py) (J10-12)
        si Pu / Py > 0.75
    """
    notes: list = []
    Fy = p.Fy_c
    Vn_elastic = 0.60 * Fy * p.d_c * p.t_w
    ratio = p.P_u / max(p.P_y, 1e-9)
    if not p.consider_plastification:
        if ratio > 0.4:
            Vn = Vn_elastic * max(1.4 - ratio, 0.0)
            notes.append(f"Sin plastificación, Pu/Py={ratio:.2f} > 0.4 -> 1.4 - Pu/Py (J10-10)")
        else:
            Vn = Vn_elastic
            notes.append("Sin plastificación (J10-9)")
        gov = "elastic"
    else:
        factor = 1.0 + (3.0 * p.b_f_c * p.t_f_c**2) / (p.d_b * p.d_c * p.t_w)
        Vn_plastic = Vn_elastic * factor
        if p.P_u / max(p.P_y, 1e-9) > 0.75:
            reduction = 1.9 - 1.2 * (p.P_u / p.P_y)
            Vn_plastic *= max(reduction, 0.1)
            notes.append(f"Pu/Py={p.P_u/p.P_y:.2f} > 0.75 -> reduccion (J10-12)")
        else:
            notes.append("J10-11 aplica (Pu/Py <= 0.75)")
        Vn = Vn_plastic
        gov = "plastic"
    phi = 0.90
    Vd = phi * Vn
    dcr = V_demand / Vd if Vd > 0 else 99.0
    notes.append(f"Vn = {Vn/1e3:.1f} kN, phiVn = {Vd/1e3:.1f} kN, DCR = {dcr:.2f}")
    return PanelZoneResult(Vn=Vn, DCR=dcr, governs=gov, notes=notes)


# ----------------------------------------------------------------------
# API original: clase PanelZone (kN, mm, MPa)
# ----------------------------------------------------------------------


@dataclass
class PanelZone:
    """
    Verificación de panel zone en conexión viga-columna.

    Parameters
    ----------
    Mu_left_kNm, Mu_right_kNm : momentos de vigas a izq/der [kN·m].
                                Si nodo exterior (solo viga a un lado), poner 0 el otro.
    Vu_col_kN     : cortante en la columna sobre el nodo [kN]
    Pr_kN         : carga axial requerida en la columna [kN] (compresión > 0)
    Py_kN         : Fy · Ag de la columna [kN] (Pc = Py para LRFD con φ=1.0 en §J10.6)
    db_mm         : peralte de la viga [mm]
    bf_b_mm       : ancho del ala de la viga [mm]
    tf_b_mm       : espesor del ala de la viga [mm]
    dc_mm         : peralte de la columna [mm]
    tw_c_mm       : espesor del alma de la columna [mm]
    bcf_mm        : ancho del ala de la columna [mm]
    tcf_mm        : espesor del ala de la columna [mm]
    Fy_col_MPa    : Fy del acero de la columna [MPa]
    inelastic_action : bool — True si el diseño considera deformación inelástica
                              del panel zone (típico en SMF/IMF sísmicos).
    """
    Mu_left_kNm: float
    Mu_right_kNm: float
    Vu_col_kN: float
    Pr_kN: float
    Py_kN: float
    db_mm: float
    bf_b_mm: float
    tf_b_mm: float
    dc_mm: float
    tw_c_mm: float
    bcf_mm: float
    tcf_mm: float
    Fy_col_MPa: float = 345.0
    inelastic_action: bool = False
    phi: float = 0.90   # AISC §J10.6 LRFD

    # ------------------------------------------------------------------
    def panel_demand_kN(self) -> float:
        """
        Vu_panel = (Mu_L + Mu_R) / (db - tf) - Vu_col   [kN]
        Aproximación común (AISC Seismic Design Manual).
        """
        arm_m = (self.db_mm - self.tf_b_mm) / 1000.0
        if arm_m <= 0:
            return 0.0
        return (self.Mu_left_kNm + self.Mu_right_kNm) / arm_m - self.Vu_col_kN

    def _Rn_N(self, tw_eff_mm: float) -> float:
        Fy = self.Fy_col_MPa
        dc = self.dc_mm
        tw = tw_eff_mm
        ratio = self.Pr_kN / self.Py_kN if self.Py_kN > 0 else 0.0
        # Términos base
        Rn_base = 0.60 * Fy * dc * tw     # N (MPa·mm·mm)
        # Factor de incremento por alas de la columna (sólo si inelastic_action)
        if self.inelastic_action:
            incr = 1.0 + (3.0 * self.bcf_mm * self.tcf_mm**2) / (self.db_mm * dc * tw)
        else:
            incr = 1.0
        if self.inelastic_action:
            Rn = Rn_base * incr * (1.0 if ratio <= 0.75 else (1.9 - 1.2 * ratio))
        else:
            Rn = Rn_base * (1.0 if ratio <= 0.4 else (1.4 - ratio))
        return max(Rn, 0.0)

    def capacity(self) -> dict:
        """φRn del panel zone (sin doubler)."""
        Rn = self._Rn_N(self.tw_c_mm)
        return {
            "Rn_N": round(Rn, 1),
            "phi_Rn_kN": round(self.phi * Rn / 1000.0, 3),
            "inelastic_action": self.inelastic_action,
        }

    def required_doubler(self, tol_mm: float = 0.1, t_max_mm: float = 50.0) -> dict:
        """
        Calcula el espesor de doubler plate requerido (si φRn < Vu_panel).
        Búsqueda lineal en t_dp ∈ [0, t_max_mm].
        """
        Vu = self.panel_demand_kN() * 1000.0  # N
        Rn0 = self._Rn_N(self.tw_c_mm)
        if self.phi * Rn0 >= Vu:
            return {
                "needs_doubler": False,
                "Vu_panel_kN": round(Vu / 1000.0, 3),
                "phi_Rn_kN": round(self.phi * Rn0 / 1000.0, 3),
                "t_doubler_mm": 0.0,
            }
        # Bisección
        lo, hi = 0.0, t_max_mm
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if self.phi * self._Rn_N(self.tw_c_mm + mid) >= Vu:
                hi = mid
            else:
                lo = mid
            if hi - lo < tol_mm:
                break
        t_dp = hi
        Rn_new = self._Rn_N(self.tw_c_mm + t_dp)
        # Espesor mínimo de doubler por estabilidad (§J10.6): t ≥ (dz+wz)/90
        # donde dz=db-2tf, wz=dc-2tcf. Sólo aplica si no se sueldan tapones internos.
        dz = self.db_mm - 2 * self.tf_b_mm
        wz = self.dc_mm - 2 * self.tcf_mm
        t_min_stability = (dz + wz) / 90.0
        return {
            "needs_doubler": True,
            "Vu_panel_kN": round(Vu / 1000.0, 3),
            "phi_Rn_no_doubler_kN": round(self.phi * Rn0 / 1000.0, 3),
            "phi_Rn_with_doubler_kN": round(self.phi * Rn_new / 1000.0, 3),
            "t_doubler_mm": round(t_dp, 2),
            "t_doubler_min_stability_mm": round(t_min_stability, 2),
            "t_doubler_governing_mm": round(max(t_dp, t_min_stability), 2),
        }

    def design(self) -> dict:
        Vu = self.panel_demand_kN()
        cap = self.capacity()
        util = (Vu * 1000.0) / (cap["phi_Rn_kN"] * 1000.0) if cap["phi_Rn_kN"] > 0 else float("inf")
        out = {
            "check": "Panel zone shear (AISC §J10.6)",
            "Vu_panel_kN": round(Vu, 3),
            **cap,
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }
        if not out["is_ok"]:
            out["doubler_plate"] = self.required_doubler()
        return out
