# steeljoints

Diseño de uniones de acero multinorma: pernos y grupos de pernos (método del centro instantáneo de rotación), soldaduras en ángulo y a tope, grupos de soldadura (elástico e ICR), chapas de testa (end plate) con efecto palanca, chapas de cortante (shear tab), angulares, empalmes, placas base y anclajes (ACI 318-25 cap. 17), zona de panel, rotura por bloque de cortante, conexiones RBS y WUF-W (AISC 358), rotura frágil y miembros a tracción EC3, y exportación IOM a IDEA StatiCa. Normas: AISC 360-22, AISC 358, EN 1993-1-8, NSR-10 F.2.

[![CI](https://github.com/jmurgass99/steeljoints/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/steeljoints/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Paquete independiente. Única dependencia obligatoria: `numpy`.

## Instalación

```bash
pip install git+https://github.com/jmurgass99/steeljoints.git
```

Extras: `api` (REST), `dxf` (detalles con ezdxf), `numeric` (scipy), `memos` (memorias con handcalcs), `test`.

## Inicio rápido

```python
from steeljoints import Bolt, BoltGroup, FilletWeld, ShearTab, EndPlate, BasePlate, PanelZone
from steeljoints.block_shear_multi import BlockShearInput, block_shear

help(ShearTab)      # cada clase documenta sus parámetros y la norma aplicada
```

El script `examples/example_aisc_manual_part10.py` resuelve una conexión de cortante del Manual AISC (Parte 10) paso a paso y es el mejor punto de partida: pernos, chapa, soldadura y bloque de cortante con sus comprobaciones.

## Módulos

| Módulo | Contenido |
|---|---|
| `bolts`, `bolt_group`, `prying` | Pernos, grupos ICR, efecto palanca |
| `welds`, `groove_welds`, `weld_group` | Soldaduras y grupos |
| `shear_tab`, `clip_angle`, `end_plate`, `splice_design`, `haunch_connection` | Uniones viga-pilar y empalmes |
| `base_plate`, `aci318_25_anchors` | Placas base y anclajes |
| `panel_zone`, `wuf_w`, `services/rbs` | Zona de panel, WUF-W y RBS (AISC 358) |
| `block_shear`, `block_shear_multi`, `flexural_torsional` | Bloque de cortante multinorma, pandeo flexo-torsional |
| `codes/` (`ec3_1_8`, `nsr`, `aisc`) y `ec3_fracture`, `ec3_tension_members` | Cláusulas por norma |
| `catalog` | Catálogo de pernos y perfiles |
| `steelnode`, `steelnode_schemas`, `ideastatica_iom` | Modelo de nudo y exportación IOM a IDEA StatiCa |
| `dxf_detail`, `memos/`, `services/`, `api/` | Detalles DXF (extra `dxf`), memorias, servicios y REST |
| `integration/` | Puentes a seismodyn y fastsap (opcionales; sus tests se omiten si faltan) |

## Validación

Tests golden contra EN 1993-1-8 (T-stub, chapas de testa a partir de esfuerzos), interacción J3.7 de AISC, exportación IOM, NSR-10 F.2, y tests de propiedades con hypothesis. Los contratos de "ausencia no es cero" garantizan que una soldadura o un momento no informado no se aprueba en silencio.

## Licencia

MIT. Consulta [LICENSE](LICENSE).

---

Parte del toolkit estructural de código abierto **Loadpath**, de [Jesús Murgas](https://github.com/jmurgass99).
