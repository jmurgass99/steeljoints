"""IDEA StatiCa Open Model (IOM) & Dlubal RFEM 6 gRPC Bridge — SteelJoints.

ESTADO REAL (1.2.0): estructura PROPIA con nombres inspirados en el IDEA Open Model, no el formato
que importa IDEA StatiCa. Probado contra IDEA StatiCa 21.1: el ``XmlSerializer`` de
``IdeaRS.OpenModel.OpenModel`` RECHAZA el XML de ``export_iom_xml`` (su raíz real es ``OpenModel`` con
``Version`` 2, unidades SI base y tipos ``xsi:type``; aquí la raíz es ``IdeaOpenModel``). El diccionario
de ``export_iom_dict`` y la petición de ``build_rfem6_grpc_payload`` tampoco se han validado contra
IDEA ni contra Dlubal RFEM 6: son contenedores de datos (nodos, barras, secciones, esfuerzos por
caso) para construir el fichero real fuera de aquí.

Contenido:
  1. Nodos, barras conectadas, secciones en I, un acero y esfuerzos de extremo (N, Vy, Vz, Mx, My, Mz)
     por caso de carga, serializados a dict y a XML.
  2. Un diccionario con la forma de una petición «create_model» para RFEM 6 (no hace ninguna llamada).

All public dataclasses declare ``units`` explicitly and avoid unit-suffixed field names.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Sequence
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class IomNode:
    """Node in IDEA Open Model (IOM). Units: coordinates in meters."""

    id: int
    name: str
    x: float
    y: float
    z: float
    units: str = "SI_m"


@dataclass(frozen=True)
class IomCrossSection:
    """Cross-section definition in IDEA Open Model (IOM)."""

    id: int
    name: str
    material_id: int
    shape_type: str = "I_Section"
    depth: float = 0.30
    width: float = 0.15
    web_thickness: float = 0.007
    flange_thickness: float = 0.010
    units: str = "SI_m"


@dataclass(frozen=True)
class IomMember:
    """Connected member in IDEA Open Model (IOM)."""

    id: int
    name: str
    start_node_id: int
    end_node_id: int
    cross_section_id: int
    is_continuous: bool = False
    units: str = "SI_m"


@dataclass(frozen=True)
class IomMemberForces:
    """6-DOF member end internal forces in IDEA Open Model (IOM).

    Units: axial force N in kN (+ = tension), shear Vy, Vz in kN,
    torsion Mx in kNm, bending My, Mz in kNm.
    """

    member_id: int
    position: str  # "Begin" or "End"
    n: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0
    units: str = "SI_kN_kNm"


@dataclass(frozen=True)
class IomLoadCase:
    """Load case containing member end force vectors in IDEA Open Model (IOM)."""

    id: int
    name: str
    forces: list[IomMemberForces] = field(default_factory=list)


@dataclass(frozen=True)
class IdeaOpenModelConnection:
    """Complete connection assembly in IDEA Open Model (IOM) format."""

    connection_id: int
    name: str
    joint_node_id: int
    design_code: str = "ECEN"  # "ECEN" (Eurocode) or "AISC"
    steel_grade: str = "S355"
    fy: float = 355.0  # MPa
    fu: float = 510.0  # MPa
    nodes: list[IomNode] = field(default_factory=list)
    cross_sections: list[IomCrossSection] = field(default_factory=list)
    members: list[IomMember] = field(default_factory=list)
    load_cases: list[IomLoadCase] = field(default_factory=list)
    units: str = "SI_m_kN_kNm_MPa"


def export_iom_dict(model: IdeaOpenModelConnection) -> dict[str, Any]:
    """Serialize an ``IdeaOpenModelConnection`` into standard IOM JSON format."""
    return {
        "OpenModel": {
            "Version": "24.1.0",
            "ProjectData": {
                "Name": model.name,
                "DesignCode": model.design_code,
            },
            "Point3D": [
                {"Id": nd.id, "Name": nd.name, "X": nd.x, "Y": nd.y, "Z": nd.z}
                for nd in model.nodes
            ],
            "MatSteel": [
                {
                    "Id": 1,
                    "Name": model.steel_grade,
                    "E": 2.1e11,
                    "G": 8.07e10,
                    "UnitMass": 7850.0,
                    "fy": model.fy * 1.0e6,
                    "fu": model.fu * 1.0e6,
                }
            ],
            "CrossSection": [
                {
                    "Id": cs.id,
                    "Name": cs.name,
                    "Material": {"Id": cs.material_id},
                    "Type": cs.shape_type,
                    "Height": cs.depth,
                    "Width": cs.width,
                    "WebThickness": cs.web_thickness,
                    "FlangeThickness": cs.flange_thickness,
                }
                for cs in model.cross_sections
            ],
            "Element1D": [
                {
                    "Id": m.id,
                    "Name": m.name,
                    "CrossSection": {"Id": m.cross_section_id},
                    "Segment": {
                        "StartPoint": {"Id": m.start_node_id},
                        "EndPoint": {"Id": m.end_node_id},
                    },
                }
                for m in model.members
            ],
            "ConnectionData": [
                {
                    "Id": model.connection_id,
                    "Name": model.name,
                    "PointOnModel": {"Id": model.joint_node_id},
                    "ConnectedMembers": [{"Id": m.id} for m in model.members],
                }
            ],
        },
        "OpenModelResult": {
            "ConnectionResults": [
                {
                    "ConnectionId": model.connection_id,
                    "LoadCases": [
                        {
                            "Id": lc.id,
                            "Name": lc.name,
                            "MemberForces": [
                                {
                                    "MemberId": f.member_id,
                                    "Position": f.position,
                                    "N": f.n * 1.0e3,
                                    "Vy": f.vy * 1.0e3,
                                    "Vz": f.vz * 1.0e3,
                                    "Mx": f.mx * 1.0e3,
                                    "My": f.my * 1.0e3,
                                    "Mz": f.mz * 1.0e3,
                                }
                                for f in lc.forces
                            ],
                        }
                        for lc in model.load_cases
                    ],
                }
            ]
        },
    }


def export_iom_xml(model: IdeaOpenModelConnection) -> str:
    """Serialize an ``IdeaOpenModelConnection`` into standard IOM XML string."""
    root = ET.Element("IdeaOpenModel", attrib={"Version": "24.1.0", "Code": model.design_code})
    proj = ET.SubElement(root, "ProjectData")
    ET.SubElement(proj, "Name").text = model.name

    pts = ET.SubElement(root, "Points")
    for nd in model.nodes:
        pt = ET.SubElement(pts, "Point", attrib={"Id": str(nd.id), "Name": nd.name})
        ET.SubElement(pt, "X").text = str(nd.x)
        ET.SubElement(pt, "Y").text = str(nd.y)
        ET.SubElement(pt, "Z").text = str(nd.z)

    members_el = ET.SubElement(root, "Members")
    for m in model.members:
        mb = ET.SubElement(members_el, "Member", attrib={"Id": str(m.id), "Name": m.name})
        ET.SubElement(mb, "CrossSectionId").text = str(m.cross_section_id)
        ET.SubElement(mb, "StartNodeId").text = str(m.start_node_id)
        ET.SubElement(mb, "EndNodeId").text = str(m.end_node_id)

    conn_el = ET.SubElement(root, "Connection", attrib={"Id": str(model.connection_id)})
    ET.SubElement(conn_el, "JointNodeId").text = str(model.joint_node_id)

    lcs_el = ET.SubElement(root, "LoadCases")
    for lc in model.load_cases:
        lc_tag = ET.SubElement(lcs_el, "LoadCase", attrib={"Id": str(lc.id), "Name": lc.name})
        for f in lc.forces:
            f_tag = ET.SubElement(
                lc_tag,
                "Force",
                attrib={
                    "MemberId": str(f.member_id),
                    "Position": f.position,
                    "N": str(f.n),
                    "Vy": str(f.vy),
                    "Vz": str(f.vz),
                    "Mx": str(f.mx),
                    "My": str(f.my),
                    "Mz": str(f.mz),
                },
            )

    return ET.tostring(root, encoding="utf-8").decode("utf-8")


@dataclass(frozen=True)
class Rfem6GrpcRequest:
    """gRPC message specification for Dlubal RFEM 6 (dlubal.api)."""

    model_name: str
    nodes_payload: list[dict[str, Any]]
    members_payload: list[dict[str, Any]]
    materials_payload: list[dict[str, Any]]
    rpc_method: str = "create_model"
    status: str = "CALCULADO"


def build_rfem6_grpc_payload(model: IdeaOpenModelConnection) -> Rfem6GrpcRequest:
    """Build a Dlubal RFEM 6 gRPC service request dictionary from joint member geometry."""
    nodes = [{"no": nd.id, "coordinates": [nd.x, nd.y, nd.z]} for nd in model.nodes]
    members = [
        {
            "no": m.id,
            "node_start_no": m.start_node_id,
            "node_end_no": m.end_node_id,
            "section_distribution_type": "STANDARD",
        }
        for m in model.members
    ]
    materials = [{"no": 1, "name": model.steel_grade}]

    return Rfem6GrpcRequest(
        model_name=model.name,
        nodes_payload=nodes,
        members_payload=members,
        materials_payload=materials,
        rpc_method="create_model",
        status="CALCULADO",
    )


__all__ = [
    "IdeaOpenModelConnection",
    "IomCrossSection",
    "IomLoadCase",
    "IomMember",
    "IomMemberForces",
    "IomNode",
    "Rfem6GrpcRequest",
    "build_rfem6_grpc_payload",
    "export_iom_dict",
    "export_iom_xml",
]
