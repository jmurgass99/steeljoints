"""Bridge bidireccional con FastSAP / ETABS.

Extrae fuerzas de viga-columna de un modelo SAP/ETABS conectado y las
pasa a los services para diseno de conexion.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConnectionForces:
    """Fuerzas extraidas en un nudo viga-columna para diseno de conexion."""
    joint_name: str
    Vu_kN: float
    Mu_kNm: float
    Pu_kN: float = 0.0
    notes: list[str] | None = None


def extract_beam_column_forces(
    sap_client: Any, joint_name: str,
    *, beam_name: str | None = None,
    case_name: str = "ULS",
) -> ConnectionForces:
    """Extrae las fuerzas maximas de la viga conectada al joint para diseno."""
    if sap_client is None:
        raise ValueError("Se requiere sap_client conectado")
    sap_model = sap_client.SapModel
    try:
        sap_model.Results.Setup.DeselectAllCasesAndCombosForOutput()
        sap_model.Results.Setup.SetCaseSelectedForOutput(case_name)
    except Exception as exc:
        return ConnectionForces(
            joint_name=joint_name, Vu_kN=0.0, Mu_kNm=0.0,
            notes=[f"Setup de output fallo: {exc}"],
        )

    if beam_name is None:
        return ConnectionForces(
            joint_name=joint_name, Vu_kN=0.0, Mu_kNm=0.0,
            notes=["beam_name no proporcionado - placeholder"],
        )

    try:
        ret = sap_model.Results.FrameForce(beam_name, 0)
        if isinstance(ret, tuple) and len(ret) > 14:
            V_arr = ret[10] if len(ret) > 10 else [0.0]
            M_arr = ret[14] if len(ret) > 14 else [0.0]
            V = max(abs(v) for v in V_arr) if V_arr else 0.0
            M = max(abs(m) for m in M_arr) if M_arr else 0.0
            return ConnectionForces(
                joint_name=joint_name,
                Vu_kN=V / 1e3, Mu_kNm=M / 1e3,
                notes=[f"Extraido de {beam_name}@{case_name}"],
            )
    except Exception as exc:
        return ConnectionForces(
            joint_name=joint_name, Vu_kN=0.0, Mu_kNm=0.0,
            notes=[f"FrameForce fallo: {exc}"],
        )
    return ConnectionForces(joint_name=joint_name, Vu_kN=0.0, Mu_kNm=0.0,
                            notes=["sin datos"])


def design_panel_zone_from_sap(
    sap_client: Any, joint_name: str, beam_name: str,
    column_section_dims: dict,
    *, case_name: str = "ULS",
):
    """Pipeline completo: extrae fuerzas + disena panel zone."""
    from ..services.panel_zone import (
        PanelZoneServiceInput, design_panel_zone,
    )
    forces = extract_beam_column_forces(
        sap_client, joint_name, beam_name=beam_name, case_name=case_name,
    )
    db = column_section_dims.get("d_b_mm", 400)
    V_panel = forces.Mu_kNm / (db / 1000) if db > 0 else forces.Vu_kN
    inp = PanelZoneServiceInput(
        d_c_mm=column_section_dims["d_c_mm"],
        t_w_mm=column_section_dims["t_w_mm"],
        d_b_mm=db,
        b_f_c_mm=column_section_dims["b_f_c_mm"],
        t_f_c_mm=column_section_dims["t_f_c_mm"],
        Fy_c_MPa=column_section_dims.get("Fy_c_MPa", 345.0),
        Pu_kN=forces.Pu_kN,
        Py_kN=column_section_dims.get("Py_kN", 5000.0),
        V_demand_kN=V_panel,
    )
    return design_panel_zone(inp), forces
