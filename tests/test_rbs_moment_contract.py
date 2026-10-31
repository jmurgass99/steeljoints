"""AC-03 (P0): el momento de demanda de una conexion RBS nacia en 0.0 y firmaba.

    Mu_demand_kNm: float = 0.0          # RBSInput, RBSPayload
    ...
    if inp.Mu_demand_kNm > 0:
        DCR = inp.Mu_demand_kNm / M_f_kNm if M_f_kNm > 0 else 99.0
    else:
        DCR = 0.0                        # <-- ausente, cero, negativo y NaN
    status = "OK" if DCR <= 1.0 else "NG"

MEDIDO, W24x76 con corte RBS dentro de limites (M_f = 1077.2 kN.m), por los tres
caminos productivos que llegan a este numero:

    design_rbs        sin Mu      -> DCR 0.0   OK
                      Mu = 0.0    -> DCR 0.0   OK
                      Mu = -2000  -> DCR 0.0   OK      (|Mu|/M_f = 1.857)
                      Mu = NaN    -> DCR 0.0   OK
                      Mu = -inf   -> DCR 0.0   OK
                      Mu = 2000   -> DCR 1.857 NG
    POST /rbs         sin Mu      -> 200 OK ;  Mu=-2000 -> 200 OK ;  "NaN" -> 200 OK
    bridge seismodyn M_Ed=-2000  -> util -2.15  is_safe=True  n_safe=1
                      M_Ed=0      -> util  0.0   is_safe=True
                      M_Ed=NaN    -> util  nan   is_safe=False n_unsafe=1   (falso FALLA)

Un momento de -2000 kN.m --1.86 veces la capacidad en cara de columna-- se publica
como conforme porque la comparacion `> 0` lo manda a la rama del cero. Y el cero
no distingue nada: el default del schema, un cero enviado, un negativo y un NaN
producen el MISMO byte.

CONTRATO QUE FIJA ESTE FICHERO (los cuatro estados de la demanda):

    MISSING   Mu ausente / None    -> NO_CALCULADO, `missing_inputs` lo nombra
    ZERO      Mu == 0.0 declarado  -> NO_CALCULADO: una conexion a momento sin
                                      momento no es un estado verificable, y 0.0
                                      era ademas el default que anunciaba el
                                      schema, asi que un cliente generado lo
                                      manda sin haberlo medido. Mismo criterio
                                      que `welds.py` (`demand_present = Mu != 0`).
    INVALID   NaN / +inf / -inf    -> REQUIERE_REVISION, DCR no se publica
    POSITIVE  |Mu| finito > 0      -> DCR = |Mu| / M_f, CUMPLE <= 1 < FALLA

CONVENCION DE SIGNOS (documentada, no supuesta): la RBS recorta LAS DOS alas
(`Z_RBS = Z_x - 2*c*t_f*(d - t_f)`), asi que su capacidad es la misma para momento
positivo y negativo, y en cara de columna el momento gravitatorio es negativo en
la convencion habitual. Un momento con signo es una demanda REAL, no una
ausencia: se toma su magnitud y la nota lo dice. Un negativo NO se convierte en
cero ni se rechaza.

Y la geometria fuera de los limites de AISC 358 s5.8.1 no es "OK con aviso": el
procedimiento de precalificacion no aplica a esa conexion, asi que el veredicto
es REQUIERE_REVISION (alcance), nunca CUMPLE.
"""
from __future__ import annotations

import math

import pytest

from steeljoints._common.audit_status import CalculationStatus
from steeljoints.integration.seismodyn_bridge import (
    BeamDynamicDemand,
    RBSConnectionDefinition,
    verify_connections_vs_demand,
)
from steeljoints.services import rbs

CUMPLE = CalculationStatus.CALCULADO_CUMPLE
FALLA = CalculationStatus.CALCULADO_FALLA
NO_CALC = CalculationStatus.NO_CALCULADO
REVISION = CalculationStatus.REQUIERE_REVISION

#: W24x76 con corte RBS dentro de limites AISC 358 (el mismo de test_api_rbs_wuf).
W24 = dict(d_mm=608.0, bf_mm=228.0, tf_mm=17.3, tw_mm=11.2, Zx_mm3=3_050_000.0,
           Fy_MPa=345.0, Fu_MPa=450.0, a_mm=140.0, b_mm=460.0, c_mm=45.0,
           L_clear_m=6.0, wu_kN_per_m=15.0)

CONN = RBSConnectionDefinition("B1", beam_d=608.0, beam_bf=228.0, beam_tf=17.3,
                               beam_Z_x=3_050_000.0, a=140.0, b=460.0, c=45.0,
                               L_clear=6.0, wu=15.0)


def _rbs(**extra):
    return rbs.design_rbs(rbs.RBSInput(**{**W24, **extra}))


def _bridge(m_ed: float):
    rep = verify_connections_vs_demand(
        [CONN], [BeamDynamicDemand("B1", M_Ed_kNm=m_ed, V_Ed_kN=80.0)])
    return rep, rep.rows[0]


# --------------------------------------------------------------------------- #
# EL CASO: servicio
# --------------------------------------------------------------------------- #
def test_un_momento_negativo_mayor_que_la_capacidad_no_firma() -> None:
    """EL ATAQUE. -2000 kN.m es 1.86 x M_f y salia OK con DCR 0.0."""
    r = _rbs(Mu_demand_kNm=-2000.0)

    assert r.calculation_status is FALLA, (
        f"DCR={r.DCR} status={r.status} {r.calculation_status}: un momento de "
        f"-2000 kN.m contra M_f={r.M_f_kNm:.1f} se publico como conforme")
    assert r.status == "NG"
    assert r.DCR == pytest.approx(2000.0 / r.M_f_kNm)


def test_sin_momento_de_demanda_no_hay_veredicto() -> None:
    """MISSING. Sin demanda no se compara nada; el DCR no puede ser 0.0."""
    r = _rbs()                                   # Mu ausente -> None

    assert r.calculation_status is NO_CALC
    assert r.status != "OK"
    assert r.DCR is None, f"se publico DCR={r.DCR} sin ninguna demanda"
    assert any("Mu_demand" in m for m in r.missing_inputs), r.missing_inputs


def test_un_momento_cero_declarado_no_firma() -> None:
    """ZERO. Una conexion a momento sin momento no es verificable."""
    r = _rbs(Mu_demand_kNm=0.0)

    assert r.calculation_status is NO_CALC
    assert r.status != "OK"


def test_ausente_y_cero_no_son_el_mismo_motivo() -> None:
    """Los dos son NO_CALCULADO, pero el ingeniero tiene que leer motivos distintos."""
    ausente = _rbs().missing_inputs
    cero = _rbs(Mu_demand_kNm=0.0).missing_inputs

    assert ausente and cero
    assert ausente != cero, f"mismo motivo para ausente y cero: {ausente}"


@pytest.mark.parametrize("mu", [math.nan, math.inf, -math.inf],
                         ids=["NaN", "+inf", "-inf"])
def test_un_momento_no_finito_requiere_revision(mu: float) -> None:
    """INVALID. Un NaN no es un momento pequeno; un infinito no es un momento grande."""
    r = _rbs(Mu_demand_kNm=mu)

    assert r.calculation_status is REVISION, f"{mu!r} -> {r.calculation_status}"
    assert r.status not in ("OK", "NG")
    assert r.DCR is None, f"se publico un DCR {r.DCR!r} calculado con {mu!r}"


def test_la_matriz_completa_del_momento() -> None:
    """INPUT / EXPECTED / ACTUAL, en una sola tabla legible en el fallo."""
    casos = [
        (None,      NO_CALC),
        (0.0,       NO_CALC),
        (-2000.0,   FALLA),
        (-400.0,    CUMPLE),
        (math.nan,  REVISION),
        (math.inf,  REVISION),
        (-math.inf, REVISION),
        (400.0,     CUMPLE),
        (1077.0,    CUMPLE),      # justo por debajo de M_f = 1077.2
        (2000.0,    FALLA),
    ]
    filas, malos = [], []
    for mu, esperado in casos:
        r = _rbs(Mu_demand_kNm=mu)
        filas.append(f"  Mu={mu!r:<10} esperado={esperado:<18} actual={r.calculation_status}")
        if r.calculation_status is not esperado:
            malos.append(mu)
    assert not malos, "\n" + "\n".join(filas)


# --------------------------------------------------------------------------- #
# Convencion de signos: documentada, no supuesta
# --------------------------------------------------------------------------- #
def test_el_signo_no_cambia_el_ratio_porque_la_rbs_es_simetrica() -> None:
    pos = _rbs(Mu_demand_kNm=400.0)
    neg = _rbs(Mu_demand_kNm=-400.0)

    assert pos.calculation_status is neg.calculation_status is CUMPLE
    assert pos.DCR == pytest.approx(neg.DCR)


def test_el_signo_descartado_queda_escrito_en_las_notas() -> None:
    """Descartar un signo sin decirlo es esconder una decision de ingenieria."""
    neg = _rbs(Mu_demand_kNm=-400.0)
    pos = _rbs(Mu_demand_kNm=400.0)

    assert any("signo" in n.lower() for n in neg.notes), neg.notes
    assert not any("signo" in n.lower() for n in pos.notes), pos.notes


# --------------------------------------------------------------------------- #
# Capacidad invalida y alcance
# --------------------------------------------------------------------------- #
def test_un_corte_que_deja_z_rbs_no_positivo_se_rechaza_no_se_inventa_99() -> None:
    """`else 99.0` era un numero fabricado. Z_RBS <= 0 es una capacidad INVALIDA."""
    with pytest.raises(ValueError, match="Z_RBS"):
        _rbs(c_mm=228.0 / 2.0 - 0.01 + 100.0, Mu_demand_kNm=400.0)   # c enorme


def test_geometria_fuera_de_limites_no_es_cumple() -> None:
    """Fuera de s5.8.1 la conexion no esta precalificada: el metodo no aplica."""
    r = _rbs(c_mm=100.0, Mu_demand_kNm=400.0)     # c = 100 >> 0.25*bf = 57

    assert r.is_geometry_ok is False
    assert r.calculation_status is REVISION, r.calculation_status
    assert r.status != "OK"


# --------------------------------------------------------------------------- #
# El control no puede impedir el trabajo legitimo
# --------------------------------------------------------------------------- #
def test_un_momento_valido_por_debajo_de_la_capacidad_firma() -> None:
    r = _rbs(Mu_demand_kNm=400.0)

    assert r.calculation_status is CUMPLE
    assert r.status == "OK"
    assert r.DCR == pytest.approx(400.0 / r.M_f_kNm)
    assert not r.missing_inputs


def test_un_momento_valido_por_encima_de_la_capacidad_falla() -> None:
    r = _rbs(Mu_demand_kNm=2000.0)

    assert r.calculation_status is FALLA
    assert r.status == "NG"
    assert r.DCR > 1.0


def test_las_magnitudes_de_capacidad_no_dependen_de_la_demanda() -> None:
    """Z_RBS, M_pr, V_pr y M_f son de la conexion; se calculan haya o no demanda."""
    a, b = _rbs(), _rbs(Mu_demand_kNm=400.0)

    assert (a.Z_RBS_mm3, a.M_pr_kNm, a.V_pr_kN, a.M_f_kNm) == \
           (b.Z_RBS_mm3, b.M_pr_kNm, b.V_pr_kN, b.M_f_kNm)
    assert a.M_f_kNm > a.M_pr_kNm > 0


# --------------------------------------------------------------------------- #
# EL CASO: HTTP /api/connections/rbs (montado tal cual en el gateway)
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def client():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from steeljoints.api.app import app
    return TestClient(app)


def test_http_sin_momento_no_publica_ok(client) -> None:
    r = client.post("/api/connections/rbs", json=W24)
    assert r.status_code == 200, r.text
    d = r.json()

    assert d["status"] != "OK", d
    assert d["calculation_status"] == "NO_CALCULADO"
    assert d["DCR"] is None
    assert any("Mu_demand" in m for m in d["missing_inputs"])


def test_http_momento_negativo_grande_falla(client) -> None:
    d = client.post("/api/connections/rbs", json={**W24, "Mu_demand_kNm": -2000.0}).json()

    assert d["calculation_status"] == "CALCULADO_FALLA", d
    assert d["status"] == "NG"


@pytest.mark.parametrize("mu", ["NaN", "Infinity", "-Infinity"])
def test_http_momento_no_finito_requiere_revision(client, mu: str) -> None:
    r = client.post("/api/connections/rbs", json={**W24, "Mu_demand_kNm": mu})
    assert r.status_code == 200, r.text
    d = r.json()

    assert d["calculation_status"] == "REQUIERE_REVISION", d
    assert d["DCR"] is None


def test_http_momento_nulo_explicito_no_firma(client) -> None:
    d = client.post("/api/connections/rbs", json={**W24, "Mu_demand_kNm": None}).json()
    assert d["calculation_status"] == "NO_CALCULADO", d


def test_http_momento_valido_firma_y_conserva_los_campos(client) -> None:
    """ADITIVO: ningun campo anterior desaparece, y el caso valido sigue OK."""
    d = client.post("/api/connections/rbs", json={**W24, "Mu_demand_kNm": 400.0}).json()

    for clave in ("Z_RBS_mm3", "M_pr_kNm", "V_pr_kN", "M_f_kNm", "DCR", "status",
                  "is_geometry_ok", "notes"):
        assert clave in d, clave
    assert d["status"] == "OK"
    assert d["calculation_status"] == "CALCULADO_CUMPLE"
    assert 0.0 < d["DCR"] < 1.0


# --------------------------------------------------------------------------- #
# EL CASO: bridge seismodyn (JmWorkbench lo invoca como paso `funcion`)
# --------------------------------------------------------------------------- #
def test_bridge_momento_negativo_grande_no_es_safe() -> None:
    """util = M_Ed / M_pr = -2.15 <= 1.0 era True: firmaba por el signo."""
    rep, row = _bridge(-2000.0)

    assert row.is_safe is False, f"util={row.utilization_ratio}: firmo por el signo"
    assert row.calculation_status is FALLA
    assert (rep.n_safe, rep.n_unsafe) == (0, 1)
    assert row.utilization_ratio == pytest.approx(2000.0 / row.M_pr_capacity_kNm)


def test_bridge_momento_cero_no_es_safe() -> None:
    rep, row = _bridge(0.0)

    assert row.is_safe is False
    assert row.calculation_status is NO_CALC
    assert rep.n_safe == 0


@pytest.mark.parametrize("m", [math.nan, math.inf], ids=["NaN", "+inf"])
def test_bridge_momento_no_finito_no_es_ni_safe_ni_unsafe(m: float) -> None:
    """Antes contaba como `n_unsafe`: un NaN no es un incumplimiento evaluado."""
    rep, row = _bridge(m)

    assert row.is_safe is False
    assert row.calculation_status is REVISION
    assert rep.n_unsafe == 0, "un NaN se contabilizo como incumplimiento"
    assert rep.n_sin_veredicto == 1


def test_bridge_los_contadores_suman_el_total() -> None:
    conns = [RBSConnectionDefinition(f"B{i}", beam_d=608.0, beam_bf=228.0, beam_tf=17.3,
                                     beam_Z_x=3_050_000.0, a=140.0, b=460.0, c=45.0,
                                     L_clear=6.0, wu=15.0) for i in range(4)]
    dem = [BeamDynamicDemand("B0", 400.0, 80.0), BeamDynamicDemand("B1", 2000.0, 80.0),
           BeamDynamicDemand("B2", 0.0, 80.0), BeamDynamicDemand("B3", math.nan, 80.0)]
    rep = verify_connections_vs_demand(conns, dem)

    assert (rep.n_safe, rep.n_unsafe, rep.n_sin_veredicto) == (1, 1, 2)
    assert rep.n_safe + rep.n_unsafe + rep.n_sin_veredicto == rep.n_total == 4


def test_bridge_el_maximo_no_lo_fija_un_no_finito() -> None:
    conns = [RBSConnectionDefinition(f"B{i}", beam_d=608.0, beam_bf=228.0, beam_tf=17.3,
                                     beam_Z_x=3_050_000.0, a=140.0, b=460.0, c=45.0,
                                     L_clear=6.0, wu=15.0) for i in range(2)]
    rep = verify_connections_vs_demand(
        conns, [BeamDynamicDemand("B0", math.inf, 80.0), BeamDynamicDemand("B1", 400.0, 80.0)])

    assert math.isfinite(rep.max_utilization)
    assert rep.critical_beam == "B1"


def test_bridge_el_caso_valido_sigue_safe() -> None:
    rep, row = _bridge(400.0)

    assert row.is_safe is True
    assert row.calculation_status is CUMPLE
    assert (rep.n_safe, rep.n_unsafe, rep.n_sin_veredicto) == (1, 0, 0)
    assert 0.0 < row.utilization_ratio < 1.0


def test_bridge_signo_descartado_queda_en_las_notas() -> None:
    _, neg = _bridge(-400.0)
    _, pos = _bridge(400.0)

    assert neg.is_safe is True and neg.utilization_ratio == pytest.approx(pos.utilization_ratio)
    assert any("signo" in n.lower() for n in neg.notes), neg.notes
