"""Golden test para exportación tabular de esfuerzos de diseño a IDEA StatiCa (JSON y CSV).

Requisitos:
1. Contrato JSON con schema estructurado, metadata y listado de fuerzas (N, Vy, Vz, Mx, My, Mz) por barra/extremo/combinación.
2. Contrato CSV con encabezados de importación estándar y round-trip determinista.
"""
from __future__ import annotations

import json
import pytest
from steeljoints.integration.idea_statica_export import (
    IdeaStaticaForceRow,
    export_idea_statica_csv,
    export_idea_statica_json,
    parse_idea_statica_csv,
)


def test_golden_idea_statica_export_json_and_csv():
    """GOLDEN. Valida exportación de tabla de esfuerzos de diseño por combinación a IDEA StatiCa."""
    forces = [
        IdeaStaticaForceRow(
            member_id="B1",
            position="Begin",
            combo_name="1.2D + 1.6L",
            N_kN=-150.500,
            Vy_kN=12.300,
            Vz_kN=95.400,
            Mx_kNm=3.200,
            My_kNm=8.500,
            Mz_kNm=-180.250,
        ),
        IdeaStaticaForceRow(
            member_id="B1",
            position="End",
            combo_name="1.2D + 1.6L",
            N_kN=-148.200,
            Vy_kN=-12.300,
            Vz_kN=-88.700,
            Mx_kNm=-3.200,
            My_kNm=-8.500,
            Mz_kNm=165.100,
        ),
    ]

    # 1. Validación de contrato JSON
    json_str = export_idea_statica_json(forces)
    data = json.loads(json_str)
    assert data["software_target"] == "IDEA StatiCa Connection"
    assert data["count"] == 2
    assert len(data["member_forces"]) == 2
    assert data["member_forces"][0]["member_id"] == "B1"
    assert data["member_forces"][0]["Mz_kNm"] == -180.250

    # 2. Validación de contrato CSV y Round-Trip
    csv_str = export_idea_statica_csv(forces)
    assert "Member,Position,LoadingCase,N [kN],Vy [kN],Vz [kN],Mx [kNm],My [kNm],Mz [kNm]" in csv_str
    parsed = parse_idea_statica_csv(csv_str)
    assert len(parsed) == 2
    assert parsed[0].member_id == "B1"
    assert parsed[0].position == "Begin"
    assert parsed[0].N_kN == -150.500
    assert parsed[0].Vz_kN == 95.400
    assert parsed[0].Mz_kNm == -180.250
