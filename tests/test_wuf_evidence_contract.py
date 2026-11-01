"""WUF-W (P0, hermano de AC-03): el mismo DCR ciego, una columna inventada y un
axil declarado que nunca se leia.

TRES DEFECTOS EN `services/wuf.py`, medidos por POST /api/connections/wuf con la
viga W21x62 de los tests del paquete:

1. El mismo bloque de DCR que la RBS:

       if inp.Mu_demand_kNm > 0: DCR = Mu / M_pr ...  else: DCR = 0.0

   Mu = -3000 kN.m (2.9 x M_pr = 1030) -> DCR 0.000. Ausente, cero, negativo y
   NaN, el mismo byte.

2. LA COLUMNA SE INVENTABA. `WUFInput` y `WUFPayload` traian
   `col_d_mm=350, col_bf_mm=350, col_tf_mm=18, col_tw_mm=11, col_Zx_mm3=4e6,
   col_Fy_MPa=345` como DEFAULTS. Un cliente que manda solo la viga recibe
   `scwb_ratio=1.70` y `pz_DCR=2.37`: un veredicto de columna fuerte / zona de
   panel sobre una columna que no existe en ningun modelo.

3. `Pu_col_kN` y `Py_col_kN` existian en el input "para la reduccion por axil" y
   `design_wuf` NO LOS LEIA NUNCA. El SCWB salia `Zc*Fyc / (Zb*Fyb)`, es decir,
   AISC 341 E3-1 con Pu = 0: la COTA SUPERIOR mas favorable, publicada como si
   fuera el ratio. (`Vu_demand_kN` tampoco se leia; no hay comprobacion de
   cortante en este servicio y ahora el schema lo dice.)

CONTRATO QUE FIJA ESTE FICHERO:

* Momento: MISSING/ZERO -> NO_CALCULADO, INVALID -> REQUIERE_REVISION,
  POSITIVE -> |Mu|/M_pr (misma `_demanda` y misma convencion de signos que RBS).
* Columna: sin defaults. Sin columna no hay SCWB ni zona de panel -> NO_CALCULADO
  con los campos nombrados en `missing_inputs`; `scwb_ratio`/`pz_DCR` = None.
* SCWB con axil: `M*pc = Zc*Fyc*(1 - Pu/Py)` (AISC 341 E3-1, con Ag = Py/Fy). Sin
  Pu/Py declarados el ratio publicado es la cota superior (Pu=0), y una cota
  superior solo puede PROBAR UN FALLO: si ya es < 1 con Pu = 0, la columna es
  debil con cualquier axil -> CALCULADO_FALLA. Si es >= 1, no prueba nada ->
  NO_CALCULADO hasta que Pu y Py se declaren. Pu >= Py -> REQUIERE_REVISION.
* El veredicto global es FALLA si CUALQUIER comprobacion evaluada falla
  (compacidad, zona de panel, SCWB, momento), aunque otra no sea evaluable: un
  fallo probado es un hecho sobre la conexion. CUMPLE exige las cuatro evaluadas
  y aprobadas, con la demanda y el axil declarados.
"""
from __future__ import annotations

import math

import pytest

from steeljoints._common.audit_status import CalculationStatus
from steeljoints.services import wuf

CUMPLE = CalculationStatus.CALCULADO_CUMPLE
FALLA = CalculationStatus.CALCULADO_FALLA
NO_CALC = CalculationStatus.NO_CALCULADO
REVISION = CalculationStatus.REQUIERE_REVISION

#: W21x62 (la viga de test_api_rbs_wuf).
VIGA = dict(beam_d_mm=533.0, beam_bf_mm=209.0, beam_tf_mm=15.6, beam_tw_mm=10.2,
            beam_Zx_mm3=2_350_000.0, beam_Fy_MPa=345.0, beam_Fu_MPa=450.0,
            beam_length_m=7.0)
#: Columna con alma suficiente para que la zona de panel cumpla (tw = 25 mm).
COLUMNA = dict(col_d_mm=381.0, col_bf_mm=394.0, col_tf_mm=30.2, col_tw_mm=25.0,
               col_Zx_mm3=4_700_000.0, col_Fy_MPa=345.0)
#: Axil de columna declarado: Pu/Py = 0.125 -> reduce M*pc un 12.5 %.
AXIL = dict(Pu_col_kN=1000.0, Py_col_kN=8000.0)


def _wuf(**extra):
    return wuf.design_wuf(wuf.WUFInput(**{**VIGA, **COLUMNA, **AXIL, **extra}))


# --------------------------------------------------------------------------- #
# 1. Momento de demanda
# --------------------------------------------------------------------------- #
def test_un_momento_negativo_grande_falla() -> None:
    r = _wuf(Mu_demand_kNm=-3000.0)

    assert r.calculation_status is FALLA, (r.DCR, r.status, r.notes)
    assert r.DCR == pytest.approx(3000.0 / r.M_pr_kNm)
    assert r.status == "NG"


def test_sin_momento_no_hay_veredicto() -> None:
    r = _wuf()

    assert r.calculation_status is NO_CALC
    assert r.DCR is None
    assert r.status != "OK"
    assert any("Mu_demand" in m for m in r.missing_inputs), r.missing_inputs


def test_momento_cero_no_firma() -> None:
    r = _wuf(Mu_demand_kNm=0.0)
    assert r.calculation_status is NO_CALC and r.status != "OK"


@pytest.mark.parametrize("mu", [math.nan, math.inf, -math.inf], ids=["NaN", "+inf", "-inf"])
def test_momento_no_finito_requiere_revision(mu: float) -> None:
    r = _wuf(Mu_demand_kNm=mu)

    assert r.calculation_status is REVISION, r.calculation_status
    assert r.DCR is None


def test_signo_descartado_con_nota() -> None:
    neg, pos = _wuf(Mu_demand_kNm=-600.0), _wuf(Mu_demand_kNm=600.0)

    assert neg.DCR == pytest.approx(pos.DCR)
    assert any("signo" in n.lower() for n in neg.notes), neg.notes


# --------------------------------------------------------------------------- #
# 2. La columna no se inventa
# --------------------------------------------------------------------------- #
def test_sin_columna_no_hay_scwb_ni_zona_de_panel() -> None:
    """EL CASO 2. Antes: scwb=1.70 y pz_DCR=2.37 sobre una columna por defecto."""
    r = wuf.design_wuf(wuf.WUFInput(**VIGA, **AXIL, Mu_demand_kNm=600.0))

    assert r.scwb_ratio is None, f"SCWB {r.scwb_ratio} calculado sin columna"
    assert r.pz_DCR is None and r.pz_Vn_kN is None
    assert r.calculation_status is NO_CALC
    assert r.status != "OK"
    assert any("col_" in m for m in r.missing_inputs), r.missing_inputs


def test_el_input_no_trae_ninguna_columna_por_defecto() -> None:
    """Un default de columna es una capacidad inventada. Ninguno puede quedar."""
    import dataclasses
    defaults = {f.name: f.default for f in dataclasses.fields(wuf.WUFInput)
                if f.name.startswith("col_")}
    assert defaults and all(v is None for v in defaults.values()), defaults


def test_columna_parcial_nombra_lo_que_falta() -> None:
    r = wuf.design_wuf(wuf.WUFInput(**VIGA, **AXIL, Mu_demand_kNm=600.0,
                                    col_Zx_mm3=4_700_000.0, col_Fy_MPa=345.0))
    faltan = " ".join(r.missing_inputs)
    assert "col_d_mm" in faltan and "col_tw_mm" in faltan, r.missing_inputs


# --------------------------------------------------------------------------- #
# 3. SCWB con el axil declarado
# --------------------------------------------------------------------------- #
def test_el_axil_reduce_el_scwb() -> None:
    """AISC 341 E3-1: M*pc = Zc (Fyc - Pu/Ag) = Zc Fyc (1 - Pu/Py)."""
    con = _wuf(Mu_demand_kNm=600.0)
    cota = _wuf(Mu_demand_kNm=600.0, Pu_col_kN=None, Py_col_kN=None)

    # v1.2: M*pb = Mpr + Vpr·dc/2 (AISC 341 §E3.4a); la v1.1 usaba Zb·Fyb nominal.
    m_pb = cota.M_pr_kNm + cota.V_pr_kN * COLUMNA["col_d_mm"] / 2000.0
    assert cota.scwb_ratio == pytest.approx(COLUMNA["col_Zx_mm3"] * COLUMNA["col_Fy_MPa"] / 1e6 / m_pb)
    assert con.scwb_ratio == pytest.approx(cota.scwb_ratio * (1.0 - 1000.0 / 8000.0))


def test_sin_axil_una_cota_superior_favorable_no_firma() -> None:
    """scwb (Pu=0) = 2.0 >= 1 no prueba nada sin conocer Pu."""
    r = _wuf(Mu_demand_kNm=600.0, Pu_col_kN=None, Py_col_kN=None)

    assert r.scwb_ratio is not None and r.scwb_ratio >= 1.0
    assert r.calculation_status is NO_CALC, r.calculation_status
    assert any("Pu_col" in m for m in r.missing_inputs), r.missing_inputs


def test_sin_axil_una_cota_superior_que_ya_falla_es_un_fallo_probado() -> None:
    """Columna debil con Pu = 0 es debil con cualquier Pu: FALLA sin necesitar el axil."""
    r = _wuf(Mu_demand_kNm=600.0, Pu_col_kN=None, Py_col_kN=None, col_Zx_mm3=500_000.0)

    assert r.scwb_ratio is not None and r.scwb_ratio < 1.0
    assert r.calculation_status is FALLA
    assert r.status == "NG"


def test_un_axil_que_agota_la_columna_requiere_revision() -> None:
    r = _wuf(Mu_demand_kNm=600.0, Pu_col_kN=9000.0, Py_col_kN=8000.0)
    assert r.calculation_status is REVISION
    assert r.status not in ("OK", "NG")


def test_solo_uno_de_los_dos_axiles_no_basta() -> None:
    r = _wuf(Mu_demand_kNm=600.0, Py_col_kN=None)
    assert r.calculation_status is NO_CALC
    assert any("Py_col" in m for m in r.missing_inputs), r.missing_inputs


# --------------------------------------------------------------------------- #
# Composicion del veredicto
# --------------------------------------------------------------------------- #
def test_caso_completo_y_sano_firma() -> None:
    r = _wuf(Mu_demand_kNm=600.0)

    assert r.calculation_status is CUMPLE, (r.missing_inputs, r.notes)
    assert r.status == "OK"
    assert r.is_compact and r.pz_DCR <= 1.0 and r.scwb_ratio >= 1.0 and r.DCR <= 1.0
    assert not r.missing_inputs


def test_zona_de_panel_que_falla_es_falla_aunque_falte_la_demanda() -> None:
    """Un fallo probado en una comprobacion evaluada es un hecho sobre la conexion."""
    r = _wuf(col_tw_mm=11.0)          # sin Mu; el alma fina agota la zona de panel

    assert r.pz_DCR is not None and r.pz_DCR > 1.0
    assert r.calculation_status is FALLA
    assert r.status == "NG"


def test_columna_debil_es_falla_aunque_falte_la_demanda() -> None:
    """Conserva lo que test_api_rbs_wuf::test_wuf_weak_column_detected ya exigia."""
    r = _wuf(col_Zx_mm3=500_000.0)
    assert r.calculation_status is FALLA and r.status == "NG"


def test_las_capacidades_no_dependen_de_la_demanda() -> None:
    a, b = _wuf(), _wuf(Mu_demand_kNm=600.0)
    assert (a.M_pr_kNm, a.V_pr_kN, a.pz_Vn_kN, a.scwb_ratio, a.weld_capacity_kN) == \
           (b.M_pr_kNm, b.V_pr_kN, b.pz_Vn_kN, b.scwb_ratio, b.weld_capacity_kN)


# --------------------------------------------------------------------------- #
# HTTP /api/connections/wuf
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def client():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from steeljoints.api.app import app
    return TestClient(app)


def test_http_solo_viga_no_publica_un_scwb(client) -> None:
    d = client.post("/api/connections/wuf", json={**VIGA, "Mu_demand_kNm": 600.0}).json()

    assert d["scwb_ratio"] is None and d["pz_DCR"] is None, d
    assert d["calculation_status"] == "NO_CALCULADO"
    assert d["status"] != "OK"


def test_http_momento_negativo_grande_falla(client) -> None:
    d = client.post("/api/connections/wuf",
                    json={**VIGA, **COLUMNA, **AXIL, "Mu_demand_kNm": -3000.0}).json()
    assert d["calculation_status"] == "CALCULADO_FALLA", d
    assert d["DCR"] > 1.0


def test_http_sin_momento_no_publica_dcr_cero(client) -> None:
    d = client.post("/api/connections/wuf", json={**VIGA, **COLUMNA, **AXIL}).json()
    assert d["DCR"] is None and d["calculation_status"] == "NO_CALCULADO"


def test_http_el_axil_se_puede_declarar_y_el_caso_sano_firma(client) -> None:
    d = client.post("/api/connections/wuf",
                    json={**VIGA, **COLUMNA, **AXIL, "Mu_demand_kNm": 600.0}).json()

    assert d["calculation_status"] == "CALCULADO_CUMPLE", d
    assert d["status"] == "OK"
    for clave in ("M_pr_kNm", "V_pr_kN", "is_compact", "scwb_ratio", "pz_Vn_kN",
                  "pz_DCR", "weld_capacity_kN", "DCR", "status", "notes",
                  "calculation_status", "missing_inputs"):
        assert clave in d, clave


def test_http_el_schema_no_anuncia_columna_por_defecto(client) -> None:
    """El OpenAPI es lo que lee un cliente generado: no puede prometer una columna."""
    schema = client.get("/openapi.json").json()["components"]["schemas"]["WUFPayload"]
    props = schema["properties"]
    for campo in ("col_d_mm", "col_bf_mm", "col_tf_mm", "col_tw_mm", "col_Zx_mm3", "col_Fy_MPa"):
        assert props[campo].get("default") is None, (campo, props[campo])
    assert props["Mu_demand_kNm"].get("default") is None
