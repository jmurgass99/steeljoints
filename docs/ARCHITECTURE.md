# Arquitectura — patrón de módulo de cálculo

> Inspirado en [Flocode Python Intermediate, módulo 02 (Modularization)](https://github.com/flocode/flocode-python-intermediate) — MIT.

Este satélite sigue el patrón **service layer + dataclasses + tests headless**
para todos sus módulos de cálculo.

## Estructura objetivo de un módulo

```
steelconnectionjm/services/<topic>.py    # Funciones puras tipadas
  ├── @dataclass(frozen=True) <Topic>Input         # entradas con type hints
  ├── @dataclass(frozen=True) <Topic>Result        # salidas serializables
  └── def design_<topic>(inp: <Topic>Input) -> <Topic>Result:
          """Docstring con norma + ejemplo."""
          ...
tests/test_<topic>.py
  ├── tests unitarios (cada función pública: 2-3 tests)
  ├── @pytest.mark.safety_critical contra bibliografía
  └── @pytest.mark.property con hypothesis si hay invariantes
```

## Principios de diseño

### 1. Funciones puras
- Sin estado global.
- Sin side effects (no print, no I/O, solo `log.debug`).
- Determinista: misma entrada → misma salida.

### 2. Dataclasses frozen para Input/Result
- Inmutables → hashables → safe para multiprocessing y cache.
- Type hints estrictos en cada campo.
- Defaults sensatos cuando aplica.

### 3. Composición sobre herencia
- Una `BeamSection` _tiene_ un `Material`, no _es_ un `Material`.
- Cada satélite expone clases concretas, no jerarquías abstractas.

### 4. Validation-first
- Validar inputs ANTES de calcular.
- Errores con custom exceptions (`GeometryError`, `CodeError`, etc.).
- Mensajes con contexto: qué falló, qué valor, qué rango aceptable.

### 5. Service layer
- `services/` separa la lógica de negocio de la presentación (GUI/REST/CLI).
- Reusable desde FastAPI, Tk desktop, Streamlit, CLI, AI Copilot.

## Ejemplo mínimo

```python
# steelconnectionjm/services/example.py
from dataclasses import dataclass
from ..exceptions import GeometryError


@dataclass(frozen=True)
class BeamInput:
    L_mm: float
    b_mm: float
    h_mm: float
    fy_MPa: float = 345.0


@dataclass(frozen=True)
class BeamResult:
    Mn_kNm: float
    DCR: float


def design_beam_simple(inp: BeamInput, Mu_kNm: float) -> BeamResult:
    """Diseño simplificado en flexión (AISC §F2 placeholder)."""
    if inp.b_mm <= 0 or inp.h_mm <= 0:
        raise GeometryError(f"Dimensiones inválidas: b={inp.b_mm}, h={inp.h_mm}")
    Z = (inp.b_mm * inp.h_mm ** 2) / 4
    Mn = 0.9 * inp.fy_MPa * Z / 1e6   # kN·m
    DCR = Mu_kNm / Mn if Mn > 0 else 99
    return BeamResult(Mn_kNm=Mn, DCR=DCR)
```

```python
# tests/test_example.py
from steelconnectionjm.services.example import BeamInput, design_beam_simple

def test_designed_capacity_positive():
    res = design_beam_simple(BeamInput(L_mm=4000, b_mm=300, h_mm=500), Mu_kNm=50)
    assert res.Mn_kNm > 0 and res.DCR > 0
```

## Convenciones del repo

- type hints estrictos (`from __future__ import annotations`)
- docstrings PEP-257 castellano con `Args/Returns/Raises`
- `logging.getLogger("steelconnectionjm.<module>")`, jamás `print`
- pytest markers: `unit`, `integration`, `slow`, `safety_critical`, `property`
- Coverage gate definido en `pyproject.toml`
