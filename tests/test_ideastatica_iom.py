"""Tests for IDEA StatiCa Open Model (IOM) and Dlubal RFEM 6 gRPC bridge."""
from __future__ import annotations

import json
import pytest

from steelconnectionjm.ideastatica_iom import (
    IdeaOpenModelConnection,
    IomCrossSection,
    IomLoadCase,
    IomMember,
    IomMemberForces,
    IomNode,
    build_rfem6_grpc_payload,
    export_iom_dict,
    export_iom_xml,
)


def _sample_beam_column_joint() -> IdeaOpenModelConnection:
    n1 = IomNode(id=1, name="ColumnBottom", x=0.0, y=0.0, z=0.0)
    n2 = IomNode(id=2, name="JointNode", x=0.0, y=0.0, z=3.5)
    n3 = IomNode(id=3, name="ColumnTop", x=0.0, y=0.0, z=7.0)
    n4 = IomNode(id=4, name="BeamRight", x=6.0, y=0.0, z=3.5)

    cs_col = IomCrossSection(id=1, name="HEB300", material_id=1, depth=0.30, width=0.30)
    cs_beam = IomCrossSection(id=2, name="IPE400", material_id=1, depth=0.40, width=0.18)

    m1 = IomMember(id=1, name="ColumnLow", start_node_id=1, end_node_id=2, cross_section_id=1)
    m2 = IomMember(id=2, name="ColumnHigh", start_node_id=2, end_node_id=3, cross_section_id=1)
    m3 = IomMember(id=3, name="Beam", start_node_id=2, end_node_id=4, cross_section_id=2)

    f_beam = IomMemberForces(member_id=3, position="Begin", n=15.0, vz=-120.0, my=185.0)
    lc1 = IomLoadCase(id=1, name="ULS01", forces=[f_beam])

    return IdeaOpenModelConnection(
        connection_id=101,
        name="Node2_MomentConnection",
        joint_node_id=2,
        design_code="ECEN",
        steel_grade="S355",
        nodes=[n1, n2, n3, n4],
        cross_sections=[cs_col, cs_beam],
        members=[m1, m2, m3],
        load_cases=[lc1],
    )


def test_export_idea_open_model_dict() -> None:
    model = _sample_beam_column_joint()
    data = export_iom_dict(model)

    assert "OpenModel" in data
    assert "OpenModelResult" in data
    assert data["OpenModel"]["ProjectData"]["DesignCode"] == "ECEN"
    assert len(data["OpenModel"]["Point3D"]) == 4
    assert len(data["OpenModel"]["Element1D"]) == 3
    # Check force units scaled to SI (N and Nm) in IOM
    res = data["OpenModelResult"]["ConnectionResults"][0]
    forces = res["LoadCases"][0]["MemberForces"][0]
    assert forces["Vz"] == pytest.approx(-120_000.0)
    assert forces["My"] == pytest.approx(185_000.0)


def test_export_idea_open_model_xml() -> None:
    model = _sample_beam_column_joint()
    xml_str = export_iom_xml(model)

    assert "<IdeaOpenModel" in xml_str
    assert 'Code="ECEN"' in xml_str
    assert 'Name="JointNode"' in xml_str
    assert '<JointNodeId>2</JointNodeId>' in xml_str
    assert 'My="185.0"' in xml_str


def test_build_rfem6_grpc_payload() -> None:
    model = _sample_beam_column_joint()
    req = build_rfem6_grpc_payload(model)

    assert req.status == "CALCULADO"
    assert req.model_name == "Node2_MomentConnection"
    assert len(req.nodes_payload) == 4
    assert len(req.members_payload) == 3
    assert req.materials_payload[0]["name"] == "S355"
