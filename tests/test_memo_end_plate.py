"""Tests memo end-plate."""
import pytest

from steeljoints.memos.end_plate import (
    BoltRow, EndPlateInput, render_end_plate_memo,
)

# Geometria de filas usada por los tests de humo (brazo h_r y parametros de
# T-stub). No hay defaults: sin ella el memo declara NO CALCULADO.
_ROWS_SMOKE = (
    BoltRow(h_mm=400.0, leff_mm=150.0, m_mm=45.0, n_mm=45.0, n_bolts=2),
    BoltRow(h_mm=300.0, leff_mm=150.0, m_mm=45.0, n_mm=45.0, n_bolts=2),
)


def test_demanda_baja_safe():
    # End-plate suficientemente gruesa para resistir 20 kN.m
    r = render_end_plate_memo(EndPlateInput(
        M_demand_kNm=20, bolt_diameter_mm=25.4,
        plate_thickness_mm=50, plate_width_mm=400,
        bolt_rows=_ROWS_SMOKE,
    ))
    assert r.is_safe
    assert r.DCR_moment < 1


def test_demanda_alta_falla():
    r = render_end_plate_memo(EndPlateInput(
        M_demand_kNm=2000, bolt_diameter_mm=20,
        plate_thickness_mm=20, plate_width_mm=200,
        bolt_rows=(
            BoltRow(h_mm=300.0, leff_mm=100.0, m_mm=40.0, n_mm=40.0),
            BoltRow(h_mm=200.0, leff_mm=100.0, m_mm=40.0, n_mm=40.0),
        ),
    ))
    assert not r.is_safe


def test_markdown_estructura():
    r = render_end_plate_memo(EndPlateInput(M_demand_kNm=300,
                                            bolt_diameter_mm=22,
                                            bolt_rows=_ROWS_SMOKE))
    for kw in ("Paso 1", "Paso 2", "Paso 3", "DCR"):
        assert kw in r.markdown


def test_sin_geometria_de_filas_declara_no_calculado():
    """Sin ``bolt_rows`` no hay brazo ni T-stub: Mj,Rd es NO CALCULABLE.

    La regla es propagar la ausencia, no sustituirla. El memo devuelve None en
    ``M_resistance_kNm``, ``DCR_moment`` e ``is_safe`` (veredicto NO emitido) y
    lo dice en el markdown. La capacidad de los pernos, que si es calculable
    con los datos disponibles, se sigue devolviendo.
    """
    r = render_end_plate_memo(EndPlateInput(M_demand_kNm=300,
                                            bolt_diameter_mm=24))
    assert r.M_resistance_kNm is None
    assert r.DCR_moment is None
    assert r.is_safe is None
    assert r.T_bolts_capacity_kN > 0
    assert "NO CALCULADO" in r.markdown


# ---------------------------------------------------------------------------
# GOLDEN — conexion End-Plate
#
# El modulo declara "EN 1993-1-8 / AISC 360-22". Se anclan:
#   * la capacidad a traccion de los tornillos (AISC 360-22 Tabla J3.2 +
#     Ec. J3-1), nominal y de diseno (phi = 0.75, §J3.7);
#   * la resistencia a flexion de la CONEXION (EN 1993-1-8 §6.2.7.2 Ec. 6.25
#     con las filas resueltas por el T-stub equivalente §6.2.4.1 Tabla 6.2).
#
# Los goldens del T-stub en si (modos 1/2/3) YA existen sobre la funcion
# canonica ``codes.ec3_1_8.t_stub_FT_Rd`` en tests/test_ec3_1_8_golden.py
# (clase TestTStubGolden, fichas W01425 / W01457) — el memo la REUTILIZA, no la
# reimplementa, y aqui no se duplican.
# ---------------------------------------------------------------------------

_GOLDEN_EP = dict(M_demand_kNm=300.0, n_bolts=8, plate_thickness_mm=25.0,
                  plate_Fy_MPa=345.0, plate_width_mm=250.0,
                  bolt_pitch_mm=80.0)

# Dos filas traccionadas identicas, brazos al centro de compresion 560 y
# 460 mm; T-stub leff = 150 mm, m = n = 40 mm, 2 tornillos por fila.
_GOLDEN_ROWS = (
    BoltRow(h_mm=560.0, leff_mm=150.0, m_mm=40.0, n_mm=40.0, n_bolts=2),
    BoltRow(h_mm=460.0, leff_mm=150.0, m_mm=40.0, n_mm=40.0, n_bolts=2),
)


def test_golden_traccion_tornillos_aisc_360_tabla_J3_2_A325():
    """AISC 360-22 Tabla J3.2 + Ec. (J3-1) — traccion de tornillos Grupo A.

    Fuente: ANSI/AISC 360-22, Tabla J3.2 "Nominal Stress of Fasteners",
    Grupo A (ASTM F3125 Gr. A325): Fnt = 90 ksi = 620 MPa. Ec. (J3-1):
    Rn = Fn·Ab. Derivado a mano para 4 tornillos de 24 mm en traccion:

        Ab = pi·d^2/4 = pi·24^2/4 = pi·144 = 452.38934 mm^2
        Rn por tornillo = Fnt·Ab = 620·452.38934 = 280 481.4 N = 280.481 kN
        Rn 4 tornillos  = 4·280.481 = 1 121.926 kN

    El modulo NO usa el Fnt tabulado: calcula 0.75·Fu. Con Fu = 827 MPa
    (catalogo del repo para A325, clave Fub) resulta 0.75·827 = 620.25 MPa
    frente a los 620 MPa tabulados. Ese 0.04 % es el redondeo de la conversion
    blanda ksi->MPa: 90 ksi = 0.75·120 ksi es EXACTO en unidades imperiales, y
    620 / 827 MPa son los redondeos de 90 / 120 ksi. Por eso la referencia se
    ancla con rel=1e-3 — no es holgura para tapar un desacuerdo de modelo.

        modulo: 0.75·827·452.38934·4 = 1 122 378.0 N = 1 122.378 kN

    phi = 0.75 (§J3.7), CORREGIDO — antes faltaba y la verificacion quedaba
    1/0.75 = 1.33x del lado inseguro:

        phi·Rn (Tabla J3.2) = 0.75·1 121.926 = 841.44 kN
        phi·Rn (modulo)     = 0.75·1 122.378 = 841.783 kN

    ``T_bolts_capacity_kN`` conserva su significado NOMINAL (compatibilidad) y
    la capacidad de diseno se expone aparte en
    ``T_bolts_capacity_design_kN``.
    """
    r = render_end_plate_memo(EndPlateInput(
        bolt_diameter_mm=24.0, bolt_grade_Fu_MPa=827.0,
        bolt_rows=_GOLDEN_ROWS, **_GOLDEN_EP))
    # Referencia AISC Tabla J3.2 (Fnt = 620 MPa exactos)
    assert r.T_bolts_capacity_kN == pytest.approx(1121.926, rel=1e-3)
    # Valor exacto del modelo del modulo (0.75·Fu con Fu = 827 MPa)
    assert r.T_bolts_capacity_kN == pytest.approx(1122.378, abs=0.01)
    # Capacidad de DISENO, phi = 0.75 (§J3.7)
    assert r.T_bolts_capacity_design_kN == pytest.approx(841.44, abs=1.0)
    assert r.T_bolts_capacity_design_kN == pytest.approx(841.783, abs=0.01)


def test_golden_traccion_tornillos_aisc_360_tabla_J3_2_A490():
    """AISC 360-22 Tabla J3.2, Grupo B (ASTM F3125 Gr. A490).

    Fuente: Tabla J3.2, Fnt = 113 ksi = 779 MPa; Fu = 150 ksi = 1034 MPa
    (ambos coinciden con el catalogo del repo para A490). Derivado a mano
    para 4 tornillos de 22 mm:

        Ab = pi·22^2/4 = pi·121 = 380.13271 mm^2
        Rn por tornillo (Tabla J3.2) = 779·380.13271 = 296 123.4 N
        Rn 4 tornillos               = 1 184.494 kN

    Modelo del modulo (0.75·Fu = 0.75·1034 = 775.5 MPa):
        775.5·380.13271 = 294 792.9 N ; ·4 = 1 179.172 kN

    Diferencia: 1 179.172/1 184.494 - 1 = -0.449 %. A diferencia del caso
    A325 esta NO es puro redondeo: 113 ksi no es 0.75·150 ksi (= 112.5 ksi),
    la Tabla J3.2 redondea hacia arriba. El modelo 0.75·Fu queda por tanto un
    0.45 % por debajo de la tabla — pequeno y del lado seguro, pero real.
    """
    r = render_end_plate_memo(EndPlateInput(
        bolt_diameter_mm=22.0, bolt_grade_Fu_MPa=1034.0,
        bolt_rows=_GOLDEN_ROWS, **_GOLDEN_EP))
    assert r.T_bolts_capacity_kN == pytest.approx(1179.172, abs=0.01)
    assert r.T_bolts_capacity_kN / 1184.494 - 1.0 == pytest.approx(-0.00449,
                                                                  abs=1e-4)


def test_golden_M_resistance_es_momento_de_conexion_EN_6_2_7_2():
    """GOLDEN — resistencia a flexion de la CONEXION.

    Fuentes citadas:
      * EN 1993-1-8:2005 §6.2.7.2, Ec. (6.25):  Mj,Rd = SUM_r h_r·Ft,r,Rd
      * EN 1993-1-8:2005 §6.2.4.1, Tabla 6.2 (T-stub equivalente, modos 1/2/3)
      * AISC 360-22 Ec. (J3-1) + Tabla J3.2 y §J3.7 (phi = 0.75) para la
        traccion de los tornillos; §J4.1(a) (fluencia de elementos de union,
        phi = 0.90; equivale al phi_b = 0.90 de AISC Design Guide 4 §3.3 sobre
        el momento de lineas de fluencia de la end plate — NO es §F1, que es
        flexion de miembros) para la flexion de la chapa. Formato LRFD
        homogeneo: no se mezclan phi y gamma_M dentro de un mismo producto (el
        phi de la chapa entra en ``t_stub_FT_Rd`` por su parametro
        gamma_M0 = 1/0.90, que es donde divide a Mpl,Rd).

    ALCANCE: el valor aseverado limita cada fila SOLO por el T-stub del lado
    de la chapa frontal. Es una COTA SUPERIOR de la Mj,Rd real del nudo, que
    EN 1993-1-8 §6.2.7.2 limita ademas por los componentes del pilar y por los
    limites de grupo. Ver el docstring del modulo.

    CASO DERIVADO A MANO — chapa 250 x 25 mm, Fy = 345 MPa; dos filas de 2
    tornillos de 24 mm, Fu = 827 MPa; leff = 150 mm, m = n = 40 mm; brazos al
    centro de compresion h1 = 560 mm, h2 = 460 mm.

      Tornillos:
        Ab      = pi·24^2/4 = 452.389342 mm^2
        Rn      = 0.75·827·452.389342 = 280 594.490 N   (nominal, por tornillo)
        phi·Rn  = 0.75·280 594.490    = 210 445.867 N   (diseno, por tornillo)
        Fila de 2:  SUM Ft nominal = 561 188.979 N ; diseno = 420 891.734 N

      Chapa (Mpl,Rd = 0.25·leff·tp^2·fy / gamma_M0):
        nominal (gamma_M0 = 1.0):    0.25·150·625·345           = 8 085 937.5 N·mm
        diseno  (gamma_M0 = 1/0.90): 0.25·150·625·345·0.90      = 7 277 343.75 N·mm

      Modos (Tabla 6.2), NOMINAL:
        F1 = 4·8 085 937.5/40                                = 808 593.750 N
        F2 = (2·8 085 937.5 + 40·561 188.979)/(40+40)        = 482 742.927 N  <- gobierna
        F3 = 561 188.979 N
      Modos, DISENO:
        F1 = 4·7 277 343.75/40                               = 727 734.375 N
        F2 = (2·7 277 343.75 + 40·420 891.734)/80            = 392 379.461 N  <- gobierna
        F3 = 420 891.734 N

      Ec. (6.25), ambas filas con la misma geometria:
        Mj,Rd nominal = 482 742.927·(560 + 460) = 492 397 785.6 N·mm
                      = 492.398 kN·m
        Mj,Rd diseno  = 392 379.461·(560 + 460) = 400 227 049.2 N·mm
                      = 400.227 kN·m

      Verificacion con M_demand = 300 kN·m:
        DCR_moment = 300/400.227 = 0.74957  ->  is_safe = True

    ANTES DE LA CORRECCION el modulo devolvia b·t^2/4·Fy = 13.477 kN·m (el
    momento plastico de la SECCION TRANSVERSAL de la chapa, una magnitud de la
    chapa y no de la conexion) y lo comparaba contra el momento de la VIGA:
    DCR_moment = 300/13.477 = 22.26 e is_safe = False, con los tornillos
    holgados (DCR_bolts = 0.67). Declaraba fallo en conexiones correctas.
    """
    r = render_end_plate_memo(EndPlateInput(
        bolt_diameter_mm=24.0, bolt_grade_Fu_MPa=827.0,
        bolt_rows=_GOLDEN_ROWS, **_GOLDEN_EP))

    assert r.M_resistance_nominal_kNm == pytest.approx(492.398, abs=1e-3)
    assert r.M_resistance_kNm == pytest.approx(400.227, abs=1e-3)
    assert r.DCR_moment == pytest.approx(0.74957, abs=1e-5)
    assert r.is_safe is True

    # Cada fila la resuelve el T-stub canonico; gobierna el modo 2.
    assert len(r.rows) == 2
    for rr in r.rows:
        assert rr.governing_mode == "Modo 2"
        assert rr.Ft_Rd_design_kN == pytest.approx(392.379461, abs=1e-5)
        assert rr.Ft_Rd_nominal_kN == pytest.approx(482.742927, abs=1e-5)

    # Ya NO devuelve el Mp de la seccion de la chapa (250·25^2/4·345 = 13.477).
    assert r.M_resistance_kNm != pytest.approx(13.4765625, abs=1.0)


def test_golden_reutiliza_t_stub_canonico_del_repo():
    """El memo REUTILIZA ``codes.ec3_1_8.t_stub_FT_Rd`` (que tiene sus propios
    goldens en tests/test_ec3_1_8_golden.py), no reimplementa el T-stub.

    Se comprueba llamando a la funcion canonica con exactamente las mismas
    entradas de fila que el memo usa internamente y exigiendo identidad
    numerica de la fuerza de fila de diseno.
    """
    from steeljoints.codes.ec3_1_8 import t_stub_FT_Rd
    from steeljoints.memos.end_plate import (
        PHI_BOLT_TENSION, PHI_PLATE_BENDING,
    )
    from math import pi

    inp = EndPlateInput(bolt_diameter_mm=24.0, bolt_grade_Fu_MPa=827.0,
                        bolt_rows=_GOLDEN_ROWS, **_GOLDEN_EP)
    r = render_end_plate_memo(inp)

    Ab = pi * 24.0 ** 2 / 4.0
    sum_Ft_des = 2 * PHI_BOLT_TENSION * 0.75 * 827.0 * Ab
    ref = t_stub_FT_Rd(leff_mm=150.0, tp_mm=25.0, fy_plate_MPa=345.0,
                       Ft_Rd_bolt_N=sum_Ft_des, n_mm=40.0, m_mm=40.0,
                       gamma_M0=1.0 / PHI_PLATE_BENDING)
    assert r.rows[0].Ft_Rd_design_kN == pytest.approx(ref["FT_Rd_N"] / 1000.0,
                                                      abs=1e-9)
    assert r.rows[0].governing_mode == ref["governing_mode"]


@pytest.mark.characterization
def test_T_required_y_DCR_bolts_son_un_PROXY():
    """CARACTERIZACION — ``T_bolts_required_kN`` y ``DCR_bolts`` NO estan
    trazados a norma; los valores aseverados se obtuvieron EJECUTANDO la
    implementacion.

    Al retirar la heuristica sin fuente ``arm_m = 5·bolt_pitch``, la demanda de
    traccion de los tornillos se queda sin definicion normativa. En vez de
    redefinirla en silencio, el memo la calcula como M_demand/h_max (brazo
    mayor) y la marca como PROXY INFORMATIVO: NO entra en ``is_safe``. La
    traccion de los tornillos ya esta cubierta dentro de Mj,Rd por el modo 3
    del T-stub, que es quien gobierna el veredicto.

        T_required = 300/0.560           = 535.7143 kN
        DCR_bolts  = 535.7143/841.7835   = 0.63640
    """
    r = render_end_plate_memo(EndPlateInput(
        bolt_diameter_mm=24.0, bolt_grade_Fu_MPa=827.0,
        bolt_rows=_GOLDEN_ROWS, **_GOLDEN_EP))
    assert r.T_bolts_required_kN == pytest.approx(535.7143, abs=1e-4)
    assert r.DCR_bolts == pytest.approx(0.63640, abs=1e-5)
    assert "PROXY" in r.markdown
    # El veredicto lo dicta el momento, no el proxy.
    assert r.is_safe is (r.DCR_moment <= 1.0)
