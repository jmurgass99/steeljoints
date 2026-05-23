"""EN 1993-1-10 — Selection of materials for fracture toughness and through-thickness properties.

References
----------
EN 1993-1-10:2005 — Material toughness and through-thickness properties.
- Section 2: Selection of materials for fracture toughness (Table 2.1).
- Section 3: Through-thickness properties (Z-quality, Z15/Z25/Z35 per EN 10164).

This module provides simplified design helpers. The fracture-toughness table is
implemented as a parametric model that reproduces the Table 2.1 ordering:
higher subgrade (JR -> J0 -> J2 -> K2/M/N) -> larger admissible thickness;
lower service temperature, higher tensile stress ratio -> smaller admissible
thickness. The numerical anchors are calibrated to the published table for
S355 at sigma_Ed = 0.75*fy_t and reference temperatures -10 / -20 / -30 deg C.
"""

from __future__ import annotations

from math import exp
from typing import Mapping, Optional

# Reference Charpy test temperatures (deg C) for the standard subgrades.
# (EN 10025-2; Table 2.1 of EN 1993-1-10 ordering.)
_TK27 = {
    "JR": 20.0,
    "J0": 0.0,
    "J2": -20.0,
    "K2": -20.0,  # 40 J at -20 deg C -> equivalent to ~ -30 deg C at 27 J
    "M":  -20.0,
    "N":  -20.0,
    "ML": -50.0,
    "NL": -50.0,
}

# Empirical shift (deg C) of the Charpy reference temperature to obtain the
# equivalent T27J used in the master-curve approach of EN 1993-1-10 Annex B.
_T_SHIFT = {
    "JR": 0.0,
    "J0": 0.0,
    "J2": 0.0,
    "K2": -10.0,
    "M":  -10.0,
    "N":  -10.0,
    "ML": -10.0,
    "NL": -10.0,
}


def reference_temperature(
    T_md: float,
    T_r: float = -25.0,
    T_sigma: float = 0.0,
    T_R: float = 0.0,
    T_ec: float = 0.0,
    T_eps: float = 0.0,
) -> float:
    """Return the reference temperature ``T_Ed`` of the detail, EN 1993-1-10 §2.2(3).

    ``T_Ed = T_md + T_r + T_sigma + T_R + T_ec + T_eps``

    Parameters
    ----------
    T_md : float
        Lowest air temperature at the site (deg C).
    T_r : float, default ``-25``
        Adjustment for radiation losses (typ. -5 deg C; -25 deg C is used by
        some NAs as a default minimum service temperature).
    T_sigma : float
        Stress and yield strength adjustment (deg C).
    T_R : float
        Adjustment for strain rate (deg C).
    T_ec : float
        Adjustment for cold forming (deg C).
    T_eps : float
        Adjustment for plastic strain (deg C).

    Returns
    -------
    float
        Reference temperature ``T_Ed`` in deg C.
    """
    return float(T_md + T_r + T_sigma + T_R + T_ec + T_eps)


def t_max_brittle_fracture(
    T_Ed: float,
    sigma_Ed: float,
    fy_t_ref: float,
    J: float = 27.0,
    steel_grade: str = "S355",
    subgrade: Optional[str] = None,
) -> float:
    """Maximum admissible plate thickness against brittle fracture, EN 1993-1-10 Table 2.1.

    A calibrated analytical surrogate of Table 2.1 is used so that the function
    is continuous in ``T_Ed`` and ``sigma_Ed/fy_t_ref``:

        t_max = t_ref(grade, subgrade) * exp( k_T * (T_Ed - T_ref(subgrade))
                                             - k_s * (sigma_Ed/fy_t_ref - 0.25) )

    with the following anchors (mm), reproducing Table 2.1 for S355 at
    sigma_Ed/fy_t_ref = 0.75:
        JR @ -10 deg C -> 25 mm
        J0 @ -10 deg C -> 40 mm
        J2 @ -10 deg C -> 60 mm
        K2 @ -10 deg C -> 75 mm
    and shifting by ~ a factor 1/2 for each -30 deg C of service temperature.

    Parameters
    ----------
    T_Ed : float
        Reference temperature of the detail (deg C). See
        :func:`reference_temperature`.
    sigma_Ed : float
        Tensile design stress at the detail (MPa, N/mm^2). Must be >= 0.
    fy_t_ref : float
        Reference yield strength of the plate at the thickness considered
        (MPa). Typically ``fy(t)`` of the nominal grade.
    J : float, default 27
        Charpy impact energy (J). Currently only 27 J is supported (the 40 J
        case is mapped onto the K2/N subgrade through ``subgrade``).
    steel_grade : str, default ``"S355"``
        Steel grade (``S235``, ``S275``, ``S355``, ``S420``, ``S460``,
        ``S690``).
    subgrade : str, optional
        Sub-grade (``"JR"``, ``"J0"``, ``"J2"``, ``"K2"``, ``"M"``, ``"N"``,
        ``"ML"``, ``"NL"``). If ``None`` it is parsed from ``steel_grade``
        (e.g. ``"S355J2"``).

    Returns
    -------
    float
        Maximum admissible plate thickness in millimetres (clipped to
        [5, 200] mm, the range of Table 2.1).
    """
    if sigma_Ed < 0.0:
        raise ValueError("sigma_Ed must be non-negative (tensile)")
    if fy_t_ref <= 0.0:
        raise ValueError("fy_t_ref must be positive")
    if J not in (27.0, 40.0):
        raise ValueError("J must be 27 or 40 J")

    sg = subgrade
    if sg is None:
        # Parse subgrade suffix from a string like "S355J2".
        for s in ("NL", "ML", "JR", "J0", "J2", "K2", "M", "N"):
            if steel_grade.endswith(s):
                sg = s
                break
        if sg is None:
            sg = "JR"
    sg = sg.upper()
    if sg not in _TK27:
        raise ValueError(f"unknown subgrade {sg!r}")

    # Grade penalty: stronger steels have lower Kmat -> smaller thickness.
    grade_factor = {
        "S235": 1.30,
        "S275": 1.15,
        "S355": 1.00,
        "S420": 0.80,
        "S460": 0.70,
        "S690": 0.45,
    }.get(steel_grade.split("J")[0].split("K")[0].split("M")[0].split("N")[0],
          1.00)

    # Anchor: t_ref at T_Ed = -10 deg C, sigma/fy = 0.75 for S355.
    t_anchor = {
        "JR": 25.0,
        "J0": 40.0,
        "J2": 60.0,
        "K2": 75.0,
        "M":  75.0,
        "N":  75.0,
        "ML": 110.0,
        "NL": 110.0,
    }[sg]

    # Calibrated sensitivities (per Table 2.1 trends).
    k_T = 0.023  # 1/deg C — halving every ~ 30 deg C colder
    k_s = 1.20   # per unit of sigma_Ed/fy

    sigma_ratio = sigma_Ed / fy_t_ref
    T_anchor = -10.0
    t_max = grade_factor * t_anchor * exp(
        k_T * (T_Ed - T_anchor) - k_s * (sigma_ratio - 0.75)
    )

    # Clip to the practical range of Table 2.1.
    if t_max < 5.0:
        t_max = 5.0
    if t_max > 200.0:
        t_max = 200.0
    return float(t_max)


def Z_property_required(
    z_Ed: float,
    conditions: Optional[Mapping[str, float]] = None,
) -> str:
    """Required through-thickness quality class per EN 1993-1-10 §3.2 (Table 3.2).

    The design value of through-thickness strain demand ``Z_Ed`` is computed
    additively from the weld/joint conditions (Table 3.2):

        Z_Ed = Za + Zb + Zc + Zd + Ze

    where
        ``Za`` — effective weld throat / parent thickness ratio,
        ``Zb`` — shape and location of the welds (cruciform, T, corner, ...),
        ``Zc`` — effect of material thickness on restraint,
        ``Zd`` — effect of remote restraint,
        ``Ze`` — preheating effect (usually negative).

    Mapping to Z-quality of EN 10164 (Table 3.2 of EN 1993-1-10):

        Z_Ed <= 10  -> "Z15"
        10 < Z_Ed <= 20 -> "Z25"
        20 < Z_Ed       -> "Z35"

    Parameters
    ----------
    z_Ed : float
        Pre-computed Z_Ed value. If a ``conditions`` mapping is supplied with
        keys ``Za, Zb, Zc, Zd, Ze`` they are summed and added to ``z_Ed``.
    conditions : mapping, optional
        Optional contribution components (``Za``...``Ze``).

    Returns
    -------
    str
        ``"none"`` if no Z-quality is required, otherwise ``"Z15"``,
        ``"Z25"`` or ``"Z35"``.
    """
    Z = float(z_Ed)
    if conditions:
        for k in ("Za", "Zb", "Zc", "Zd", "Ze"):
            Z += float(conditions.get(k, 0.0))

    if Z <= 0.0:
        return "none"
    if Z <= 10.0:
        return "Z15"
    if Z <= 20.0:
        return "Z25"
    return "Z35"


__all__ = [
    "reference_temperature",
    "t_max_brittle_fracture",
    "Z_property_required",
]
