"""
bolt_group.py — Eccentric bolt group: Instantaneous Center of Rotation (ICR) method.

Reference
---------
AISC Manual 15th Ed., Part 7, "Design of Bolted Connections"
AISC 360-22 §J3 (commentary)
Crawford & Kulak (1971): "Eccentrically Loaded Bolted Connections", J. Struct. Div.

The ICR method assumes the bolt group rotates about an Instantaneous Center (IC).
Each bolt deformation Δi is proportional to its distance ri from the IC. The
load-deformation curve of a single bolt is empirical:

    R(Δ) = Rult · (1 - exp(-10·Δ))^0.55      with  Δmax = 0.34 in (8.6 mm)

Equilibrium (three equations) is iterated until the assumed IC produces forces
that satisfy ΣFx = ΣFy - Pu = ΣM(IC) = 0.

Units: positions in mm, forces in N, moments in N·mm. Output also in kN.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from math import sqrt, exp, atan2, cos, sin

from .exceptions import ConvergenceError, ConfigurationError

log = logging.getLogger("steelconnectionjm.bolt_group")


# Bolt load-deformation curve constants (Crawford & Kulak, AISC Manual)
DELTA_MAX = 8.6        # mm — deformación máxima del perno crítico (=0.34")
CURVE_LAMBDA = 10.0    # per in (convertido a per mm: 10/25.4)
CURVE_LAMBDA_MM = 10.0 / 25.4
CURVE_MU = 0.55


def _bolt_force(delta_mm: float, Rult_N: float) -> float:
    """
    Fuerza en un perno a deformación delta [N].
    R(Δ) = Rult · (1 - exp(-λ·Δ))^μ
    Δ en mm; λ original es 10/in = 10/25.4 /mm.
    """
    if delta_mm <= 0:
        return 0.0
    base = 1.0 - exp(-CURVE_LAMBDA_MM * delta_mm)
    return Rult_N * (base ** CURVE_MU)


@dataclass
class BoltGroupICR:
    """
    Grupo de pernos bajo carga excéntrica — Método ICR (AISC Manual Part 7).

    Parameters
    ----------
    positions : list[(x, y)]   posiciones de pernos [mm], referidas a un origen arbitrario.
    Pu_N      : float          carga aplicada [N]
    ex_mm     : float          excentricidad de la carga respecto al centroide [mm]
                               (medida perpendicular a la línea de acción)
    load_angle_deg : float     ángulo de la carga respecto al eje +Y [deg].
                               0 = carga vertical (gravity), 90 = horizontal.
    Rult_N    : float          resistencia última de un perno [N] (corte: 0.75·Fnv·Ab típ.)

    Notes
    -----
    Se asume todos los pernos del mismo tamaño/grado (Rult constante).
    Resultado: factor C tal que Pu_admisible = C · Rult.
    """
    positions: list[tuple[float, float]]
    Pu_N: float
    ex_mm: float
    load_angle_deg: float = 0.0   # 0 = vertical
    Rult_N: float = 1.0           # si =1, devuelve C directamente

    def __post_init__(self) -> None:
        self.n = len(self.positions)
        xs = [p[0] for p in self.positions]
        ys = [p[1] for p in self.positions]
        self.cx = sum(xs) / self.n
        self.cy = sum(ys) / self.n
        # Coords relativas al centroide
        self.rel = [(x - self.cx, y - self.cy) for (x, y) in self.positions]

    # ------------------------------------------------------------------
    def _residuals(self, x0: float, y0: float):
        """
        Para un IC supuesto en (x0,y0), calcula:
          - r_max (distancia al perno más alejado)
          - lista de (rx, ry, ri, Ri) por perno
          - ΣFx, ΣFy, ΣM(IC) inducidos por los pernos (resistencia)
        La fuerza de cada perno es perpendicular al vector IC->bolt y de
        magnitud R(Δi) con Δi = Δmax · ri / r_max.
        """
        bolt_data = []
        r_max = 0.0
        for (rx_c, ry_c) in self.rel:
            # Vector desde IC al perno
            rx = rx_c - x0
            ry = ry_c - y0
            ri = sqrt(rx*rx + ry*ry)
            bolt_data.append([rx, ry, ri])
            if ri > r_max:
                r_max = ri

        if r_max < 1e-9:
            return None

        Fx_sum = 0.0
        Fy_sum = 0.0
        M_sum = 0.0
        for bd in bolt_data:
            rx, ry, ri = bd
            delta_i = DELTA_MAX * ri / r_max
            Ri = _bolt_force(delta_i, self.Rult_N)
            # Dirección: perpendicular al vector IC→bolt, rotada 90° en
            # el sentido de la carga aplicada.
            # vector unitario perpendicular: (-ry/ri, +rx/ri)
            ux = -ry / ri
            uy =  rx / ri
            Fx = Ri * ux
            Fy = Ri * uy
            Fx_sum += Fx
            Fy_sum += Fy
            # Momento respecto a IC: |r × F| = ri · Ri (todos en mismo sentido)
            M_sum += ri * Ri
            bd.append(Ri)
        return Fx_sum, Fy_sum, M_sum, r_max, bolt_data

    # ------------------------------------------------------------------
    # Geometría auxiliar (carga / excentricidad)
    # ------------------------------------------------------------------
    def _load_geometry(self):
        """
        Devuelve (Px_hat, Py_hat, perp_x, perp_y, sign, ex_abs):
          - Px_hat, Py_hat: vector unitario de la carga aplicada P.
            load_angle_deg=0  → carga vertical (+Y), 90 → horizontal (+X).
          - perp_x, perp_y : unitario perpendicular a la carga, lado opuesto
            al punto de aplicación.
        """
        import math
        ang = math.radians(self.load_angle_deg)
        Px_hat = math.sin(ang)
        Py_hat = math.cos(ang)
        perp_x = -Py_hat
        perp_y =  Px_hat
        sign = 1.0 if self.ex_mm >= 0 else -1.0
        return Px_hat, Py_hat, perp_x, perp_y, sign, abs(self.ex_mm)

    # ------------------------------------------------------------------
    # Solver 1: Bisección 1D (legado — fallback)
    # ------------------------------------------------------------------
    def _solve_ic_bisection(self, tol: float = 1e-3, max_iter: int = 200):
        """
        Resuelve la posición del IC por bisección sobre r0 (distancia IC↔CG
        a lo largo del eje perpendicular a la carga). Sólo es exacto cuando
        la carga es perpendicular a un eje de simetría del grupo.

        Devuelve (x_ic_rel, y_ic_rel, Pn, info_dict) en coords relativas al CG.
        """
        Px_hat, Py_hat, perp_x, perp_y, sign, ex_abs = self._load_geometry()

        def residual(r0: float):
            x_ic = -sign * r0 * perp_x
            y_ic = -sign * r0 * perp_y
            res = self._residuals(x_ic, y_ic)
            if res is None:
                return float("inf"), {}
            Fx_sum, Fy_sum, M_sum, r_max, bolt_data = res
            arm = r0 + ex_abs
            if arm <= 0:
                return float("inf"), {}
            P_from_M = M_sum / arm
            F_along = Fx_sum * Px_hat + Fy_sum * Py_hat
            diff = abs(F_along) - P_from_M
            info = {
                "x_ic": x_ic, "y_ic": y_ic, "P_from_M": P_from_M,
                "F_along": F_along, "Fx_sum": Fx_sum, "Fy_sum": Fy_sum,
                "M_sum": M_sum, "r_max": r_max,
            }
            return diff, info

        r_lo, r_hi = 1.0, max(1000.0, 10 * ex_abs + 500.0)
        f_lo, _ = residual(r_lo)
        f_hi, _ = residual(r_hi)
        tries = 0
        while f_lo * f_hi > 0 and tries < 20:
            r_hi *= 2.0
            f_hi, _ = residual(r_hi)
            tries += 1

        if f_lo * f_hi > 0:
            r_best, f_best = r_lo, abs(f_lo)
            for k in range(1, 500):
                r = r_lo + (r_hi - r_lo) * k / 500.0
                f, _ = residual(r)
                if abs(f) < f_best:
                    f_best, r_best = abs(f), r
            r0 = r_best
        else:
            for _ in range(max_iter):
                r_mid = 0.5 * (r_lo + r_hi)
                f_mid, _ = residual(r_mid)
                if abs(f_mid) < tol:
                    r_lo = r_mid
                    break
                if f_lo * f_mid < 0:
                    r_hi = r_mid
                else:
                    r_lo = r_mid; f_lo = f_mid
            r0 = 0.5 * (r_lo + r_hi)

        _, info = residual(r0)
        Pn = info.get("P_from_M", 0.0)
        return info.get("x_ic", 0.0), info.get("y_ic", 0.0), Pn, info

    # ------------------------------------------------------------------
    # Solver 2: Newton 2D (recomendado — funciona con carga oblicua)
    # ------------------------------------------------------------------
    def _solve_ic_newton2d(self, tol: float = 1e-4, max_iter: int = 50):
        """
        Resuelve (x_ic, y_ic) por Newton-Raphson 2D usando scipy.fsolve.

        Ecuaciones de equilibrio (coords relativas al CG):
          La carga aplicada P actúa sobre la línea de acción definida por
          dirección (Px_hat, Py_hat) pasando por el punto de aplicación
          A = (ex_x, ex_y) = sign·ex_abs·(perp_x, perp_y) (al lado opuesto del IC).

          Para un IC dado, calculamos las fuerzas de los pernos (Fx_b, Fy_b)
          y su momento respecto al centroide. La magnitud Pn se determina
          de modo que el resultante de fuerzas iguale a la carga aplicada:

            Pn = |F_bolt| (proyectado en (Px_hat,Py_hat))
            Residuales:
              R1 = (Fx_b) - Pn·Px_hat
              R2 = (Fy_b) - Pn·Py_hat
          donde Pn se computa internamente desde el momento de equilibrio:
              Pn = M_bolts_about_A / 0  (no es estable) ⇒
          mejor: parametrizar Pn como incógnita escalar implícita y usar
          las 2 ecuaciones independientes:
              R1 = angle(F_bolt) - load_angle             (cross product = 0)
              R2 = M_bolts(IC) - Pn·d_IC_to_load_line     ; Pn = |F_bolt|

        En la práctica, eliminamos Pn definiendo:
              R1 = Fx_b · Py_hat - Fy_b · Px_hat          (resultante paralela a la carga)
              R2 = M_bolt_about_A                          (momento respecto al punto de aplic = 0)
        Estas 2 condiciones son equivalentes a equilibrio puro.
        """
        from scipy.optimize import fsolve
        import numpy as np

        Px_hat, Py_hat, perp_x, perp_y, sign, ex_abs = self._load_geometry()
        # Punto de aplicación de la carga (coords relativas al CG)
        Ax = sign * ex_abs * perp_x
        Ay = sign * ex_abs * perp_y

        def equations(ic_xy):
            x_ic, y_ic = ic_xy
            res = self._residuals(x_ic, y_ic)
            if res is None:
                return [1e9, 1e9]
            Fx_b, Fy_b, _M_ic, _rmax, _ = res
            # Momento neto de las fuerzas de los pernos respecto al
            # punto de aplicación de la carga A:
            #   M_about_A = Σ (rx_b - Ax)·Fy_i - (ry_b - Ay)·Fx_i
            # Como ya tenemos resumenes, lo recalculamos:
            M_about_A = 0.0
            for (rx_c, ry_c) in self.rel:
                rx = rx_c - x_ic
                ry = ry_c - y_ic
                ri = sqrt(rx*rx + ry*ry)
                if ri < 1e-12:
                    continue
                delta_i = DELTA_MAX * ri / _rmax
                Ri = _bolt_force(delta_i, self.Rult_N)
                ux = -ry / ri; uy = rx / ri
                Fx = Ri * ux; Fy = Ri * uy
                M_about_A += (rx_c - Ax) * Fy - (ry_c - Ay) * Fx
            # R1: resultante paralela a la carga (cross product nulo)
            R1 = Fx_b * Py_hat - Fy_b * Px_hat
            # R2: momento neto respecto a A = 0
            R2 = M_about_A
            return [R1, R2]

        # Punto inicial: centroide + offset al lado opuesto a la carga,
        # escalado por la excentricidad (mínimo 10% del tamaño del grupo).
        size = max(
            max(rx for rx, _ in self.rel) - min(rx for rx, _ in self.rel),
            max(ry for _, ry in self.rel) - min(ry for _, ry in self.rel),
            1.0,
        )
        r0_guess = max(0.1 * size, min(2.0 * ex_abs + 0.5 * size, 5.0 * ex_abs + 2.0 * size))
        x0 = -sign * r0_guess * perp_x
        y0 = -sign * r0_guess * perp_y

        try:
            sol, infodict, ier, _ = fsolve(
                equations, [x0, y0], full_output=True,
                xtol=tol, maxfev=max_iter * 10,
            )
            x_ic, y_ic = float(sol[0]), float(sol[1])
            res = self._residuals(x_ic, y_ic)
            if res is None:
                return None
            Fx_b, Fy_b, M_ic_b, r_max, _ = res
            # Verificar residuales contra una escala física (norma de la fuerza
            # resultante de los pernos, o brazo·F si predomina momento).
            r_final = equations([x_ic, y_ic])
            F_scale = max(sqrt(Fx_b * Fx_b + Fy_b * Fy_b), 1e-9)
            M_scale = max(abs(M_ic_b), F_scale * max(r_max, 1.0), 1e-9)
            # ier==1 → fsolve declaró convergencia; igualmente validamos.
            if (abs(r_final[0]) / F_scale > 1e-3 or
                abs(r_final[1]) / M_scale > 1e-3):
                # fsolve puede quedar atrapado en saddle si el problema es
                # casi-simétrico. Reintento con perturbación pequeña.
                x0p = x0 + 0.05 * size
                y0p = y0 + 0.05 * size
                sol2, _, ier2, _ = fsolve(
                    equations, [x0p, y0p], full_output=True,
                    xtol=tol, maxfev=max_iter * 10,
                )
                x_ic, y_ic = float(sol2[0]), float(sol2[1])
                res = self._residuals(x_ic, y_ic)
                if res is None:
                    return None
                Fx_b, Fy_b, M_ic_b, r_max, _ = res
                r_final = equations([x_ic, y_ic])
                F_scale = max(sqrt(Fx_b * Fx_b + Fy_b * Fy_b), 1e-9)
                M_scale = max(abs(M_ic_b), F_scale * max(r_max, 1.0), 1e-9)
                if (abs(r_final[0]) / F_scale > 1e-3 or
                    abs(r_final[1]) / M_scale > 1e-3):
                    return None
            # Pn = magnitud del resultante (proyectado en dirección de la carga)
            Pn = Fx_b * Px_hat + Fy_b * Py_hat
            Pn = abs(Pn)
            info = {
                "x_ic": x_ic, "y_ic": y_ic, "P_from_M": Pn,
                "Fx_sum": Fx_b, "Fy_sum": Fy_b, "M_sum": M_ic_b,
                "r_max": r_max,
            }
            return x_ic, y_ic, Pn, info
        except Exception:
            return None

    # ------------------------------------------------------------------
    def _is_aligned_with_axis(self, tol_deg: float = 1e-3) -> bool:
        """
        True si la carga aplicada está alineada con un eje cardinal
        (load_angle ≈ 0°, 90°, 180°, 270°). En ese caso la bisección 1D
        es exacta y preferible (más estable y rápida).
        """
        from math import radians, sin, cos
        ang = radians(self.load_angle_deg)
        s, c = sin(ang), cos(ang)
        return abs(s) < tol_deg or abs(c) < tol_deg

    # ------------------------------------------------------------------
    def solve(
        self,
        tol: float = 1e-4,
        max_iter: int = 50,
        solver: str = "auto",
    ) -> dict:
        """
        Resuelve el grupo de pernos por ICR.

        Parameters
        ----------
        solver : {"auto", "bisection", "newton2d"}
            - "bisection": fuerza el solver legado de bisección 1D
              (exacto sólo si la carga es paralela a un eje de simetría).
            - "newton2d": fuerza Newton 2D (scipy.optimize.fsolve).
              Si no converge, cae silenciosamente a bisección.
            - "auto" (default): usa bisección si la carga está alineada
              con un eje cardinal (0°/90°); de lo contrario Newton 2D,
              con bisección como fallback silencioso.

        Caso degenerado: si ex_mm ≈ 0 y la carga está en el centroide, el
        IC está en infinito y la capacidad es Pn = N · Rult (cortante puro).
        """
        ex_abs = abs(self.ex_mm)
        # --- Caso degenerado: carga centrada ---
        if ex_abs < 1e-9:
            Pn = self.n * self.Rult_N
            C = Pn / self.Rult_N if self.Rult_N > 0 else 0.0
            util = self.Pu_N / Pn if Pn > 0 else float("inf")
            return {
                "method": "ICR (Crawford-Kulak / AISC Manual Part 7)",
                "solver": "centered_load",
                "Pn_N": round(Pn, 1),
                "Pn_kN": round(Pn / 1000.0, 3),
                "C_coefficient": round(C, 4),
                "IC_x_mm": float("inf"),
                "IC_y_mm": float("inf"),
                "r0_mm": float("inf"),
                "r_max_mm": 0.0,
                "Pu_N": self.Pu_N,
                "Pu_kN": self.Pu_N / 1000.0,
                "utilization": round(util, 4),
                "is_ok": util <= 1.0,
            }

        # --- Dispatch ---
        if solver not in ("auto", "bisection", "newton2d"):
            raise ConfigurationError(
                f"solver debe ser 'auto', 'bisection' o 'newton2d'; recibido: {solver!r}"
            )

        use_bisection_first = (
            solver == "bisection"
            or (solver == "auto" and self._is_aligned_with_axis())
        )

        log.debug("BoltGroupICR.solve: solver=%s ex_abs=%.3f load_angle=%.2f n=%d",
                  solver, ex_abs, self.load_angle_deg, self.n)

        if use_bisection_first:
            solver_used = "bisection"
            result = self._solve_ic_bisection(tol=max(tol, 1e-3), max_iter=200)
            # result siempre devuelve algo (la bisección nunca falla aquí),
            # pero por consistencia validamos.
            if result is None or result[2] <= 0:
                log.warning("bisection no produjo solución válida; intentando Newton 2D")
                # Intento de rescate con Newton 2D
                alt = self._solve_ic_newton2d(tol=tol, max_iter=max_iter)
                if alt is not None:
                    solver_used = "newton2d_fallback"
                    result = alt
        else:
            solver_used = "newton2d"
            result = self._solve_ic_newton2d(tol=tol, max_iter=max_iter)
            if result is None:
                log.warning("Newton 2D no convergió; cayendo a bisección")
                solver_used = "bisection_fallback"
                result = self._solve_ic_bisection(
                    tol=max(tol, 1e-3), max_iter=200
                )

        if result is None or (isinstance(result, tuple) and len(result) >= 3
                              and (result[2] is None or result[2] <= 0)):
            raise ConvergenceError(
                f"ICR no convergió para BoltGroup (n={self.n}, "
                f"ex_mm={self.ex_mm}, load_angle_deg={self.load_angle_deg}).",
                iteration=max_iter,
                residual=float("nan"),
            )

        log.debug("BoltGroupICR.solve: solver_used=%s Pn=%.3f", solver_used, result[2])
        x_ic, y_ic, Pn, info = result
        C = Pn / self.Rult_N if self.Rult_N > 0 else 0.0
        util = self.Pu_N / Pn if Pn > 0 else float("inf")
        r0 = sqrt(x_ic * x_ic + y_ic * y_ic)

        return {
            "method": "ICR (Crawford-Kulak / AISC Manual Part 7)",
            "solver": solver_used,
            "Pn_N": round(Pn, 1),
            "Pn_kN": round(Pn / 1000.0, 3),
            "C_coefficient": round(C, 4),
            "IC_x_mm": round(x_ic + self.cx, 2),
            "IC_y_mm": round(y_ic + self.cy, 2),
            "r0_mm": round(r0, 2),
            "r_max_mm": round(info.get("r_max", 0), 2),
            "Pu_N": self.Pu_N,
            "Pu_kN": self.Pu_N / 1000.0,
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------
def rectangular_pattern(nx: int, ny: int, sx: float, sy: float) -> list[tuple[float, float]]:
    """
    Genera posiciones (x,y) de un patrón rectangular nx × ny con espaciamientos sx, sy.
    Centrado en (0,0).
    """
    xs = [(-(nx - 1) / 2.0 + i) * sx for i in range(nx)]
    ys = [(-(ny - 1) / 2.0 + j) * sy for j in range(ny)]
    return [(x, y) for x in xs for y in ys]
