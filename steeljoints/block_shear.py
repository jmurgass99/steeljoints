"""
block_shear.py — Block shear failure (AISC 360-22 §J4.3, EC3-1-8 §3.10.2).
"""
from __future__ import annotations


def block_shear_strength(Agv: float, Anv: float, Ant: float,
                          Fy: float, Fu: float,
                          Ubs: float = 1.0,
                          code: str = "AISC",
                          phi: float = 0.75,
                          gamma_M0: float = 1.0,
                          gamma_M2: float = 1.25) -> dict:
    """
    Block shear rupture strength.

    Parameters
    ----------
    Agv : float  gross area subject to shear [mm²]
    Anv : float  net area subject to shear [mm²]
    Ant : float  net area subject to tension [mm²]
    Fy  : float  yield stress [MPa]
    Fu  : float  ultimate stress [MPa]
    Ubs : float  uniform tension stress coefficient
                 1.0 for uniform tension (angles, plates)
                 0.5 for non-uniform (beams: bolts not in line)
    code : str   'AISC' or 'EC3'
    phi  : float  resistance factor (AISC)
    gamma_M0, gamma_M2 : float  partial factors (EC3)

    Returns
    -------
    dict with strength and governing failure mode.

    AISC 360-22 §J4.3:
        Rn = 0.6·Fu·Anv + Ubs·Fu·Ant  (rupture)
          or 0.6·Fy·Agv + Ubs·Fu·Ant  (yielding governs shear path)
        Design: φRn = 0.75·Rn

    EC3-1-8 §3.10.2 (Ec. 3.9, grupo simétrico):
        Veff,1,Rd = fu·Ant/γM2 + (1/√3)·fy·Anv/γM0
    Con el área NETA a cortante: hasta la versión 1.1 se usaba Agv y el resultado no coincidía con
    ``block_shear_multi`` (que ya usaba Anv).
    """
    code = code.upper()

    if code == "AISC":
        Rn_rupture  = 0.6 * Fu * Anv + Ubs * Fu * Ant
        Rn_yielding = 0.6 * Fy * Agv + Ubs * Fu * Ant
        Rn = min(Rn_rupture, Rn_yielding)
        phi_Rn = phi * Rn
        return {
            "code": "AISC 360-22 §J4.3",
            "Rn_rupture_N": round(Rn_rupture, 1),
            "Rn_yielding_N": round(Rn_yielding, 1),
            "Rn_N": round(Rn, 1),
            "phi_Rn_N": round(phi_Rn, 1),
            "phi_Rn_kN": round(phi_Rn / 1000, 3),
            "governs": "rupture" if Rn_rupture <= Rn_yielding else "shear_yielding",
        }
    else:  # EC3
        import math
        Veff = (Ant * Fu / gamma_M2) + (Anv * Fy) / (math.sqrt(3) * gamma_M0)
        return {
            "code": "EC3-1-8 §3.10.2",
            "Veff_N": round(Veff, 1),
            "Veff_kN": round(Veff / 1000, 3),
        }
