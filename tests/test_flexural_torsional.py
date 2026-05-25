"""Suite 9.1 — Pandeo torsional y flexotorsional (AISC 360-16 E4).

Comprobaciones cerradas:
  * Sección doblemente simétrica (xo=yo=0): la cúbica E4-6 factoriza en
    (Fe-Fex)(Fe-Fey)(Fe-Fez)=0 → la raíz gobernante es el Euler mínimo
    π²E·I/(Lc)² / A  (coincidencia < 0.5 %).
  * Sección con un eje de simetría (yo=0): la raíz menor de la cúbica
    general coincide con la fórmula cerrada flexo-torsional E4-5.
"""
import math

import pytest

from steelconnectionjm.flexural_torsional import (
    BucklingInput,
    elastic_buckling_stress,
    flexural_torsional_closed_form,
    critical_load,
)

E = 200_000.0   # MPa
G = 77_000.0    # MPa


def _doubly_symmetric():
    # Perfil tipo W doblemente simétrico (xo=yo=0)
    return BucklingInput(
        A=11_500.0, Ix=2.0e8, Iy=6.7e7, J=1.0e6, Cw=1.0e12,
        xo=0.0, yo=0.0, E=E, G=G, Lcx=4000.0, Lcy=4000.0, Lcz=4000.0,
    )


def test_doubly_symmetric_reduces_to_euler():
    inp = _doubly_symmetric()
    Fe = elastic_buckling_stress(inp)
    # Euler mínimo = el del eje débil (Iy)
    euler_y = math.pi ** 2 * E * inp.Iy / inp.Lcy ** 2 / inp.A
    assert Fe == pytest.approx(euler_y, rel=5e-3)


def test_critical_load_matches_euler():
    inp = _doubly_symmetric()
    Pcr = critical_load(inp)
    Pe = math.pi ** 2 * E * inp.Iy / inp.Lcy ** 2
    assert Pcr == pytest.approx(Pe, rel=5e-3)


def test_governing_is_minimum_of_three_modes():
    inp = _doubly_symmetric()
    Fe = elastic_buckling_stress(inp)
    assert Fe <= inp.Fex + 1e-6
    assert Fe <= inp.Fey + 1e-6
    assert Fe <= inp.Fez + 1e-6


def test_torsional_governs_for_short_open_section():
    # Sección abierta con baja rigidez torsional y poca longitud:
    # el modo torsional puede gobernar por debajo del flexional.
    inp = BucklingInput(
        A=8000.0, Ix=1.0e8, Iy=9.0e7, J=2.0e4, Cw=2.0e10,
        xo=0.0, yo=0.0, E=E, G=G, Lcx=2000.0, Lcy=2000.0, Lcz=2000.0,
    )
    Fe = elastic_buckling_stress(inp)
    assert Fe == pytest.approx(inp.Fez, rel=1e-6)
    assert inp.Fez < inp.Fey


def test_singly_symmetric_matches_closed_form():
    # Eje de simetría x → yo=0, xo≠0 (canal). La cúbica general debe dar
    # el mismo resultado que la fórmula cerrada E4-5.
    inp = BucklingInput(
        A=5000.0, Ix=1.2e8, Iy=3.0e7, J=5.0e4, Cw=8.0e10,
        xo=40.0, yo=0.0, E=E, G=G, Lcx=3500.0, Lcy=3500.0, Lcz=3500.0,
    )
    Fe_cubic = elastic_buckling_stress(inp)
    Fe_closed = flexural_torsional_closed_form(inp)
    assert Fe_cubic == pytest.approx(Fe_closed, rel=1e-6)


def test_ro2_and_H_definitions():
    inp = BucklingInput(
        A=5000.0, Ix=1.2e8, Iy=3.0e7, J=5.0e4, Cw=8.0e10,
        xo=40.0, yo=0.0, E=E, G=G, Lcx=3500.0, Lcy=3500.0, Lcz=3500.0,
    )
    ro2 = (inp.xo ** 2 + inp.yo ** 2) + (inp.Ix + inp.Iy) / inp.A
    assert inp.ro2 == pytest.approx(ro2)
    assert inp.H == pytest.approx(1.0 - (inp.xo ** 2 + inp.yo ** 2) / ro2)
