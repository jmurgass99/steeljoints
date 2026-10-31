"""
tests/test_improvements.py — Tests para las dos mejoras:
  1. dxf_detail.end_plate_dxf (smoke + DXF válido)
  2. catalog.get_electrode_FEXX parser laxo
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from steeljoints import catalog
from steeljoints.end_plate import EndPlate
from steeljoints import dxf_detail


# ---------------------------------------------------------------------------
# Mejora 1 — end_plate_dxf
# ---------------------------------------------------------------------------
ezdxf = pytest.importorskip("ezdxf")


@pytest.mark.parametrize("n_rows", [2, 4])
def test_end_plate_dxf_smoke(n_rows):
    """Genera el DXF de una conexión end-plate y verifica que es legible."""
    ep = EndPlate(
        Mu=150.0, Vu=80.0,
        beam_depth=460.0, beam_tf=14.0, beam_bf=190.0,
        bolt_size="1", bolt_grade="A490",
        plate_thickness=25.0,
        n_bolt_rows=n_rows,
        electrode="E70XX",
    )
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, f"endplate_{n_rows}.dxf")
        path = dxf_detail.end_plate_dxf(ep, out)
        assert path == out
        assert os.path.exists(out)
        assert os.path.getsize(out) > 1000   # archivo no vacío
        # Lectura DXF válida
        doc = ezdxf.readfile(out)
        # Capas esperadas
        layers = {ly.dxf.name for ly in doc.layers}
        for required in ("STEEL", "BOLTS", "WELDS", "DIM", "TEXT", "TABLE"):
            assert required in layers, f"Falta capa {required}"
        # Entidades dibujadas
        msp = doc.modelspace()
        assert len(list(msp)) > 20    # al menos lineas+circulos+textos


# ---------------------------------------------------------------------------
# Mejora 2 — get_electrode_FEXX parser laxo
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("inp, expected_MPa", [
    ("E70XX", 482.6),         # canónico
    ("E70",   482.6),         # sin XX
    ("E80",   551.6),
    ("E90",   620.5),
    ("E100",  689.5),
    ("E110",  758.4),
    ("E70T-1", 482.6),        # FCAW / proceso T-1
    ("E80T-X", 551.6),
    ("E7018", 482.6),         # AWS A5.1 SMAW
    ("E7024", 482.6),
    ("E8018", 551.6),
    ("70 ksi", 482.6),        # texto libre
    ("FEXX=70", 482.6),
    ("  e70xx  ", 482.6),     # whitespace + minúsculas
])
def test_get_electrode_FEXX_parser(inp, expected_MPa):
    got = catalog.get_electrode_FEXX(inp)
    assert got == pytest.approx(expected_MPa, rel=1e-3)


def test_get_electrode_FEXX_invalid():
    with pytest.raises(KeyError):
        catalog.get_electrode_FEXX("")
    with pytest.raises(KeyError):
        catalog.get_electrode_FEXX("no-electrode-here")
