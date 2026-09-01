"""Exportador tabular de esfuerzos para IDEA StatiCa Connection (Open Model / Table Contract).

Genera contratos tabulares en formato JSON y CSV estándar requeridos para importar
esfuerzos seccionales en IDEA StatiCa por barra, posición de extremo (Begin / End) y combinación de carga.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass
from typing import Any, Sequence


@dataclass(frozen=True)
class IdeaStaticaForceRow:
    """Fila de esfuerzos seccionales para intercambio con IDEA StatiCa."""
    member_id: str
    position: str        # 'Begin' o 'End' o '0.00' / 'L'
    combo_name: str      # e.g. '1.2D + 1.6L', '1.0D + 1.0L + 1.0Ex'
    N_kN: float          # Esfuerzo axial (+ tracción, - compresión)
    Vy_kN: float         # Cortante en eje local y
    Vz_kN: float         # Cortante en eje local z (principal)
    Mx_kNm: float        # Torsor
    My_kNm: float        # Momento flector eje débil
    Mz_kNm: float        # Momento flector eje fuerte

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def export_idea_statica_json(forces: Sequence[IdeaStaticaForceRow]) -> str:
    """Exporta lista de esfuerzos seccionales a contrato JSON estructurado para IDEA StatiCa."""
    payload = {
        "schema_version": "1.0",
        "software_target": "IDEA StatiCa Connection",
        "units": {
            "forces": "kN",
            "moments": "kNm",
        },
        "count": len(forces),
        "member_forces": [f.to_dict() for f in forces],
    }
    return json.dumps(payload, indent=2)


def export_idea_statica_csv(forces: Sequence[IdeaStaticaForceRow]) -> str:
    """Exporta lista de esfuerzos seccionales a formato CSV tabular compatible con IDEA StatiCa Excel/CSV import."""
    output = io.StringIO()
    fieldnames = [
        "Member",
        "Position",
        "LoadingCase",
        "N [kN]",
        "Vy [kN]",
        "Vz [kN]",
        "Mx [kNm]",
        "My [kNm]",
        "Mz [kNm]",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()

    for f in forces:
        writer.writerow({
            "Member": f.member_id,
            "Position": f.position,
            "LoadingCase": f.combo_name,
            "N [kN]": f"{f.N_kN:.3f}",
            "Vy [kN]": f"{f.Vy_kN:.3f}",
            "Vz [kN]": f"{f.Vz_kN:.3f}",
            "Mx [kNm]": f"{f.Mx_kNm:.3f}",
            "My [kNm]": f"{f.My_kNm:.3f}",
            "Mz [kNm]": f"{f.Mz_kNm:.3f}",
        })

    return output.getvalue()


def parse_idea_statica_csv(csv_content: str) -> list[IdeaStaticaForceRow]:
    """Parsea contenido CSV generado para verificar la integridad bidireccional del contrato."""
    reader = csv.DictReader(io.StringIO(csv_content))
    rows: list[IdeaStaticaForceRow] = []
    for r in reader:
        rows.append(
            IdeaStaticaForceRow(
                member_id=r["Member"],
                position=r["Position"],
                combo_name=r["LoadingCase"],
                N_kN=float(r["N [kN]"]),
                Vy_kN=float(r["Vy [kN]"]),
                Vz_kN=float(r["Vz [kN]"]),
                Mx_kNm=float(r["Mx [kNm]"]),
                My_kNm=float(r["My [kNm]"]),
                Mz_kNm=float(r["Mz [kNm]"]),
            )
        )
    return rows


__all__ = [
    "IdeaStaticaForceRow",
    "export_idea_statica_json",
    "export_idea_statica_csv",
    "parse_idea_statica_csv",
]
