"""Exportar una unión viga-pilar hacia IDEA StatiCa: modelo IOM (nodos, secciones, barras y esfuerzos por combinación) en diccionario y XML, tabla de esfuerzos en CSV/JSON con lectura de vuelta, y la carga útil para Dlubal RFEM 6. Dice qué se ha comprobado y qué no.

`ideastatica_iom.export_iom_dict / export_iom_xml / build_rfem6_grpc_payload` y `integration.idea_statica_export`
(`export_idea_statica_csv`, `export_idea_statica_json`, `parse_idea_statica_csv`). El XML NO es importable en IDEA StatiCa 21.1:
el formato real tiene raíz `OpenModel` (versión 2) y el programa lo rechaza; la carga útil de RFEM no se ha probado contra RFEM.

Ejecutar:  python examples/ideastatica_iom_xml_dict_and_member_forces_csv_json_roundtrip_declared_not_importable.py
"""
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

from steeljoints.ideastatica_iom import (
    IdeaOpenModelConnection, IomCrossSection, IomLoadCase, IomMember, IomMemberForces, IomNode,
    build_rfem6_grpc_payload, export_iom_dict, export_iom_xml,
)
from steeljoints.integration.idea_statica_export import (
    IdeaStaticaForceRow, export_idea_statica_csv, export_idea_statica_json, parse_idea_statica_csv,
)

OUT = Path(os.environ.get("JM_EXAMPLES_OUT_DIR", Path(__file__).resolve().parent / "out"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    model = IdeaOpenModelConnection(
        connection_id=1, name="Nudo B3 viga-pilar", joint_node_id=2, design_code="ECEN", steel_grade="S355",
        nodes=[IomNode(1, "N1", 0.0, 0.0, 0.0), IomNode(2, "N2", 0.0, 0.0, 3.5), IomNode(3, "N3", 6.0, 0.0, 3.5), IomNode(4, "N4", 0.0, 0.0, 7.0)],
        cross_sections=[IomCrossSection(1, "HEB300", 1, depth=0.30, width=0.30, web_thickness=0.011, flange_thickness=0.019),
                        IomCrossSection(2, "IPE400", 1, depth=0.40, width=0.18, web_thickness=0.0086, flange_thickness=0.0135)],
        members=[IomMember(1, "Pilar inf.", 1, 2, 1, is_continuous=True), IomMember(2, "Pilar sup.", 2, 4, 1, is_continuous=True), IomMember(3, "Viga", 2, 3, 2)],
        load_cases=[IomLoadCase(1, "ELU 1.35G+1.5Q", [IomMemberForces(3, "Begin", n=-12.0, vz=-185.0, my=-210.0),
                                                       IomMemberForces(1, "End", n=-950.0, vy=4.0, my=60.0)])],
    )
    d = export_iom_dict(model)
    print(f"IOM en diccionario: claves {sorted(d)}")
    print(f"  {len(model.nodes)} nodos, {len(model.members)} barras, {sum(len(lc.forces) for lc in model.load_cases)} vectores de esfuerzos; unidades {model.units}")
    xml = export_iom_xml(model)
    (OUT / "nudo_B3.iom.xml").write_text(xml, encoding="utf-8")
    root = ET.fromstring(xml)
    print(f"  XML de {len(xml)} caracteres; raíz <{root.tag}> con hijos {[c.tag for c in root]}")
    rows = [IdeaStaticaForceRow("Viga", "Begin", "1.35G+1.5Q", -12.0, 0.0, -185.0, 0.0, -210.0, 0.0),
            IdeaStaticaForceRow("Viga", "Begin", "G+0.3Q+Ex", 35.0, 2.0, -95.0, 1.5, -340.0, 12.0),
            IdeaStaticaForceRow("Pilar inf.", "End", "1.35G+1.5Q", -950.0, 4.0, 0.0, 0.0, 60.0, 0.0)]
    csv_text = export_idea_statica_csv(rows)
    (OUT / "nudo_B3_esfuerzos.csv").write_text(csv_text, encoding="utf-8")
    back = parse_idea_statica_csv(csv_text)
    print(f"\nCSV de esfuerzos ({len(csv_text.splitlines())} líneas):")
    for line in csv_text.splitlines()[:3]:
        print(f"  {line}")
    print(f"  Lectura de vuelta: {len(back)} filas, idénticas a las originales: {[r.to_dict() for r in back] == [r.to_dict() for r in rows]}")
    js = json.loads(export_idea_statica_json(rows))
    print(f"JSON: claves {sorted(js) if isinstance(js, dict) else type(js).__name__}")
    rf = build_rfem6_grpc_payload(model)
    print(f"\nRFEM 6: método {rf.rpc_method}, {len(rf.nodes_payload)} nodos, {len(rf.members_payload)} barras, {len(rf.materials_payload)} materiales; primer nodo {rf.nodes_payload[0]}")
    print(f"\nFicheros en {OUT.name}/: nudo_B3.iom.xml, nudo_B3_esfuerzos.csv")
    print("El CSV y el JSON sirven para pegar esfuerzos en IDEA StatiCa a mano o con su API. El XML IOM de este módulo NO lo importa IDEA StatiCa 21.1 "
          "(el formato real es `OpenModel` versión 2), y la carga útil de RFEM 6 no se ha enviado nunca a un RFEM real: trátalos como borradores de intercambio.")


if __name__ == "__main__":
    main()
