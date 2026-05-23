# SteelConnectionJm — Diseño de Conexiones de Acero Multi-Código

[![CI](https://github.com/jmurgass99/steelconnectionjm/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/steelconnectionjm/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-62.11%25-yellow?style=flat)](https://github.com/jmurgass99/steelconnectionjm)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Proprietary-red)]()

## Objetivo
Librería Python para el diseño y verificación de conexiones de acero estructural según **AISC 360-22 (Chapter J)**, **EN 1993-1-8:2005 (Eurocódigo 3)** y **NSR-10 (Título F.2)**. Cubre conexiones atornilladas, soldadas, placas de base y conexiones viga-columna momento-resistentes.

Este proyecto **completa el ciclo de diseño en acero** de FastSAP, que actualmente tiene `design_aisc_adapter.py` para chequeo de miembros pero NO diseña las uniones entre ellos.

---

## ¿Qué va a hacer?

### 1. Conexiones Atornilladas
- Resistencia por perno: cortante (shear), aplastamiento (bearing), tracción (tension), interacción cortante-tracción
- Conexiones tipo fricción (slip-critical) y tipo aplastamiento (bearing-type)
- Pernos de alta resistencia: A325/A490 (AISC) o 8.8/10.9 (EC3)
- Grupos de pernos: método de centro instantáneo de rotación (ICR)

### 2. Conexiones Soldadas
- Soldadura de filete: resistencia direccional (longitudinal, transversal, oblicua)
- Soldadura de penetración completa (CJP) y parcial (PJP)
- Grupos de soldadura: método elástico y método de rotura

### 3. Shear Connections (Simple)
- Shear tab (single plate)
- Clip angle (double angle)
- Verificación de bloque de cortante (block shear)
- Diseño de placa gusset

### 4. Moment Connections
- Extended end-plate (4 y 8 pernos)
- Flush end-plate
- Verificaciones de panel zone
- Pre-calificadas AISC 358 para conexiones sísmicas

### 5. Placas de Base (Base Plates)
- Diseño por flexión bajo carga axial (concéntrica y excéntrica)
- Diseño de pernos de anclaje (tension + shear)
- Presión sobre concreto (bearing on concrete): A1/A2 ratio
- Placa de corte (shear lug) para cortante elevado

### 6. Exportación
- Plano de detalle de la conexión en DXF (usando `ezdxf`)
- Tabla de pernos/soldaduras para memoria de cálculo

---

## Estructura de Módulos Planificada

```
steelconnectionjm/
├── __init__.py
├── bolts.py                # Resistencia por bolt: Rn shear, bearing, tension, slip
├── bolt_group.py           # ICR method, grupo de pernos excéntrico
├── welds.py                # Filete (Rn directional), CJP, PJP
├── weld_group.py           # Grupo de soldaduras: elástico y rotura
├── block_shear.py          # Verificación de block shear (Ubs, Ant, Anv)
├── shear_tab.py            # Single-plate shear connection design
├── clip_angle.py           # Double-angle shear connection
├── end_plate.py            # Extended/flush end plate moment connections
├── base_plate.py           # Base plate + anchor bolts + shear lug
├── panel_zone.py           # Panel zone shear (doubler plates)
├── codes/
│   ├── __init__.py
│   ├── aisc360_j.py        # AISC 360-22 Chapter J (bolts, welds, affected elements)
│   ├── aisc358.py          # AISC 358 pre-qualified seismic connections
│   ├── ec3_1_8.py          # EN 1993-1-8:2005 (categories A-E, T-stubs, component method)
│   └── nsr10_f2.py         # NSR-10 Título F.2
├── dxf_detail.py           # Genera plano de detalle con ezdxf
├── catalog.py              # Catálogo de pernos A325/A490/8.8/10.9, electrodos E70XX
└── tests/
    ├── test_bolts.py
    ├── test_welds.py
    ├── test_shear_tab.py
    ├── test_end_plate.py
    └── test_base_plate.py
```

---

## Fuentes de Información

### Normas y Códigos
| Código | Secciones | Contenido |
|--------|-----------|-----------|
| **AISC 360-22** | Chapter J (J1-J10) | Diseño de conexiones: pernos, soldaduras, elementos afectados |
| **AISC 358-22** | Sections 6-8 | Conexiones precalificadas para sismo (end plates, RBS, BFP) |
| **AISC Design Guide 1** | Completo | Base plates and anchor rod design |
| **AISC Steel Construction Manual** | Tables 7, 8, 10 | Capacidades tabuladas de pernos y soldaduras |
| **EN 1993-1-8:2005** | §3 (bolts), §4 (welds), §6 (joints) | Método de componentes EC3 |
| **NSR-10 Título F.2** | §F.2.10 (conexiones) | Norma colombiana de conexiones |

### Repositorios de Referencia (ya descargados)
- `steel-as-main` — Diseño de miembros de acero (complemento directo)
- `steel_beam_designer-main` — Diseño de vigas de acero
- `SteelColumn-master` — Verificación de columnas de acero
- `Structural-Engineering-master` — Ejemplos generales de conexiones

### Integración con FastSAP
- `fastsap/design_aisc_adapter.py` — Adaptador AISC existente (chequeo de miembros)
- `fastsap/section_catalog.py` — Catálogo de perfiles W, HSS, L, C
- `fastsap/extractor.py` — Extrae fuerzas en extremos de miembros para diseño de conexiones
- `fastsap/codes/ec3_buckling.py` — Módulo EC3 existente

---

## Criterio de Éxito
- [ ] Diseñar una shear tab connection completa (pernos + placa + block shear)
- [ ] Diseñar una extended end-plate moment connection (8-bolt stiffened)
- [ ] Diseñar una base plate bajo carga axial + momento
- [ ] Validar contra AISC Design Examples (Manual Part 10)
- [ ] Generar plano DXF de la conexión con cotas y tabla de materiales
- [ ] Suite de tests con ≥30 casos

## Ecosystem

This project is part of the **jmurgass99 structural engineering ecosystem**:

- [fastsap](https://github.com/jmurgass99/fastsap) - orquestador SAP2000/ETABS
- [dynamicsjmpro](https://github.com/jmurgass99/dynamicsjmpro) - SaaS frontend + backend
- [dynamicsjm](https://github.com/jmurgass99/dynamicsjm) - motor dinamico
- [foundationdesignjm](https://github.com/jmurgass99/foundationdesignjm) - cimentaciones
- [windloadjm](https://github.com/jmurgass99/windloadjm) - cargas de viento
- [seismicrecordsjm](https://github.com/jmurgass99/seismicrecordsjm) - records sismicos
- [slopestabilityjm](https://github.com/jmurgass99/slopestabilityjm) - estabilidad de taludes
- [steelconnectionjm](https://github.com/jmurgass99/steelconnectionjm) - conexiones de acero
- [steeloptimizerjm](https://github.com/jmurgass99/steeloptimizerjm) - optimizacion GA
- [coldformedjm](https://github.com/jmurgass99/coldformedjm) - acero conformado en frio
- [fatiguejm](https://github.com/jmurgass99/fatiguejm) - analisis de fatiga
- [firesteeljm](https://github.com/jmurgass99/firesteeljm) - analisis termico al fuego
- [dxfstructuraljm](https://github.com/jmurgass99/dxfstructuraljm) - generacion DXF
