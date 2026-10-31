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

from steeljoints.flexural_torsional import (
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
    """GOLDEN. Sección doblemente simétrica (xo=yo=0) reduce al pandeo flexional de Euler.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings.
      - Chapter E §E4: Torsional and Flexural-Torsional Buckling of Members without Slender Elements.
        * Eq. (E4-4): Fe = min(Fex, Fey, Fez).
    """
    inp = _doubly_symmetric()
    Fe = elastic_buckling_stress(inp)
    # Euler mínimo = el del eje débil (Iy)
    euler_y = math.pi ** 2 * E * inp.Iy / inp.Lcy ** 2 / inp.A
    assert Fe == pytest.approx(euler_y, rel=5e-3)


def test_critical_load_matches_euler():
    """GOLDEN. Carga crítica elástica de Euler en sección doblemente simétrica.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings, Chapter E §E4.
    """
    inp = _doubly_symmetric()
    Pcr = critical_load(inp)
    Pe = math.pi ** 2 * E * inp.Iy / inp.Lcy ** 2
    assert Pcr == pytest.approx(Pe, rel=5e-3)


def test_governing_is_minimum_of_three_modes():
    """CARACTERIZACIÓN. La tensión elástica es la menor de los 3 modos desacoplados (AISC 360-16 Eq. E4-4)."""
    inp = _doubly_symmetric()
    Fe = elastic_buckling_stress(inp)
    assert Fe <= inp.Fex + 1e-6
    assert Fe <= inp.Fey + 1e-6
    assert Fe <= inp.Fez + 1e-6


def test_torsional_governs_for_short_open_section():
    """CARACTERIZACIÓN. Sección abierta corta donde el pandeo torsional gobierna sobre el flexional."""
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
    """GOLDEN. Sección con simetría simple coincide con fórmula cerrada AISC 360-16 Eq. E4-5.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings.
      - Chapter E §E4, Eq. (E4-5): Fe = ((Fey + Fez)/(2*H)) * (1 - sqrt(1 - 4*Fey*Fez*H/(Fey+Fez)^2)).
    """
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
    """GOLDEN. Definición analítica de radio de giro polar ro² y factor H según AISC 360-16 Eq. E4-9 y E4-10.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings.
      - Chapter E §E4, Eq. (E4-9): ro² = xo² + yo² + (Ix + Iy)/Ag.
      - Chapter E §E4, Eq. (E4-10): H = 1 - (xo² + yo²)/ro².
    """
    inp = BucklingInput(
        A=5000.0, Ix=1.2e8, Iy=3.0e7, J=5.0e4, Cw=8.0e10,
        xo=40.0, yo=0.0, E=E, G=G, Lcx=3500.0, Lcy=3500.0, Lcz=3500.0,
    )
    ro2 = (inp.xo ** 2 + inp.yo ** 2) + (inp.Ix + inp.Iy) / inp.A
    assert inp.ro2 == pytest.approx(ro2)
    assert inp.H == pytest.approx(1.0 - (inp.xo ** 2 + inp.yo ** 2) / ro2)
