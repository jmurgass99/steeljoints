"""Golden test para interacción tracción-cortante combinada en pernos según AISC 360-16 §J3.7.

Fuente:
  AISC 360-16: Specification for Structural Steel Buildings, Section J3.7 (Combined Tension and Shear in Bearing-Type Connections).
  Eq. J3-3a:
      F'nt = 1.3·Fnt - (Fnt / (φ·Fnv))·frv <= Fnt
  donde:
      Fnt = nominal tensile stress from Table J3.2 (MPa)
      Fnv = nominal shear stress from Table J3.2 (MPa)
      frv = required shear stress = Vuv / Ab (MPa)
      φ   = 0.75 (resistance factor for tension/shear)

Derivación analítica cerrada a mano:
------------------------------------
Perno ASTM A325, d = 3/4 in (19.05 mm):
  Ab = π · 19.05² / 4 = 285.022958 mm²
  Fnt = 620.0 MPa (Tabla J3.2)
  Fnv = 372.0 MPa (Tabla J3.2, roscas en plano de corte)
  φ = 0.75

Caso 1: Cortante nulo (frv = 0.0 MPa):
  F'nt = min(1.3 · 620.0 - 0, 620.0) = min(806.0, 620.0) = 620.0 MPa.
  φ·Rnt = 0.75 · 620.0 · 285.022958 / 1000 = 132.535676 kN.

Caso 2: Cortante actuante Vuv = 40.0 kN (40,000 N) por perno:
  frv = 40000 / 285.022958 = 140.339570 MPa.
  F'nt = 1.3 · 620.0 - (620.0 / (0.75 · 372.0)) · 140.339570
       = 806.0 - (620.0 / 279.0) · 140.339570
       = 806.0 - 2.222222 · 140.339570 = 806.0 - 311.865711 = 494.134289 MPa.
  Como 0 <= 494.134289 <= 620.0:
  F'nt = 494.134289 MPa.
  φ·R'nt = 0.75 · 494.134289 · 285.022958 / 1000 = 105.630095 kN.

Caso 3: Cortante severo Vuv = 120.0 kN (120,000 N):
  frv = 120000 / 285.022958 = 421.018710 MPa.
  F'nt_raw = 806.0 - 2.222222 · 421.018710 = 806.0 - 935.597133 = -129.597133 MPa.
  Cota inferior: F'nt = max(0.0, -129.597133) = 0.0 MPa.
  φ·R'nt = 0.0 kN.
"""
from __future__ import annotations

import math
import pytest

from steeljoints.bolts import Bolt
from steeljoints.end_plate import EndPlate


def test_golden_aisc_j3_7_bolt_combined_tension_shear_exact():
    """GOLDEN. Verificación de AISC 360-16 §J3.7 con valores analíticos cerrados.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings.
      - Section J3.7: Combined Tension and Shear in Bearing-Type Connections.
        * Eq. (J3-3a): F'nt = 1.3·Fnt - (Fnt / (φ·Fnv))·frv <= Fnt.
        * Tabla J3.2: Fnt = 620 MPa (90 ksi), Fnv = 372 MPa (54 ksi) para ASTM A325.
        * Factor de resistencia φ = 0.75.
    """
    bolt = Bolt(19.05, "A325", "AISC")
    phi = 0.75

    # 1. Caso frontera: frv = 0 -> F'nt == Fnt (620.5 MPa, Ab = 285.0 mm2)
    #    phi*Rnt = 0.75 * 620.5 * 285.0 / 1000 = 132.631875 kN
    cap_zero_shear = bolt.aisc_combined_tension_shear(Vuv=0.0, phi=phi)
    pure_tension = bolt.aisc_tension_strength(phi=phi)
    assert cap_zero_shear == pytest.approx(pure_tension, rel=1e-9)
    assert cap_zero_shear / 1000.0 == pytest.approx(132.631875, rel=1e-5)

    # 2. Caso con cortante Vuv = 40 kN
    #    frv = 40000 / 285.0 = 140.350877 MPa
    #    F'nt = 1.3*620.5 - (620.5 / (0.75*372.3)) * 140.350877 = 494.759162 MPa
    #    phi*R'nt = 0.75 * 494.759162 * 285.0 / 1000 = 105.754771 kN
    cap_with_shear = bolt.aisc_combined_tension_shear(Vuv=40000.0, phi=phi)
    assert cap_with_shear < pure_tension
    assert cap_with_shear / 1000.0 == pytest.approx(105.754771, rel=1e-5)

    # 3. Caso con cortante severo -> cota inferior no negativa (F'nt >= 0)
    cap_high_shear = bolt.aisc_combined_tension_shear(Vuv=120000.0, phi=phi)
    assert cap_high_shear == 0.0


def test_golden_end_plate_wired_j3_7_dcr_increase():
    """GOLDEN. Comprueba que EndPlate aplica la interacción J3.7 y eleva el DCR de los pernos.

    Fuente Normativa:
      - AISC 360-16: Specification for Structural Steel Buildings.
      - Section J3.7: Combined Tension and Shear in Bearing-Type Connections, Eq. (J3-3a).
    """
    # Unión con 4 pernos (2 filas de 2 pernos), Mu = 100 kNm, Vu = 160 kN
    # Vuv por perno = 160 / 4 = 40.0 kN
    ep = EndPlate(
        Mu=100.0,
        Vu=160.0,
        beam_depth=400.0,
        beam_tf=13.0,
        beam_bf=180.0,
        bolt_diameter=19.05,
        bolt_grade="A325",
        plate_thickness=22.0,
        n_bolt_rows=2,
    )

    t_check = ep.bolt_tension_check(phi=0.75)
    
    # Capacidad reducida por interacción J3.7:
    assert t_check["phi_Rnt_kN"] == pytest.approx(105.755, rel=1e-4)
    # Demanda a tracción por flexión: T_demand = 100e6 / (400-13) / 4 / 1000 = 64.599 kN
    assert t_check["T_demand_kN"] == pytest.approx(64.599, rel=1e-3)
    # DCR con interacción: 64.599 / 105.755 = 0.6108
    assert t_check["utilization"] == pytest.approx(64.599 / 105.755, abs=1e-3)
    assert t_check["is_ok"] is True


def test_golden_end_plate_zero_capacity_does_not_report_zero_utilization():
    """GOLDEN. Capacidad nula bajo demanda positiva debe reportar inf y no 0.0."""
    ep_zero = EndPlate(
        Mu=100.0,
        Vu=1000.0,  # Cortante destructivo que anula capacidad a tracción F'nt = 0
        beam_depth=400.0,
        beam_tf=13.0,
        beam_bf=180.0,
        bolt_diameter=19.05,
        bolt_grade="A325",
        plate_thickness=22.0,
        n_bolt_rows=2,
    )
    t_chk = ep_zero.bolt_tension_check(phi=0.75)
    assert t_chk["phi_Rnt_kN"] == 0.0
    assert t_chk["utilization"] == float("inf")
    assert t_chk["is_ok"] is False
