"""Tests memo panel zone (AISC 341-22 §E3.6e)."""
from steelconnectionjm.memos.panel_zone import (
    PanelZoneInput, render_panel_zone_memo,
)


def test_demanda_baja_safe():
    r = render_panel_zone_memo(PanelZoneInput(
        M_f1_kNm=200, M_f2_kNm=180,
        d_beam_mm=500, d_column_mm=400,
        t_web_column_mm=20, b_flange_column_mm=400, t_flange_column_mm=25,
    ))
    assert not r.needs_doubler


def test_doubler_si_columna_debil():
    r = render_panel_zone_memo(PanelZoneInput(
        M_f1_kNm=1000, M_f2_kNm=900,
        d_beam_mm=500, d_column_mm=300,
        t_web_column_mm=8, b_flange_column_mm=300, t_flange_column_mm=12,
    ))
    assert r.needs_doubler
    assert r.DCR > 1
