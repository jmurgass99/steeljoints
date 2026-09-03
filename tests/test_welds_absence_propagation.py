"""
tests/test_welds_absence_propagation.py — la ausencia se propaga como ausencia
en ``steelconnectionjm.welds``.

Dos defectos de tipo "aprobado silencioso" en ``welds.py``:

1. ``WeldGroup.utilization`` (línea ~178): cuando la capacidad de diseño
   ``phi_Rn_per_unit`` no se aporta (0.0 o negativa), la utilización se emitía
   como ``0`` y ``is_ok=True`` — la lectura OPUESTA a la verdadera. Medido:
   la MISMA demanda con capacidad presente da utilización 1.7806 / is_ok=False.
   El idioma correcto para esta MISMA magnitud ya existe en el paquete, en
   ``weld_group.py:158`` (``... if phi_Rn_per_mm > 0 else float("inf")``).

2. ``FilletWeld.ec3_strength`` (línea ~84): ``_EC3_BETA_W.get(grade, 0.85)``
   asumía en silencio S275 para cualquier grado desconocido o ausente
   (``None``), sobrestimando Fw,Rd un +17.6 % frente a S460 (β_w=1.00).
   β_w es EN 1993-1-8:2005 Tabla 4.1; no hay valor normativo "por defecto".

Los valores de utilización/resistencia del CAMINO SANO que aparecen abajo son
CARACTERIZACIÓN (capturados ejecutando la implementación), no goldens
normativos; se marcan como tales. Lo que sí es normativo es β_w (Tabla 4.1).
"""
from __future__ import annotations

import math

import pytest

from jmstructural_common.audit_status import CalculationStatus
from steelconnectionjm.weld_group import WeldGroupElastic, WeldSegment
from steelconnectionjm.welds import FilletWeld, WeldGroup


def _group() -> WeldGroup:
    """Grupo sano: dos cordones de 8 mm x 200 mm separados 200 mm."""
    return WeldGroup(
        welds=[FilletWeld(8.0, 200.0), FilletWeld(8.0, 200.0)],
        positions=[(0.0, -100.0), (0.0, 100.0)],
    )


# Demanda usada en todo el fichero (una conexión REALMENTE sobrecargada).
_VU = 500_000.0        # N
_MU = 50_000_000.0     # N·mm
# φRn/mm para E70 y w=8 mm: φ·0.60·FEXX·a = 0.75·0.60·482.6·(8/√2)
_CAP = 0.75 * 0.60 * 482.6 * (8.0 / math.sqrt(2.0))


# ---------------------------------------------------------------------------
# 1) WeldGroup.utilization — capacidad ausente
# ---------------------------------------------------------------------------

class TestUtilizationAbsentCapacity:
    def test_healthy_path_is_a_failing_connection(self):
        """Caracterización: con capacidad presente esta conexión FALLA."""
        res = _group().utilization(Vu=_VU, Mu=_MU, phi_Rn_per_unit=_CAP)
        assert res["utilization"] == pytest.approx(1.7806, abs=1e-4)
        assert res["is_ok"] is False

    @pytest.mark.parametrize("cap", [0.0, -1.0])
    def test_absent_capacity_is_never_a_pass(self, cap):
        """La ausencia de capacidad NO puede leerse como holgura."""
        res = _group().utilization(Vu=_VU, Mu=_MU, phi_Rn_per_unit=cap)
        assert res["is_ok"] is False, "capacidad ausente emitida como APROBADO"
        assert res["utilization"] != 0, "utilización inventada como 0"

    def test_absent_capacity_propagates_as_infinity(self):
        """Mismo idioma que weld_group.py:158 para la MISMA magnitud."""
        res = _group().utilization(Vu=_VU, Mu=_MU, phi_Rn_per_unit=0.0)
        assert res["utilization"] == float("inf")

    def test_absent_capacity_status_is_no_calculado(self):
        res = _group().utilization(Vu=_VU, Mu=_MU, phi_Rn_per_unit=0.0)
        assert res["status"] == CalculationStatus.NO_CALCULADO
        assert "phi_Rn_per_unit" in res["missing_inputs"]

    def test_demand_is_still_reported_when_capacity_absent(self):
        """La demanda SÍ se computó: publicarla, es lo único que se sabe."""
        res = _group().utilization(Vu=_VU, Mu=_MU, phi_Rn_per_unit=0.0)
        assert res["max_stress_N_mm2"] == pytest.approx(386.699, abs=1e-3)

    def test_sibling_implementations_agree_on_absence(self):
        """welds.WeldGroup y weld_group.WeldGroupElastic, misma convención."""
        mine = _group().utilization(Vu=_VU, Mu=_MU, phi_Rn_per_unit=0.0)
        sibling = WeldGroupElastic(
            segments=[WeldSegment(0.0, -100.0, 0.0, 100.0, 8.0)],
            Vy=-_VU, Mz=_MU,
        ).utilization(FEXX_MPa=0.0, w_mm=8.0)
        assert mine["utilization"] == sibling["utilization"] == float("inf")
        assert mine["is_ok"] is sibling["is_ok"] is False

    def test_healthy_path_status_is_calculado(self):
        res = _group().utilization(Vu=_VU, Mu=_MU, phi_Rn_per_unit=_CAP)
        assert res["status"] == CalculationStatus.CALCULADO_FALLA
        assert res["missing_inputs"] == []


# ---------------------------------------------------------------------------
# 2) WeldGroup.utilization — Ip degenerado con momento aplicado
# ---------------------------------------------------------------------------

class TestUtilizationDegenerateIp:
    class _DegenerateGroup(WeldGroup):
        def polar_moment(self) -> float:
            return 0.0

    @classmethod
    def _degenerate(cls) -> WeldGroup:
        """Grupo sintético con polar_moment() == 0 para verificar propagación de ausencia."""
        return cls._DegenerateGroup(
            welds=[FilletWeld(8.0, 200.0)],
            positions=[(0.0, 0.0)],
        )

    def test_precondition_ip_is_zero(self):
        assert self._degenerate().polar_moment() == 0.0

    def test_zero_ip_with_moment_does_not_discard_the_moment(self):
        """Mu=900 kN·m desaparecía y la conexión salía APROBADA (util 0.4167)."""
        res = self._degenerate().utilization(
            Vu=100_000.0, Mu=900_000_000.0, phi_Rn_per_unit=1200.0
        )
        assert res["is_ok"] is False, "momento descartado y emitido APROBADO"
        assert res["status"] == CalculationStatus.NO_CALCULADO
        assert "polar_moment_Ip" in res["missing_inputs"]

    def test_zero_ip_without_moment_is_legitimate(self):
        """Sin momento no hay nada que distribuir: Ip=0 no es una ausencia."""
        res = self._degenerate().utilization(
            Vu=100_000.0, Mu=0.0, phi_Rn_per_unit=1200.0
        )
        assert res["missing_inputs"] == []
        assert res["status"] == CalculationStatus.CALCULADO_CUMPLE
        assert res["is_ok"] is True


# ---------------------------------------------------------------------------
# 3) FilletWeld.ec3_strength — β_w ausente/desconocido
# ---------------------------------------------------------------------------

class TestEc3BetaW:
    @staticmethod
    def _w(grade):
        return FilletWeld(8.0, 200.0, code="EC3", steel_grade=grade)

    @pytest.mark.parametrize(
        "grade, beta_w",
        [("S235", 0.80), ("S275", 0.85), ("S355", 0.90),
         ("S420", 1.00), ("S460", 1.00)],
    )
    def test_table_4_1_values_are_normative(self, grade, beta_w):
        """EN 1993-1-8:2005 Tabla 4.1 — Fw,Rd = fu/(β_w·√3·γM2)·a·L."""
        fu, gamma_M2 = 550.0, 1.25
        w = self._w(grade)
        expected = fu / (beta_w * math.sqrt(3.0) * gamma_M2) * w.a * w.length
        assert w.ec3_strength(fu=fu) == pytest.approx(expected, rel=1e-12)

    @pytest.mark.parametrize("grade", ["S690", "", "  ", "Q345", None])
    def test_unknown_or_absent_grade_raises(self, grade):
        """Sin grado no hay β_w: no se inventa S275."""
        with pytest.raises(ValueError, match="beta_w|β_w|desconocido"):
            self._w(grade).ec3_strength(fu=550.0)

    def test_case_is_normalised_not_silently_defaulted(self):
        """'s460' era 338.126 kN (β_w=0.85); S460 real es 287.407 kN."""
        assert self._w("s460").ec3_strength(fu=550.0) == pytest.approx(
            self._w("S460").ec3_strength(fu=550.0), rel=1e-12
        )

    def test_silent_default_overestimated_s460_by_17_6_percent(self):
        """Cuantifica la sobrestimación que producía el 0.85 silencioso."""
        w = self._w("S460")
        fu, gamma_M2 = 550.0, 1.25
        silent = fu / (0.85 * math.sqrt(3.0) * gamma_M2) * w.a * w.length
        honest = w.ec3_strength(fu=fu)
        assert silent / honest == pytest.approx(1.00 / 0.85, rel=1e-12)
        assert silent / honest == pytest.approx(1.1765, abs=1e-4)
