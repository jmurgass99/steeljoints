"""
codes/ — Funciones puras por código normativo.

Cada submódulo expone Rn (resistencia nominal) y/o φRn (Rd) según el código:
  - aisc360_j  — AISC 360-22 Chapter J (pernos, soldaduras, elementos afectados)
  - aisc358    — AISC 358-22 conexiones precalificadas sísmicas
  - ec3_1_8    — EN 1993-1-8:2005 (componentes, T-stubs)
  - nsr10_f2   — NSR-10 Título F.2 (Colombia, basada en AISC 360)
"""
from . import aisc360_j, aisc358, ec3_1_8, nsr10_f2

__all__ = ["aisc360_j", "aisc358", "ec3_1_8", "nsr10_f2"]
