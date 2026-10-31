"""Tests WUF-W."""
from steeljoints.wuf_w import WUFWInput, design_wuf_w


def test_demanda_basica():
    r = design_wuf_w(WUFWInput(beam_Zx_mm3=2_000_000), beam_length_m=8.0)
    assert r.Mpr_kNm > 0
    assert r.Vu_kN > 0


def test_compacto():
    r = design_wuf_w(WUFWInput(
        beam_Zx_mm3=2_000_000, beam_db_mm=500, beam_bf_mm=200,
        beam_tf_mm=20, beam_tw_mm=12,
    ))
    assert r.is_compact_per_AISC341


def test_scwb_marca_columna_debil():
    r = design_wuf_w(WUFWInput(
        beam_Zx_mm3=3_000_000, column_Zx_mm3=2_000_000,
    ))
    assert r.scwb_ratio < 1.0
    assert any("SCWB" in n for n in r.notes)
