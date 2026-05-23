"""Tests block shear multi-código."""
import pytest

from steelconnectionjm.block_shear_multi import BlockShearInput, block_shear


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
