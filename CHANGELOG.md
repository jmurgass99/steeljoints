# Changelog

## 1.2.0 — 2026-11-01

### Corregido
- `bolts.Bolt.aisc_shear_strength`: aplicaba dos veces la reducción por rosca (Fnv «-N» de la Tabla J3.2 y además 0,75·Ab). Un A325-N de 3/4" daba 59,7 kN en vez de 79,6 kN, y con la rosca excluida no subía a Fnv «-X». Ahora Rn = Fnv(N o X)·Ab·planos. Lo usan `ShearTab` y `ClipAngle`.
- Tabla J3.2 en ksi convertidos exactamente: A307 27 ksi (antes 24), A490-N 68 ksi (antes 66 en `bolts` y 457 MPa en `catalog`), y valores «-X» para todos los grados.
- `bolts.Bolt.ec3_tension_strength`: usaba el área bruta en lugar del área resistente As (+28 % en M20, del lado inseguro). `ec3_shear_strength` aproximaba As con 0,75·Ab (M20 8.8: 90,5 → 94,1 kN). Nuevo `bolt_tensile_stress_area` (catálogo o ISO 898-1).
- `bolts.Bolt.ec3_bearing_strength`: los cocientes αd y k1 usaban d en vez del diámetro del agujero d0; ahora d0 = d + holgura normal de EN 1090-2 Tabla 11 (1/2/3 mm), con `d0=` opcional.
- `block_shear.block_shear_strength(code="EC3")`: usaba el área bruta a cortante Agv en lugar de Anv (EN 1993-1-8 Ec. 3.9); ahora coincide con `block_shear_multi`.
- `panel_zone`: la API funcional no reducía la capacidad con axil alto cuando no se considera la deformación de la zona de panel (falta 1,4 − Pr/Pc por encima de 0,4·Pc, lado inseguro), y la clase `PanelZone` aplicaba el umbral 0,4 y 1,4 − Pr/Pc también cuando sí se considera (debe ser 0,75 y 1,9 − 1,2·Pr/Pc; hasta un 36 % de capacidad perdida).
- `end_plate.EndPlate._Yp`: h1 se medía desde el eje del ala comprimida restando solo tf/2; la fila interior está a pfi de la cara interior del ala traccionada, h1 = d − 1,5·tf − pfi.
- `EndPlate`: el perno interno usaba rosca excluida en la interacción J3.7 mientras el cortante usaba rosca incluida; ahora ambos con rosca en el plano (hipótesis conservadora).
- `services.bolts`: en EC3 αv dependía de la condición de rosca en lugar del grado y el área era siempre la bruta; el grupo con momento multiplicaba la capacidad por 0,6 sin método. Ahora αv por grado, As con rosca, y método elástico para una línea de pernos (fuerza del perno extremo √((V/n)² + (M·y/Σy²)²)).
- `services.end_plate`: calculaba 4·(Fy·bp·tp²/4)·(db/2), dimensionalmente inconsistente (≈ 6 kN·m para una chapa de 20 mm); delega en `EndPlate.plate_flexure_check`.
- `services.base_plate`: el espesor ignoraba n y λn' y el 0,9, y el DCR ignoraba el espesor dado; delega en `BasePlate` y el DCR incluye tp,req/tp.
- `prying`: nuevo `Fu_MPa` opcional; el Manual AISC usa Fu en t_c desde la 13.ª edición (sin él se mantiene Fy, conservador).
- Centro instantáneo (`BoltGroupICR` con carga oblicua, `WeldGroupICR` con excentricidad): importaban scipy sin capturar el error; ahora lanzan `DependencyError` con la instrucción de instalación. El CI instala el extra `numeric`.
- `ideastatica_iom`: el docstring decía que generaba IOM válido para IDEA StatiCa; IDEA StatiCa 21.1 rechaza ese XML (raíz real `OpenModel`, versión 2). Ahora lo declara.
- Resúmenes OpenAPI que prometían otra norma o método (soldadura «EN 1993-1-8 §4.5.3» que era AISC J2.4, chapa frontal «SCI P398», empalme «EN 1993-1-8», grupo de pernos «centro instantáneo»).
- `import steeljoints` fallaba sin pydantic (lo importa `steelnode_schemas` desde `__init__`) y pydantic solo venía con el extra `api`: ahora es dependencia.
- Versión única 1.2.0 en `pyproject.toml`, `steeljoints.__version__` y la API (antes 1.0.0 / 1.1.0 / 0.1.0).
- `welds.WeldGroup.utilization`: evaluaba la tensión en el centro de cada cordón con el coseno director equivocado. Un cordón único centrado ignoraba el momento (20 kN·m sobre un cordón de 200 mm no cambiaba la utilización) y dos cordones horizontales de 200 mm daban 386,7 N/mm² en vez de 420,7. Ahora evalúa los extremos y coincide con `WeldGroupElastic`.
- `welds.FilletWeld.ec3_strength` se presentaba como método direccional (§4.5.3.2) y es el simplificado (§4.5.3.3); el cálculo no cambia.
- `codes.ec3_1_8.fillet_weld_Rd_directional` y `fillet_weld_Rd_simplified` tomaban βw = 0,85 para un grado desconocido (+17,6 % en S460 mal escrito); ahora usan `beta_w()`, que acepta «S355JR» y rechaza lo que no está en la Tabla 4.1, igual que `FilletWeld.ec3_strength`.
- `WeldGroupICR` con carga centrada sumaba cada elemento a su propia deformación última. Con cordones longitudinales y transversales eso ignora la compatibilidad (el transversal rompe antes): una C de 200 × 100 mm con cordón de 8 mm daba 819 kN en vez de 762 kN (AISC 360-22 §J2.4(b)(2) da 770 kN). Ahora todos los elementos van a la deformación del menos dúctil.
- `FilletWeld.ec3_strength` usa `codes.ec3_1_8.beta_w`: acepta «S355J2» y sigue rechazando grados fuera de la Tabla 4.1.
- `ShearTab.plate_block_shear`: el área neta a tracción se medía hacia el borde soldado (ancho − distancia al borde); ahora va al borde libre, (Leh − dh/2)·t, como el Manual AISC Parte 10. Con la chapa por defecto de 75 mm apenas cambia; con 115 mm el área a tracción era 2,4 veces la real.
- `block_shear_multi` con `code="AU"`: AS 4100 §9.1.9 tiene la misma forma que AISC §J4.3, pero el módulo omitía el tope de fluencia 0,6·fy·Agv y el factor kbs (Ubs); ahora usa la misma expresión que AISC.
- `services.bolts.design_single_bolt`: el aplastamiento ignoraba `edge_distance_mm` y tomaba siempre 2,4·d·t·Fu, también en EC3. Un A325 de 3/4" a 30 mm del borde de una chapa de 10 mm daba 182,9 kN en vez de 94,5 kN. Ahora usa lc en AISC y αb·k1 con d0 en EC3.
- `services.wuf.design_wuf`: el SCWB dividía por Zb·Fyb nominal; AISC 341 §E3.4a pide el momento probable proyectado al eje del pilar, Mpr + Vpr·dc/2, como ya hacía `wuf_w.design_wuf_w`. Una W610 × 125 contra un pilar de 400 mm con Pu/Py = 0,29 daba 1,07 (cumple) y da 0,79 (no cumple).
- `integration.seismodyn_bridge.verify_connections_vs_demand`: las uniones sin demanda desaparecían del informe; ahora salen como NO_CALCULADO con la demanda en None. Una viga con geometría RBS no evaluable ya no aborta el informe: sale como REQUIERE_REVISION.
- `memos.rbs_aisc358`: el cortante en la rótula dividía M_pr [kN·m] por la luz en mm, así que el término sísmico salía 1000 veces menor (Vp 105 kN en vez de 471 kN y Mf 1185 en vez de 1321 kN·m en una W610 × 125); además usaba la luz libre en lugar de la distancia entre rótulas. Ahora coincide con `services.rbs`. El puente con seismodyn solo usaba M_pr y no estaba afectado.
- `ec3_fracture.Z_property_required`: la correspondencia con las clases de EN 10164 iba una clase por encima de la Tabla 3.2 de EN 1993-1-10 (pedía Z15 con cualquier Z_Ed positivo y Z35 desde 20). Ahora: sin requisito hasta 10, Z15 hasta 20, Z25 hasta 30 y Z35 por encima.
- `ec3_tension_members.bending_stress_at_anchorage` devolvía la tensión de flexión para una desviación de 1 rad sin decirlo (11 700 MPa con 200 kN en un cable de 35 mm). Nuevo parámetro `theta_rad` (por defecto 1,0, compatible) y documentación explícita.
- `catalog.standard_hole` sigue AISC 360-22 Tablas J3.3 y J3.3M: los tornillos métricos usan la tabla métrica (M24 → 27 mm, antes 25,6) y el de 1" lleva d + 1/8" (28,6 mm, antes 27,0). `oversized_hole` queda sin contrastar y lo dice su docstring.

### Añadido
- Casos de uso ejecutables en `examples/` con salida en `examples/output/`, y `tests/test_examples.py` que los ejecuta en CI.
- `tests/test_v120_corrections.py` con un oráculo por corrección.

### Límites documentados (sin cambio de código)
- `codes.aisc358.Yp_4E_unstiffened`: la expresión lleva términos que la forma habitual de 4E no tiene (parecen del caso 4ES) y da un Yp un 30–40 % mayor; no se ha podido contrastar con AISC 358 Tabla 6.2 y no se cambia. Afecta a `EndPlate` y al servicio de chapa frontal. Para 8ES se usa la misma expresión.
- `services.splice` (brazo fijo de 0,5 m, Fy fijo) y `services.clip_angle` (solo fluencia por cortante bruto) son provisionales; las clases `ClipAngle` y `splice_design` son las de cálculo. `splice_design.SpliceConnection` usa un brazo de 0,3 m «de demostración».
- `ec3_fracture.t_max_brittle_fracture` es un sustituto paramétrico ajustado a la Tabla 2.1 de EN 1993-1-10, no la tabla.
- `aci318_25_anchors`: exponentes de interacción (2 y 5/3) y multiplicador de arco para encepados según la interpretación del módulo; sin contrastar con el texto de ACI 318-25.
- `codes.nsr10_f2` usa los valores de AISC 360-10 y posteriores; NSR-10 se basa en AISC 360-05.
- Las etiquetas de ecuación de §J10.6 difieren entre la API funcional (J10-9…J10-12) y la memoria (J10-11/J10-12); la física es la misma.
- `ShearTab` no comprueba la flexión de la chapa ni la excentricidad de los pernos y descuenta agujeros de d + 2 mm.
- `codes.ec3_1_8.bolt_bearing_Rd` con `direction_inner=False` toma k1 = mín(2,8·e2/d0 − 1,7; 2,5) sin el término 1,4·p2/d0 − 1,7 que la Tabla 3.4 añade a los tornillos de borde cuando hay más de una fila, y su d0 por defecto es d (compatibilidad). `Bolt.ec3_bearing_strength` incluye los dos términos y usa d0 real.
- `groove_welds`: φ = 0,75 para la soldadura PJP también a tracción normal al eje (AISC da Ω = 1,88, es decir φ = 0,80) y φ = 0,90 para el cortante CJP (§J4.2 usa 1,00): conservador. FEXX de E70 = 485 MPa en ese módulo frente a 482,6 en el resto.
- `BasePlate`: el aplastamiento y el espesor usan Pu/(B·N) y no incluyen Mu (del lado inseguro con momento: +120 % de presión con e = 150 mm en el caso de uso), y `anchor_tension` usa un modelo lineal propio, mucho más conservador que Design Guide 1 §3.4. Con momento, usa el bloque rectangular de DG1.
- `memos.panel_zone` usa V = 0,8·ΣMf/d_b − Vc, con un 0,8 sin trazar a norma que su propio texto declara; queda por debajo de la demanda de `PanelZone`.
- `haunch_connection.design_haunch` es un modelo simplificado (ΔZ = bf·tf·(d + h/2)) sin contrastar, y su `Mn_kNm` ya incluye φ.
- `aci318_25_anchors.verify_deep_shear_aci318_25`: el multiplicador por efecto arco (hasta 2,5) es la interpretación del módulo, sin contrastar.
