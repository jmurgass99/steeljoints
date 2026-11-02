# steeljoints — uniones de acero en Python: pernos, soldaduras, chapas, placas base y uniones sísmicas

**Español** · [English](README.en.md) · [Português](README.pt.md) · [Italiano](README.it.md)

Pernos y grupos de pernos por el método elástico y por centro instantáneo, efecto palanca, cordones de filete y a tope, grupos de soldadura elásticos y por centro instantáneo, chapas a cortante, dobles angulares, bloque de cortante en cuatro normas, chapas frontales por líneas de fluencia y por T-stub de EN 1993-1-8, placas base, zona de panel con chapa de refuerzo, RBS y WUF-W de AISC 358, anclajes, fractura frágil, cables de EN 1993-1-11, pandeo por flexotorsión, exportación a IDEA StatiCa, CalculiX y DXF, y una API REST. Dependencias: `numpy` y `pydantic`.

[![CI](https://github.com/jmurgass99/steeljoints/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/steeljoints/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Qué problema resuelve

Una unión de acero se comprueba con una cadena de estados límite: el perno a cortante, la chapa a aplastamiento, el bloque de cortante, la palanca, la soldadura, la zona de panel. Las hojas de cálculo que los encadenan suelen equivocarse en los mismos sitios: la rosca descontada dos veces, el área bruta donde va la resistente, la distancia al borde ignorada, la tensión de una soldadura evaluada en el centro del cordón, la zona de panel sin reducción por axil. `steeljoints` calcula cada estado límite con la fórmula de la norma a la vista, publica la utilización de cada uno y el que gobierna, y cuando falta un dato devuelve NO_CALCULADO en lugar de un cero que se lee como holgura.

**Úsalo cuando**

- quieras la resistencia de un perno o tornillo en AISC 360-22 o EN 1993-1-8 (cortante con rosca incluida o excluida, tracción, aplastamiento con el agujero real, interacción) o la capacidad de un grupo excéntrico por centro instantáneo;
- dimensiones un cordón de filete o a tope, o un grupo de soldaduras en C o en L con carga excéntrica;
- compruebes una chapa a cortante, un doble angular, una chapa frontal extendida, una placa base con compresión centrada o una zona de panel con chapa de refuerzo;
- prediseñes uniones precalificadas RBS y WUF-W de AISC 358 y quieras confrontarlas con los momentos de un pushover;
- necesites el T-stub de EN 1993-1-8 con sus tres modos, el bloque de cortante en AISC, EN 1993-1-8, AS 4100 y NSR-10, o el espesor máximo frente a rotura frágil;
- quieras mover esfuerzos a IDEA StatiCa en CSV o JSON, sacar un mazo de CalculiX o planos DXF de detalle, o servir los cálculos por HTTP.

**No lo uses para**

- verificar una unión entera sin revisar: la chapa a cortante no comprueba la flexión de la chapa ni la excentricidad de los pernos, la memoria de chapa frontal de EN 1993-1-8 es una cota superior sin los componentes del pilar, y la placa base no incluye el momento en el aplastamiento ni en el espesor;
- uniones con modelo de elementos finitos de componentes (IDEA StatiCa, CBFEM): aquí todo es cálculo a mano normativo;
- importar un modelo en IDEA StatiCa: el XML IOM del paquete no es el formato que acepta IDEA StatiCa 21.1;
- normas que el paquete marca como no contrastadas: el multiplicador por efecto arco de ACI 318-25, los coeficientes de cables de EN 1993-1-11 y el sustituto continuo de la Tabla 2.1 de EN 1993-1-10.

## Instalación

```bash
pip install git+https://github.com/jmurgass99/steeljoints.git
```

Extras: `numeric` (scipy, para el centro instantáneo con carga oblicua o excéntrica; sin él se lanza `DependencyError` con la instrucción), `api` (FastAPI, uvicorn, httpx), `dxf` (ezdxf), `memos` (handcalcs; sin él las memorias salen con texto plano), `test`. Para desarrollo: `git clone`, `pip install -e ".[test,api,memos,dxf,numeric]"`, `pytest -q` (42 ficheros de tests; `tests/test_examples.py` ejecuta los 33 casos de uso como subprocesos). En Windows, si la consola no es UTF-8, ejecuta los ejemplos con `python -X utf8 examples/<nombre>.py`. Los ejemplos escriben sus ficheros (XML, CSV, `.inp`, DXF) en `examples/out/`, que no se versiona, y su salida de consola en `examples/output/`.

## Capacidades

| Capacidad | Módulos | Norma o referencia | Casos de uso |
|---|---|---|---|
| Pernos y grupos de pernos: cortante con rosca N y X, tracción, aplastamiento con lc, interacción J3.7; tornillos EC3 con As y d0, interacción de la Tabla 3.4; grupo excéntrico elástico y por centro instantáneo con carga oblicua; efecto palanca con Fy o Fu; catálogo de tamaños, agujeros y electrodos | `bolts`, `bolt_group`, `prying`, `catalog` | AISC 360-22 §J3; EN 1993-1-8 Tabla 3.4; EN 1090-2 Tabla 11; AISC Manual Partes 7 y 9 | [6 casos](#1-pernos-y-grupos-de-pernos) |
| Soldaduras: filete con aumento direccional (AISC) y métodos direccional y simplificado (EC3); grupos de soldadura elásticos y por centro instantáneo de Lesik y Kennedy con compatibilidad; a tope CJP y PJP; tamaños mínimo y máximo | `welds`, `weld_group`, `groove_welds`, `codes.ec3_1_8` | AISC 360-22 §J2; EN 1993-1-8 §4.5.3; AISC Manual Parte 8 | [5 casos](#2-soldaduras) |
| Uniones a cortante y bloque de cortante: chapa simple, doble angular con viga despatinada, bloque de cortante en cuatro normas, NSR-10 F.2, capa de servicios para la API | `shear_tab`, `clip_angle`, `block_shear`, `block_shear_multi`, `codes.nsr10_f2`, `services` | AISC 360-22 §J4; EN 1993-1-8 §3.10.2; AS 4100 §9.1.9; NSR-10 Título F.2 | [5 casos](#3-uniones-a-cortante-y-bloque-de-cortante) |
| Uniones a momento y sísmicas: chapa frontal 4E por líneas de fluencia y memoria EN 1993-1-8 por T-stub; RBS y WUF-W con Mpr, cortante en la rótula y pilar fuerte–viga débil con axil; zona de panel en los cuatro casos de §J10.6 con chapa de refuerzo; puente con los momentos de seismodyn; cartela | `end_plate`, `memos`, `codes.aisc358`, `services.rbs`, `services.wuf`, `wuf_w`, `panel_zone`, `integration.seismodyn_bridge`, `haunch_connection` | AISC 358 caps. 5, 6 y 8; AISC 341 §E3; AISC 360-22 §J10.6; EN 1993-1-8 §6.2.7.2 | [6 casos](#4-uniones-a-momento-y-sísmicas) |
| Placas base, T-stub y anclajes: placa base con compresión (aplastamiento con confinamiento, m, n, λn′) y con momento; T-stub con sus tres modos, deslizamiento y punzonamiento; interacción de anclajes y cortante con efecto de tamaño de ACI 318 | `base_plate`, `codes.ec3_1_8`, `aci318_25_anchors` | AISC Design Guide 1; EN 1993-1-8 §6.2.4, §3.9; ACI 318-19 y 318-25 caps. 17 y 22 | [5 casos](#5-placas-base-t-stub-y-anclajes) |
| Materiales, estabilidad e integraciones: rotura frágil y clase Z; cables y cordones; pandeo por flexotorsión E4; IOM y esfuerzos para IDEA StatiCa, carga útil para RFEM 6; mazo de CalculiX y planos DXF; API REST | `ec3_fracture`, `ec3_tension_members`, `flexural_torsional`, `ideastatica_iom`, `integration.idea_statica_export`, `steelnode`, `dxf_detail`, `api` | EN 1993-1-10; EN 1993-1-11; AISC 360-22 §E4 | [6 casos](#6-materiales-estabilidad-e-integraciones) |

Cada caso de uso es un script de `examples/` que se ejecuta tal cual. La salida que sigue es la que produce, copiada sin editar de `examples/output/`.

## Casos de uso

### 1. Pernos y grupos de pernos

#### Perno A325 y A490 de AISC con rosca incluida y excluida: cortante, tracción, aplastamiento e interacción J3.7 comprobados a mano

<details><summary>Salida real de <code>python examples/bolt_aisc_single_a325_a490_threads_n_x_shear_tension_bearing_and_j3_7_interaction_hand_check.py</code></summary>

```text
φRn por perno [kN], AISC 360-22 Tabla J3.2, φ = 0,75:
  perno      Ab [mm²] corte -N corte -X doble -N tracción
  A325 5/8"     197.9     55.3     69.6    110.5     92.1
  A490 5/8"     197.9     69.6     86.0    139.2    115.6
  A325 3/4"     285.0     79.6    100.2    159.2    132.6
  A490 3/4"     285.0    100.2    123.8    200.4    166.5
  A325 7/8"     387.9    108.3    136.4    216.6    180.5
  A490 7/8"     387.9    136.4    168.5    272.8    226.7
  A325 1"       506.7    141.5    178.2    283.0    235.8
  A490 1"       506.7    178.2    220.1    356.3    296.1

A mano, A325-N de 3/4": Ab = 285.0 mm²; φRn = 0,75·54 ksi·Ab = 0,75·372.3·285.0 = 79.58 kN (función 79.58)
  En unidades US: 0,75·54·0,442 in² = 17.89 kip = 79.6 kN (Manual AISC Tabla 7-1: 17,9 kip)

Aplastamiento en una chapa de 10 mm, Fu = 450 MPa, con la deformación como estado de servicio (§J3.10):
  lc =  20.0 mm → φRn =   81.0 kN (desgarro 1,2·lc·t·Fu, tope 2,4·d·t·Fu = 154.3 kN)
  lc =  30.0 mm → φRn =  121.5 kN (desgarro 1,2·lc·t·Fu, tope 2,4·d·t·Fu = 154.3 kN)
  lc =  38.1 mm → φRn =  154.3 kN (desgarro 1,2·lc·t·Fu, tope 2,4·d·t·Fu = 154.3 kN)
  lc =  50.0 mm → φRn =  154.3 kN (desgarro 1,2·lc·t·Fu, tope 2,4·d·t·Fu = 154.3 kN)

Interacción J3.7 (rosca incluida): resistencia a tracción disponible con cortante concomitante
  Vu/perno [kN] frv [MPa] F′nt [MPa] φR′nt [kN]
              0       0.0      620.5      132.6
             20      70.2      620.5      132.6
             40     140.4      494.8      105.8
             60     210.5      338.8       72.4
             80     280.7      182.9       39.1
            100     350.9       26.9        5.8
  A mano con 40 kN: F′nt = 1,3·620,5 − 620,5/(0,75·372,3)·140.4 = 494.8 MPa

Hasta la versión 1.1 el cortante -N se calculaba con 0,75·Ab además de Fnv-N (59,7 kN en vez de 79,6 kN para el A325 de 3/4") y la rosca excluida no subía a Fnv-X. El aplastamiento toma lc como dato: calcúlalo con el agujero real (d + 1/16" estándar).
```

</details>

#### Tornillos M16 a M30 de clases 8.8 y 10.9 en EN 1993-1-8: área resistente, agujero d0, aplastamiento e interacción

<details><summary>Salida real de <code>python examples/bolt_ec3_m16_m30_grades_8_8_10_9_shear_tension_bearing_with_hole_d0_and_combined_check.py</code></summary>

```text
Resistencias de cálculo por tornillo [kN], un plano de corte, γM2 = 1,25:
  tornillo     As   d0 Fv,Rd rosca Fv,Rd vástago  Ft,Rd
  M16 8.8     157   18        60.3          77.2   90.4
  M16 10.9    157   18        62.8          80.4  113.0
  M20 8.8     245   22        94.1         120.7  141.1
  M20 10.9    245   22        98.0         125.7  176.4
  M24 8.8     353   26       135.6         173.7  203.3
  M24 10.9    353   26       141.2         181.0  254.2
  M30 8.8     561   33       215.4         271.4  323.1
  M30 10.9    561   33       224.4         282.8  403.9

A mano, M20 8.8: Fv,Rd = 0,6·800·245/1,25 = 94.08 kN; Ft,Rd = 0,9·800·245/1,25 = 141.12 kN (tablas habituales: 94,1 y 141,1 kN)

Aplastamiento de un M20 8.8 en chapa S275 (fu = 430 MPa) de 12 mm, d0 = 22 mm:
    e1   p1   e2   p2     αd     k1 Fb,Rd [kN] con d en vez de d0
    30   55   30   55  0.455  1.800       67.5               88.8
    40   70   35   70  0.606  2.500      125.1              137.6
    50   80   40   80  0.758  2.500      156.4              172.0
    66   90   50   90  1.000  2.500      206.4              206.4
  Con e1 = 3·d0 = 66 mm y p2 ≥ 3·d0 se alcanzan αd = 1 y k1 = 2,5: Fb,Rd = 2,5·fu·d·t/γM2 = 206.4 kN.

Interacción cortante-tracción (Tabla 3.4): Fv,Ed/Fv,Rd + Ft,Ed/(1,4·Ft,Rd) ≤ 1
  Fv,Ed =   40 kN, Ft,Ed =   60 kN → 0.729 cumple
  Fv,Ed =   60 kN, Ft,Ed =   80 kN → 1.043 NO cumple
  Fv,Ed =   70 kN, Ft,Ed =  100 kN → 1.250 NO cumple
  Fv,Ed =   90 kN, Ft,Ed =   30 kN → 1.108 NO cumple

El aplastamiento toma el tornillo más desfavorable de la unión (mín. de los casos de borde e interior para αd y k1), una envolvente conservadora; para tornillos concretos usa codes.ec3_1_8.bolt_bearing_Rd(direction_inner=…, d0_mm=…). Sin punzonamiento ni deslizamiento aquí (funciones aparte en codes.ec3_1_8).
```

</details>

#### Grupo de seis pernos con carga excéntrica: método elástico frente a centro instantáneo y coeficiente C

<details><summary>Salida real de <code>python examples/bolt_group_eccentric_elastic_vector_vs_instantaneous_center_icr_c_coefficient_vs_eccentricity.py</code></summary>

```text
Grupo 2 × 3 (gramil 75 mm, paso 75 mm), A325-N de 3/4": φrn = 79.6 kN por perno
  e [mm] C elástico   C ICR ICR/elás.   IC (x, y) [mm] φRn ICR [kN]    solver
       0      6.000   6.000     1.000                ∞        477.5 centered_load
      50      3.882   4.476     1.153          (87, 0)        356.2 bisection
     100      2.657   3.054     1.150          (46, 0)        243.1 bisection
     150      1.985   2.249     1.133          (37, 0)        178.9 bisection
     200      1.576   1.774     1.126          (32, 0)        141.2 bisection
     300      1.111   1.241     1.117          (24, 0)         98.8 bisection
     500      0.696   0.769     1.105          (15, 0)         61.2 bisection

Comprobación de una ménsula con Pu = 200 kN a 200 mm: φRn = C·φrn = 141.2 kN → utilización 1.42 NO cumple
  Método elástico: perno crítico 126.9 kN frente a 79.6 kN → utilización 1.59

Con e = 0 los dos métodos dan C = n = 6. Con excentricidad el ICR da entre un 11 % y un 15 % más que el elástico: es la reserva por ductilidad de los pernos interiores que el método elástico no usa. Los C de las Tablas 7-6 a 7-14 del Manual salen de este mismo modelo, pero aquí no se han comparado valor a valor.
```

</details>

#### Centro instantáneo con carga oblicua: Newton 2D, bisección exacta con carga alineada y error claro sin scipy

<details><summary>Salida real de <code>python examples/bolt_group_icr_oblique_load_newton_vs_aligned_bisection_and_missing_scipy_dependency_error.py</code></summary>

```text
Grupo 2 × 4 (90 × 75 mm), excentricidad 150 mm, Rult = 1 → C. scipy instalado: True

  Ángulo medido desde el eje +Y: 0° es carga vertical, paralela al lado largo del grupo (225 mm); 90° es horizontal.
  ángulo       C IC x [mm] IC y [mm]             solver
       0   3.764      57.1       0.0          bisection
      15   3.686      54.0     -23.0           newton2d
      30   3.603      47.2     -37.5           newton2d
      45   3.558      41.4     -48.6           newton2d
      60   3.523      30.2     -61.4           newton2d
      75   3.503      16.1     -69.3           newton2d
      90   3.505       0.0     -71.8          bisection

Carga vertical: bisección C = 3.7645, Newton 2D C = 3.7645 (+0.000 %)

Simulando un entorno sin scipy, carga a 30° → DependencyError: el centro instantáneo con carga oblicua o excéntrica necesita scipy: pip install steeljoints[numeric]
Carga centrada (e = 0): C = 8 = número de pernos, sin solver (centered_load).

En este grupo C va de 3.503 a 75° a 3.764 a 0° (7.4 % de diferencia): con la misma excentricidad, la carga paralela al lado largo es la favorable.
La bisección solo es exacta con la carga paralela a un eje de simetría: por eso con carga oblicua se exige scipy en vez de caer en silencio a un método inexacto.
```

</details>

#### Efecto palanca en un T-stub: barrido del espesor del ala con Fy y con Fu

<details><summary>Salida real de <code>python examples/prying_action_t_stub_flange_thickness_sweep_alpha_prime_available_tension_fy_vs_fu.py</code></summary>

```text
Perno A325 de 7/8": B = φRnt = 180.5 kN; ala con b = 45 mm, a = 40 mm, p = 90 mm por perno, Fy = 345 / Fu = 450 MPa
  b′ = 33.89 mm, ρ = 0.663, δ = 0.731; t_c(Fy) = √(4·180.5e3·33.89/(0,9·90·345)) = 29.6 mm

  t [mm]  t_c Fy     α′ T_disp Fy  t_c Fu     α′ T_disp Fu  palanca
    10.0    29.6  1.000      35.7    25.9  1.000      46.5       sí
    12.0    29.6  1.000      51.4    25.9  1.000      67.0       sí
    14.0    29.6  1.000      69.9    25.9  1.000      91.2       sí
    16.0    29.6  1.000      91.3    25.9  1.000     119.1       sí
    19.0    29.6  1.000     128.8    25.9  0.707     147.3       sí
    22.0    29.6  0.666     148.3    25.9  0.318     160.4       sí
    25.0    29.6  0.330     159.9    25.9  0.061     175.6       sí
    28.0    29.6  0.096     173.0    25.9  0.000     180.5       no

Con Fu, el ala de 26.0 mm ya deja al perno trabajar a su resistencia completa (t ≥ t_c = 25.9 mm).
Por debajo de t_c la palanca reduce la tracción útil del perno; con alas finas α′ = 1 y la reducción es la de flexión del ala. El Manual usa Fu en t_c desde la 13.ª edición; sin Fu_MPa el módulo usa Fy y sale conservador (t_c un 14 % mayor).
```

</details>

#### Catálogo: tamaños imperiales y métricos, área resistente, agujeros de las Tablas J3.3 y J3.3M, grados y electrodos

<details><summary>Salida real de <code>python examples/bolt_catalog_imperial_metric_sizes_tensile_area_hole_sizes_grades_and_electrode_parser.py</code></summary>

```text
  tamaño   d [mm] Ab [mm²] As [mm²]  As/Ab agujero est. sobredim.
  1/2       12.70    126.7     91.5  0.722         14.3      17.5
  5/8       15.88    197.9    145.8  0.737         17.5      20.7
  3/4       19.05    285.0    215.5  0.756         20.6      23.9
  7/8       22.23    387.9    298.7  0.770         23.8      28.6
  1         25.40    506.7    391.0  0.772         28.6      31.8
  1-1/8     28.57    641.3    491.6  0.767         31.8      35.0
  M12       12.00    113.1     84.3  0.745         14.0      16.8
  M14       14.00    153.9    115.0  0.747         16.0      18.8
  M16       16.00    201.1    157.0  0.781         18.0      20.8
  M18       18.00    254.5    192.0  0.755         20.0      22.8
  M20       20.00    314.2    245.0  0.780         22.0      24.8
  M22       22.00    380.1    303.0  0.797         24.0      26.8
  M24       24.00    452.4    353.0  0.780         27.0      30.4
  M27       27.00    572.6    459.0  0.802         30.0      33.4
  M30       30.00    706.9    561.0  0.794         33.0      36.4

  As fuera de catálogo por ISO 898-1, π/4·(d − 0,9382·P)²: M33 → 694 mm², M36 → 817 mm² (tablas ISO: 694 y 817)

Grados AISC 360-22 Tabla J3.2 [MPa]: A307: Fnt 310, Fnv-N 186, Fnv-X 186; A325: Fnt 620, Fnv-N 372, Fnv-X 469; A490: Fnt 779, Fnv-N 469, Fnv-X 579; F1852: Fnt 620, Fnv-N 372, Fnv-X 469; F2280: Fnt 779, Fnv-N 469, Fnv-X 579
Clases EN ISO 898-1 (EC3 Tabla 3.1) [MPa]: 4.6: fyb 240, fub 400, αv 0.6; 4.8: fyb 320, fub 400, αv 0.5; 5.6: fyb 300, fub 500, αv 0.6; 5.8: fyb 400, fub 500, αv 0.5; 6.8: fyb 480, fub 600, αv 0.5; 8.8: fyb 640, fub 800, αv 0.6; 10.9: fyb 900, fub 1000, αv 0.5

Lector de electrodos (FEXX en MPa):
  'E70XX'      →  482.6
  'E7018'      →  482.6
  'E70T-1'     →  482.6
  'E80'        →  551.6
  '70 ksi'     →  482.6
  'FEXX=90'    →  620.5
  '480 MPa'    →  480.0
  70           →  482.6
  482.6        →  482.6
  'E110XX'     →  758.4
  'acero'      → KeyError: "Electrodo desconocido 'acero'. Disponibles: ['E60XX', 'E70XX', 'E80XX', 'E90XX', 'E100XX', 'E110XX']"

Tamaño inexistente → KeyError: "Tamaño desconocido 'M21'. Imperial: ['1/2', '5/8', '3/4', '7/8', '1', '1-1/8', …

As/Ab ronda 0,75–0,78: por eso EN 1993-1-8 usa As cuando la rosca está en el plano de corte y en tracción, y AISC lo incorpora en Fnt y en Fnv-N. El agujero estándar sale de AISC 360-22 Tabla J3.3 (d + 1/16" por debajo de 1", d + 1/8" desde 1") y de la Tabla J3.3M para métricos (M24 → 27 mm); EN 1090-2 usa otras holguras (1/2/3 mm, ver bolts.ec3_normal_hole_clearance). La columna de sobredimensionados no está contrastada con la tabla.
```

</details>

### 2. Soldaduras

#### Cordón de 8 mm de 0° a 90°: aumento direccional de AISC frente a los métodos direccional y simplificado de EC3

<details><summary>Salida real de <code>python examples/fillet_weld_directional_strength_0_to_90_deg_aisc_e70_vs_ec3_s355_directional_and_simplified.py</code></summary>

```text
Cordón de 8 mm, garganta a = 5.66 mm. AISC: E70 (FEXX 482,6 MPa), φ = 0,75. EC3: S355, fu = 510 MPa, βw = 0.9, γM2 = 1,25.

    θ AISC φRn [N/mm]   ×θ=0 EC3 direcc. [N/mm] ×simplif. EC3 simplif.
    0            1228  1.000               1481     1.000         1481
   15            1309  1.066               1497     1.011         1481
   30            1446  1.177               1546     1.044         1481
   45            1594  1.297               1622     1.095         1481
   60            1724  1.403               1710     1.155         1481
   75            1812  1.475               1784     1.205         1481
   90            1843  1.500               1813     1.225         1481

A mano a 90°: AISC 1 + 0,5·1 = 1,5 (función 1.500); EC3 √(3/2) = 1.225 (función 1.225).
A 0° el EC3 simplificado y el direccional coinciden (1481 N/mm) y quedan un 21 % por encima del AISC E70 con estos materiales.

A 90° el método direccional de EC3 sube un 22 % y AISC un 50 %. AISC aplica el aumento completo a un grupo lineal de tamaño uniforme cargado por su centro de gravedad (§J2.4(b)(1)); si se mezclan cordones longitudinales y transversales, §J2.4(b)(2) limita a máx(Rnwl + Rnwt, 0,85·Rnwl + 1,5·Rnwt) por compatibilidad de deformaciones. En EC3 el simplificado es siempre seguro.
```

</details>

#### Ménsula soldada en C con carga excéntrica: método elástico, punto crítico y tamaño de cordón

<details><summary>Salida real de <code>python examples/weld_group_elastic_c_shape_bracket_eccentric_load_required_leg_size_line_method_cross_check.py</code></summary>

```text
Grupo en C: Lw = 400 mm, centroide x̄ = 25.0 mm, Ip = 3.083e+06 mm³ (línea de espesor unidad)
  Carga 150 kN hacia abajo a x = 300 mm → excentricidad 275.0 mm, M = 41.25 kN·m
  Punto crítico (100, 100) mm, f_max = 1920.9 N/mm
  A mano en (100, ±100): directo 375.0, torsión (1337.8; 1003.4) → f = √(1337.8² + (375.0 + 1003.4)²) = 1920.9 N/mm

Tamaño de cordón con E70, φ = 0,75 (sin aumento direccional):
  w_req = f_max/(0,75·0,60·FEXX/√2) = 12.5 mm → cordón comercial de 14 mm
  w =    8 mm: φRn = 1228 N/mm → utilización 1.564 NO cumple
  w =   10 mm: φRn = 1536 N/mm → utilización 1.251 NO cumple
  w =   12 mm: φRn = 1843 N/mm → utilización 1.042 NO cumple

welds.WeldGroup con los mismos cordones de 8 mm: 339.6 N/mm² en la garganta = 1920.9 N/mm de cordón; utilización 1.564 (CALCULADO_FALLA).
Las dos implementaciones dan la misma tensión. El método elástico ignora la ductilidad y el aumento direccional; el centro instantáneo da más capacidad para la misma ménsula.
```

</details>

#### La misma C por centro instantáneo: barrido de la excentricidad, compatibilidad con carga centrada y coeficiente del Manual

<details><summary>Salida real de <code>python examples/weld_group_icr_lesik_kennedy_c_shape_eccentricity_sweep_vs_elastic_and_manual_coefficient.py</code></summary>

```text
C de 200 × 100 mm, cordón de 8 mm E70 (Rn longitudinal 1638 N/mm), carga vertical, excentricidad desde el centroide.

  ex [mm] Pn ICR [kN] Pn elást. [kN] ICR/elás. IC x [mm] C Manual         solver
        0       761.8          655.2     1.163         ∞    4.316  centered_load
       50       635.8          404.0     1.574       183    3.602       newton2d
      100       466.8          277.5     1.682       103    2.645       newton2d
      150       357.1          208.9     1.709        69    2.023       newton2d
      200       289.0          166.9     1.731        53    1.637       newton2d
      300       199.9          118.6     1.685        38    1.133 bisection_fallback
      400       151.6           91.9     1.650        31    0.859 bisection_fallback

Carga centrada: todos los cordones se deforman lo mismo y manda la deformación última de las alas transversales, así que el alma no llega a su capacidad. ICR 761.8 kN frente a AISC 360-22 §J2.4(b)(2) máx(Rnwl + Rnwt, 0,85·Rnwl + 1,5·Rnwt) = 769.9 kN.
Con excentricidad el ICR da entre 1.57 y 1.73 veces la capacidad elástica. Newton 2D no convergió con ex = 300, 400 mm y se usó la bisección, exacta aquí porque la C es simétrica respecto a la horizontal.

La ménsula del caso elástico (150 kN a 300 mm del alma): φPn = 0,75·217.1 = 162.8 kN → utilización 0.921 cumple con cordón de 8 mm.
```

</details>

#### Soldaduras a tope: CJP de una chapa a tracción y cortante, PJP con garganta según ángulo y proceso

<details><summary>Salida real de <code>python examples/groove_welds_cjp_plate_tension_shear_pjp_effective_throat_angle_and_governing_metal.py</code></summary>

```text
Chapa de 20 × 300 mm, A572 Gr. 50 (Fy = 345, Fu = 450 MPa), A = 6000 mm²
  CJP a tracción: Rn = 2070 kN, φRn = 1863 kN (metal_base)
  CJP a cortante: Rn = 1242 kN, φRn = 1118 kN (metal_base)
  A mano a tracción: mín(0,90·345·6000, 0,75·450·6000) = mín(1863, 2025) kN → fluencia

PJP sobre la misma chapa, electrodo E70, L = 300 mm, tracción normal al eje:
  prof. [mm] ángulo proceso E [mm] φRn [kN]   gobierna
           6     60    SMAW    6.0      393  soldadura
          10     60    SMAW   10.0      655  soldadura
          10     45    SMAW    7.0      458  soldadura
          10     45     SAW   10.0      655  soldadura
          14     60    GMAW   14.0      917  soldadura
          20     60    SMAW   20.0     1310  soldadura
  Ranura a 30° → GeometryError: angulo de ranura PJP < 45deg no recomendado

Este módulo usa FEXX = 485 MPa para E70 (el resto del paquete, 482,6 = 70 ksi exactos: +0.5 %) y φ = 0.75 para la soldadura en todos los casos. Un informe de investigación de AISC da Ω = 1,88 (φ = 0,80) para PJP a tracción normal al eje, así que aquí sale del lado seguro. El cortante CJP usa φ = 0.9 sobre 0,6·Fy; §J4.2 usa φ = 1,00 para la fluencia por cortante (conservador).
```

</details>

#### Tamaños mínimo y máximo de cordón, y datos que faltan: NO_CALCULADO, nunca un aprobado

<details><summary>Salida real de <code>python examples/fillet_weld_min_max_leg_size_and_missing_capacity_unknown_grade_propagated_never_as_pass.py</code></summary>

```text
Tamaño mínimo por la chapa más delgada (Tabla J2.4):
  t =  5.00 mm → w_min =  3.17 mm (2.0/16")
  t =  6.35 mm → w_min =  3.17 mm (2.0/16")
  t = 10.00 mm → w_min =  4.76 mm (3.0/16")
  t = 16.00 mm → w_min =  6.35 mm (4.0/16")
  t = 19.05 mm → w_min =  6.35 mm (4.0/16")
  t = 25.00 mm → w_min =  8.00 mm (5.0/16")

Tamaño máximo en el borde de una chapa (§J2.2b: t si t < 1/4", t − 1/16" si no):
  t =  5.00 mm → función  5.00 mm; norma  5.00 mm
  t =  6.35 mm → función  4.35 mm; norma  4.76 mm
  t = 10.00 mm → función  8.00 mm; norma  8.41 mm
  t = 20.00 mm → función 18.00 mm; norma 18.41 mm
  La función resta 2 mm en vez de 1/16" (1,6 mm): 0,4 mm del lado seguro.

Datos ausentes:
  WeldGroup sin capacidad: utilización inf, is_ok False, NO_CALCULADO, falta ['phi_Rn_per_unit'], demanda 126.0 N/mm² (se publica)
  WeldGroup con capacidad 1228,5 N/mm: utilización 0.580, CALCULADO_CUMPLE
  WeldGroupElastic con FEXX = 0: utilización inf, is_ok False
  FilletWeld EC3 grado 'S355': Fw,Rd = 148.1 kN
  FilletWeld EC3 grado 'S355J2': Fw,Rd = 148.1 kN
  FilletWeld EC3 grado 'S690': ValueError: Grado de acero desconocido para beta_w (EN 1993-1-8:2005 Tabla 4.1): 'S690'. Conocidos: ['…
  FilletWeld EC3 grado '': ValueError: Grado de acero desconocido para beta_w (EN 1993-1-8:2005 Tabla 4.1): ''. Conocidos: ['S235…
  codes.ec3_1_8.beta_w('S355J2') = 0.9; 'S690' → ValueError (EN 1993-1-8:2005 Tabla 4.1 llega a S460)

Un cero de capacidad leído como «utilización 0» aprobaría la unión; aquí la ausencia se propaga como ausencia. FilletWeld exige el grado exacto de la tabla y beta_w() acepta sufijos de calidad (J2, JR, N…).
```

</details>

### 3. Uniones a cortante y bloque de cortante

#### Chapa simple de 2 a 6 pernos: todos los estados límite, el que gobierna y la capacidad

<details><summary>Salida real de <code>python examples/shear_tab_single_plate_two_to_six_bolts_all_limit_states_governing_check_and_capacity.py</code></summary>

```text
Chapa de 9,5 mm, A572 Gr. 50 (Fy 345 / Fu 450 MPa), paso 75 mm, bordes 38 mm, ancho 75 mm. φRn [kN]:

   n h [mm]   cortante pernos     aplastamiento fluencia cortante   rotura cortante            bloque          gobierna φRn [kN]
   2    151             159.2             252.3             296.9             209.5             244.7   cortante pernos    159.2
   3    226             238.7             398.9             444.4             313.3             348.5   cortante pernos    238.7
   4    301             318.3             545.5             591.9             417.1             452.3   cortante pernos    318.3
   5    376             397.9             692.1             739.4             520.9             556.1   cortante pernos    397.9
   6    451             477.5             838.7             886.9             624.6             659.9   cortante pernos    477.5

Comprobación de una viga con Vu = 280 kN y 4 pernos:
  cortante pernos   φRn =   318.3 kN → 0.880 cumple
  aplastamiento     φRn =   545.5 kN → 0.513 cumple
  fluencia cortante φRn =   591.9 kN → 0.473 cumple
  rotura cortante   φRn =   417.1 kN → 0.671 cumple
  bloque            φRn =   452.3 kN → 0.619 cumple
  Gobierna cortante pernos con 0.880: cumple.
  Con chapa de 6,4 mm gobierna rotura cortante con 0.997: cumple.

Con la chapa de 9,5 mm gobierna «cortante pernos» de 2 a 6 pernos; el siguiente estado límite (rotura a cortante) queda un 31 % por encima con 4 pernos. Al adelgazar la chapa la rotura a cortante pasa delante. La clase no comprueba la flexión de la chapa ni la excentricidad de los pernos (Manual AISC Parte 10, configuración convencional), la soldadura al soporte ni el aplastamiento en el alma de la viga, y descuenta agujeros de d + 2 mm (§B4.3b pediría d + 1/8" en el área neta).
```

</details>

#### Doble angular en una viga despatinada: pernos, aplastamiento y bloque en angulares y alma

<details><summary>Salida real de <code>python examples/clip_angle_double_angle_beam_web_and_support_bolts_bearing_block_shear_coped_beam.py</code></summary>

```text
Vu = 250 kN, 3 pernos a 75 mm, angulares de 9,5 mm, alma de 8 mm (A572 Gr. 50), gramil al borde del alma 35 mm:
  Bolt shear (web, double shear)                 φRn =   477.5 kN → 0.524 cumple
  Bolt shear (support, single shear ×2 angles)   φRn =   477.5 kN → 0.524 cumple
  Bearing on beam web                            φRn =   335.9 kN → 0.744 cumple
  Bearing on angle legs (2 angles)               φRn =   709.1 kN → 0.352 cumple
  Angle shear yielding (2 angles)                φRn =   639.0 kN → 0.391 cumple
  Angle shear rupture (2 angles)                 φRn =   557.0 kN → 0.449 cumple
  Block shear (2 angles)                         φRn =   692.0 kN → 0.361 cumple
  Block shear (beam web)                         φRn =   285.4 kN → 0.876 cumple
  Gobierna: Block shear (beam web) (0.876)

Espesor del alma de la viga:
  tw =  5.0 mm → gobierna Block shear (beam web)                         1.402
  tw =  6.5 mm → gobierna Block shear (beam web)                         1.078
  tw =  8.0 mm → gobierna Block shear (beam web)                         0.876
  tw = 10.0 mm → gobierna Block shear (beam web)                         0.701
  tw = 12.0 mm → gobierna Block shear (beam web)                         0.584
  tw = 14.0 mm → gobierna Bolt shear (web, double shear)                 0.524
  tw = 16.0 mm → gobierna Bolt shear (web, double shear)                 0.524

Número de pernos con alma de 8 mm:
  n = 2 → altura de angular 151 mm, φRn =  198.0 kN (Block shear (beam web))
  n = 3 → altura de angular 226 mm, φRn =  285.4 kN (Block shear (beam web))
  n = 4 → altura de angular 301 mm, φRn =  372.8 kN (Block shear (beam web))
  n = 5 → altura de angular 376 mm, φRn =  460.2 kN (Block shear (beam web))

Servicio en modo rápido: Rn = 393.3 kN, DCR = 0.64 frente a 0.88 de la clase completa (285.4 kN).
  Nota del servicio: Fluencia por cortante bruto con Fy = 345 MPa; activa full_aisc_checks=True para pernos, aplastamiento y bloque de cortante
Servicio con full_aisc_checks=True: DCR = 0.88 (Block shear (beam web)); igual que la clase con los mismos datos.

Hasta un alma de 12 mm manda «Block shear (beam web)»; desde 14 mm pasa a mandar «Bolt shear (web, double shear)». El modo rápido del servicio ignora pernos, aplastamiento y bloque: úsalo solo como orden de magnitud.
```

</details>

#### Bloque de cortante de la misma chapa en AISC, EN 1993-1-8, AS 4100 y NSR-10

<details><summary>Salida real de <code>python examples/block_shear_aisc_en1993_as4100_nsr10_same_bolted_plate_ubs_and_governing_path.py</code></summary>

```text
S275 (fy 275 / fu 430 MPa): Agv = 1800, Anv = 1250, Ant = 290 mm²

  norma                         Ubs  Rn [kN]  Rd [kN]  factor      modo
  AISC 360-22 §J4.3             1.0    421.7    316.3   0.750     yield
  AISC 360-22 §J4.3             0.5    359.4    269.5   0.750     yield
  EN 1993-1-8 §3.10.2 (Ec. 3.9)  1.0    323.2    298.2   0.923  fracture
  AS 4100 §9.1.9                1.0    421.7    316.3   0.750     yield
  AS 4100 §9.1.9                0.5    359.4    269.5   0.750     yield
  NSR-10 F.2 (vía AISC)         1.0    421.7    316.3   0.750     yield
  NSR-10 F.2 (vía AISC)         0.5    359.4    269.5   0.750     yield

Contraste: block_shear_strength AISC φRn = 316.3 kN (shear_yielding), EC3 Veff = 298.2 kN; NSR-10 φRn = 316.3 kN (shear_yield).
  A mano AISC: mín(0,6·430·1250, 0,6·275·1800) + 430·290 = 421.7 kN → ×0,75 = 316.3 kN
  A mano EC3: 430·290/1,25 + 275·1250/(√3·1,0) = 298.2 kN

EC3 con la Ec. 3.9 queda un -6 % respecto a AISC; AS 4100 y NSR-10 coinciden con AISC. Ubs = 0,5 (tracción no uniforme) baja AISC a 269.5 kN.
La Ec. 3.9 supone un grupo simétrico con carga centrada. Un bloque en L como este, con una sola fila junto al borde, se parece más al caso de la Ec. 3.10 (0,5·fu·Ant/γM2 + fy·Anv/(√3·γM0) = 248.3 kN), que el módulo no implementa: calcúlala aparte si tu unión es de ese tipo.
```

</details>

#### NSR-10 Título F.2 frente a AISC 360-22: pernos, cordón de filete y bloque

<details><summary>Salida real de <code>python examples/nsr10_f2_colombia_bolts_fillet_weld_block_shear_compared_with_aisc_360_22.py</code></summary>

```text
NSR-10 Título F.2 — Estructuras de Acero (Colombia)

  perno          φRn corte NSR [kN] AISC 360-22 [kN]   dif. φRn tracción NSR   AISC
  A307-N 3/4"                  40.2             39.8  +1.0%             66.3   66.3
  A325-N 3/4"                  79.5             79.6  -0.1%            132.5  132.6
  A325-X 3/4"                  99.3            100.2  -0.9%            132.5  132.6
  A490-N 3/4"                  97.7            100.2  -2.5%            166.7  166.5
  A490-X 3/4"                 124.6            123.8  +0.6%            166.7  166.5

Cordón de 8 mm × 150 mm, E70:
  θ =    0° → NSR-10 φRn =  184.0 kN, AISC 360-22  184.3 kN
  θ =   45° → NSR-10 φRn =  238.7 kN, AISC 360-22  239.1 kN
  θ =   90° → NSR-10 φRn =  276.0 kN, AISC 360-22  276.4 kN

La rosca excluida usa Fnv = 0,563·Fu (464 MPa en A325) en vez de la Tabla J3.2 (468,8 MPa, 68 ksi); de ahí la diferencia en las filas -X. El A490-N de la tabla NSR del módulo tiene 457 MPa frente a 468,8 MPa (68 ksi) de AISC 360-22.
Las notas del resultado dicen: NSR-10 F.2.10.3 — perno A325 Ø19.05 mm
NSR-10 F.2 sigue a AISC 360-05, donde el A325-N tenía 48 ksi (330 MPa); el módulo usa 372 MPa (54 ksi, AISC 360-10). Si el proyecto exige la edición literal de NSR-10, comprueba las resistencias nominales de pernos de F.2.10.3 antes de usar estos valores.
```

</details>

#### Capa de servicios: perno con distancia al borde, línea de pernos con momento y modo rápido frente a comprobación completa

<details><summary>Salida real de <code>python examples/services_layer_single_bolt_group_fillet_weld_clip_splice_quick_vs_full_checks.py</code></summary>

```text
Perno individual en chapa de 10 mm (Fu 400 MPa), distancia al borde variable:
  AISC A325 e =   25 mm → Rn corte  105.8 | aplastamiento   70.5 kN → gobierna bearing
  AISC A325 e =   30 mm → Rn corte  105.8 | aplastamiento   94.5 kN → gobierna bearing
  AISC A325 e =   40 mm → Rn corte  105.8 | aplastamiento  142.5 kN → gobierna shear
  AISC A325 e =   60 mm → Rn corte  105.8 | aplastamiento  182.9 kN → gobierna shear
  EC3  8.8  e =   25 mm → Rn corte  117.6 | aplastamiento   75.8 kN → gobierna bearing
  EC3  8.8  e =   30 mm → Rn corte  117.6 | aplastamiento   90.9 kN → gobierna bearing
  EC3  8.8  e =   40 mm → Rn corte  117.6 | aplastamiento  121.2 kN → gobierna shear
  EC3  8.8  e =   60 mm → Rn corte  117.6 | aplastamiento  181.8 kN → gobierna shear
  φRn corte del servicio 79.4 kN frente a 79.6 kN de la clase Bolt (el servicio usa Fnv = 0,45·Fu en vez de la Tabla J3.2)
  Notas: ['Rn shear = 105.8 kN | bearing = 94.5 kN', 'Aplastamiento AISC §J3.10: lc = 19.7 mm, mín(1,2·lc·t·Fu, 2,4·d·t·Fu)', 'Gobierna: bearing']

Línea de 4 pernos A325 de 3/4" a 76 mm con Vu = 150 kN y momento:
  Mu =    0 kN·m → Rn grupo  423.3 kN, DCR 0.47
  Mu =    5 kN·m → Rn grupo  415.8 kN, DCR 0.53
  Mu =   10 kN·m → Rn grupo  392.7 kN, DCR 0.69
  Mu =   20 kN·m → Rn grupo  281.8 kN, DCR 1.10

Cordón de 8 × 150 mm, FEXX 482 MPa:
  θ =   0° → φRn = 184.0 kN (factor 1.000)
  θ =  90° → φRn = 276.0 kN (factor 1.500)

Doble angular 2L 100 × 100 × 9,5 con Vu = 250 kN, modo rápido y comprobación completa:
  rápido   → DCR 0.64 (Gross shear yield); Fluencia por cortante bruto con Fy = 345 MPa; activa full_aisc_checks=True para pernos, aplastamiento y bloque de cortante
  completo → DCR 0.88 (Block shear (beam web)); Capacidad gobernante efectiva φRn = 285.4 kN
Empalme con Mu = 150 kN·m y Vu = 80 kN:
  solo alas, canto por defecto → Mn 345 kN·m, DCR 0.43; Mn = 345.0 kN*m (brazo d = 500 mm, Fy = 345 MPa), DCR = 0.43
  canto 450 mm y 4 pernos de alma → Mn 310 kN·m, DCR 0.48, perno más cargado 26.3 kN (DCR 0.33)

Salida serializable: ['Rd_shear_kN', 'Rn_bearing_kN', 'Rn_shear_kN', 'Rn_tension_kN', 'governs', 'notes']
El modo rápido del doble angular da DCR 0.64 frente a 0.88 del completo: subestima la demanda. Para proyecto, full_aisc_checks=True o la clase ClipAngle.
```

</details>

### 4. Uniones a momento y sísmicas

#### Chapa frontal 4E: tracción de pernos, líneas de fluencia, barrido del espesor y Yp frente a AISC 358 Tabla 6.2

<details><summary>Salida real de <code>python examples/end_plate_4e_extended_aisc358_bolt_tension_plate_yield_line_thickness_sweep_and_yp_table_6_2_check.py</code></summary>

```text
Viga de 450 × 190 × 14,6 mm, chapa de 230 × 22 mm (Fy 345 MPa), pernos A325 de 7/8", pfo = pfi = 38 mm, gramil 140 mm:
  Bolt tension                     utilización 0.795 cumple
  Bolt shear (Vu)                  utilización 0.277 cumple
  End plate flexure                utilización 0.439 cumple
  Welds (flange CJP + web fillet)  utilización 0.667 cumple
  Gobierna: Bolt tension (0.795)
  A mano: T = Mu/(2·(h0 + h1)) = 250e3/(2·(480.7 + 390.1)) = 143.5 kN (función 143.5)

Yp del módulo = 3790 mm; forma habitual de 4E = 3790 mm (+0 %).
  tp [mm] φMn módulo φMn Yp habitual                         gobierna  util.
     14.0      230.6           230.6                End plate flexure  1.084
     16.0      301.2           301.2                End plate flexure  0.830
     19.0      424.8           424.8                     Bolt tension  0.795
     22.0      569.5           569.5                     Bolt tension  0.795
     25.0      735.4           735.4                     Bolt tension  0.795

Espesor necesario para 250 kN·m: 14.6 mm con el Yp del módulo y 14.6 mm con la forma habitual.
El Yp del módulo coincide con la forma de AISC 358 Tabla 6.2 / DG4 escrita en el ejemplo, así que los dos espesores son el mismo. La comprobación sísmica (seismic=True con Zx y Ry) usa Mpr en lugar de Mu.
```

</details>

#### Memoria de chapa frontal por EN 1993-1-8: T-stub por fila con las longitudes eficaces de la Tabla 6.6

<details><summary>Salida real de <code>python examples/end_plate_memo_en1993_1_8_t_stub_rows_effective_lengths_moment_resistance_upper_bound.py</code></summary>

```text
Fila 1 (extensión): mx = 35.9, nx = 44.9 mm; leff = mín de la Tabla 6.6 = 125.0 mm (0,5·bp); brazo 487.7 mm
Fila 2 (bajo el ala): m = 38.5, n = 48.1 mm; leff = mín(2πm, 4,45·m) = 171.4 mm (α = 4,45 es la cota inferior de la Fig. 6.11); brazo 378.1 mm

  tp [mm] Mj nominal Mj diseño DCR (200 kN·m)  seguro
       12      133.8     120.4          1.661   False
       15      209.0     188.1          1.063   False
       20      309.2     244.3          0.819    True
       25      355.7     286.1          0.699    True

Filas con chapa de 20 mm:
  h =  487.7 mm → Ft,Rd =  272.8 kN (nominal 346.8), modo Modo 2
  h =  378.1 mm → Ft,Rd =  294.2 kN (nominal 370.6), modo Modo 2

Sin bolt_rows: M_resistance_kNm = None, DCR_moment = None, is_safe = None (NO CALCULADO, no se inventa el brazo).
Mj es una cota superior: falta el ala del pilar a flexión, el alma del pilar a tracción, cortante y compresión, el alma de la viga a tracción y los límites de grupo de filas (§6.2.7.2).
```

</details>

#### RBS en una W610 × 125: profundidad del corte, límites de §5.8, Mpr y momento en la cara del pilar

<details><summary>Salida real de <code>python examples/rbs_reduced_beam_section_aisc358_cut_depth_sweep_geometry_limits_probable_and_face_moment.py</code></summary>

```text
W610 × 125: d = 612, bf = 229, tf = 19.6, Zx = 3.67e6 mm³, A992 (Fy 345, Ry 1,1). Límites §5.8: {'a_mm': 143.1, 'b_mm': 459.0, 'c_mm': 45.8, 'bf_reduced_mm': 137.4, 'Sh_mm': 372.6, 'limits': {'a_range_mm': (114.5, 171.75), 'b_range_mm': (397.8, 520.1999999999999), 'c_range_mm': (22.900000000000002, 57.25)}}

a = 143 mm, b = 459 mm, luz libre 7,0 m, wu = 30 kN/m. φd·Mpe = 1,0·Ry·Fy·Zx = 1393 kN·m

  c [mm]  c/bf Z_RBS/Zx     Mpr    Vpr      Mf Mf/φdMpe geometría             estado
      15 0.066    0.905    1450    569    1662    1.193     fuera  REQUIERE_REVISION
      25 0.109    0.842    1348    536    1548    1.112        OK   CALCULADO_CUMPLE
      35 0.153    0.779    1247    504    1435    1.030        OK   CALCULADO_CUMPLE
      45 0.197    0.715    1146    471    1321    0.949        OK   CALCULADO_CUMPLE
      57 0.249    0.639    1024    432    1185    0.851        OK   CALCULADO_CUMPLE
      65 0.284    0.589     943    407    1094    0.786     fuera  REQUIERE_REVISION

El corte más pequeño que deja Mf ≤ φd·Mpe es c ≈ 39 mm (0.17·bf), dentro del rango 0,1–0,25·bf.
A mano con c = 45 mm: Z_RBS = 3.67e+06 − 2·45·19.6·(612 − 19.6) = 2.625e+06 mm³; Mpr = 1,15·1,1·345·Z_RBS = 1146 kN·m
Memoria rbs_aisc358_memo con c = 45 mm: Mpr = 1146 kN·m, Mf = 1321 kN·m; devuelve (texto de 1130 caracteres, resultado).
El estado CALCULADO_* compara la demanda Mu = 900 kN·m con la capacidad; la comprobación de la cara del pilar (Mf ≤ φd·Mpe) es la columna Mf/φdMpe.
```

</details>

#### WUF-W contra un pilar de 400 mm: pilar fuerte–viga débil con axil, zona de panel y pilar ausente

<details><summary>Salida real de <code>python examples/wuf_w_welded_unreinforced_flange_web_probable_moment_scwb_with_axial_panel_zone_and_missing_column.py</code></summary>

```text
Pilar de 400 × 400 (tf 24, tw 15, Zx 5,5e6 mm³, Fy 345), Mu = 1000 kN·m, Vu = 300 kN:
  Pu/Py    Mpr   Vpr compacta   SCWB PZ DCR    DCR           estado
   0.00   1602   555     True   1.11   2.04   0.62  CALCULADO_FALLA
   0.14   1602   555     True   0.95   2.04   0.62  CALCULADO_FALLA
   0.29   1602   555     True   0.79   2.04   0.62  CALCULADO_FALLA
   0.50   1602   555     True   0.55   2.04   0.62  CALCULADO_FALLA
   0.71   1602   555     True   0.32   2.04   0.62  CALCULADO_FALLA

Notas con Pu = 2000 kN:
  · SCWB: M*pb = Mpr + Vpr·dc/2 = 1712.6 kN.m
  · SCWB con axil: M*pc = Zc Fyc (1 - Pu/Py), Pu/Py = 0.286
  · SCWB = 0.79 < 1.0 - NO CUMPLE
  · M_pr = 1601.7 kN.m (C_pr=1.15, Ry=1.1)
  · V_pr = 554.6 kN
  · Panel zone: phiVn=1328.2 kN, DCR=2.04
  · SCWB ratio = 0.79
  · CJP weld capacity = 1548.5 kN
  · Incumple: SCWB 0.79 < 1.0
  · Incumple: zona de panel DCR 2.04
  A mano: Mpr = 1,15·1,1·345·3,67e6 = 1602 kN·m; M*pb = Mpr + Vpr·dc/2 = 1602 + 555·0,2 = 1713 kN·m; SCWB = Zc·Fyc·(1 − Pu/Py)/M*pb = 0.79 (un pilar y una viga; en un nudo interior con dos pilares y dos vigas el cociente es el mismo)

Sin pilar declarado: estado NO_CALCULADO, scwb_ratio None, faltan ['col_d_mm (columna) ausente', 'col_bf_mm (columna) ausente', 'col_tf_mm (columna) ausente', 'col_tw_mm (columna) ausente', 'col_Zx_mm3 (columna) ausente', 'col_Fy_MPa (columna) ausente']
design_wuf_w (simplificado): Mpr 1602 kN·m, Vu 555 kN, compacta True, SCWB 0.79

Con este pilar fallan la zona de panel (DCR 2.04) y, en cuanto el axil pasa de cero, el pilar fuerte–viga débil. Hace falta chapa de refuerzo (ver el caso de zona de panel) y un pilar con más módulo plástico. Sin pilar, el servicio no inventa uno: el veredicto queda NO_CALCULADO. Hasta la versión 1.1 el servicio dividía por Zb·Fyb nominal y daba SCWB 1,07 (cumple) en este mismo nudo.
```

</details>

#### Zona de panel: los cuatro casos de §J10.6, barrido del axil, chapa de refuerzo y memoria

<details><summary>Salida real de <code>python examples/panel_zone_aisc_j10_6_four_cases_axial_sweep_doubler_plate_and_memo.py</code></summary>

```text
Demanda del panel: ΣMu/(db − tf) − Vc = 1738 kN (vigas de 600 y 500 kN·m)

  Pr/Pc φRn sin deform. [kN] φRn con deform. [kN]
   0.00                968.8               1183.4
   0.20                968.8               1183.4
   0.40                968.8               1183.4
   0.50                871.9               1183.4
   0.60                775.0               1183.4
   0.75                629.7               1183.4
   0.85                532.8               1041.4
   1.00                387.5                828.4

A mano, Pr = 0: φ·0,6·Fy·dc·tw = 968.8 kN; con deformación ×(1 + 3·bcf·tcf²/(db·dc·tw)) = ×1.222 = 1183.4 kN

Chapa de refuerzo con Pr = 0,3·Pc, sin considerar la deformación del panel:
  utilización sin refuerzo 1.79; refuerzo 10.3 mm (resistencia 10.3 mm, estabilidad 10.2 mm) → φRn 1740 kN

Memoria: ecuación J10-11, demanda 1317 kN, φRn 969 kN, DCR 1.36, refuerzo sí; 543 caracteres de Markdown.
La memoria usa V = 0,8·(Mf1 + Mf2)/d_b − Vc, con un coeficiente 0,8 que su propio texto declara sin trazar a norma y el canto d_b como brazo: su demanda (1317 kN) queda un 24 % por debajo de la de la clase (1738 kN, ΣMu/(db − tf) − Vc). Para verificar usa la clase PanelZone. Considerar la deformación del panel aumenta la capacidad y retrasa la reducción por axil (umbral 0,75·Pc en vez de 0,4·Pc), pero exige que el análisis la incluya.
```

</details>

#### Uniones RBS de un pórtico contra los momentos de un pushover, una viga sin demanda y una cartela

<details><summary>Salida real de <code>python examples/seismodyn_bridge_rbs_connections_vs_pushover_demands_and_haunch_retrofit.py</code></summary>

```text
4 uniones: 2 seguras, 0 que no cumplen, 2 sin veredicto, 1 con geometría fuera de §5.8
  viga   M demanda     Mpr  util. geometría             estado
  V-101        980    1146  0.855        OK   CALCULADO_CUMPLE
  V-102       -640     763  0.839        OK   CALCULADO_CUMPLE
  V-103        520     369  1.410     fuera  REQUIERE_REVISION
  V-104          —     493      —        OK       NO_CALCULADO
  Viga crítica: V-103 (utilización 1.410)
  V-104: falta ["sin demanda para beam_id='V-104'"]

Cartela de refuerzo bajo la viga de 460 mm (ala 191 × 14,5, Zx 1,62e6 mm³), cartela de 250 × 600 mm con ala 180 × 15 mm:
  USA: resistencia 993 kN·m (factor 0.90), ángulo 22.6°, fuerza vertical 0.712 kN por kN·m, ala b/2t = 6.0 compacta
  EU : resistencia 1104 kN·m (factor 1.00), ángulo 22.6°, fuerza vertical 0.712 kN por kN·m, ala b/2t = 6.0 compacta
  Viga sola: φ·Fy·Zx = 503 kN·m.

El signo del momento se descarta (|M|). V-103 tiene un corte de 60 mm, más de 0,25·bf: queda fuera de la precalificación y pide revisión aunque su utilización sea conocida. V-104 no tiene demanda en el análisis y sale sin veredicto (hasta la versión 1.1 desaparecía del informe). La resistencia de la cartela es un modelo simplificado sin contrastar con AISC Design Guide 21 ni con la FEMA 355D: úsala para predimensionar, no para verificar. El valor devuelto ya incluye φ, aunque el campo se llame Mn_kNm.
```

</details>

### 5. Placas base, T-stub y anclajes

#### Placa base con compresión centrada: aplastamiento con confinamiento y espesor por los voladizos

<details><summary>Salida real de <code>python examples/base_plate_aisc_dg1_concentric_axial_bearing_confinement_and_thickness_sweep.py</code></summary>

```text
Pu = 2000 kN, hormigón f′c = 28 MPa, placa Fy = 250 MPa:

   B × N [mm] √(A2/A1)     fp    φFp aplast.      m      n    λn′  tp,req
    400 × 400     1.00  12.50  15.47   0.808   52.8   78.0   18.4    26.0
    450 × 450     1.00   9.88  15.47   0.638   77.8  103.0   16.3    30.5
    500 × 500     1.00   8.00  15.47   0.517  102.8  128.0   14.6    34.1
    400 × 400     1.50  12.50  23.20   0.539   52.8   78.0   18.4    26.0
    400 × 400     2.00  12.50  30.94   0.404   52.8   78.0   18.4    26.0
    600 × 600     1.00   5.56  15.47   0.359  152.8  178.0   12.2    39.6

Área mínima sin confinamiento: A1 = Pu/(0,65·0,85·f′c) = 129282 mm² → placa cuadrada de 360 mm.
A mano, placa de 450 mm: m = (450 − 0,95·310)/2 = 77.8, n = (450 − 0,8·305)/2 = 103.0 mm; tp = 103.0·√(2·9.88/(0,9·250)) = 30.5 mm

Servicio (con espesor dado):
  tp =   25 mm → tp,req = 30.5 mm, DCR = 1.22
  tp =   32 mm → tp,req = 30.5 mm, DCR = 0.95
  tp =   40 mm → tp,req = 30.5 mm, DCR = 0.76

Confinar el hormigón (pedestal mayor que la placa) sube Fp hasta el doble y deja usar una placa más pequeña, pero el espesor lo fija el voladizo mayor. Pasa √(A2/A1), no A2/A1: con una zapata cuatro veces mayor que la placa el valor es 2,0.
```

</details>

#### Placa base con momento: núcleo central, anclajes, levantamiento y comparación con Design Guide 1 §3.4

<details><summary>Salida real de <code>python examples/base_plate_moment_eccentricity_kern_limit_anchor_tension_uplift_and_bearing_without_moment.py</code></summary>

```text
Pu = 800 kN, placa 450 × 550 mm, 2 anclajes F1554 Gr. 36 de 1" por lado (Fut 400 MPa). Núcleo central: e ≤ N/6 = 92 mm

DG1: fp,max = 0,65·0,85·28 = 15.47 MPa, e_crit = 218 mm; anclajes a f = 225 mm del eje.

     Mu e [mm] fp módulo  fp DG1 T/ancl. módulo T/ancl. DG1   φRnt
      0      0      3.23    3.23            0.0         0.0      —
     40     50      3.23    3.95            0.0         0.0      —
     73     91      3.23    4.84            0.0         0.0      —
    120    150      3.23    7.11          127.3         0.0  114.0
    175    219      3.23   15.47          277.3         1.3  114.0
    200    250      3.23   15.47          345.5        34.2  114.0
    280    350      3.23   15.47          563.6       145.5  114.0

Levantamiento (Pu = −150 kN, Mu = 60 kN·m): T = 143.2 kN por anclaje (Uplift/tension case — bolts resist full tension + moment couple), utilización 1.26
  Espesor: None — Pu < 0 (levantamiento): la placa flecta por la traccion de los anclajes y esa comprobacion no esta implementada; la formula DG1 §3.3.4 es de compresion
  Informe: ❌ FAILED (gobierna Anchor bolt tension)

Con momento el módulo deja fp en Pu/(B·N): con e = 150 mm la presión de DG1 es un 120 % mayor (del lado inseguro). Su modelo de anclajes va al revés: con e = 150 mm pide 127 kN por anclaje donde DG1 no pide ninguno, y con e = 350 mm pide 564 kN frente a 145 kN. Úsalo con compresión centrada; con momento usa BasePlate.dg1_eccentric_pressure.
dg1_eccentric_pressure frente a la implementación del caso: diferencia máxima 0.000 (MPa o kN) en 7 filas.
```

</details>

#### T-stub de EN 1993-1-8: los tres modos, el espesor de transición, deslizamiento y punzonamiento

<details><summary>Salida real de <code>python examples/ec3_t_stub_three_failure_modes_flange_thickness_sweep_mode_transition_and_slip_punching.py</code></summary>

```text
T-stub de leff = 160 mm, m = 35, n = 43.75 mm (≤ 1,25·m), S275; 2 × M20 10.9: ΣFt,Rd = 2·0,9·1000·245/1,25 = 352.8 kN

    tp  F1 [kN]  F2 [kN]  F3 [kN]   FT,Rd    modo
     8     80.5    213.9    352.8    80.5  Modo 1
    10    125.7    223.9    352.8   125.7  Modo 1
    12    181.0    236.2    352.8   181.0  Modo 1
    15    282.9    258.9    352.8   258.9  Modo 2
    18    407.3    286.5    352.8   286.5  Modo 2
    20    502.9    307.7    352.8   307.7  Modo 2
    25    785.7    370.6    352.8   352.8  Modo 3
    30   1131.4    447.4    352.8   352.8  Modo 3

Fronteras: modo 1 → 2 con tp = 14.2 mm; modo 2 → 3 con tp = 23.7 mm.
A mano con tp = 15: Mpl = 0,25·160·15²·275 = 2.475 kN·m; F2 = (2·Mpl + 43.75·ΣFt)/(35 + 43.75) = 258.9 kN (función 258.9)

Los mismos tornillos pretensados (Fp,C = 0,7·fub·As):
  superficie clase A (μ = 0.5): Fs,Rd =  68.6 kN por tornillo y plano
  superficie clase B (μ = 0.4): Fs,Rd =  54.9 kN por tornillo y plano
  superficie clase C (μ = 0.3): Fs,Rd =  41.2 kN por tornillo y plano
  superficie clase D (μ = 0.2): Fs,Rd =  27.4 kN por tornillo y plano
  Punzonamiento de una chapa de 12 mm (fu 430 MPa) bajo cabeza de M20 (dm ≈ 32,4 mm): Bp,Rd = 252.1 kN frente a Ft,Rd = 176.4 kN

Con alas finas manda el modo 1 (plastificación completa del ala); al engrosar el ala la rotura pasa a los tornillos con palanca (modo 2) y, con ala gruesa, a los tornillos solos (modo 3). La clave del modo 1 se llama F1_Nmm pero su valor está en N.
```

</details>

#### Anclaje con tracción y cortante: interacción desacoplada acero/hormigón frente a la acoplada de 2019

<details><summary>Salida real de <code>python examples/aci318_25_anchor_uncoupled_steel_concrete_interaction_vs_2019_coupled_sweep.py</code></summary>

```text
Capacidades de diseño [kN]: acero φNsa 150, φVsa 90; hormigón φNnc 110 (arrancamiento), φVnc 120 (rotura del borde)
Carga resultante de 80 kN con ángulo θ respecto al eje del anclaje:

    θ    Nua    Vua  acero hormigón   2025     modo   2019 2019/2025
    0   80.0    0.0  0.284    0.588  0.588 concrete  0.588      1.00
   15   77.3   20.7  0.318    0.609  0.609 concrete  0.641      1.05
   30   69.3   40.0  0.411    0.623  0.623 concrete  0.722      1.16
   45   56.6   56.6  0.537    0.616  0.616 concrete  0.791      1.29
   60   40.0   69.3  0.664    0.586  0.664    steel  0.832      1.25
   75   20.7   77.3  0.756    0.542  0.756    steel  0.837      1.11
   90    0.0   80.0  0.790    0.509  0.790    steel  0.822      1.04

Compresión (Nua = −30) y cortante negativo: la tracción se toma como 0 y el cortante en valor absoluto → 0.198 (steel)
Capacidad nula → ValueError: All design capacities (phi * Nn, phi * Vn) must be strictly positive.

La interacción acoplada de 2019 empareja la peor capacidad a tracción con la peor a cortante aunque sean de modos distintos; en este barrido da entre 1.00 y 1.29 veces la desacoplada. Comprueba los exponentes con ACI 318-25 §17.8 antes de usarla en proyecto.
```

</details>

#### Cortante en una dirección con efecto de tamaño λs y el multiplicador por efecto arco sin contrastar

<details><summary>Salida real de <code>python examples/aci318_one_way_shear_size_effect_lambda_s_depth_sweep_and_short_span_arching_unverified.py</code></summary>

```text
Zapata de 1000 mm de ancho, f′c = 28 MPa, ρw = 0,4 %, sin armadura de cortante:

  d [mm]     λs τc [MPa]  φVc [kN] φVc/d [kN/mm]
     250  1.000    0.554     103.9         0.416
     500  0.817    0.453     169.7         0.339
     750  0.707    0.392     220.5         0.294
    1000  0.632    0.351     263.0         0.263
    1500  0.534    0.296     333.4         0.222
    2000  0.471    0.261     392.0         0.196

A mano con d = 1000: λs = √(2/(1 + 4)) = 0.632 (función 0.632); τc = 0,66·0.632·0,004^(1/3)·√28 = 0.351 MPa

Cuantía (d = 1000 mm):
  ρw = 0.2 % → φVc = 208.7 kN
  ρw = 0.4 % → φVc = 263.0 kN
  ρw = 0.8 % → φVc = 331.3 kN
  ρw = 1.5 % → φVc = 408.5 kN

Vano de cortante corto (a_v/d < 2), Vu = 1500 kN, d = 1000 mm:
  sin a_v      → multiplicador 1.00, φVc =   263.0 kN, utilización 5.70 NO cumple
  a_v/d = 2.5  → multiplicador 1.00, φVc =   263.0 kN, utilización 5.70 NO cumple
  a_v/d = 1.5  → multiplicador 1.33, φVc =   350.6 kN, utilización 4.28 NO cumple
  a_v/d = 1.0  → multiplicador 2.00, φVc =   525.9 kN, utilización 2.85 NO cumple
  a_v/d = 0.5  → multiplicador 2.50, φVc =   657.4 kN, utilización 2.28 NO cumple

λs reduce la resistencia de los cantos grandes: a 2 m la tensión resistente es un 53 % menor que a 250 mm. El multiplicador por efecto arco (hasta 2,5) es la interpretación del módulo y no está contrastado con ACI 318-25 §13.4: no lo uses para verificar un encepado.
```

</details>

### 6. Materiales, estabilidad e integraciones

#### Rotura frágil: temperatura de referencia, espesor máximo por subgrado y clase Z

<details><summary>Salida real de <code>python examples/ec3_brittle_fracture_reference_temperature_t_max_by_subgrade_surrogate_and_z_quality_class.py</code></summary>

```text
Temperatura de referencia: T_md = −20 °C (mínima del aire) + ΔT_r = −5 (radiación) = -25 °C

Espesor máximo [mm] de S355 según subgrado y nivel de tensión σEd/fy(t) (sustituto de la Tabla 2.1):
  subgrado  0,25·fy  0,50·fy  0,75·fy
  S355JR         32       24       18
  S355J0         52       38       28
  S355J2         77       57       42
  S355K2         97       72       53
  S355ML        142      105       78

Temperatura de servicio (S355J2, σEd = 0,75·fy):
  T_Ed =    10 °C → t_max =    95 mm
  T_Ed =   -10 °C → t_max =    60 mm
  T_Ed =   -30 °C → t_max =    38 mm
  T_Ed =   -50 °C → t_max =    24 mm

Grado, mismo subgrado J2, T_Ed = −25 °C, σEd = 0,75·fy:
  S235J2 →    55 mm
  S275J2 →    49 mm
  S355J2 →    42 mm
  S460J2 →    30 mm

Desgarro laminar: clase Z según Z_Ed = Za + Zb + Zc + Zd + Ze (Tabla 3.2):
  ala de 20 mm, cordón 5 mm, sin coacción              Z_Ed =   5 → none
  chapa de 40 mm en T, cordón 10 mm                    Z_Ed =  18 → Z15
  chapa de 60 mm en cruz, cordón 20 mm, coacción alta  Z_Ed =  31 → Z35
  igual, con precalentamiento                          Z_Ed =  23 → Z25

Subgrado inexistente → ValueError: unknown subgrade 'X9'
Las contribuciones Za…Ze de la tabla son datos de ejemplo; tómalas de la Tabla 3.2 para tu detalle. El espesor máximo sale de un ajuste continuo con anclas en −10 °C y 0,75·fy: para proyecto, lee la Tabla 2.1.
```

</details>

#### Cables y cordones de EN 1993-1-11: resistencia, coeficiente parcial, flexión en el anclaje y fatiga

<details><summary>Salida real de <code>python examples/en1993_1_11_cables_and_tendons_resistance_groups_partial_factors_anchorage_bending_fatigue.py</code></summary>

```text
Resistencia característica F_Rk [kN] con alambres de 5 mm y f_uk = 1770 MPa:
    7 alambres (A_m =    137 mm²): grupo 1     243 | grupo 2     224 | grupo 3     207
   19 alambres (A_m =    373 mm²): grupo 1     660 | grupo 2     607 | grupo 3     561
   37 alambres (A_m =    726 mm²): grupo 1    1286 | grupo 2    1183 | grupo 3    1093
   61 alambres (A_m =   1198 mm²): grupo 1    2120 | grupo 2    1950 | grupo 3    1802

Coeficiente parcial γM del módulo:
  clase 1: construction 0.990 | service 1.350 | fatigue 1.215 | accidental 0.900
  clase 2: construction 1.100 | service 1.500 | fatigue 1.350 | accidental 1.000
  clase 3: construction 1.210 | service 1.650 | fatigue 1.485 | accidental 1.100

Cordón de 37 alambres, clase 2, servicio: F_Rd = F_Rk/γM = 1183/1.50 = 789 kN

Tensión de flexión en el anclaje con una desviación angular de 0,5° (barra maciza equivalente de 35 mm, E = 165 GPa):
  F =  200 kN → σ_b =  102.2 MPa (tensión media  207.9 MPa); por radián   11713 MPa
  F =  400 kN → σ_b =  144.6 MPa (tensión media  415.8 MPa); por radián   16565 MPa
  F =  600 kN → σ_b =  177.0 MPa (tensión media  623.6 MPa); por radián   20288 MPa
  σ_b = θ·(d/2)·√(F·E/I). El modelo trata el cable como barra maciza (I y d/2 del conjunto); en un cordón cada alambre flecta con su propio radio, así que usa la expresión del fabricante para un cordón real.

Categoría de fatiga del módulo:
  wire         d = 36 mm → Δσ_C = 160 MPa
  strand       d = 36 mm → Δσ_C = 150 MPa
  locked_coil  d = 36 mm → Δσ_C = 120 MPa
  bar          d = 36 mm → Δσ_C = 105 MPa

γM de servicio = 1,5 por un factor de clase (0,9 / 1,0 / 1,1). El agrupamiento 1/2/3, los coeficientes 0,92 y 0,85 y los γM son la interpretación del módulo; compruébalos con EN 1993-1-11 y con la documentación del fabricante antes de usarlos.
```

</details>

#### Pandeo por flexotorsión de una T soldada: cúbica E4-6 frente a la fórmula cerrada E4-5

<details><summary>Salida real de <code>python examples/flexural_torsional_buckling_aisc_e4_welded_tee_cubic_vs_closed_form_length_sweep.py</code></summary>

```text
T soldada: A = 5700 mm², ȳ = 66.3 mm desde la cara del ala, Ix = 37.92e6, Iy = 10.69e6 mm⁴, J = 356.4e3 mm⁴, Cw = 0.705e9 mm⁶, centro de cortante a yo = 58.3 mm del centroide

  L [m]     Fex     Fey     Fez Fe cúbica Fe cerrada Pcr [kN]           modo
    1.5    5836    1645     414     381.0      381.0     2171   flexotorsión
    2.0    3283     925     410     349.3      349.3     1991   flexotorsión
    3.0    1459     411     407     266.6      266.6     1520   flexotorsión
    4.0     821     231     406     186.3      186.3     1062   flexotorsión
    6.0     365     103     405      94.6       94.6      539   flexotorsión
    8.0     205      58     405      55.3       55.3      315   flexotorsión

A mano con L = 3 m: r̄o² = yo² + (Ix + Iy)/A = 11930 mm² (función 11930); H = 1 − yo²/r̄o² = 0.715; Fez = (π²·E·Cw/Lcz² + G·J)/(A·r̄o²) = 406.9 MPa
Sección sin eje de simetría con la fórmula cerrada → ValueError: la fórmula cerrada sólo aplica con un eje de simetría

El eje de simetría es el vertical (y): la flexión alrededor del eje horizontal (Fex) queda desacoplada y la flexión alrededor de y (Fey) se acopla con la torsión (Fez). La reducción respecto al menor de Fey y Fez es máxima cuando ambos se igualan (34 % con 3 m) y pequeña cuando la flexión domina (4 % con 8 m). La cúbica y la fórmula cerrada coinciden en todo el barrido.
```

</details>

#### IDEA StatiCa y RFEM 6: modelo IOM, esfuerzos en CSV y JSON con lectura de vuelta, y qué no es importable

<details><summary>Salida real de <code>python examples/ideastatica_iom_xml_dict_and_member_forces_csv_json_roundtrip_declared_not_importable.py</code></summary>

```text
IOM en diccionario: claves ['OpenModel', 'OpenModelResult']
  4 nodos, 3 barras, 2 vectores de esfuerzos; unidades SI_m_kN_kNm_MPa
  XML de 1107 caracteres; raíz <IdeaOpenModel> con hijos ['ProjectData', 'Points', 'Members', 'Connection', 'LoadCases']

CSV de esfuerzos (4 líneas):
  Member,Position,LoadingCase,N [kN],Vy [kN],Vz [kN],Mx [kNm],My [kNm],Mz [kNm]
  Viga,Begin,1.35G+1.5Q,-12.000,0.000,-185.000,0.000,-210.000,0.000
  Viga,Begin,G+0.3Q+Ex,35.000,2.000,-95.000,1.500,-340.000,12.000
  Lectura de vuelta: 3 filas, idénticas a las originales: True
JSON: claves ['count', 'member_forces', 'schema_version', 'software_target', 'units']

RFEM 6: método create_model, 4 nodos, 3 barras, 1 materiales; primer nodo {'no': 1, 'coordinates': [0.0, 0.0, 0.0]}

Ficheros en out/: nudo_B3.iom.xml, nudo_B3_esfuerzos.csv
El CSV y el JSON sirven para pegar esfuerzos en IDEA StatiCa a mano o con su API. El XML IOM de este módulo NO lo importa IDEA StatiCa 21.1 (el formato real es `OpenModel` versión 2), y la carga útil de RFEM 6 no se ha enviado nunca a un RFEM real: trátalos como borradores de intercambio.
```

</details>

#### Mazo de CalculiX para una chapa y planos DXF de cuatro uniones

<details><summary>Salida real de <code>python examples/calculix_plate_deck_inp_and_dxf_details_shear_tab_clip_angle_base_plate_end_plate.py</code></summary>

```text
CalculiX: chapa 300 × 150 × 12 mm, malla 12 × 6 → 91 nodos, 72 elementos S4
  Palabras clave: *HEADING *NODE *ELEMENT *MATERIAL *ELASTIC *SHELL SECTION *NSET *BOUNDARY *STEP *STATIC *CLOAD *EL PRINT *NODE PRINT *END STEP
  Comprobación: (nx + 1)·(ny + 1) = 91, nx·ny = 72

Planos DXF (entidades por capa al releerlos con ezdxf):
  chapa_cortante.dxf    47.3 KiB, versión AC1024: BOLTS 12, STEEL 1, TABLE 8, TEXT 11
  doble_angular.dxf     47.5 KiB, versión AC1024: BOLTS 9, STEEL 5, TABLE 8, TEXT 10
  placa_base.dxf        44.4 KiB, versión AC1024: BOLTS 12, STEEL 1, TEXT 1
  chapa_frontal.dxf     58.1 KiB, versión AC1024: BOLTS 32, DIM 16, STEEL 7, TABLE 10, TEXT 19, WELDS 12

Ficheros en out/. El mazo de CalculiX es una chapa en voladizo con carga puntual en el borde libre: sirve para contrastar una placa a mano, no modela tornillos ni contacto. Los planos son esquemas de detalle con cotas y tabla de datos, no planos de taller.
```

</details>

#### API REST sin servidor: pernos, cordón, placa base, RBS, WUF-W y datos inválidos

<details><summary>Salida real de <code>python examples/rest_api_fastapi_testclient_bolts_welds_base_plate_rbs_wuf_and_validation_errors.py</code></summary>

```text
SteelJoints API 1.2.0: 11 rutas
  POST /api/connections/base_plate
  POST /api/connections/bolts/group
  POST /api/connections/bolts/single
  POST /api/connections/clip_angle
  POST /api/connections/end_plate
  POST /api/connections/end_plate/from_member_forces
  POST /api/connections/panel_zone
  POST /api/connections/rbs
  POST /api/connections/splice
  POST /api/connections/welds/fillet
  POST /api/connections/wuf

POST /bolts/single → 200: {'Rn_shear_kN': 105.81, 'Rn_tension_kN': 176.36, 'Rn_bearing_kN': 94.47, 'Rd_shear_kN': 79.36, 'governs': 'bearing'}
POST /bolts/single → 200: {'Rn_shear_kN': 117.6, 'Rn_tension_kN': 176.4, 'Rn_bearing_kN': 121.21, 'Rd_shear_kN': 94.08, 'governs': 'shear'}
POST /bolts/group → 200: {'Rn_group_kN': 392.71, 'DCR_shear': 0.69}
POST /welds/fillet → 200: {'throat_mm': 5.66, 'Rn_kN': 368.04, 'Rd_kN': 276.03, 'directional_factor': 1.5}
POST /base_plate → 200: {'fp_actual_MPa': 9.88, 'fp_allow_MPa': 15.47, 'tp_required_mm': 30.52, 'DCR': 0.95}
POST /rbs → 200: {'Z_RBS_mm3': 2625006.4, 'M_pr_kNm': 1145.62, 'V_pr_kN': 471.3, 'M_f_kNm': 1321.18, 'DCR': 0.68, 'status': 'OK', 'calculation_status': 'CALCULADO_CUMPLE', 'is_geometry_ok': True}
POST /wuf → 200: {'M_pr_kNm': 1601.68, 'V_pr_kN': 554.6, 'is_compact': True, 'scwb_ratio': None, 'pz_Vn_kN': None, 'pz_DCR': None, 'weld_capacity_kN': 1548.5, 'DCR': 0.62, 'status': 'UNKNOWN', 'cal

Datos inválidos:
  diámetro negativo → 422: Input should be greater than 0
  falta leg_size_mm → 422: ['body', 'leg_size_mm'] Field required
  WUF-W sin pilar ni demanda → 200, estado NO_CALCULADO, faltan 7 datos

Los errores de tipo y rango los rechaza pydantic con 422; la falta de datos de ingeniería sale con 200 y un veredicto NO_CALCULADO que nombra lo que falta.
```

</details>

## Verificación

- Pernos AISC contra la Tabla J3.2 en ksi convertidos exactamente y contra el Manual (A325-N de 3/4″ = 17,9 kip = 79,6 kN), interacción J3.7 contra valores calculados a mano (`test_golden_j3_7_interaction.py`, `test_v120_corrections.py`).
- EN 1993-1-8 contra fichas del máster con su cálculo a mano: aplastamiento, cordón direccional y simplificado, T-stub en sus tres modos; una ficha con errata se ancla a su propio cálculo y lo declara (`test_ec3_1_8_golden.py`).
- Grupos de soldadura: `welds.WeldGroup` coincide con el método de línea de `WeldGroupElastic`; el centro instantáneo con carga centrada coincide con la suma de elementos a la deformación del menos dúctil y queda a menos de un 2 % de AISC §J2.4(b)(2) (`test_v120_corrections.py`).
- Contratos de estado cerrado por defecto: capacidad ausente, pilar ausente, demanda ausente o no finita salen como NO_CALCULADO o REQUIERE_REVISION, nunca como aprobado (`test_welds_absence_propagation.py`, `test_wuf_evidence_contract.py`, `test_rbs_moment_contract.py`, `test_b59_placa_base_con_traccion.py`).
- Propiedades con hypothesis: monotonía de capacidades con el diámetro, el tamaño del cordón y el número de pernos (`test_property_invariants.py`).
- Correcciones de la 1.2.0, cada una con su test: cortante AISC sin doble descuento por rosca, As y d0 en EC3, bloque de cortante con Anv y con tope de fluencia en AS 4100, zona de panel en los cuatro casos, h1 de la chapa frontal, palanca con Fu, grupos de soldadura en los extremos de los cordones, compatibilidad del centro instantáneo con carga centrada, βw por grado, agujeros J3.3M, aplastamiento con distancia al borde en el servicio, bloque de la chapa a cortante hacia el borde libre, SCWB con Mpr + Vpr·dc/2, unidades del cortante en la memoria RBS, uniones sin demanda en el puente sísmico, clases Z de la Tabla 3.2 y ángulo de desviación en la flexión de anclajes. Detalle en [CHANGELOG.md](CHANGELOG.md).
- `tests/test_examples.py` ejecuta los 33 casos de uso en ubuntu y windows × Python 3.11–3.13.

## Limitaciones

- `ShearTab` no comprueba la flexión de la chapa, la excentricidad de los pernos, la soldadura al soporte ni el aplastamiento en el alma de la viga, y descuenta agujeros de d + 2 mm.
- `memos.end_plate` (EN 1993-1-8) da una cota superior: solo el T-stub de la chapa, sin ala ni alma del pilar ni límites de grupo de filas. Sin filas declaradas no calcula.
- `BasePlate` calcula el aplastamiento y el espesor con Pu/(B·N), sin el momento (del lado inseguro con momento), y los anclajes con un modelo lineal propio, mucho más conservador que Design Guide 1 §3.4. Con momento, usa `BasePlate.dg1_eccentric_pressure` (bloque rectangular de DG1 §3.4–3.5; el caso de uso lo contrasta con una implementación propia). `A2_A1` es √(A2/A1).
- `memos.panel_zone` usa 0,8·ΣMf/d_b − Vc, con un 0,8 sin trazar a norma que su propio texto declara; para verificar, `PanelZone`. Las etiquetas de ecuación de §J10.6 difieren entre la API funcional y la memoria.
- `services.clip_angle` en modo rápido (por defecto) solo comprueba la fluencia bruta y subestima la demanda; con `full_aisc_checks=True` delega en `ClipAngle`. `services.splice` sin `n_bolts_web` solo comprueba las placas de ala con el brazo `beam_depth_mm` (500 mm por defecto). `services.bolts` aproxima Fnv con 0,45·Fu y 0,563·Fu.
- `codes.ec3_1_8.bolt_bearing_Rd` con `direction_inner=False` omite el término 1,4·p2/d0 − 1,7 de k1 para tornillos de borde con varias filas, y su d0 por defecto es d; `Bolt.ec3_bearing_strength` usa los dos términos y d0 real. El bloque de cortante de EC3 implementa la Ec. 3.9, no la 3.10 de grupos con carga excéntrica.
- `groove_welds` usa φ = 0,75 para la soldadura también en PJP a tracción normal al eje (φ = 0,80 en AISC) y φ = 0,90 para el cortante CJP (1,00 en §J4.2), y FEXX = 485 MPa para E70.
- `catalog.oversized_hole` no está contrastado con la columna de sobredimensionados de las Tablas J3.3 y J3.3M.
- `codes.nsr10_f2` usa los valores de AISC 360-10 y posteriores; NSR-10 se basa en AISC 360-05 (A325-N de 48 ksi allí).
- `haunch_connection.design_haunch` es un modelo simplificado (ΔZ = bf·tf·(d + h/2)) sin contrastar, y su `Mn_kNm` ya incluye φ.
- `aci318_25_anchors`: exponentes de interacción (2 y 5/3) y multiplicador por efecto arco según la interpretación del módulo, sin contrastar con ACI 318-25.
- `ec3_fracture.t_max_brittle_fracture` es un ajuste continuo de la Tabla 2.1 de EN 1993-1-10, no la tabla. `ec3_tension_members`: grupos, coeficientes 0,92 y 0,85 y γM según la interpretación del módulo; la flexión en el anclaje modela el cable como barra maciza.
- `ideastatica_iom` genera un XML que IDEA StatiCa 21.1 no importa (el formato real es `OpenModel` versión 2) y una carga útil de RFEM 6 nunca probada contra RFEM. `integration.fastsap_bridge` necesita SAP2000 abierto y el paquete `fastsap`.

## Normas y referencias

- ANSI/AISC 360-22, *Specification for Structural Steel Buildings*: §B4.3b, §E4, §J2, §J3 (Tablas J3.2, J3.3 y J3.3M), §J4, §J10.6. AISC *Steel Construction Manual*, 16.ª ed.: Partes 7 (grupos de pernos), 8 (grupos de soldadura), 9 (efecto palanca) y 10 (uniones a cortante).
- ANSI/AISC 358, *Prequalified Connections for Special and Intermediate Steel Moment Frames*: caps. 5 (RBS), 6 (chapa frontal) y 8 (WUF-W). ANSI/AISC 341, *Seismic Provisions*: §D1 y §E3.
- AISC Design Guide 1, *Base Connection Design for Steel Structures*; Design Guide 4, *Extended End-Plate Moment Connections*; Design Guide 16, *Flush and Extended Multiple-Row Moment End-Plate Connections*.
- EN 1993-1-8:2005 (§3.6, §3.9, §3.10.2, §4.5.3, §6.2.4, §6.2.7.2, Tablas 3.4, 4.1 y 6.6); EN 1993-1-10:2005 (Tablas 2.1 y 3.2); EN 1993-1-11:2006; EN 1090-2 (Tabla 11, holguras de agujero); EN ISO 898-1 (clases de tornillos); EN 10164 (clases Z).
- ACI 318-19 y ACI 318-25, caps. 17 (anclajes) y 22.5 (cortante en una dirección). AS 4100, §9.1.9 (bloque de cortante, enmienda de 2012). NSR-10, Título F.2.
- D. F. Crawford y G. L. Kulak, «Eccentrically loaded bolted connections», J. Struct. Div. ASCE 97(ST3) (1971). D. F. Lesik y D. J. L. Kennedy, «Ultimate strength of fillet welded connections loaded in plane», Can. J. Civ. Eng. 17(1) (1990). W. A. Thornton, «Prying action — a general treatment», Eng. J. AISC 22(2) (1985).
- Formatos: CalculiX (`*SHELL SECTION`, S4), IDEA StatiCa Open Model, Dlubal RFEM 6 API, DXF de AutoCAD vía ezdxf.

## Licencia

MIT. Consulta [LICENSE](LICENSE).

---

Parte de **Loadpath**, la colección de librerías estructurales de código abierto de [Jesús Murgas](https://github.com/jmurgass99).
