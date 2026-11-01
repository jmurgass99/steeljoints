"""Bloque de cortante de una chapa de 10 mm con una fila de tres tornillos M20 (paso 70, extremo 40, borde lateral 40 mm), calculado con AISC 360-22 §J4.3, EN 1993-1-8 §3.10.2, AS 4100 §9.1.9 y NSR-10 F.2, con tracción uniforme y no uniforme.

`block_shear_multi.block_shear(BlockShearInput(Agv, Anv, Ant, Fy, Fu, Ubs), code)` con code «US», «EU», «AU»
y «CO»; `block_shear.block_shear_strength(..., code)` y `codes.nsr10_f2.design_block_shear_nsr10` como contraste.

Ejecutar:  python examples/block_shear_aisc_en1993_as4100_nsr10_same_bolted_plate_ubs_and_governing_path.py
"""
from steeljoints.block_shear import block_shear_strength
from steeljoints.block_shear_multi import BlockShearInput, block_shear
from steeljoints.codes.nsr10_f2 import NSR10BlockShearInput, design_block_shear_nsr10


def main() -> None:
    t, d0, p, e1, e2, n = 10.0, 22.0, 70.0, 40.0, 40.0, 3
    Agv = ((n - 1) * p + e1) * t
    Anv = Agv - (n - 0.5) * d0 * t
    Ant = (e2 - d0 / 2) * t
    fy, fu = 275.0, 430.0
    print(f"S275 (fy {fy:.0f} / fu {fu:.0f} MPa): Agv = {Agv:.0f}, Anv = {Anv:.0f}, Ant = {Ant:.0f} mm²\n")
    print(f"  {'norma':28} {'Ubs':>4} {'Rn [kN]':>8} {'Rd [kN]':>8} {'factor':>7} {'modo':>9}")
    res = {}
    for code, nombre in (("US", "AISC 360-22 §J4.3"), ("EU", "EN 1993-1-8 §3.10.2 (Ec. 3.9)"), ("AU", "AS 4100 §9.1.9"), ("CO", "NSR-10 F.2 (vía AISC)")):
        for ubs in (1.0, 0.5):
            if code == "EU" and ubs == 0.5:
                continue
            r = block_shear(BlockShearInput(Agv, Anv, Ant, fy, fu, Ubs=ubs), code)
            res[(code, ubs)] = r.Rd_kN
            print(f"  {nombre:28} {ubs:4.1f} {r.Rn_kN:8.1f} {r.Rd_kN:8.1f} {r.phi_or_gamma:7.3f} {r.governing:>9}")
    a = block_shear_strength(Agv, Anv, Ant, fy, fu, Ubs=1.0, code="AISC")
    e = block_shear_strength(Agv, Anv, Ant, fy, fu, code="EC3")
    c = design_block_shear_nsr10(NSR10BlockShearInput(Agv, Anv, Ant, fy, fu, 1.0))
    print(f"\nContraste: block_shear_strength AISC φRn = {a['phi_Rn_kN']:.1f} kN ({a['governs']}), EC3 Veff = {e['Veff_kN']:.1f} kN; NSR-10 φRn = {c.Rd_kN:.1f} kN ({c.governing}).")
    print(f"  A mano AISC: mín(0,6·{fu:.0f}·{Anv:.0f}, 0,6·{fy:.0f}·{Agv:.0f}) + {fu:.0f}·{Ant:.0f} = {min(0.6 * fu * Anv, 0.6 * fy * Agv) / 1e3 + fu * Ant / 1e3:.1f} kN → ×0,75 = {0.75 * (min(0.6 * fu * Anv, 0.6 * fy * Agv) + fu * Ant) / 1e3:.1f} kN")
    print(f"  A mano EC3: {fu:.0f}·{Ant:.0f}/1,25 + {fy:.0f}·{Anv:.0f}/(√3·1,0) = {(fu * Ant / 1.25 + fy * Anv / 3 ** 0.5) / 1e3:.1f} kN")
    v2 = (0.5 * fu * Ant / 1.25 + fy * Anv / 3 ** 0.5) / 1e3
    print(f"\nEC3 con la Ec. 3.9 queda un {(res[('EU', 1.0)] / res[('US', 1.0)] - 1) * 100:+.0f} % respecto a AISC; AS 4100 y NSR-10 coinciden con AISC. "
          f"Ubs = 0,5 (tracción no uniforme) baja AISC a {res[('US', 0.5)]:.1f} kN.")
    print(f"La Ec. 3.9 supone un grupo simétrico con carga centrada. Un bloque en L como este, con una sola fila junto al borde, se parece más al caso de la Ec. 3.10 "
          f"(0,5·fu·Ant/γM2 + fy·Anv/(√3·γM0) = {v2:.1f} kN), que el módulo no implementa: calcúlala aparte si tu unión es de ese tipo.")


if __name__ == "__main__":
    main()
