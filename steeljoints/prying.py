# -*- coding: utf-8 -*-
"""Accion de palanca (prying action) en conexiones traccionadas — AISC Manual Part 9.

El efecto palanca amplifica la traccion en los pernos de conexiones tipo T-stub
(end-plates, angulos, tes) cuando el ala/placa es flexible. Omitirlo sobreestima
la capacidad hasta ~30%. Metodo del AISC Steel Construction Manual, Parte 9
(15a ed.); equivalente al T-stub de EN 1993-1-8 §6.2.4.

Geometria (por perno, ancho tributario p):
    b  = distancia del perno a la cara del alma/te
    a  = distancia del perno al borde (<= 1.25·b en el calculo)
    t  = espesor del ala/placa que flexiona
    d  = diametro del perno;  d_hole = diametro del agujero
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .exceptions import GeometryError

_PHI_B = 0.90  # factor de resistencia a flexion de la placa (LRFD)


@dataclass(frozen=True)
class PryingInput:
    B_kN: float          # resistencia de diseno a traccion de UN perno (phi·Rn)
    b_mm: float
    a_mm: float
    p_mm: float          # ancho tributario por perno
    t_mm: float          # espesor del ala/placa
    d_mm: float          # diametro del perno
    Fy_MPa: float
    d_hole_mm: float | None = None  # por defecto d + 2 mm


@dataclass(frozen=True)
class PryingResult:
    t_c_mm: float            # espesor sin palanca (Q=0, perno plenamente cargado)
    alpha_prime: float       # parametro alfa' (0..1)
    delta: float             # 1 - d_hole/p
    rho: float               # b'/a'
    T_avail_kN: float        # traccion disponible por perno INCLUYENDO palanca
    prying_governs: bool     # True si t < t_c (hay efecto palanca)


def prying_capacity(inp: PryingInput) -> PryingResult:
    """Traccion disponible por perno considerando la accion de palanca (AISC Part 9)."""
    if min(inp.B_kN, inp.b_mm, inp.a_mm, inp.p_mm, inp.t_mm, inp.d_mm, inp.Fy_MPa) <= 0:
        raise GeometryError("todos los parametros deben ser > 0")
    d_hole = inp.d_hole_mm if inp.d_hole_mm is not None else inp.d_mm + 2.0

    b_prime = inp.b_mm - inp.d_mm / 2.0
    a_eff = min(inp.a_mm, 1.25 * inp.b_mm)
    a_prime = a_eff + inp.d_mm / 2.0
    rho = b_prime / a_prime
    delta = 1.0 - d_hole / inp.p_mm

    B_N = inp.B_kN * 1.0e3
    # Espesor para el cual no hay palanca (el perno alcanza B con la placa al limite).
    t_c = math.sqrt(4.0 * B_N * b_prime / (_PHI_B * inp.p_mm * inp.Fy_MPa))

    # alpha' (AISC Eq. 9-...), acotado a [0, 1].
    if delta <= 0:
        alpha = 0.0
    else:
        alpha = ((t_c / inp.t_mm) ** 2 - 1.0) / (delta * (1.0 + rho))
        alpha = max(0.0, min(1.0, alpha))

    # Traccion disponible por perno con palanca, sin superar B.
    T_avail = inp.B_kN * (inp.t_mm / t_c) ** 2 * (1.0 + delta * alpha)
    T_avail = min(T_avail, inp.B_kN)

    return PryingResult(
        t_c_mm=t_c, alpha_prime=alpha, delta=delta, rho=rho,
        T_avail_kN=T_avail, prying_governs=inp.t_mm < t_c,
    )


__all__ = ["PryingInput", "PryingResult", "prying_capacity"]
