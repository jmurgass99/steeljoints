"""Esquemas Pydantic v2 - SteelNodeFEAJm (backlog #8).

Describe una placa de conexion rectangular discretizada en una malla estructurada
de nx x ny celdas (elementos shell S4). Unidades coherentes (recomendado SI: m, Pa, N
o bien mm, MPa, N); el deck no impone unidades, solo reproduce los valores.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PlateDeckIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    length: float = Field(..., gt=0.0, description="Largo de la placa (direccion X)")
    width: float = Field(..., gt=0.0, description="Ancho de la placa (direccion Y)")
    thickness: float = Field(..., gt=0.0, description="Espesor de la placa (shell S4)")

    nx: int = Field(..., ge=1, description="Divisiones de malla en X (>=1)")
    ny: int = Field(..., ge=1, description="Divisiones de malla en Y (>=1)")

    E: float = Field(..., gt=0.0, description="Modulo de Young (unidades de presion)")
    nu: float = Field(..., gt=0.0, lt=0.5, description="Coeficiente de Poisson (0 < nu < 0.5)")

    load: float = Field(
        ...,
        description="Carga puntual total aplicada en el borde libre (direccion -Y, *CLOAD)",
    )


class InpDeckOut(BaseModel):
    inp: str           # deck CalculiX (.inp) completo, como texto
    n_nodes: int       # (nx+1)*(ny+1)
    n_elements: int    # nx*ny


__all__ = ["PlateDeckIn", "InpDeckOut"]
