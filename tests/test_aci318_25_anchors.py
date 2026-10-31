"""Tests for ACI 318-25 Chapter 17 uncoupled anchor interaction and deep shear effects."""
from __future__ import annotations

import math
import pytest

from steeljoints.aci318_25_anchors import (
    Aci318Anchor2025Input,
    Aci318DeepShear2025Input,
    compute_size_effect_lambda_s,
    verify_anchor_interaction_aci318_25,
    verify_deep_shear_aci318_25,
)


def test_aci318_25_uncoupled_anchor_gain_over_aci318_19() -> None:
    # Case where concrete breakout governs tension (phi_N_nc = 100 kN < phi_N_sa = 180 kN)
    # and steel governs shear (phi_V_sa = 90 kN < phi_V_nc = 150 kN).
    # Under ACI 318-19 coupled equation: (75/100)^(5/3) + (60/90)^(5/3) = 0.619 + 0.509 = 1.128 > 1.0 (FAILS)
    # Under ACI 318-25 uncoupled equations:
    #   Steel:    (75/180)^2 + (60/90)^2 = 0.1736 + 0.4444 = 0.618 <= 1.0
    #   Concrete: (75/100)^(5/3) + (60/150)^(5/3) = 0.6188 + 0.2172 = 0.836 <= 1.0 (PASSES!)
    inp = Aci318Anchor2025Input(
        n_ua=75.0,
        v_ua=60.0,
        phi_n_sa=180.0,
        phi_v_sa=90.0,
        phi_n_nc=100.0,
        phi_v_nc=150.0,
    )
    res = verify_anchor_interaction_aci318_25(inp)
    assert res.status == "CALCULADO"
    assert res.passes is True
    assert res.governing_utilization_2025 == pytest.approx(0.836, rel=1e-2)
    assert res.legacy_coupled_utilization_2019 > 1.10
    assert res.governing_mode == "concrete"


def test_size_effect_and_deep_footing_arching_aci318_25() -> None:
    assert compute_size_effect_lambda_s(250.0) == pytest.approx(1.0)
    assert compute_size_effect_lambda_s(1000.0) == pytest.approx(math.sqrt(2.0 / 5.0))

    inp = Aci318DeepShear2025Input(
        bw=1200.0,
        d=800.0,
        fc=30.0,
        v_u=650.0,
        a_v=800.0,  # a_v / d = 1.0 < 2.0 -> arching_multiplier = 2.0
        rho_w=0.008,
    )
    res = verify_deep_shear_aci318_25(inp)
    assert res.arching_multiplier == pytest.approx(2.0)
    assert res.lambda_s == pytest.approx(math.sqrt(2.0 / (1.0 + 0.004 * 800.0)), abs=1e-4)
    assert res.vc_nominal == pytest.approx(957.913, rel=1e-3)
    assert res.phi_vc == pytest.approx(718.435, rel=1e-3)
    assert res.passes is True
