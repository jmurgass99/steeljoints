# Diseño de objetos de ingeniería

> Inspirado en [Flocode Python Intermediate, módulo 05 (OOP)](https://github.com/flocode/flocode-python-intermediate) — MIT.

## Composición sobre herencia

En ingeniería estructural muchos objetos son combinaciones, no especializaciones:

- Una **viga** _tiene_ un material, _tiene_ una sección, _tiene_ apoyos.
  No _es_ un material ni _es_ una sección.
- Un **muro** _tiene_ una geometría, _tiene_ refuerzo, _tiene_ cargas.
  No _es_ una geometría.

Esto se modela con **composición** (atributos), no con herencia.

### Mal (herencia profunda)
```python
class StructuralElement: ...
class Beam(StructuralElement): ...
class RCBeam(Beam): ...
class PrestressedRCBeam(RCBeam): ...
class PostTensionedPRCBeam(PrestressedRCBeam): ...  # ← jerarquía rígida
```
Problemas: cambiar `StructuralElement` rompe todo. Difícil reusar comportamiento entre ramas.

### Bien (composición)
```python
@dataclass(frozen=True)
class Material: ...

@dataclass(frozen=True)
class Section: ...

@dataclass(frozen=True)
class Beam:
    material: Material
    section: Section
    length: float
    supports: tuple[SupportType, ...]
    prestress: Prestress | None = None
```
Ventajas: cada componente evoluciona independientemente, fácil de testear,
serializable, hashable.

## Cuándo SÍ usar herencia

Sólo cuando hay una **relación "es-un" real y estable**:

- `class ConvergenceError(SolverError, NumericalError): ...` — taxonomía de errores
- `class ETABSv22Client(EtabsClient): ...` — variantes de versión de un cliente

NO uses herencia para:
- "Quiero reusar este método" → usa una función helper o mixin
- "Estos objetos comparten campos" → usa composición o un dataclass común incluido

## Identidad vs valor

- **Value objects** (`@dataclass(frozen=True)`): Material, Section, Load — comparables por valor, hashables, inmutables.
- **Entities**: SapClient, DXFDocument — tienen identidad propia, mutables, manejan recursos.

Usa `frozen=True` por defecto. Sólo mutable cuando hay buena razón (e.g. lista de barras editable desde GUI).

## Encapsulamiento práctico

- Atributos privados (`_internal_state`) sólo cuando hay invariantes que mantener.
- En Python no hay `private` real — usa el guion bajo como convención.
- Properties sólo cuando el cálculo es derivado (`@property def area(self): ...`) o
  cuando hay validación al setear.

## Patrones aplicados en este satélite

TODO: documentar 2-3 ejemplos concretos del propio satélite donde se aplica
composición correctamente, linkeando a los archivos.
