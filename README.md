# steeljoints

**Español** · [English](README.en.md)

Uniones de acero en Python: pernos, soldaduras, chapas, placas base y uniones sísmicas.

[![CI](https://github.com/jmurgass99/steeljoints/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/steeljoints/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green)](LICENSE)

## Qué hace

- Pernos y grupos de pernos (método elástico y centro instantáneo), efecto palanca y bloque de cortante en cuatro normas.
- Cordones de filete y a tope, y grupos de soldadura.
- Chapas a cortante, dobles angulares, chapas frontales (líneas de fluencia y T-stub de EN 1993-1-8), placas base y zona de panel.
- Uniones sísmicas RBS y WUF-W (AISC 358), anclajes, cables (EN 1993-1-11) y pandeo por flexotorsión.
- Exportación a IDEA StatiCa, CalculiX y DXF, y API REST opcional.

## Instalación

```bash
pip install git+https://github.com/jmurgass99/steeljoints.git
```

Extras opcionales: `api`, `dxf`, `numeric`. Dependencias base: `numpy` y `pydantic`.

## Ejemplo

Resistencia de diseño de un perno A325 de 3/4" (19,05 mm) con la rosca en el plano de corte, según NSR-10 F.2:

```python
from steeljoints.codes.nsr10_f2 import NSR10BoltInput, design_bolt_nsr10

r = design_bolt_nsr10(NSR10BoltInput("A325", 19.05, "N"))
print(round(r.Rd_shear_kN, 1), round(r.Rd_tension_kN, 1))   # 79.5 132.5
```

Más casos en [`examples/`](examples).

## Qué no hace

- Verificar una unión entera sin revisar: por ejemplo, la chapa a cortante no comprueba la flexión de la chapa ni la excentricidad de los pernos.
- Modelo de elementos finitos de componentes (IDEA StatiCa, CBFEM): aquí todo es cálculo a mano normativo.
- Importar en IDEA StatiCa: el XML IOM que genera no es el formato que acepta IDEA StatiCa 21.1.
- Las normas marcadas como no contrastadas (efecto arco de ACI 318-25, coeficientes de cables de EN 1993-1-11).

El detalle está en [docs/LIMITACIONES.md](docs/LIMITACIONES.md).

## Pruebas

```bash
pip install -e ".[test]"
pytest -q
```

## Licencia

MIT. Ver [LICENSE](LICENSE). Autor: [Jesús Murgas](https://github.com/jmurgass99).
