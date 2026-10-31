"""B59: la placa base con TRACCION (Pu < 0). Lo destapo la auditoria de B52.

MEDIDO (Mu = 150 kN*m, placa 350x400, 4 anclajes):

    Pu =    0.0  -> T/perno 281.25 kN, util 1.1932, FALLA
    Pu =   -0.001-> T/perno 117.19 kN, util 0.4972, CUMPLE
    Pu = -200.0  -> T/perno 167.19 kN, util 0.7093, CUMPLE

1. `design()` con cualquier Pu < 0 lanzaba `ValueError: math domain error`
   (`sqrt(X)` con X < 0 en `required_thickness`, porque fp = Pu/A1 < 0). La
   clase declara el caso de levantamiento en `anchor_tension`, pero el informe
   completo no llegaba a emitirse. Se arregla aqui: sin compresion no hay
   aplastamiento (demanda 0, medida) y la flexion de la placa por la traccion de
   los anclajes NO esta implementada, asi que ese check sale NO EVALUADO y el
   informe no firma (`all_checks_ok` None), en vez de reventar.

2. PARADA (xfail strict): la rama de traccion usa brazo 0.8*N y reparte el
   axil entre TODOS los pernos; la de compresion usa N/2 - N/6 = N/3. Por eso
   no es monotona: 200 kN de traccion piden MENOS anclaje que axil nulo. Elegir
   el brazo cambia veredictos hacia fuera (con N/3 el termino de momento sube
   x2.4 en traccion): decision del usuario.

3. PARADA (xfail strict): el espesor de placa nunca se comprueba. La clase no
   recibe el espesor dispuesto; `required_thickness` lo DIMENSIONA y publica
   `is_ok: True`, `utilization: 0.0  # informational`. Es el mismo patron que
   §8.27 (B55 cerro el cortante: dimensionar no es comprobar). Aplicarlo aqui
   deja de firmar TODAS las placas base que hoy firman: decision del usuario.
"""
from __future__ import annotations

import pytest

from steeljoints.base_plate import BasePlate


def _placa(Pu: float, Mu: float = 150.0) -> BasePlate:
    return BasePlate(Pu=Pu, Mu=Mu, plate_B=350.0, plate_N=400.0, n_anchors=4)


# --------------------------------------------------------------------------- #
# 1. design() con traccion no revienta y no firma
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("Pu", [-0.001, -10.0, -200.0])
def test_design_con_traccion_emite_informe_en_vez_de_reventar(Pu: float) -> None:
    r = _placa(Pu).design()
    assert r["all_checks_ok"] is not True
    por_nombre = {c["check"]: c for c in r["checks"]}
    espesor = por_nombre["Plate thickness"]
    assert espesor["is_ok"] is None
    assert espesor["utilization"] is None
    assert espesor["motivo_no_evaluado"]
    if r["all_checks_ok"] is None:
        # el check que falta podia gobernar: no se publica la de los presentes
        assert r["governing_utilization"] is None
        assert r["summary"] == "NO EVALUADO"


def test_fastsap_una_placa_en_levantamiento_no_firma_ni_revienta() -> None:
    """Ruta de produccion: fastsap.design -> SteelJoints.BasePlate.design()."""
    fastsap_design = pytest.importorskip("fastsap.design")
    req = fastsap_design.DesignRequest(
        element_id="BP1", element_type="connection", material="steel",
        section_name="W12x50", V_Ed_kN=0.0, N_Ed_kN=-10.0, My_Ed_kNm=150.0,
        params={"connection_type": "base_plate"})
    r = fastsap_design.design_element(req)
    assert str(r.calculation_status) not in ("CALCULADO_CUMPLE", "CalculationStatus.CALCULADO_CUMPLE")
    assert not any("designer fall" in f for f in r.findings), r.findings


def test_design_con_traccion_sin_compresion_no_hay_aplastamiento() -> None:
    aplast = {c["check"]: c for c in _placa(-10.0).design()["checks"]}["Concrete bearing"]
    assert aplast["fp_MPa"] == 0.0
    assert aplast["utilization"] == 0.0
    assert aplast["is_ok"] is True


def test_design_con_traccion_que_falla_en_anclajes_publica_FALLA() -> None:
    """Un check que FALLA manda sobre uno no evaluado: el informe dice False."""
    r = _placa(-2000.0, Mu=0.0).design()
    assert r["all_checks_ok"] is False
    assert r["governing_check"] == "Anchor bolt tension"


def test_GUARDA_compresion_igual_que_antes() -> None:
    r = BasePlate(Pu=500.0, Mu=10.0, plate_B=350.0, plate_N=400.0, n_anchors=4).design()
    assert r["all_checks_ok"] is True
    por_nombre = {c["check"]: c for c in r["checks"]}
    assert por_nombre["Plate thickness"]["is_ok"] is True
    assert por_nombre["Anchor bolt tension"]["utilization"] == 0.0


def test_GUARDA_Pu_cero_con_momento_sigue_fallando() -> None:
    r = _placa(0.0).design()
    assert r["all_checks_ok"] is False
    assert r["governing_utilization"] == pytest.approx(1.1932, abs=1e-3)


# --------------------------------------------------------------------------- #
# 2 y 3. Decisiones PARADAS
# --------------------------------------------------------------------------- #

@pytest.mark.xfail(strict=True, reason=(
    "PARADA B59.2: la rama de traccion usa brazo 0.8*N y la de compresion N/3; "
    "200 kN de traccion piden menos anclaje que axil nulo. Elegir el brazo cambia "
    "veredictos hacia fuera: decision del usuario."))
def test_mas_traccion_nunca_pide_menos_anclaje() -> None:
    u_cero = _placa(0.0).anchor_tension()["utilization"]
    u_trac = _placa(-200.0).anchor_tension()["utilization"]
    assert u_trac >= u_cero


@pytest.mark.xfail(strict=True, reason=(
    "PARADA B59.3: el espesor de placa solo se dimensiona (is_ok True, util 0.0 "
    "'informational'); no hay espesor dispuesto que comprobar. Igual que §8.27/B55, "
    "pero aplicarlo deja de firmar todas las placas base: decision del usuario."))
def test_sin_espesor_dispuesto_la_placa_no_firma() -> None:
    r = BasePlate(Pu=500.0, Mu=10.0, plate_B=350.0, plate_N=400.0, n_anchors=4).design()
    assert r["all_checks_ok"] is not True
