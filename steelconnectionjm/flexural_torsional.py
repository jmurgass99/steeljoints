"""Suite 9.1 — Pandeo torsional y flexotorsional de columnas (AISC 360-16 §E4).

Tensiones de pandeo elástico:

    Fex = π²E / (Lcx/rx)²            (flexión respecto a x)
    Fey = π²E / (Lcy/ry)²            (flexión respecto a y)
    Fez = [π²E·Cw/Lcz² + G·J] / (A·ro²)   (torsión)

con el radio polar de giro respecto al centro de cortante

    ro² = xo² + yo² + (Ix + Iy)/A ,   H = 1 − (xo² + yo²)/ro²

Para una sección **asimétrica** la tensión de pandeo flexotorsional Fe es la
menor raíz positiva de la ecuación cúbica (AISC E4-6):

    (Fe−Fex)(Fe−Fey)(Fe−Fez)
        − Fe²·(Fe−Fey)·(xo/ro)²
        − Fe²·(Fe−Fex)·(yo/ro)² = 0

que para xo=yo=0 (doblemente simétrica) factoriza en las tres tensiones
puras, y para un único eje de simetría se reduce a la fórmula cerrada E4-5.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BucklingInput:
    A: float        # área (mm²)
    Ix: float       # inercia respecto a x (mm⁴)
    Iy: float       # inercia respecto a y (mm⁴)
    J: float        # constante de torsión de St. Venant (mm⁴)
    Cw: float       # constante de alabeo (mm⁶)
    xo: float       # excentricidad del centro de cortante en x (mm)
    yo: float       # excentricidad del centro de cortante en y (mm)
    E: float        # módulo elástico (MPa)
    G: float        # módulo de cortante (MPa)
    Lcx: float      # longitud efectiva flexión x (mm)
    Lcy: float      # longitud efectiva flexión y (mm)
    Lcz: float      # longitud efectiva torsión (mm)

    @property
    def rx(self) -> float:
        return math.sqrt(self.Ix / self.A)

    @property
    def ry(self) -> float:
        return math.sqrt(self.Iy / self.A)

    @property
    def ro2(self) -> float:
        return self.xo ** 2 + self.yo ** 2 + (self.Ix + self.Iy) / self.A

    @property
    def H(self) -> float:
        return 1.0 - (self.xo ** 2 + self.yo ** 2) / self.ro2

    @property
    def Fex(self) -> float:
        return math.pi ** 2 * self.E / (self.Lcx / self.rx) ** 2

    @property
    def Fey(self) -> float:
        return math.pi ** 2 * self.E / (self.Lcy / self.ry) ** 2

    @property
    def Fez(self) -> float:
        return (math.pi ** 2 * self.E * self.Cw / self.Lcz ** 2 + self.G * self.J) / (
            self.A * self.ro2
        )


def elastic_buckling_stress(inp: BucklingInput) -> float:
    """Menor raíz positiva de la cúbica E4-6 → tensión de pandeo elástico Fe."""
    Fex, Fey, Fez = inp.Fex, inp.Fey, inp.Fez
    a = (inp.xo ** 2) / inp.ro2
    b = (inp.yo ** 2) / inp.ro2
    # Coeficientes en potencias descendentes de Fe.
    c3 = 1.0 - a - b
    c2 = -(Fex + Fey + Fez) + a * Fey + b * Fex
    c1 = Fex * Fey + Fex * Fez + Fey * Fez
    c0 = -Fex * Fey * Fez
    roots = np.roots([c3, c2, c1, c0])
    real = [r.real for r in roots if abs(r.imag) < 1e-6 and r.real > 0]
    if not real:
        raise ValueError("sin raíz real positiva en la cúbica de pandeo")
    return min(real)


def flexural_torsional_closed_form(inp: BucklingInput) -> float:
    """Fórmula cerrada E4-5 para secciones con un eje de simetría.

    Acopla la flexión en el plano de simetría con la torsión; el modo de
    flexión perpendicular queda desacoplado.
    """
    if inp.xo != 0.0 and inp.yo != 0.0:
        raise ValueError("la fórmula cerrada sólo aplica con un eje de simetría")
    Fex, Fey, Fez, H = inp.Fex, inp.Fey, inp.Fez, inp.H
    if inp.yo == 0.0:          # simetría respecto a x (yo=0) → acopla Fex y Fez
        Fa, Fb, Func = Fex, Fez, Fey
    else:                      # simetría respecto a y (xo=0) → acopla Fey y Fez
        Fa, Fb, Func = Fey, Fez, Fex
    coupled = (Fa + Fb) / (2 * H) * (
        1.0 - math.sqrt(1.0 - 4.0 * Fa * Fb * H / (Fa + Fb) ** 2)
    )
    return min(Func, coupled)


def critical_load(inp: BucklingInput) -> float:
    """Carga crítica elástica Pcr = Fe·A (N)."""
    return elastic_buckling_stress(inp) * inp.A
