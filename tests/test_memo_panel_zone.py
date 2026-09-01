"""Tests memo panel zone (AISC 360-22 §J10.6)."""
import pytest

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


# ---------------------------------------------------------------------------
# GOLDEN — AISC 360-22 §J10.6 "Web Panel Zone Shear", Ecs. (J10-11) y (J10-12)
#
# Fuente citada: ANSI/AISC 360-22, §J10.6, caso alpha·Pr <= 0.4·Pc:
#
#   (J10-11)  Rn = 0.60·Fy·dc·tw
#             (deformacion de la zona de panel NO considerada en el analisis)
#
#   (J10-12)  Rn = 0.60·Fy·dc·tw · (1 + 3·bcf·tcf^2 / (db·dc·tw))
#             (deformacion de la zona de panel SI considerada en el analisis)
#
#   Factor de resistencia LRFD (§J10.6): phi = 0.90.
#
# CASO DERIVADO A MANO (columna tipo perfil ancho, viga de 600 mm de canto):
#   Fy  = 345 MPa
#   dc  = 380 mm    canto de la columna
#   tw  = 18 mm     espesor del alma de la columna (sin doubler)
#   bcf = 400 mm    ancho del ala de la columna
#   tcf = 28 mm     espesor del ala de la columna
#   db  = 600 mm    canto de la viga
#
#   Base comun a ambas ecuaciones:
#     0.60·Fy = 0.60·345 = 207 MPa
#     0.60·Fy·dc·tw = 207·380·18 = 207·6 840 = 1 415 880 N = 1 415.880 kN
#
#   Termino de las alas de la columna (solo en J10-12):
#     3·bcf·tcf^2      = 3·400·28^2 = 3·400·784 = 940 800 mm^3
#     db·dc·tw         = 600·380·18 = 4 104 000 mm^3
#     cociente         = 940 800/4 104 000 = 0.2292398
#     factor (1 + ...) = 1.2292398
#
#   (J10-12)  Rn = 1 415 880·1.2292398 = 1 740 456.0 N = 1 740.456 kN
#   (J10-11)  Rn = 1 415.880 kN
#   Aumento de J10-12 sobre J10-11: +22.92 %.
#
# ESTADO: los dos defectos que estos goldens documentaban (J10-12 aplicada
# incondicionalmente; ausencia de phi) estan CORREGIDOS. La seleccion de
# ecuacion es ahora un parametro explicito, `include_panel_deformation`, con
# default False (la rama restrictiva), y el modulo expone Rn y phi·Rn por
# separado con el DCR construido sobre phi·Rn.
# ---------------------------------------------------------------------------

_GOLDEN_PZ = dict(d_beam_mm=600.0, d_column_mm=380.0, t_web_column_mm=18.0,
                  b_flange_column_mm=400.0, t_flange_column_mm=28.0,
                  Fy_MPa=345.0, M_f1_kNm=500.0, M_f2_kNm=500.0)


def test_golden_aisc_360_J10_12_capacidad_nominal():
    """AISC 360-22 Ec. (J10-12) con el caso derivado a mano en la cabecera.

        Rn = 0.60·Fy·dc·tw·(1 + 3·bcf·tcf^2/(db·dc·tw))
           = 207·380·18 · (1 + 940 800/4 104 000)
           = 1 415 880 · 1.2292398
           = 1 740 456.0 N = 1 740.456 kN

    Requiere seleccionar explicitamente la rama J10-12
    (``include_panel_deformation=True``): el analisis del portico debe incluir
    la deformacion de la zona de panel para que el termino de las alas del
    pilar este permitido.
    """
    r = render_panel_zone_memo(PanelZoneInput(
        include_panel_deformation=True, **_GOLDEN_PZ))
    assert r.equation == "J10-12"
    assert r.V_capacity_kN == pytest.approx(1740.456, abs=1e-3)


def test_golden_aisc_360_J10_12_con_doubler():
    """AISC 360-22 Ec. (J10-12), MISMO caso pero con placa doubler de 10 mm.
    Segundo golden derivado a mano de forma independiente (tw cambia en los
    tres sitios donde aparece, tambien en el denominador del termino de alas):

        tp = tw + t_doubler = 18 + 10 = 28 mm
        0.60·Fy·dc·tp = 207·380·28 = 207·10 640 = 2 202 480 N
        3·bcf·tcf^2   = 940 800 mm^3   (no cambia)
        db·dc·tp      = 600·380·28 = 6 384 000 mm^3
        cociente      = 940 800/6 384 000 = 0.1473684
        Rn = 2 202 480·1.1473684 = 2 527 056.0 N = 2 527.056 kN

    Comprueba que el doubler entra en AMBOS terminos (un error frecuente es
    sumarlo solo al primero, lo que daria 2 202 480·1.2292398 = 2 707.4 kN,
    un 7.1 % de mas).
    """
    r = render_panel_zone_memo(PanelZoneInput(
        t_doubler_mm=10.0, include_panel_deformation=True, **_GOLDEN_PZ))
    assert r.V_capacity_kN == pytest.approx(2527.056, abs=1e-3)
    assert r.V_capacity_kN != pytest.approx(2707.4, abs=1.0)


def test_golden_aisc_360_J10_11_es_el_default():
    """GOLDEN — AISC 360-22 Ec. (J10-11), la rama RESTRICTIVA, y ademas el
    comportamiento por DEFECTO del modulo.

        Rn = 0.60·Fy·dc·tw = 207·380·18 = 1 415 880 N = 1 415.880 kN

    §J10.6 solo permite el termino 3·bcf·tcf^2/(db·dc·tw) cuando el efecto de
    la deformacion de la zona de panel SI se considera en el analisis de
    estabilidad del portico. Antes el modulo aplicaba J10-12 SIEMPRE, un
    +22.92 % de capacidad frente a J10-11 para este caso — inseguro cuando el
    analisis no contempla esa deformacion.

    Ahora la eleccion es un parametro explicito y el DEFAULT es la rama
    restrictiva: un llamante que ignore el parametro obtiene J10-11. La
    relacion entre ambas ramas se asevera con la misma geometria real (ya no
    hace falta el degenerado bcf = 0 mm que la version anterior necesitaba):

        1 740.456/1 415.880 - 1 = 0.2292398
    """
    r11 = render_panel_zone_memo(PanelZoneInput(**_GOLDEN_PZ))
    assert r11.equation == "J10-11"
    assert r11.V_capacity_kN == pytest.approx(1415.880, abs=1e-3)

    r12 = render_panel_zone_memo(PanelZoneInput(
        include_panel_deformation=True, **_GOLDEN_PZ))
    assert r12.V_capacity_kN / r11.V_capacity_kN - 1.0 == pytest.approx(
        0.2292398, abs=1e-6)


def test_golden_phi_0_90_y_DCR_sobre_capacidad_de_diseno():
    """GOLDEN — AISC 360-22 §J10.6 fija phi = 0.90 para el cortante de la zona
    de panel. Valores de diseno derivados a mano sobre el caso de la cabecera:

        phi·Rn (J10-11) = 0.90·1 415.880 = 1 274.292 kN
        phi·Rn (J10-12) = 0.90·1 740.456 = 1 566.410 kN

    Antes el modulo comparaba la demanda contra Rn sin factorizar: DCR y
    needs_doubler quedaban 1/0.90 = 1.111 -> ~11.1 % del lado INSEGURO. Ahora
    Rn y phi·Rn se exponen por separado y el DCR usa phi·Rn.
    """
    r11 = render_panel_zone_memo(PanelZoneInput(**_GOLDEN_PZ))
    assert r11.phi == 0.90
    assert r11.phi_Rn_kN == pytest.approx(1274.292, abs=1e-3)
    assert r11.DCR == pytest.approx(r11.V_demand_kN / 1274.292, abs=1e-9)

    r12 = render_panel_zone_memo(PanelZoneInput(
        include_panel_deformation=True, **_GOLDEN_PZ))
    assert r12.V_capacity_kN == pytest.approx(1740.456, abs=1e-3)
    assert r12.phi_Rn_kN == pytest.approx(1566.410, abs=1e-3)
    # 1 566.410 es el phi·Rn de la cabecera redondeado a 3 decimales (exacto:
    # 1 566.4104); por eso el DCR se compara con abs=1e-6 y no con 1e-9.
    assert r12.DCR == pytest.approx(r12.V_demand_kN / 1566.410, abs=1e-6)


def test_geometria_no_fisica_es_error_no_silencio():
    """La version anterior sumaba 1e-9 al denominador y max(...,1e-9) al
    dividir, de modo que un t_p = 0 producia un numero en vez de un fallo.
    Ahora la geometria no fisica se rechaza explicitamente.
    """
    with pytest.raises(ValueError):
        render_panel_zone_memo(PanelZoneInput(
            **dict(_GOLDEN_PZ, t_web_column_mm=0.0)))


@pytest.mark.characterization
def test_demanda_factor_0_8_y_brazo_db_sin_fuente():
    """CARACTERIZACION — el coeficiente 0.8 y el brazo db NO estan trazados a
    norma; el valor aseverado se obtuvo EJECUTANDO la implementacion.

    El modulo calcula V_pz = 0.8·(Mf1 + Mf2)/db - Vc. No he podido situar ese
    0.8 en AISC 341-22 §E3.6e: la norma obtiene el cortante requerido de la
    suma de momentos en las caras de columna correspondientes a las rotulas
    plasticas proyectadas (Mpr), sin un coeficiente global 0.8. Ademas el
    brazo empleado es db (canto de la viga) cuando la practica habitual es
    (db - tf), es decir la distancia entre centros de alas.

    NO CORREGIDO a proposito: usar (db - tf) exige el espesor de ala de la
    viga, que ``PanelZoneInput`` no tiene; sustituirlo sin ese dato seria
    inventar una hipotesis. Queda documentado en el docstring del modulo y en
    el markdown del memo.

    Este test NO ancla la demanda contra ninguna fuente: solo fija el valor
    que el codigo produce, para que un cambio de formula sea visible.

        V_pz = 0.8·(500 + 500)/0.600 - 0 = 800/0.600 = 1 333.333 kN
    """
    r = render_panel_zone_memo(PanelZoneInput(**_GOLDEN_PZ))
    assert r.V_demand_kN == pytest.approx(1333.3333, abs=1e-3)
    assert "0.8" in r.markdown and "d_b - t_f" in r.markdown
