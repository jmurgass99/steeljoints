"""Tests memo end-plate."""
import pytest

from steelconnectionjm.memos.end_plate import (
    EndPlateInput, render_end_plate_memo,
)


def test_demanda_baja_safe():
    # End-plate suficientemente gruesa para resistir 20 kN.m
    r = render_end_plate_memo(EndPlateInput(
        M_demand_kNm=20, bolt_diameter_mm=25.4,
        plate_thickness_mm=50, plate_width_mm=400,
    ))
    assert r.is_safe
    assert r.DCR_moment < 1


def test_demanda_alta_falla():
    r = render_end_plate_memo(EndPlateInput(
        M_demand_kNm=2000, bolt_diameter_mm=20,
        plate_thickness_mm=20, plate_width_mm=200,
    ))
    assert not r.is_safe


def test_markdown_estructura():
    r = render_end_plate_memo(EndPlateInput(M_demand_kNm=300,
                                              bolt_diameter_mm=22))
    for kw in ("Paso 1", "Paso 2", "Paso 3", "DCR"):
        assert kw in r.markdown


# ---------------------------------------------------------------------------
# GOLDEN — conexion End-Plate
#
# El modulo declara en su propio docstring "AISC 358 / EN 1993-1-8". Se ancla
# lo que SI es trazable a norma (la capacidad a traccion de los tornillos,
# AISC 360-22 Tabla J3.2 + Ec. J3-1) y se documenta con un xfail ESTRICTO lo
# que NO lo es (``M_resistance_kNm``, que no es una resistencia a flexion de
# la conexion sino el momento plastico de la seccion transversal de la chapa).
#
# Los goldens de T-stub EN 1993-1-8 §6.2.4.1 Tabla 6.2 (modos 1/2/3) YA existen
# sobre la funcion canonica ``codes.ec3_1_8.t_stub_FT_Rd`` en
# tests/test_ec3_1_8_golden.py (clase TestTStub, fichas W01449 / W01457) — no
# se duplican aqui. Se usan abajo como referencia externa del xfail.
# ---------------------------------------------------------------------------

_GOLDEN_EP = dict(M_demand_kNm=300.0, n_bolts=8, plate_thickness_mm=25.0,
                  plate_Fy_MPa=345.0, plate_width_mm=250.0,
                  bolt_pitch_mm=80.0)


def test_golden_traccion_tornillos_aisc_360_tabla_J3_2_A325():
    """AISC 360-22 Tabla J3.2 + Ec. (J3-1) — traccion de tornillos Grupo A.

    Fuente: ANSI/AISC 360-22, Tabla J3.2 "Nominal Stress of Fasteners",
    Grupo A (ASTM F3125 Gr. A325): Fnt = 90 ksi = 620 MPa. Ec. (J3-1):
    Rn = Fn·Ab. Derivado a mano para 4 tornillos de 24 mm en traccion
    (n_bolts=8; el modulo toma n//2 = 4 como fila traccionada):

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

    DISCREPANCIA REAL (no de redondeo): el valor devuelto es NOMINAL (Rn). El
    AISC 360-22 §J3.7 exige phi = 0.75 en traccion (el valor de diseno LRFD se
    asevera mas abajo, sobre la referencia de la Tabla J3.2).
    Como ``DCR_bolts`` e ``is_safe`` del memo comparan la demanda contra Rn sin
    phi, la verificacion es 1/0.75 = 1.33x del lado INSEGURO. Se asevera abajo.
    """
    r = render_end_plate_memo(EndPlateInput(
        bolt_diameter_mm=24.0, bolt_grade_Fu_MPa=827.0, **_GOLDEN_EP))
    # Referencia AISC Tabla J3.2 (Fnt = 620 MPa exactos)
    assert r.T_bolts_capacity_kN == pytest.approx(1121.926, rel=1e-3)
    # Valor exacto del modelo del modulo (0.75·Fu con Fu = 827 MPa)
    assert r.T_bolts_capacity_kN == pytest.approx(1122.378, abs=0.01)
    # Es NOMINAL: NO lleva el phi = 0.75 de §J3.7. El valor de diseno LRFD
    # seria phi·Rn = 0.75·1 121.926 = 841.44 kN; se asevera que el modulo NO
    # lo devuelve (mismo patron que test_discrepancia_falta_phi_0_90 en
    # tests/test_memo_panel_zone.py).
    assert r.T_bolts_capacity_kN != pytest.approx(841.44, abs=1.0)


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
        bolt_diameter_mm=22.0, bolt_grade_Fu_MPa=1034.0, **_GOLDEN_EP))
    assert r.T_bolts_capacity_kN == pytest.approx(1179.172, abs=0.01)
    assert r.T_bolts_capacity_kN / 1184.494 - 1.0 == pytest.approx(-0.00449,
                                                                  abs=1e-4)


@pytest.mark.xfail(strict=True, reason=(
    "DEFECTO DE MODELO: render_end_plate_memo devuelve como 'M_resistance_kNm' "
    "el momento plastico de la SECCION TRANSVERSAL de la chapa (b*t^2/4*Fy), "
    "no una resistencia a flexion de la CONEXION. Ver docstring del test."))
def test_golden_M_resistance_debe_ser_momento_de_conexion_EN_6_2_7_2():
    """XFAIL ESTRICTO — la resistencia a flexion del memo no es comparable con
    ninguna fuente publicada.

    Referencia externa: EN 1993-1-8:2005 §6.2.7.2, Ec. (6.25):

        Mj,Rd = SUM_r  h_r · Ftr,Rd

    con Ftr,Rd la resistencia de cada fila obtenida del T-stub equivalente
    (§6.2.4.1, Tabla 6.2, modos 1/2/3). Es decir FUERZA de fila x BRAZO. La
    misma estructura tiene AISC Design Guide 4 (2.a ed., Ec. 3.1 y §3.3): Mn
    se obtiene de las fuerzas de tornillo por sus distancias h_i al ala
    comprimida, o del analisis de lineas de fluencia phi·Mn = phi·Fy·tp^2·Yp.

    Caso derivado a mano (chapa 250 x 25 mm, Fy = 345 MPa; 4 tornillos
    traccionados de 24 mm, Fu = 827 MPa; brazo = 5·pitch = 400 mm, que es lo
    que el propio modulo asume internamente):

        T_Rd(4 tornillos, nominal) = 1 122.378 kN   (golden A325 de arriba)
        Mj cota superior = 1 122.378 kN · 0.400 m = 448.95 kN·m

    Lo que devuelve el modulo:

        Mp_chapa = b·t^2/4·Fy = 250·25^2/4·345
                 = 39 062.5 mm^3 · 345 = 13 476 562.5 N·mm = 13.477 kN·m

    13.477 kN·m es el momento plastico de una seccion 250x25, una magnitud de
    la CHAPA, no de la conexion; el modulo lo compara directamente contra el
    momento de la VIGA (M_demand). Consecuencia para este caso:
    DCR_moment = 300/13.477 = 22.26 e ``is_safe`` = False, mientras la parte
    de tornillos da DCR_bolts = 0.67. El memo declara FALLO en conexiones
    holgadas para cualquier momento de viga realista.

    Defectos adicionales sin fuente normativa:
      * ``arm_m = 5·bolt_pitch`` es una heuristica sin norma detras (el propio
        comentario del codigo la justifica como "~0.9·d_beam para vigas
        medianas"): no depende del canto de la viga, que es precisamente la
        variable que fija el brazo.
      * No hay analisis de lineas de fluencia (Yp, AISC 358 Tabla 6.2) ni
        modos 1/2/3 de T-stub, pese a que ambos existen en el repo
        (``end_plate.EndPlate.plate_flexure_check`` y
        ``codes.ec3_1_8.t_stub_FT_Rd``).

    Este test pasara a VERDE el dia que el memo devuelva una resistencia a
    flexion de conexion; el xfail estricto se volvera entonces ROJO y obligara
    a revisar y retirar el marcador.
    """
    r = render_end_plate_memo(EndPlateInput(
        bolt_diameter_mm=24.0, bolt_grade_Fu_MPa=827.0, **_GOLDEN_EP))
    # 448.95 kN·m es una COTA SUPERIOR (fuerza de las filas x brazo, sin
    # descontar los modos 1/2 del T-stub): una Mj,Rd correcta sera <= ese
    # valor, tipicamente bastante por debajo. Por eso NO se asevera igualdad
    # contra la cota -- eso dejaria el test rojo incluso tras corregir el
    # defecto -- sino una COTA INFERIOR de orden de magnitud: la mitad.
    # Hoy da 13.477 kN·m (< 224.5) -> XFAIL, correcto. El dia que el memo
    # devuelva un momento de CONEXION pasara a XPASS y el xfail estricto se
    # pondra rojo, forzando la revision.
    assert r.M_resistance_kNm >= 0.5 * 448.95


@pytest.mark.characterization
def test_M_resistance_es_el_Mp_de_la_chapa_no_de_la_conexion():
    """CARACTERIZACION — contrapartida NO-xfail del test anterior: se asevera
    el valor que el modulo SI devuelve (obtenido EJECUTANDO la implementacion;
    la formula b·t^2/4·Fy es la del propio modulo, no la de ninguna norma de
    conexiones), para que la discrepancia quede anclada por los dos lados y una
    correccion futura no pase inadvertida.

        b·t^2/4·Fy = 250·625/4·345 = 39 062.5·345 = 13 476 562.5 N·mm
                   = 13.4765625 kN·m
        DCR_moment = 300/13.4765625 = 22.26087
    """
    r = render_end_plate_memo(EndPlateInput(
        bolt_diameter_mm=24.0, bolt_grade_Fu_MPa=827.0, **_GOLDEN_EP))
    assert r.M_resistance_kNm == pytest.approx(13.4765625, abs=1e-6)
    assert r.DCR_moment == pytest.approx(22.26087, abs=1e-5)
    # ... y sin embargo los tornillos van holgados: el veredicto is_safe lo
    # dicta una magnitud que no es la resistencia de la conexion.
    assert r.DCR_bolts < 1.0
    assert r.is_safe is False
