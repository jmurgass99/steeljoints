"""Jerarquía de excepciones tipadas de SteelJoints.

Permite al caller (REST API, bridge FastSAP) distinguir
entre:
    - Geometría inválida (GeometryError)
    - Norma fuera de aplicabilidad (CodeError)
    - Iteración numérica que no converge (ConvergenceError)
    - Falta de dependencia opcional (DependencyError)
    - Configuración del cálculo (ConfigurationError)

Las clases custom multi-heredan de `ValueError` para preservar backward
compat con código que usa `except ValueError`.
"""
from __future__ import annotations


class ConnectionError(Exception):
    """Base de todas las excepciones del paquete."""


class GeometryError(ConnectionError, ValueError):
    """Geometría inválida del conector o de la pieza.

    Ejemplos:
        - Espesor de placa <= 0
        - Diámetro de perno fuera de tabla
        - Edge distance < requerido por AISC §J3.4
    """


class CodeError(ConnectionError, ValueError):
    """Caso fuera del rango de aplicabilidad de la norma seleccionada.

    Ejemplos:
        - AISC 358 RBS con sección no prequalified
        - EC3 §3.6 con perno no en tabla
        - NSR-10 F.2 con grado no soportado
    """


class DesignError(ConnectionError, ValueError):
    """Falla en el diseño estructural (DCR > 1 sin solución, etc.)."""


class ConvergenceError(ConnectionError):
    """El solver iterativo (ICR de bolt_group / weld_group) no convergió.

    Atributos:
        iteration: último número de iteración alcanzado.
        residual: residuo numérico al fallar.
    """

    def __init__(self, message: str, *, iteration: int = -1,
                 residual: float = float("nan")) -> None:
        super().__init__(message)
        self.iteration = iteration
        self.residual = residual


class DependencyError(ConnectionError, ImportError):
    """Falta un paquete opcional (ezdxf para DXF, fastapi para REST)."""


class ConfigurationError(ConnectionError, ValueError):
    """Parámetro de configuración inválido o incompatible.

    Ejemplos:
        - Standard != AISC/EC3/NSR
        - Thread condition != N/X
    """


__all__ = [
    "ConnectionError",
    "GeometryError",
    "CodeError",
    "DesignError",
    "ConvergenceError",
    "DependencyError",
    "ConfigurationError",
]
