"""Golden test para dimensionado de conexión de chapa de testa (end-plate) desde esfuerzos dados (N, V, M).

Requisito de diseño:
La API debe recibir directamente los esfuerzos seccionales en el extremo (N, V, M) como entrada
y devolver la comprobación completa de la unión según AISC 360/358.
"""
from __future__ import annotations

import pytest
from steeljoints.end_plate import design_end_plate_from_member_forces


def test_golden_end_plate_design_from_applied_forces():
    """GOLDEN. Comprobación de end-plate a partir de terna de esfuerzos (N, V, M)."""
    N_input = 50.0   # kN tracción
    V_input = 80.0   # kN cortante
    M_input = 120.0  # kN·m flector

    # Perfil W16x40: db = 407 mm, tf = 12.8 mm, bf = 178 mm
    res = design_end_plate_from_member_forces(
        N_kN=N_input,
        V_kN=V_input,
        M_kNm=M_input,
        beam_depth_mm=407.0,
        beam_tf_mm=12.8,
        beam_bf_mm=178.0,
        bolt_grade="A325",
        plate_thickness_mm=20.0,
        plate_Fy_MPa=345.0,
        n_bolt_rows=2,
    )

    # 1. Los esfuerzos se preservan y reportan como entrada
    assert res["applied_forces"]["N_kN"] == 50.0
    assert res["applied_forces"]["V_kN"] == 80.0
    assert res["applied_forces"]["M_kNm"] == 120.0
    # M_eff = 120 + 50 * (407 - 12.8)/2 * 1e-3 = 120 + 50 * 0.1971 = 129.855 kNm
    assert res["applied_forces"]["M_effective_kNm"] == pytest.approx(129.855, rel=1e-3)

    # 2. Comprobaciones de pernos, chapa y soldadura presentes
    assert "checks" in res
    assert len(res["checks"]) == 4
    check_names = [c["check"] for c in res["checks"]]
    assert any("Bolt tension" in name for name in check_names)
    assert any("Bolt shear" in name for name in check_names)
    assert any("End plate flexure" in name for name in check_names)
    assert any("Welds" in name for name in check_names)

    # 3. Gobernancia y resultado
    assert "governing_utilization" in res
    assert res["governing_utilization"] > 0.0
