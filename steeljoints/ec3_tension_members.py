"""EN 1993-1-11 — Design of structures with tension components (cables, strands, bars).

Implements simplified design helpers for:
- Tensile resistance of cables/strands (Table 3.1, Groups A/B/C).
- Partial factors gamma_M for tensile components (Table 6.2).
- Secondary bending stress at anchorage zones due to curvature.
- Fatigue detail category of strand-type tendons (EN 1993-1-9 Table 8.10).

The numerical values reproduce the published Eurocode tables for the cases
covered by the tests; they are not a substitute for an officially endorsed
implementation.
"""

from __future__ import annotations

from math import pi
from typing import Literal


# ---------------------------------------------------------------------------
# Tensile resistance — EN 1993-1-11 Table 3.1
# ---------------------------------------------------------------------------

def tendon_resistance_FRk(
    d_w: float,
    fuk: float,
    n_wires: int,
    group: int = 1,
) -> float:
    """Characteristic tensile resistance ``F_Rk`` of a tension component.

    EN 1993-1-11, Table 3.1, Groups A/B/C (here keyed by ``group`` = 1/2/3):

        Group A (1): single round bars and wires, hot-rolled.
            F_Rk = A_m * f_uk
        Group B (2): strands / spiral strands (cold-drawn wires).
            F_Rk = 0.92 * A_m * f_uk
        Group C (3): locked-coil ropes / parallel wire bundles.
            F_Rk = 0.85 * A_m * f_uk

    where ``A_m = n_wires * pi * d_w^2 / 4`` is the metallic cross-section
    of the strand (with ``d_w`` the nominal wire diameter).

    Parameters
    ----------
    d_w : float
        Nominal wire diameter (mm). For a 7-wire prestressing strand of
        nominal diameter 15.7 mm, ``d_w`` is the equivalent single-wire
        diameter (~ 5.2 mm) and ``n_wires = 7``; alternatively pass the full
        nominal diameter with ``n_wires = 1`` (treats the strand as a
        single round bar).
    fuk : float
        Characteristic tensile strength of the wire (MPa).
    n_wires : int
        Number of wires in the strand/cable.
    group : int, default 1
        Group classification per Table 3.1 (1=A, 2=B, 3=C).

    Returns
    -------
    float
        Characteristic tensile resistance ``F_Rk`` in newtons.
    """
    if d_w <= 0.0 or fuk <= 0.0:
        raise ValueError("d_w and fuk must be positive")
    if n_wires < 1:
        raise ValueError("n_wires must be >= 1")
    if group not in (1, 2, 3):
        raise ValueError("group must be 1 (A), 2 (B) or 3 (C)")

    A_m = n_wires * pi * d_w ** 2 / 4.0
    k = {1: 1.00, 2: 0.92, 3: 0.85}[group]
    return float(k * A_m * fuk)


# ---------------------------------------------------------------------------
# Partial factors — EN 1993-1-11 Table 6.2
# ---------------------------------------------------------------------------

# Tensile components — partial factors gamma_R (Table 6.2 of EN 1993-1-11).
# The table gives one factor per condition; the "safety class" is interpreted
# as the consequence class (CC1/CC2/CC3 in EN 1990, Annex B), which scales the
# value by K_FI = 0.9 / 1.0 / 1.1 respectively.
_GAMMA_BASE = {
    "transport":  1.00,  # transport, handling, erection
    "construction": 1.10,
    "service":    1.50,  # persistent / transient — ULS
    "fatigue":    1.35,
    "accidental": 1.00,
}

_K_FI = {1: 0.9, 2: 1.0, 3: 1.1, "CC1": 0.9, "CC2": 1.0, "CC3": 1.1}


def partial_factor_gM(
    safety_class: int | str = 2,
    condition: str = "service",
) -> float:
    """Partial factor ``gamma_M`` for tensile components, EN 1993-1-11 Table 6.2.

    Parameters
    ----------
    safety_class : int or str, default 2
        Consequence/reliability class: 1 (CC1), 2 (CC2) or 3 (CC3).
    condition : str, default ``"service"``
        Load condition. One of ``"transport"``, ``"construction"``,
        ``"service"``, ``"fatigue"``, ``"accidental"``.

    Returns
    -------
    float
        Partial factor ``gamma_M`` (= ``gamma_R`` of Table 6.2 times ``K_FI``).
    """
    cond = condition.lower()
    if cond not in _GAMMA_BASE:
        raise ValueError(f"unknown condition {condition!r}")
    if safety_class not in _K_FI:
        raise ValueError(f"unknown safety_class {safety_class!r}")
    return float(_GAMMA_BASE[cond] * _K_FI[safety_class])


# ---------------------------------------------------------------------------
# Secondary bending at anchorage — beam-on-elastic-axis approximation
# ---------------------------------------------------------------------------

def bending_stress_at_anchorage(
    F: float,
    d: float,
    L_free: float,
    E: float,
    I: float,
    theta_rad: float = 1.0,
) -> float:
    """Secondary bending stress at an anchorage due to angular misalignment.

    The result is proportional to the misalignment angle ``theta_rad``. With the
    default ``theta_rad = 1.0`` it is the stress PER RADIAN (until version 1.1
    that was the only output and the docstring did not say so): pass the real
    deviation, e.g. ``math.radians(0.5)``.

    The cable is modelled as an axially loaded beam-column with a unit
    transverse rotation imposed at the anchorage. The resulting bending
    moment at the anchorage is

        M = sqrt(F * E * I)                          [N.mm]

    (the "characteristic length" of the tensioned cable solution), and the
    extreme-fibre bending stress is

        sigma_b = M * (d/2) / I = (d/2) * sqrt(F * E / I)

    Parameters
    ----------
    F : float
        Axial tensile force in the cable (N).
    d : float
        Nominal outer diameter of the cable (mm).
    L_free : float
        Free length of the cable between anchorages (mm). Kept in the
        signature because it modulates the effective rotation at the
        anchorage; for ``L_free`` larger than the characteristic length
        ``sqrt(EI/F)`` (the usual case) the formula above is recovered.
    E : float
        Young's modulus of the cable (MPa).
    I : float
        Second moment of area of the cable cross-section (mm^4).

    theta_rad : float, default 1.0
        Angular deviation imposed at the anchorage (rad).

    Returns
    -------
    float
        Secondary bending stress at the anchorage (MPa) for ``theta_rad``.
    """
    if F <= 0.0 or d <= 0.0 or E <= 0.0 or I <= 0.0 or L_free <= 0.0:
        raise ValueError("F, d, L_free, E, I must be positive")
    if theta_rad < 0.0:
        raise ValueError("theta_rad must be non-negative")
    # Characteristic length of the cable solution.
    Lc = (E * I / F) ** 0.5
    # Effective rotation reduction when L_free >> Lc (full beam-column limit).
    eta = 1.0 if L_free >= Lc else L_free / Lc
    M = theta_rad * eta * (F * E * I) ** 0.5
    sigma_b = M * (d / 2.0) / I
    return float(sigma_b)


# ---------------------------------------------------------------------------
# Fatigue detail category — EN 1993-1-9 Table 8.10 (tendons of EN 1993-1-11)
# ---------------------------------------------------------------------------

def fatigue_class_strand(
    d: float,
    type: Literal["wire", "strand", "locked_coil", "bar"] = "strand",
) -> int:
    """Detail category (delta-sigma_C in MPa) for tendons, EN 1993-1-9 Table 8.10.

    Mapping (simplified, free length, away from anchorages):

        single wires (cold-drawn) ............... 160 MPa
        parallel strands / 7-wire strands ....... 150 MPa  (d <= 40 mm)
                                                  120 MPa  (d  > 40 mm)
        locked-coil ropes ....................... 120 MPa  (d <= 80 mm)
                                                   90 MPa  (d  > 80 mm)
        prestressing/threaded bars .............. 105 MPa

    Parameters
    ----------
    d : float
        Nominal diameter of the tendon (mm).
    type : str
        ``"wire"``, ``"strand"``, ``"locked_coil"`` or ``"bar"``.

    Returns
    -------
    int
        Detail category (delta-sigma_C) in MPa.
    """
    if d <= 0.0:
        raise ValueError("d must be positive")
    t = type.lower()
    if t == "wire":
        return 160
    if t == "strand":
        return 150 if d <= 40.0 else 120
    if t == "locked_coil":
        return 120 if d <= 80.0 else 90
    if t == "bar":
        return 105
    raise ValueError(f"unknown tendon type {type!r}")


__all__ = [
    "tendon_resistance_FRk",
    "partial_factor_gM",
    "bending_stress_at_anchorage",
    "fatigue_class_strand",
]
