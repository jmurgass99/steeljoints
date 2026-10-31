"""Tests block shear multi-código."""
import pytest

from steeljoints.block_shear_multi import BlockShearInput, block_shear


@pytest.fixture
def basic():
    return BlockShearInput(Agv_mm2=3000, Anv_mm2=2400,
                            Ant_mm2=1000, Fy_MPa=345, Fu_MPa=450)


class TestBlockShearAll:
    def test_5_codes(self, basic):
        for code in ("US", "CO", "EU", "SG", "AU"):
            r = block_shear(basic, code=code)
            assert r.Rd_kN > 0
            assert r.Rn_kN > r.Rd_kN if code in ("EU", "SG") else r.Rd_kN < r.Rn_kN

    def test_aisc_governing(self, basic):
        r = block_shear(basic, code="US")
        assert r.governing in ("fracture", "yield")


def test_code_invalido(basic):
    with pytest.raises(ValueError):
        block_shear(basic, code="ZZ")


# ---------------------------------------------------------------------------
# GOLDEN — AISC 360-22 Ec. J4-5  vs  EN 1993-1-8 Ec. (3.9) (§3.10.2)
#
# Fuentes citadas:
#   * ANSI/AISC 360-22, §J4.3 "Block Shear Strength", Ecuacion (J4-5):
#         Rn = 0.60·Fu·Anv + Ubs·Fu·Ant  <=  0.60·Fy·Agv + Ubs·Fu·Ant
#         (LRFD: phi = 0.75, §J4.3)
#   * EN 1993-1-8:2005, §3.10.2(2), Ecuacion (3.9), grupo de tornillos
#     sometido a carga CONCENTRICA:
#         Veff,1,Rd = fu·Ant/gammaM2 + (1/sqrt(3))·fy·Anv/gammaM0
#         (gammaM2 = 1.25, gammaM0 = 1.00)
#
# Las areas Agv / Anv / Ant se derivan A MANO abajo a partir de una geometria
# atornillada explicita; NO se leen de ninguna implementacion.
#
# NOTA DELIBERADA DE MATERIAL: se mantiene Fy=345 / Fu=450 MPa en AMBOS codigos.
# Un revisor europeo esperaria S355 (fy=355, fu=490) en la comprobacion EN; se
# fuerza el mismo material a proposito para que la diferencia numerica entre
# normas aisle el MODELO (0.60·Fu·Anv vs fy·Anv/sqrt(3), Ubs vs gammaM2) y no
# quede contaminada por un cambio de grado de acero.
#
# GEOMETRIA (chapa de nudo, una linea de 3 tornillos M20, agujeros d0 = 22 mm):
#     t          = 10 mm      espesor de la chapa
#     s          = 60 mm      separacion entre tornillos (paso, direccion corte)
#     Le_corte   = 40 mm      distancia al borde libre en el extremo del bloque
#     Le_traccion= 40 mm      del eje de tornillos al borde, direccion traccion
#
#   Longitud bruta del plano de cortante (borde -> ultimo tornillo):
#     Lgv = 2·s + Le_corte = 2·60 + 40 = 160 mm
#     Agv = Lgv·t = 160·10 = 1600 mm^2
#   Agujeros descontados en el plano de cortante: 3 tornillos, el del extremo
#   aporta medio agujero -> 2.5·d0 = 2.5·22 = 55 mm
#     Anv = (160 - 55)·10 = 105·10 = 1050 mm^2
#   Plano de traccion: 40 mm menos medio agujero -> 40 - 0.5·22 = 29 mm
#     Ant = 29·10 = 290 mm^2
# ---------------------------------------------------------------------------

_GOLDEN_GEOM = dict(Agv_mm2=1600.0, Anv_mm2=1050.0, Ant_mm2=290.0,
                    Fy_MPa=345.0, Fu_MPa=450.0, Ubs=1.0)


def test_golden_aisc_J4_5_fractura_gobierna():
    """AISC 360-22 Ec. J4-5, geometria de la cabecera (Agv=1600, Anv=1050,
    Ant=290 mm^2; Fy=345, Fu=450 MPa; Ubs=1.0, traccion uniforme).

    Termino de FRACTURA por cortante:
        0.60·Fu·Anv + Ubs·Fu·Ant
      = 0.60·450·1050 + 1.0·450·290
      = 283 500 + 130 500 = 414 000 N = 414.0 kN
    Termino de FLUENCIA por cortante (limite superior de J4-5):
        0.60·Fy·Agv + Ubs·Fu·Ant
      = 0.60·345·1600 + 130 500
      = 331 200 + 130 500 = 461 700 N = 461.7 kN
    Rn = min(414.0 ; 461.7) = 414.0 kN  -> gobierna la FRACTURA por cortante.
    LRFD (§J4.3): phi·Rn = 0.75·414.0 = 310.5 kN.
    """
    r = block_shear(BlockShearInput(**_GOLDEN_GEOM), code="US")
    assert r.Rn_kN == pytest.approx(414.0, abs=1e-6)
    assert r.phi_or_gamma == 0.75
    assert r.Rd_kN == pytest.approx(310.5, abs=1e-6)
    assert r.governing == "fracture"


def test_golden_aisc_J4_5_fluencia_gobierna():
    """AISC 360-22 Ec. J4-5 con la MISMA geometria salvo Agv reducido a
    1200 mm^2 (plano de cortante mas corto: Le_corte = 0, Lgv = 2·60 = 120 mm,
    Agv = 120·10 = 1200 mm^2), para ejercitar la rama de FLUENCIA del min().

    Fractura : 0.60·450·1050 + 450·290 = 283 500 + 130 500 = 414 000 N
    Fluencia : 0.60·345·1200 + 450·290 = 248 400 + 130 500 = 378 900 N  <- min
    Rn = 378.9 kN ; phi·Rn = 0.75·378.9 = 284.175 kN.
    """
    geom = dict(_GOLDEN_GEOM, Agv_mm2=1200.0)
    r = block_shear(BlockShearInput(**geom), code="US")
    assert r.Rn_kN == pytest.approx(378.9, abs=1e-6)
    assert r.Rd_kN == pytest.approx(284.175, abs=1e-6)
    assert r.governing == "yield"


def test_golden_en1993_1_8_eq_3_9_mismo_caso():
    """EN 1993-1-8:2005 §3.10.2(2) Ec. (3.9), carga concentrica, MISMA
    geometria y material que ``test_golden_aisc_J4_5_fractura_gobierna``.

        Veff,1,Rd = fu·Ant/gammaM2 + (1/sqrt(3))·fy·Anv/gammaM0

    Termino de traccion (fractura, gammaM2 = 1.25):
        fu·Ant          = 450·290 = 130 500 N = 130.500 kN
        /gammaM2        = 130 500/1.25        = 104.400 kN
    Termino de cortante (fluencia de Von Mises, gammaM0 = 1.00):
        fy·Anv/sqrt(3)  = 345·1050/1.7320508 = 362 250/1.7320508
                        = 209 145.135 N       = 209.145 kN
        /gammaM0        = 209.145 kN (sin cambio)
    Veff,1,Rd = 104.400 + 209.145 = 313.545 kN

    Sin factorizar (lo que el modulo devuelve como ``Rn_kN``):
        130.500 + 209.145 = 339.645 kN
    """
    r = block_shear(BlockShearInput(**_GOLDEN_GEOM), code="EU")
    assert r.Rn_kN == pytest.approx(339.645, abs=1e-3)
    assert r.Rd_kN == pytest.approx(313.545, abs=1e-3)
    # phi_or_gamma es un factor EFECTIVO Rd/Rn, NO un gamma normativo unico.
    assert r.phi_or_gamma == pytest.approx(313.545 / 339.645, abs=1e-6)


def test_golden_diferencia_entre_normas_aisc_vs_en1993():
    """DIFERENCIA ENTRE NORMAS para el caso identico de la cabecera.

        AISC 360-22 (J4-5, LRFD)      phi·Rn      = 0.75·414.0 = 310.500 kN
        EN 1993-1-8 (Ec. 3.9)         Veff,1,Rd   = 313.545 kN
        Delta = 313.545 - 310.500     = 3.045 kN
        Delta relativo = 3.045/310.500 = +0.9807 %  (EN por ENCIMA de AISC)

    El acuerdo tan estrecho es coincidencia numerica de este caso concreto:
    los modelos NO son equivalentes. AISC toma el MINIMO entre fractura y
    fluencia en el plano de cortante y aplica un unico phi=0.75 al conjunto;
    EN suma SIEMPRE fractura en traccion (/1.25) + fluencia en cortante (/1.00)
    sin ningun min(). Con Agv pequeno (rama de fluencia de AISC, ver
    ``test_golden_aisc_J4_5_fluencia_gobierna``: 284.175 kN) la separacion
    crece a 313.545/284.175 - 1 = +10.34 %.
    """
    us = block_shear(BlockShearInput(**_GOLDEN_GEOM), code="US")
    eu = block_shear(BlockShearInput(**_GOLDEN_GEOM), code="EU")
    assert eu.Rd_kN - us.Rd_kN == pytest.approx(3.045, abs=1e-3)
    assert (eu.Rd_kN / us.Rd_kN - 1.0) * 100.0 == pytest.approx(0.9807, abs=1e-3)

    us_y = block_shear(BlockShearInput(**dict(_GOLDEN_GEOM, Agv_mm2=1200.0)),
                       code="US")
    assert (eu.Rd_kN / us_y.Rd_kN - 1.0) * 100.0 == pytest.approx(10.34, abs=0.01)


def test_en1993_veff_2_no_implementado():
    """EN 1993-1-8 §3.10.2(3) Ec. (3.10) — carga EXCENTRICA:

        Veff,2,Rd = 0.5·fu·Ant/gammaM2 + (1/sqrt(3))·fy·Anv/gammaM0

    El modulo NO expone esta variante: ``_en1993_block`` codifica unicamente
    la Ec. (3.9) (concentrica) y no hay parametro para seleccionar la (3.10).
    Este test documenta la ausencia: si el resultado EU coincidiese con
    Veff,2,Rd habria que revisar cual de las dos esta implementada.

    Veff,2,Rd para la geometria de la cabecera:
        0.5·130 500/1.25 + 209.145 kN = 52.200 + 209.145 = 261.345 kN
    """
    r = block_shear(BlockShearInput(**_GOLDEN_GEOM), code="EU")
    assert r.Rd_kN == pytest.approx(313.545, abs=1e-3)
    assert r.Rd_kN != pytest.approx(261.345, abs=1e-3)
