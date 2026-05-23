"""Tests del bridge steelconnectionjm -> dynamicsjm."""
from __future__ import annotations
import pytest

from steelconnectionjm.integration import (
    BeamDynamicDemand, RBSConnectionDefinition,
    verify_connections_vs_demand,
)


def _w24x76_conn(beam_id="B1"):
    return RBSConnectionDefinition(
        beam_id=beam_id,
        beam_d=608.0, beam_bf=228.0, beam_tf=17.3, beam_Z_x=3050000.0,
        a=140.0, b=460.0, c=45.0, L_clear=6.0, wu=15.0,
    )


def test_verify_safe_case():
    """Demanda baja: conexion cumple."""
    conns = [_w24x76_conn("B1")]
    demands = [BeamDynamicDemand("B1", M_Ed_kNm=400.0, V_Ed_kN=80.0,
                                    analysis_label="pushover")]
    report = verify_connections_vs_demand(conns, demands)
    assert report.n_total == 1
    assert report.n_safe == 1
    assert report.n_unsafe == 0
    assert report.rows[0].utilization_ratio < 1.0


def test_verify_unsafe_case():
    """Demanda excesiva: no cumple."""
    conns = [_w24x76_conn("B1")]
    demands = [BeamDynamicDemand("B1", M_Ed_kNm=2000.0, V_Ed_kN=400.0)]
    report = verify_connections_vs_demand(conns, demands)
    assert report.n_unsafe == 1
    assert report.rows[0].utilization_ratio > 1.0
    assert report.critical_beam == "B1"


def test_verify_multiple_connections():
    conns = [_w24x76_conn("B1"), _w24x76_conn("B2"), _w24x76_conn("B3")]
    demands = [
        BeamDynamicDemand("B1", 400.0, 80.0),
        BeamDynamicDemand("B2", 1200.0, 250.0),
        BeamDynamicDemand("B3", 2500.0, 500.0),  # critico
    ]
    report = verify_connections_vs_demand(conns, demands)
    assert report.n_total == 3
    assert report.critical_beam == "B3"
    assert report.max_utilization > 1.0


def test_verify_safety_margin_increases_strictness():
    conns = [_w24x76_conn("B1")]
    demands = [BeamDynamicDemand("B1", 600.0, 120.0)]
    r1 = verify_connections_vs_demand(conns, demands, safety_margin=1.0)
    r2 = verify_connections_vs_demand(conns, demands, safety_margin=2.0)
    assert r2.rows[0].utilization_ratio > r1.rows[0].utilization_ratio


def test_verify_unknown_beam_id_raises():
    conns = [_w24x76_conn("B1")]
    demands = [BeamDynamicDemand("UNKNOWN", 100.0, 20.0)]
    with pytest.raises(ValueError, match="UNKNOWN"):
        verify_connections_vs_demand(conns, demands)


def test_verify_empty_inputs_raise():
    with pytest.raises(ValueError):
        verify_connections_vs_demand([], [BeamDynamicDemand("B1", 100, 20)])
    with pytest.raises(ValueError):
        verify_connections_vs_demand([_w24x76_conn()], [])


def test_verify_duplicate_connection_raises():
    conns = [_w24x76_conn("B1"), _w24x76_conn("B1")]
    demands = [BeamDynamicDemand("B1", 100, 20)]
    with pytest.raises(ValueError, match="duplicado"):
        verify_connections_vs_demand(conns, demands)
