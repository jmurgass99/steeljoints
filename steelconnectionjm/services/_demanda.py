"""Estado estructurado de una demanda de momento: MISSING / ZERO / INVALID / POSITIVE.

Existe porque los servicios de conexiones precalificadas (RBS, WUF-W) y el bridge
con dynamicsjm hacian los tres la misma comparacion:

    if Mu > 0: DCR = Mu / M_cap
    else:      DCR = 0.0          # ausente, cero, negativo y NaN, todos iguales

y un momento de -2000 kN.m --1.86 veces la capacidad-- salia "OK". La distincion
entre "no me lo han dado", "me han dado un cero", "me han dado algo que no es un
numero" y "me han dado una demanda real" pertenece al CONTRATO DE EVIDENCIA y se
declara aqui, junto al calculo, no la adivina `resolve_status()` a partir del
valor numerico.

CONVENCION DE SIGNOS. Las conexiones a momento precalificadas de AISC 358 son
simetricas (la RBS recorta las dos alas; la WUF-W suelda las dos), asi que su
capacidad es la misma para momento positivo y negativo, y en cara de columna el
momento gravitatorio es negativo en la convencion habitual. Un momento con signo
es una demanda REAL: se toma su magnitud y se deja escrito que se descarto el
signo. NO se convierte en cero ni se rechaza.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from jmstructural_common.audit_status import CalculationStatus

MISSING = "MISSING"
ZERO = "ZERO"
INVALID = "INVALID"
POSITIVE = "POSITIVE"


@dataclass(frozen=True)
class DemandaMomento:
    """Resultado de clasificar un momento de demanda."""

    estado: str                 # MISSING | ZERO | INVALID | POSITIVE
    magnitud: float | None      # |M| finito > 0 solo en POSITIVE
    signo_descartado: bool      # True si el valor venia negativo
    motivo: str                 # texto para `missing_inputs` / notas ("" en POSITIVE)

    @property
    def presente(self) -> bool:
        """`demand_present` para `resolve_status`: se suministro un valor.

        INVALID cuenta como presente: la demanda existe pero no es finita, y ese
        camino tiene que acabar en REQUIERE_REVISION (regla 4 del contrato), no en
        NO_CALCULADO, para que el motivo sea "esto no es un numero" y no "falta".
        """
        return self.estado in (POSITIVE, INVALID)

    @property
    def es_evaluable(self) -> bool:
        return self.estado == POSITIVE


def clasificar_momento(valor: float | None, *, nombre: str) -> DemandaMomento:
    """Clasifica un momento de demanda sin convertir nada en cero.

    * ``None`` -> MISSING. Es el default de los inputs desde AC-03: antes era 0.0
      y un cliente generado desde el schema lo mandaba sin haberlo medido.
    * NaN / +-inf -> INVALID.
    * ``0.0`` -> ZERO. Una conexion a momento sin momento no es un estado
      verificable, y es indistinguible del antiguo default. Mismo criterio que
      `steelconnectionjm.welds` (`demand_present = Vu != 0 or Mu != 0`).
    * cualquier otro finito -> POSITIVE con su magnitud.
    """
    if valor is None:
        return DemandaMomento(MISSING, None, False,
                              f"{nombre} (momento de demanda) ausente")
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return DemandaMomento(INVALID, None, False,
                              f"{nombre} = {valor!r} no es un numero")
    if not math.isfinite(v):
        return DemandaMomento(INVALID, None, False,
                              f"{nombre} = {v!r} no es un momento finito")
    if v == 0.0:
        return DemandaMomento(
            ZERO, None, False,
            f"{nombre} = 0: una conexion a momento sin momento no es verificable "
            f"(y 0.0 era el antiguo default del schema, asi que no consta que se midiera)")
    return DemandaMomento(POSITIVE, abs(v), v < 0.0, "")


def nota_de_signo(dem: DemandaMomento, *, nombre: str) -> list[str]:
    """La decision de descartar el signo queda escrita en el resultado."""
    if not dem.signo_descartado:
        return []
    return [f"{nombre} negativo: signo descartado, la conexion es simetrica y se "
            f"evalua |M| = {dem.magnitud:.1f} kN.m"]


def estado_heredado(status: CalculationStatus) -> str:
    """Vocabulario heredado de los servicios ("OK" | "NG") mas el tercer valor.

    "UNKNOWN" es el mismo tercer valor que usa `classify_row` en fastsap: ni
    conforme ni incumple, porque no hay veredicto.
    """
    if status is CalculationStatus.CALCULADO_CUMPLE:
        return "OK"
    if status is CalculationStatus.CALCULADO_FALLA:
        return "NG"
    return "UNKNOWN"
