"""Tests para F.6 y F.7 en SteelConnectionJm welds.py.

F.6: polar_moment calcula el Ip real de cada cordón con su longitud y garganta propias.
F.7: min_size documenta e indexa por la parte más delgada según AISC 360-22 Tabla J2.4.
"""
import math
import pytest
from steelconnectionjm.welds import FilletWeld, WeldGroup


def test_polar_moment_different_weld_lengths():
    """Verifica que polar_moment no sobreescriba las longitudes con welds[0].length."""
    w1 = FilletWeld(weld_size=6.0, length=100.0)  # a = 6/sqrt(2) = 4.2426 mm
    w2 = FilletWeld(weld_size=6.0, length=300.0)  # a = 6/sqrt(2) = 4.2426 mm
    
    # Colocados simétricamente en x=0, y=-150 y y=150
    # Centroide cy = 75 (por ser w2 3 veces mayor que w1)
    wg = WeldGroup(
        welds=[w1, w2],
        positions=[(0.0, -150.0), (0.0, 150.0)],
    )
    
    # Ip real = Ip_self(w1) + Aw1*r1^2 + Ip_self(w2) + Aw2*r2^2
    a = 6.0 / math.sqrt(2.0)
    Aw1 = a * 100.0
    Aw2 = a * 300.0
    total_Aw = Aw1 + Aw2
    cy = (Aw1 * (-150.0) + Aw2 * 150.0) / total_Aw  # = 75.0 mm
    
    r1 = abs(-150.0 - cy)  # = 225.0 mm
    r2 = abs(150.0 - cy)   # = 75.0 mm
    
    Ip1_expected = a * (100.0**3) / 12.0 + Aw1 * (r1**2)
    Ip2_expected = a * (300.0**3) / 12.0 + Aw2 * (r2**2)
    expected_Ip = Ip1_expected + Ip2_expected
    
    actual_Ip = wg.polar_moment()
    assert actual_Ip == pytest.approx(expected_Ip, rel=1e-6)

    # Con el bug antiguo (usar welds[0].length=100 para ambos):
    buggy_Ip2_self = a * (100.0**3) / 12.0
    buggy_Ip = (a * (100.0**3) / 12.0 + Aw1 * (r1**2)) + (buggy_Ip2_self + Aw2 * (r2**2))
    assert actual_Ip > buggy_Ip, "El Ip corregido debe incluir la inercia real del cordón de 300 mm"


def test_min_size_aisc_table_j2_4_thinner_part():
    """AISC 360-22 Tabla J2.4 indexa por el espesor de la parte más delgada."""
    w = FilletWeld(8.0, 100.0)
    
    # Espesor <= 6.35 mm (1/4") -> mín 3.175 mm (1/8")
    assert w.min_size(t_thinner=5.0) == 3.175
    assert w.min_size(t_thinner=6.35) == 3.175
    
    # 6.35 < t <= 12.7 mm (1/2") -> mín 4.762 mm (3/16")
    assert w.min_size(t_thinner=8.0) == 4.762
    assert w.min_size(t_thinner=12.7) == 4.762
    
    # 12.7 < t <= 19.05 mm (3/4") -> mín 6.35 mm (1/4")
    assert w.min_size(t_thinner=15.0) == 6.35
    assert w.min_size(t_thinner=19.05) == 6.35
    
    # t > 19.05 mm -> mín 8.0 mm (5/16")
    assert w.min_size(t_thinner=20.0) == 8.0
    assert w.min_size(t_thinner=30.0) == 8.0
    
    # Retrocompatibilidad posicional y de keyword alias
    assert w.min_size(10.0) == 4.762
    assert w.min_size(t_thicker=10.0) == 4.762
