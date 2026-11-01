"""Tests para ConnectionGridMapping en SteelJoints."""
from steeljoints.geometry_mapping import SemanticBoltRow, build_connection_grid_mesh


def test_connection_grid_mapping_refinement():
    rows_short = [
        SemanticBoltRow("ROW-1", y_coord_mm=120.0, num_bolts=2),
        SemanticBoltRow("ROW-2", y_coord_mm=-60.0, num_bolts=2),
    ]
    rows_full = [
        SemanticBoltRow("ROW-1", y_coord_mm=180.0, num_bolts=2),
        SemanticBoltRow("ROW-2", y_coord_mm=100.0, num_bolts=2),
        SemanticBoltRow("ROW-3", y_coord_mm=-40.0, num_bolts=2),
        SemanticBoltRow("ROW-4", y_coord_mm=-120.0, num_bolts=2),
    ]

    bolts_4, map_4, sum_4 = build_connection_grid_mesh(rows=rows_short, shear_V_kN=120.0, moment_M_kNm=50.0)
    bolts_8, map_8, sum_8 = build_connection_grid_mesh(rows=rows_full, shear_V_kN=120.0, moment_M_kNm=50.0)

    assert len(bolts_4) == 4
    assert len(bolts_8) == 8
    assert len(map_8.row_to_bolts["ROW-1"]) == 2
    assert sum_4["max_V_per_bolt_kN"] > sum_8["max_V_per_bolt_kN"]
    assert sum_8["max_T_per_bolt_kN"] > 10.0
