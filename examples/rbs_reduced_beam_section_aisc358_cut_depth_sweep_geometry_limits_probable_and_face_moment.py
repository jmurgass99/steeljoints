"""Sección de viga reducida (RBS, «dogbone», AISC 358 cap. 5) en una W610 × 125 (W24 × 84) de A992: barrido de la profundidad del corte c, límites geométricos de §5.8, módulo plástico reducido, momento probable Mpr, cortante en la rótula y momento en la cara del pilar comparado con φd·Mpe.

`services.rbs.design_rbs(RBSInput(d, bf, tf, tw, Zx, Fy, Fu, a, b, c, L_clear_m, wu, Ry, Mu_demand_kNm))` y
`memos.rbs_aisc358.rbs_aisc358_memo` (mismo cálculo con memoria LaTeX). Z_RBS = Zx − 2·c·tf·(d − tf),
Mpr = Cpr·Ry·Fy·Z_RBS, Mf = Mpr + Vpr·(a + b/2).

Ejecutar:  python examples/rbs_reduced_beam_section_aisc358_cut_depth_sweep_geometry_limits_probable_and_face_moment.py
"""
from steeljoints.codes.aisc358 import rbs_geometry
from steeljoints.memos.rbs_aisc358 import rbs_aisc358_memo
from steeljoints.services.rbs import RBSInput, design_rbs

D, BF, TF, TW, ZX, FY, FU = 612.0, 229.0, 19.6, 11.9, 3.67e6, 345.0, 450.0


def main() -> None:
    lim = rbs_geometry(BF, D)
    print(f"W610 × 125: d = {D:.0f}, bf = {BF:.0f}, tf = {TF}, Zx = {ZX / 1e6:.2f}e6 mm³, A992 (Fy 345, Ry 1,1). Límites §5.8: {lim}\n")
    a, b = 0.625 * BF, 0.75 * D
    Mpe = 1.1 * FY * ZX / 1e6
    print(f"a = {a:.0f} mm, b = {b:.0f} mm, luz libre 7,0 m, wu = 30 kN/m. φd·Mpe = 1,0·Ry·Fy·Zx = {Mpe:.0f} kN·m\n")
    print(f"  {'c [mm]':>6} {'c/bf':>5} {'Z_RBS/Zx':>8} {'Mpr':>7} {'Vpr':>6} {'Mf':>7} {'Mf/φdMpe':>8} {'geometría':>9} {'estado':>18}")
    for c in (15.0, 25.0, 35.0, 45.0, 57.0, 65.0):
        r = design_rbs(RBSInput(d_mm=D, bf_mm=BF, tf_mm=TF, tw_mm=TW, Zx_mm3=ZX, Fy_MPa=FY, Fu_MPa=FU, a_mm=a, b_mm=b, c_mm=c,
                                L_clear_m=7.0, wu_kN_per_m=30.0, Mu_demand_kNm=900.0))
        print(f"  {c:6.0f} {c / BF:5.3f} {r.Z_RBS_mm3 / ZX:8.3f} {r.M_pr_kNm:7.0f} {r.V_pr_kN:6.0f} {r.M_f_kNm:7.0f} {r.M_f_kNm / Mpe:8.3f} {'OK' if r.is_geometry_ok else 'fuera':>9} {r.calculation_status.value:>18}")
    c_ok = next(c for c in range(10, 70) if design_rbs(RBSInput(d_mm=D, bf_mm=BF, tf_mm=TF, tw_mm=TW, Zx_mm3=ZX, Fy_MPa=FY, Fu_MPa=FU, a_mm=a, b_mm=b, c_mm=float(c),
                                                                L_clear_m=7.0, wu_kN_per_m=30.0)).M_f_kNm <= Mpe)
    print(f"\nEl corte más pequeño que deja Mf ≤ φd·Mpe es c ≈ {c_ok} mm ({c_ok / BF:.2f}·bf), dentro del rango 0,1–0,25·bf.")
    zr = ZX - 2 * 45.0 * TF * (D - TF)
    print(f"A mano con c = 45 mm: Z_RBS = {ZX:.3g} − 2·45·{TF}·({D:.0f} − {TF}) = {zr:.4g} mm³; Mpr = 1,15·1,1·345·Z_RBS = {1.15 * 1.1 * 345 * zr / 1e6:.0f} kN·m")
    texto, m = rbs_aisc358_memo(beam_d=D, beam_bf=BF, beam_tf=TF, beam_Z_x=ZX, a=a, b=b, c=45.0, L_clear=7.0, wu=30.0)
    print(f"Memoria rbs_aisc358_memo con c = 45 mm: Mpr = {m.M_pr_kNm:.0f} kN·m, Mf = {m.M_f_kNm:.0f} kN·m; devuelve (texto de {len(texto)} caracteres, resultado).")
    print("El estado CALCULADO_* compara la demanda Mu = 900 kN·m con la capacidad; la comprobación de la cara del pilar (Mf ≤ φd·Mpe) es la columna Mf/φdMpe.")


if __name__ == "__main__":
    main()
