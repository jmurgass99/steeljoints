"""
base_plate.py — Column base plate design.
AISC Design Guide 1 (DG1), 3rd ed. + AISC 360-22 §J8.

Covers:
  - Concentric compression: bearing pressure design
  - Combined axial + moment: pressure distribution (case 1 & 2)
  - Anchor bolt tension for uplift/moment cases
"""
from __future__ import annotations
from dataclasses import dataclass
from math import sqrt


@dataclass
class BasePlate:
    """
    Column base plate under axial load and bending moment.

    Parameters
    ----------
    Pu : float  factored axial load [kN] (positive = compression)
    Mu : float  factored moment at base [kN·m]
    Vu : float  factored shear [kN]
    column_d : float  column depth (bf for wide flange, d) [mm]
    column_bf : float  column flange width [mm]
    plate_B : float  plate width [mm] (parallel to column bf)
    plate_N : float  plate length [mm] (parallel to column d)
    plate_Fy : float  plate yield stress [MPa]
    fc_concrete : float  concrete compressive strength f'c [MPa]
    A2_A1 : float  confinement ratio √(A2/A1) ≤ 2.0 (AISC §J8)
    n_anchors : int  number of anchor bolts in tension zone
    anchor_diameter : float  anchor bolt diameter [mm]
    anchor_Fut : float  anchor bolt tensile strength [MPa]
    code : str  'AISC'

    Reference: AISC Design Guide 1, 3rd edition.
    """
    Pu: float                      # kN (+ = compression)
    Mu: float = 0.0                # kN·m
    Vu: float = 0.0                # kN
    column_d: float = 300.0        # mm
    column_bf: float = 200.0       # mm
    plate_B: float = 350.0         # mm
    plate_N: float = 400.0         # mm
    plate_Fy: float = 345.0        # MPa
    fc_concrete: float = 28.0      # MPa
    A2_A1: float = 1.0             # confinement factor ≤ 2.0
    n_anchors: int = 4             # bolts in tension zone
    anchor_diameter: float = 25.4  # mm (1")
    anchor_Fut: float = 827.0      # MPa (A36 rod → 400, F1554 Gr36/55/105)

    def __post_init__(self) -> None:
        self.Pu_N = self.Pu * 1000
        self.Mu_Nmm = self.Mu * 1e6
        self.A1 = self.plate_B * self.plate_N  # mm²
        # AISC DG1 design bearing strength
        self.Fp_max = 0.85 * self.fc_concrete * min(self.A2_A1, 2.0)

    # ------------------------------------------------------------------
    # Case 1: Concentric compression only
    # ------------------------------------------------------------------
    def bearing_pressure(self) -> float:
        """Maximum bearing pressure fp [MPa].

        Con traccion (Pu < 0) la placa no aprieta el hormigon: la presion de
        contacto es 0, no negativa (B59: fp < 0 llevaba `sqrt` a un dominio
        invalido en `required_thickness` y `design()` reventaba).
        """
        return max(self.Pu_N, 0.0) / self.A1

    def bearing_check(self) -> dict:
        """φcFp = 0.65 × 0.85 × f'c × √(A2/A1) (AISC §J8)."""
        phi_Fp = 0.65 * self.Fp_max
        fp = self.bearing_pressure()
        util = fp / phi_Fp
        return {
            "check": "Concrete bearing",
            "fp_MPa": round(fp, 3),
            "phi_Fp_MPa": round(phi_Fp, 3),
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
        }

    # ------------------------------------------------------------------
    # Plate thickness — DG1 Eq. 3.3.4
    # ------------------------------------------------------------------
    def required_thickness(self) -> dict:
        """
        Minimum plate thickness from bending (DG1 §3.3.4).
        tp,req = l · √(2 · fp / (0.9 · Fy))
        where l = max(m, n, lambda_n) cantilever dimensions.

        Con traccion (Pu < 0) esta formula de compresion daria tp = 0, un
        espesor FABRICADO: la placa flecta por la traccion de los anclajes, que
        este modulo no calcula. Sale NO EVALUADO, no 0 ni un aprobado (B59).
        """
        if self.Pu_N < 0:
            return {
                "check": "Plate thickness",
                "tp_required_mm": None,
                "utilization": None,
                "is_ok": None,
                "motivo_no_evaluado": (
                    "Pu < 0 (levantamiento): la placa flecta por la traccion de "
                    "los anclajes y esa comprobacion no esta implementada; la "
                    "formula DG1 §3.3.4 es de compresion"
                ),
            }
        fp = self.bearing_pressure()
        m = (self.plate_N - 0.95 * self.column_d) / 2
        n = (self.plate_B - 0.80 * self.column_bf) / 2
        # Lambda·n' (AISC DG1 Eq. 3.3.4a)
        X_num = 4 * self.column_d * self.column_bf * fp
        X_den = (self.column_d + self.column_bf)**2 * 0.9 * self.plate_Fy
        X = min(X_num / X_den, 1.0) if X_den > 0 else 0
        lam = 2 * sqrt(X) / (1 + sqrt(1 - X)) if X < 1 else 1.0
        n_prime = sqrt(self.column_d * self.column_bf) / 4
        l_crit = max(abs(m), abs(n), lam * n_prime)
        tp_req = l_crit * sqrt(2 * fp / (0.9 * self.plate_Fy))
        return {
            "check": "Plate thickness",
            "m_mm": round(m, 2),
            "n_mm": round(n, 2),
            "lambda_n_prime_mm": round(lam * n_prime, 2),
            "l_crit_mm": round(l_crit, 2),
            "tp_required_mm": round(tp_req, 2),
            "utilization": 0.0,  # informational check — no demand/capacity ratio
            "is_ok": True,
        }

    # ------------------------------------------------------------------
    # Anchor bolt tension (moment + uplift)
    # ------------------------------------------------------------------
    def anchor_tension(self) -> dict:
        """
        Anchor bolt required tension when moment causes net uplift.
        Simplified: T = Mu/lever_arm - Pu (if eccentricity > N/6)
        """
        from math import pi

        if self.Pu_N < 0:
            # Uplift case
            lever_arm = self.plate_N * 0.8
            T_total_N = abs(self.Pu_N) + abs(self.Mu_Nmm) / max(lever_arm, 1.0)
            T_per_N = T_total_N / self.n_anchors
            note = "Uplift/tension case — bolts resist full tension + moment couple"
        else:
            # Kern limit: |Mu| <= (N/6)·|Pu| equivale a e <= N/6 sin indeterminacion en Pu=0
            kern = self.plate_N / 6
            if abs(self.Mu_Nmm) <= kern * abs(self.Pu_N):
                # Full compression — no anchor tension needed
                return {
                    "check": "Anchor bolt tension",
                    "T_per_bolt_kN": 0.0,
                    "phi_Rnt_kN": None,
                    "utilization": 0.0,
                    "is_ok": True,
                    "note": "Full compression — no tension in anchors",
                }
            # Simplified linear pressure: T = (|Mu| - (N/6)·|Pu|) / (N/2 - N/6)
            T_total_N = (abs(self.Mu_Nmm) - kern * abs(self.Pu_N)) / (self.plate_N / 2 - kern)
            T_total_N = max(T_total_N, 0)
            T_per_N = T_total_N / self.n_anchors
            note = "Moment eccentricity > N/6 — tension zone exists"

        # Anchor capacity
        Ab = pi * self.anchor_diameter**2 / 4
        phi_Rnt = 0.75 * 0.75 * self.anchor_Fut * Ab  # phi=0.75, k=0.75 (embedded)
        util = T_per_N / phi_Rnt
        return {
            "check": "Anchor bolt tension",
            "T_per_bolt_kN": round(T_per_N / 1000, 3),
            "phi_Rnt_kN": round(phi_Rnt / 1000, 3),
            "utilization": round(util, 4),
            "is_ok": util <= 1.0,
            "note": note,
        }

    def design(self) -> dict:
        """Full base plate design report."""
        checks = [
            self.bearing_check(),
            self.required_thickness(),
            self.anchor_tension(),
        ]
        # Un check NO EVALUADO (utilization/is_ok None) no entra en el maximo y
        # no puede firmar: un FALLA manda; si no hay fallo pero falta un check,
        # el informe no es un aprobado (None), igual que dc_summary (B45) (B59).
        evaluados = [c for c in checks if c["utilization"] is not None]
        governing = max(evaluados, key=lambda c: c["utilization"])
        estados = [c["is_ok"] for c in checks]
        if any(e is False for e in estados):
            all_ok = False
        elif any(e is None for e in estados):
            all_ok = None
        else:
            all_ok = True
        # Sin fallo pero con un check sin evaluar, la utilizacion gobernante NO
        # se conoce (el que falta podia gobernar): no se publica la de los
        # presentes, que un lector tomaria por la de la placa.
        gov_check = governing["check"] if all_ok is not None else None
        gov_util = governing["utilization"] if all_ok is not None else None
        return {
            "connection_type": "Column Base Plate",
            "code": "AISC DG1",
            "Pu_kN": self.Pu,
            "Mu_kNm": self.Mu,
            "Vu_kN": self.Vu,
            "plate_B_mm": self.plate_B,
            "plate_N_mm": self.plate_N,
            "plate_Fy_MPa": self.plate_Fy,
            "fc_MPa": self.fc_concrete,
            "Fp_max_MPa": round(self.Fp_max, 3),
            "checks": checks,
            "governing_check": gov_check,
            "governing_utilization": gov_util,
            "all_checks_ok": all_ok,
            "summary": ("✅ OK" if all_ok is True else
                        "❌ FAILED" if all_ok is False else "NO EVALUADO"),
        }
