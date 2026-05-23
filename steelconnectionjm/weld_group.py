"""
weld_group.py — Grupo de soldaduras bajo carga excéntrica.

Implementa:
  1. Método elástico (vector): combinación vectorial de cortante directo
     (P/Aw) + torsión (M·c/Ip). Trata la soldadura como elemento lineal
     ("line method") con área Aw = Σ Li y momento polar Ip = Σ (Ix + Iy).
     Referencia: AISC Manual Part 8, Ec. 8-11; Blodgett "Design of Welded Structures".

  2. Método de rotura instantánea (Instantaneous Center of Rotation, ICR):
     análogo al ICR de pernos. Curva R(θ,Δ) de soldadura de filete según
     Lesik & Kennedy (1990), adoptada por AISC Manual Part 8 Tablas 8-4 a 8-11:

        R(θ) = 0.60·FEXX·(1.0 + 0.50·sin^1.5 θ)  · f(p)
        f(p) = [p(1.9 - 0.9·p)]^0.3
        p    = Δ / Δu,  Δu = 1.087·w·(θ+6)^(-0.65) ≤ 0.17·w  [in]

Unidades internas: mm, N, MPa. Posiciones (x,y) en mm. Cargas en N.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from math import sqrt, sin, cos, radians, degrees, atan2, exp, pi

from .exceptions import ConvergenceError

log = logging.getLogger("steelconnectionjm.weld_group")


# ---------------------------------------------------------------------------
# Segmento de soldadura
# ---------------------------------------------------------------------------
@dataclass
class WeldSegment:
    """
    Un tramo recto de soldadura de filete.

    Parameters
    ----------
    x1, y1 : extremo inicial [mm]
    x2, y2 : extremo final   [mm]
    w_mm   : tamaño nominal (leg) [mm]
    """
    x1: float; y1: float
    x2: float; y2: float
    w_mm: float

    def __post_init__(self) -> None:
        self.L = sqrt((self.x2 - self.x1)**2 + (self.y2 - self.y1)**2)
        self.a = self.w_mm / sqrt(2.0)  # garganta efectiva [mm]
        self.cx = 0.5 * (self.x1 + self.x2)
        self.cy = 0.5 * (self.y1 + self.y2)
        self.angle = atan2(self.y2 - self.y1, self.x2 - self.x1)  # rad


# ---------------------------------------------------------------------------
# Método elástico
# ---------------------------------------------------------------------------
@dataclass
class WeldGroupElastic:
    """
    Grupo de soldaduras — Método elástico (AISC Manual Part 8).

    Trata la soldadura como elemento lineal (line method). Devuelve la
    tensión resultante máxima [N/mm de soldadura] que debe compararse con
    φRn por unidad de longitud (0.60·FEXX·a·1.0 para fillet).

    Parameters
    ----------
    segments : list[WeldSegment]
    Vx, Vy   : componentes de la carga aplicada [N] (en el centroide indicado)
    Mz       : momento aplicado [N·mm] (positivo antihorario)
    load_point : (x,y) punto de aplicación de la carga [mm]. Si None, se usa
                 el centroide del grupo (sin momento adicional).
    """
    segments: list[WeldSegment]
    Vx: float = 0.0
    Vy: float = 0.0
    Mz: float = 0.0
    load_point: tuple[float, float] = None

    def __post_init__(self) -> None:
        Ls = [s.L for s in self.segments]
        self.Lw_total = sum(Ls)  # mm de soldadura (line method: A = ΣL)
        # Centroide ponderado por longitud
        self.cx = sum(s.L * s.cx for s in self.segments) / self.Lw_total
        self.cy = sum(s.L * s.cy for s in self.segments) / self.Lw_total
        # Momentos de inercia (line element, espesor unitario)
        Ix = 0.0; Iy = 0.0
        for s in self.segments:
            dx = s.cx - self.cx
            dy = s.cy - self.cy
            # Línea: Ix_own (eje x global) = L³/12 · sin²θ ; análogo Iy
            Ix_own = (s.L**3) / 12.0 * sin(s.angle)**2
            Iy_own = (s.L**3) / 12.0 * cos(s.angle)**2
            Ix += Ix_own + s.L * dy**2
            Iy += Iy_own + s.L * dx**2
        self.Ix = Ix
        self.Iy = Iy
        self.Ip = Ix + Iy
        # Momento neto respecto al centroide
        if self.load_point is None:
            self.M_net = self.Mz
        else:
            lx, ly = self.load_point
            # Momento adicional por excentricidad: M = Mz + Vy·(lx-cx) - Vx·(ly-cy)
            self.M_net = self.Mz + self.Vy * (lx - self.cx) - self.Vx * (ly - self.cy)

    def stress_at(self, x: float, y: float) -> dict:
        """
        Tensión resultante en punto (x,y) del grupo [N/mm de soldadura].

        f_direct_x = Vx / Lw
        f_direct_y = Vy / Lw
        f_tors_x   = -M · (y - cy) / Ip
        f_tors_y   = +M · (x - cx) / Ip
        """
        fdx = self.Vx / self.Lw_total
        fdy = self.Vy / self.Lw_total
        ftx = -self.M_net * (y - self.cy) / self.Ip if self.Ip > 0 else 0.0
        fty =  self.M_net * (x - self.cx) / self.Ip if self.Ip > 0 else 0.0
        fx = fdx + ftx
        fy = fdy + fty
        f_res = sqrt(fx*fx + fy*fy)
        return {"fx": fx, "fy": fy, "f_resultant": f_res}

    def max_demand(self) -> dict:
        """
        Tensión máxima en el grupo: evalúa en los extremos de cada segmento
        (donde típicamente el brazo es máximo).
        """
        f_max = 0.0
        x_max, y_max = 0.0, 0.0
        for s in self.segments:
            for (x, y) in [(s.x1, s.y1), (s.x2, s.y2)]:
                f = self.stress_at(x, y)["f_resultant"]
                if f > f_max:
                    f_max, x_max, y_max = f, x, y
        return {
            "f_max_N_per_mm": round(f_max, 3),
            "x_critical_mm": round(x_max, 2),
            "y_critical_mm": round(y_max, 2),
            "Lw_total_mm": round(self.Lw_total, 2),
            "Ip_mm3": round(self.Ip, 1),
            "cx_mm": round(self.cx, 2),
            "cy_mm": round(self.cy, 2),
        }

    def utilization(self, FEXX_MPa: float, w_mm: float,
                     phi: float = 0.75) -> dict:
        """
        Compara f_max contra φ·Rn por mm de soldadura.
        φRn/mm = φ · 0.60·FEXX · a   (AISC §J2.4)
        """
        a = w_mm / sqrt(2.0)
        phi_Rn_per_mm = phi * 0.60 * FEXX_MPa * a
        d = self.max_demand()
        util = d["f_max_N_per_mm"] / phi_Rn_per_mm if phi_Rn_per_mm > 0 else float("inf")
        return {
            **d,
            "phi_Rn_per_mm_N": round(phi_Rn_per_mm, 2),
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
            "method": "Elastic vector (AISC Manual Part 8)",
        }


# ---------------------------------------------------------------------------
# Método de rotura instantánea (ICR)
# ---------------------------------------------------------------------------
DELTA_U_FACTOR_IN = 1.087    # Δu = 1.087·w·(θ+6)^-0.65 [in]
DELTA_U_CAP_IN = 0.17        # Δu ≤ 0.17·w [in]


def _weld_capacity_at_angle_deformation(theta_deg: float, delta_mm: float,
                                         w_mm: float, FEXX_MPa: float) -> float:
    """
    Tensión [N/mm de soldadura] segun Lesik & Kennedy (AISC Manual Part 8).
    θ: ángulo entre carga y eje de la soldadura [deg].
    Δ: deformación de este elemento [mm].
    w: leg size [mm]; FEXX: resistencia electrodo [MPa].

    R(θ,Δ) = 0.60·FEXX·a·(1 + 0.50·sin^1.5 θ) · f(p)
    f(p)   = [p(1.9 - 0.9 p)]^0.3
    p = Δ / Δu
    """
    a = w_mm / sqrt(2.0)
    # Deformación última (in)
    w_in = w_mm / 25.4
    delta_in = delta_mm / 25.4
    du_in = min(DELTA_U_FACTOR_IN * w_in * (theta_deg + 6.0) ** (-0.65),
                DELTA_U_CAP_IN * w_in)
    p = delta_in / du_in if du_in > 0 else 0.0
    p = max(0.0, min(p, 1.0))
    fp = (p * (1.9 - 0.9 * p)) ** 0.3 if p > 0 else 0.0
    Rnw_per_mm = 0.60 * FEXX_MPa * a * (1.0 + 0.50 * sin(radians(theta_deg))**1.5) * fp
    return Rnw_per_mm


@dataclass
class WeldGroupICR:
    """
    Grupo de soldaduras — Método de rotura instantánea (ICR).

    Subdivide cada segmento en N elementos y resuelve la posición del IC tal
    que se satisfaga el equilibrio (ΣFx = ΣFy - Pu = ΣM = 0).

    Parameters
    ----------
    segments : list[WeldSegment]
    Pu_N     : carga aplicada [N]
    ex_mm    : excentricidad de la carga respecto al centroide [mm]
    load_angle_deg : ángulo de la carga respecto a +Y [deg]
    FEXX_MPa : resistencia del electrodo
    n_subdiv : elementos por segmento (típ. 20+)
    """
    segments: list[WeldSegment]
    Pu_N: float
    ex_mm: float
    load_angle_deg: float = 0.0
    FEXX_MPa: float = 482.6
    n_subdiv: int = 30

    def __post_init__(self) -> None:
        # Discretizar
        self.elements = []  # (x, y, dL, w, axis_angle_rad)
        for s in self.segments:
            for k in range(self.n_subdiv):
                t = (k + 0.5) / self.n_subdiv
                x = s.x1 + t * (s.x2 - s.x1)
                y = s.y1 + t * (s.y2 - s.y1)
                dL = s.L / self.n_subdiv
                self.elements.append((x, y, dL, s.w_mm, s.angle))
        Lw = sum(e[2] for e in self.elements)
        self.cx = sum(e[0] * e[2] for e in self.elements) / Lw
        self.cy = sum(e[1] * e[2] for e in self.elements) / Lw

    def _residual(self, x_ic: float, y_ic: float) -> dict:
        # Calcular r_max
        rs = []
        for (x, y, dL, w, ax) in self.elements:
            rx = x - x_ic
            ry = y - y_ic
            ri = sqrt(rx*rx + ry*ry)
            rs.append((rx, ry, ri))
        r_max = max(r for (_, _, r) in rs)
        if r_max < 1e-9:
            return {}
        # Δ_max = 1.087 · w · (θ+6)^-0.65 (in) ≤ 0.17·w. Pero AISC simplifica:
        # Δ_max_critico = 0.17·w (in) para el elemento más alejado.
        # Cada elemento: Δi = Δ_crit · ri / r_max ; con Δ_crit del elemento crítico.
        # Tomamos w del primer elemento crítico (aprox. uniforme).
        ang_load = radians(self.load_angle_deg)
        Px_hat = sin(ang_load)
        Py_hat = cos(ang_load)
        Fx_sum = 0.0; Fy_sum = 0.0; M_sum = 0.0
        # Δ crítica (en mm): se determina iterando con el elemento crítico
        # AISC usa Δ_max = 1.087·w·(θ_crit + 6)^-0.65 in del elemento más alejado.
        crit = max(zip(self.elements, rs), key=lambda t: t[1][2])
        (xc, yc, dLc, wc, axc), (rxc, ryc, ric) = crit
        # θ_crit: ángulo entre la fuerza del elemento crítico (perp al r) y su eje
        force_dir_c = (-ryc / ric, rxc / ric)
        weld_axis_c = (cos(axc), sin(axc))
        cos_th_c = abs(force_dir_c[0]*weld_axis_c[0] + force_dir_c[1]*weld_axis_c[1])
        cos_th_c = min(1.0, max(0.0, cos_th_c))
        theta_c_deg = degrees(__import__("math").acos(cos_th_c))
        # Para el elemento crítico, su θ; usamos AISC simplificación Δmax=0.17·w
        wc_in = wc / 25.4
        delta_max_in_crit = min(DELTA_U_FACTOR_IN * wc_in * (theta_c_deg + 6.0)**(-0.65),
                                DELTA_U_CAP_IN * wc_in)
        delta_max_mm_crit = delta_max_in_crit * 25.4

        for (elem, (rx, ry, ri)) in zip(self.elements, rs):
            x, y, dL, w, ax = elem
            # Fuerza perpendicular al vector IC→elemento
            ux = -ry / ri
            uy =  rx / ri
            # θ entre dirección de la fuerza y eje de la soldadura
            cax = cos(ax); sax = sin(ax)
            cos_th = abs(ux * cax + uy * sax)
            cos_th = min(1.0, max(0.0, cos_th))
            theta_deg = degrees(__import__("math").acos(cos_th))
            # Deformación de este elemento (proporcional a ri)
            delta_i = delta_max_mm_crit * ri / ric
            R_per_mm = _weld_capacity_at_angle_deformation(theta_deg, delta_i, w, self.FEXX_MPa)
            Fi = R_per_mm * dL  # [N]
            Fx_sum += Fi * ux
            Fy_sum += Fi * uy
            M_sum  += ri * Fi
        return {"Fx": Fx_sum, "Fy": Fy_sum, "M": M_sum, "r_max": r_max,
                "Px_hat": Px_hat, "Py_hat": Py_hat}

    # ------------------------------------------------------------------
    def _load_geometry(self):
        import math
        ang = math.radians(self.load_angle_deg)
        Px_hat = math.sin(ang); Py_hat = math.cos(ang)
        perp_x = -Py_hat;       perp_y = Px_hat
        sign = 1.0 if self.ex_mm >= 0 else -1.0
        return Px_hat, Py_hat, perp_x, perp_y, sign, abs(self.ex_mm)

    # ------------------------------------------------------------------
    # Solver 1: Bisección 1D (legado — fallback)
    # ------------------------------------------------------------------
    def _solve_ic_bisection(self, tol: float = 1e-3, max_iter: int = 200):
        Px_hat, Py_hat, perp_x, perp_y, sign, ex_abs = self._load_geometry()

        def residual(r0: float):
            x_ic = self.cx - sign * r0 * perp_x
            y_ic = self.cy - sign * r0 * perp_y
            r = self._residual(x_ic, y_ic)
            if not r:
                return float("inf"), None, (x_ic, y_ic)
            F_along = r["Fx"] * Px_hat + r["Fy"] * Py_hat
            arm = r0 + ex_abs
            if arm <= 0:
                return float("inf"), None, (x_ic, y_ic)
            P_from_M = r["M"] / arm
            return abs(F_along) - P_from_M, (P_from_M, r), (x_ic, y_ic)

        r_lo, r_hi = 1.0, max(500.0, 10 * ex_abs + 500.0)
        f_lo, info_lo, _ = residual(r_lo)
        f_hi, info_hi, _ = residual(r_hi)
        tries = 0
        while f_lo * f_hi > 0 and tries < 20:
            r_hi *= 2.0
            f_hi, info_hi, _ = residual(r_hi)
            tries += 1

        if f_lo * f_hi > 0:
            r_best, f_best, info_best, pt_best = r_lo, abs(f_lo), info_lo, None
            for k in range(1, 400):
                r = r_lo + (r_hi - r_lo) * k / 400.0
                f, info, pt = residual(r)
                if abs(f) < f_best:
                    r_best, f_best, info_best, pt_best = r, abs(f), info, pt
            r0, info, pt = r_best, info_best, pt_best
        else:
            for _ in range(max_iter):
                r_mid = 0.5 * (r_lo + r_hi)
                f_mid, info_mid, pt_mid = residual(r_mid)
                if abs(f_mid) < tol:
                    r_lo = r_mid
                    break
                if f_lo * f_mid < 0:
                    r_hi = r_mid
                else:
                    r_lo = r_mid; f_lo = f_mid
            r0 = 0.5 * (r_lo + r_hi)
            _, info, pt = residual(r0)

        Pn = info[0] if info else 0.0
        x_ic, y_ic = pt if pt else (0.0, 0.0)
        return x_ic, y_ic, Pn, info[1] if info else {}

    # ------------------------------------------------------------------
    # Solver 2: Newton 2D
    # ------------------------------------------------------------------
    def _residual_full(self, x_ic: float, y_ic: float):
        """
        Versión extendida de `_residual` que además computa el momento
        de las fuerzas de soldadura respecto a un punto arbitrario A.
        Devuelve (Fx, Fy, M_ic, r_max, contribuciones_por_elemento).
        """
        import math
        rs = []
        for (x, y, dL, w, ax) in self.elements:
            rx = x - x_ic; ry = y - y_ic
            ri = sqrt(rx*rx + ry*ry)
            rs.append((rx, ry, ri))
        r_max = max(r for (_, _, r) in rs)
        if r_max < 1e-9:
            return None
        # Δ crítico del elemento más alejado (igual que en _residual)
        crit = max(zip(self.elements, rs), key=lambda t: t[1][2])
        (xc, yc, dLc, wc, axc), (rxc, ryc, ric) = crit
        force_dir_c = (-ryc / ric, rxc / ric)
        weld_axis_c = (cos(axc), sin(axc))
        cos_th_c = abs(force_dir_c[0]*weld_axis_c[0] + force_dir_c[1]*weld_axis_c[1])
        cos_th_c = min(1.0, max(0.0, cos_th_c))
        theta_c_deg = degrees(math.acos(cos_th_c))
        wc_in = wc / 25.4
        delta_max_in_crit = min(DELTA_U_FACTOR_IN * wc_in * (theta_c_deg + 6.0)**(-0.65),
                                DELTA_U_CAP_IN * wc_in)
        delta_max_mm_crit = delta_max_in_crit * 25.4

        Fx_sum = 0.0; Fy_sum = 0.0; M_ic = 0.0
        contribs = []  # (x_global, y_global, Fx, Fy)
        for (elem, (rx, ry, ri)) in zip(self.elements, rs):
            x, y, dL, w, ax = elem
            ux = -ry / ri; uy = rx / ri
            cax = cos(ax); sax = sin(ax)
            cos_th = abs(ux*cax + uy*sax)
            cos_th = min(1.0, max(0.0, cos_th))
            theta_deg = degrees(math.acos(cos_th))
            delta_i = delta_max_mm_crit * ri / ric
            R_per_mm = _weld_capacity_at_angle_deformation(theta_deg, delta_i, w, self.FEXX_MPa)
            Fi = R_per_mm * dL
            Fx = Fi * ux; Fy = Fi * uy
            Fx_sum += Fx
            Fy_sum += Fy
            M_ic += ri * Fi
            contribs.append((x, y, Fx, Fy))
        return Fx_sum, Fy_sum, M_ic, r_max, contribs

    def _solve_ic_newton2d(self, tol: float = 1e-4, max_iter: int = 50):
        from scipy.optimize import fsolve
        Px_hat, Py_hat, perp_x, perp_y, sign, ex_abs = self._load_geometry()
        # Punto de aplicación de la carga (coords globales)
        Ax = self.cx + sign * ex_abs * perp_x
        Ay = self.cy + sign * ex_abs * perp_y

        def equations(ic_xy):
            x_ic, y_ic = ic_xy
            res = self._residual_full(x_ic, y_ic)
            if res is None:
                return [1e9, 1e9]
            Fx_b, Fy_b, _M_ic, _rmax, contribs = res
            # Momento neto respecto al punto de aplicación A
            M_about_A = sum((x - Ax) * Fy - (y - Ay) * Fx
                            for (x, y, Fx, Fy) in contribs)
            R1 = Fx_b * Py_hat - Fy_b * Px_hat
            R2 = M_about_A
            return [R1, R2]

        # Punto inicial razonable
        xs = [e[0] for e in self.elements]
        ys = [e[1] for e in self.elements]
        size = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
        r0_guess = max(0.1 * size, min(2.0 * ex_abs + 0.5 * size, 5.0 * ex_abs + 2.0 * size))
        x0 = self.cx - sign * r0_guess * perp_x
        y0 = self.cy - sign * r0_guess * perp_y

        try:
            sol, _, ier, _ = fsolve(equations, [x0, y0], full_output=True,
                                    xtol=tol, maxfev=max_iter * 10)
            x_ic, y_ic = float(sol[0]), float(sol[1])
            res = self._residual_full(x_ic, y_ic)
            if res is None:
                return None
            Fx_b, Fy_b, M_ic_b, r_max, _ = res
            r_final = equations([x_ic, y_ic])
            F_scale = max(sqrt(Fx_b*Fx_b + Fy_b*Fy_b), 1e-9)
            M_scale = max(abs(M_ic_b), F_scale * max(r_max, 1.0), 1e-9)
            if (abs(r_final[0]) / F_scale > 1e-3 or
                abs(r_final[1]) / M_scale > 1e-3):
                # Reintento con perturbación
                sol2, _, _, _ = fsolve(equations,
                                       [x0 + 0.05 * size, y0 + 0.05 * size],
                                       full_output=True, xtol=tol,
                                       maxfev=max_iter * 10)
                x_ic, y_ic = float(sol2[0]), float(sol2[1])
                res = self._residual_full(x_ic, y_ic)
                if res is None:
                    return None
                Fx_b, Fy_b, M_ic_b, r_max, _ = res
                r_final = equations([x_ic, y_ic])
                F_scale = max(sqrt(Fx_b*Fx_b + Fy_b*Fy_b), 1e-9)
                M_scale = max(abs(M_ic_b), F_scale * max(r_max, 1.0), 1e-9)
                if (abs(r_final[0]) / F_scale > 1e-3 or
                    abs(r_final[1]) / M_scale > 1e-3):
                    return None
            Pn = abs(Fx_b * Px_hat + Fy_b * Py_hat)
            return x_ic, y_ic, Pn, {"Fx": Fx_b, "Fy": Fy_b,
                                    "M": M_ic_b, "r_max": r_max}
        except Exception:
            return None

    # ------------------------------------------------------------------
    def solve(self, tol: float = 1e-4, max_iter: int = 50) -> dict:
        """
        Resuelve por ICR usando Newton 2D; cae a bisección 1D si falla.
        Caso degenerado (ex_mm ≈ 0): cortante puro centrado, Pn = ΣR(Δmax)·L.
        """
        ex_abs = abs(self.ex_mm)
        # --- Caso degenerado: carga centrada ---
        if ex_abs < 1e-9:
            # Toda la soldadura a su capacidad ultima a 0° (longitudinal) o
            # 90° (transversal) según la dirección de carga.
            import math
            ang = math.radians(self.load_angle_deg)
            Pn = 0.0
            for (x, y, dL, w, ax) in self.elements:
                # Ángulo entre carga y eje de la soldadura
                load_dir = (math.sin(ang), math.cos(ang))
                weld_axis = (cos(ax), sin(ax))
                cth = abs(load_dir[0]*weld_axis[0] + load_dir[1]*weld_axis[1])
                cth = min(1.0, max(0.0, cth))
                theta_deg = degrees(math.acos(cth))
                # Δ máxima del elemento (mismo cap que el solver iterativo)
                w_in = w / 25.4
                du_in = min(DELTA_U_FACTOR_IN * w_in * (theta_deg + 6.0)**(-0.65),
                            DELTA_U_CAP_IN * w_in)
                delta_mm = du_in * 25.4
                R_per_mm = _weld_capacity_at_angle_deformation(
                    theta_deg, delta_mm, w, self.FEXX_MPa)
                Pn += R_per_mm * dL
            util = self.Pu_N / Pn if Pn > 0 else float("inf")
            return {
                "method": "ICR — Lesik & Kennedy (AISC Manual Part 8)",
                "solver": "centered_load",
                "Pn_N": round(Pn, 1),
                "Pn_kN": round(Pn / 1000.0, 3),
                "IC_x_mm": float("inf"),
                "IC_y_mm": float("inf"),
                "r0_mm": float("inf"),
                "Pu_N": self.Pu_N,
                "Pu_kN": self.Pu_N / 1000.0,
                "utilization": round(util, 4),
                "is_ok": util <= 1.0,
            }

        # --- Newton 2D primario ---
        log.debug("WeldGroupICR.solve: ex_abs=%.3f load_angle=%.2f n_elem=%d",
                  ex_abs, self.load_angle_deg, len(self.elements))
        solver_used = "newton2d"
        result = self._solve_ic_newton2d(tol=tol, max_iter=max_iter)
        if result is None:
            log.warning("Newton 2D no convergió en WeldGroupICR; cayendo a bisección")
            solver_used = "bisection_fallback"
            result = self._solve_ic_bisection(tol=max(tol, 1e-3), max_iter=200)

        if result is None or (isinstance(result, tuple) and len(result) >= 3
                              and (result[2] is None or result[2] <= 0)):
            raise ConvergenceError(
                f"ICR no convergió para WeldGroup (n_elem={len(self.elements)}, "
                f"ex_mm={self.ex_mm}, load_angle_deg={self.load_angle_deg}).",
                iteration=max_iter,
                residual=float("nan"),
            )

        log.debug("WeldGroupICR.solve: solver_used=%s Pn=%.3f", solver_used, result[2])
        x_ic, y_ic, Pn, info = result
        # r0 medido desde el centroide
        r0 = sqrt((x_ic - self.cx)**2 + (y_ic - self.cy)**2)
        util = self.Pu_N / Pn if Pn > 0 else float("inf")
        return {
            "method": "ICR — Lesik & Kennedy (AISC Manual Part 8)",
            "solver": solver_used,
            "Pn_N": round(Pn, 1),
            "Pn_kN": round(Pn / 1000.0, 3),
            "IC_x_mm": round(x_ic, 2),
            "IC_y_mm": round(y_ic, 2),
            "r0_mm": round(r0, 2),
            "Pu_N": self.Pu_N,
            "Pu_kN": self.Pu_N / 1000.0,
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }
