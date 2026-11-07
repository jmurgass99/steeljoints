# Limitaciones conocidas de steeljoints

Lo que el paquete no hace o hace de forma simplificada.

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
