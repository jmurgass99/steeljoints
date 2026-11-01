"""Placa base de un pilar W310 × 97 (310 × 305 mm) con 2000 kN de compresión centrada (AISC Design Guide 1, 3.ª ed.): aplastamiento del hormigón con y sin confinamiento, voladizos m, n y λn′, espesor necesario y tamaño de placa.

`BasePlate(Pu, column_d, column_bf, plate_B, plate_N, plate_Fy, fc_concrete, A2_A1).design()`. OJO: `A2_A1` es
√(A2/A1), no el cociente de áreas (tope 2,0). φc·Fp = 0,65·0,85·f′c·√(A2/A1); tp = l·√(2·fp/(0,9·Fy)) con
l = máx(m, n, λn′). `services.base_plate.design_base_plate` delega en la clase y compara con el espesor dado.

Ejecutar:  python examples/base_plate_aisc_dg1_concentric_axial_bearing_confinement_and_thickness_sweep.py
"""
from math import sqrt

from steeljoints import BasePlate
from steeljoints.services.base_plate import BasePlateInput, design_base_plate

COL = dict(column_d=310.0, column_bf=305.0)


def main() -> None:
    Pu = 2000.0
    print(f"Pu = {Pu:.0f} kN, hormigón f′c = 28 MPa, placa Fy = 250 MPa:\n")
    print(f"  {'B × N [mm]':>11} {'√(A2/A1)':>8} {'fp':>6} {'φFp':>6} {'aplast.':>7} {'m':>6} {'n':>6} {'λn′':>6} {'tp,req':>7}")
    for B, N, conf in ((400, 400, 1.0), (450, 450, 1.0), (500, 500, 1.0), (400, 400, 1.5), (400, 400, 2.0), (600, 600, 1.0)):
        r = BasePlate(Pu=Pu, plate_B=B, plate_N=N, plate_Fy=250.0, fc_concrete=28.0, A2_A1=conf, **COL).design()
        bc, tk = r["checks"][0], r["checks"][1]
        print(f"  {B:5.0f} × {N:3.0f} {conf:8.2f} {bc['fp_MPa']:6.2f} {bc['phi_Fp_MPa']:6.2f} {bc['utilization']:7.3f} {tk['m_mm']:6.1f} {tk['n_mm']:6.1f} {tk['lambda_n_prime_mm']:6.1f} {tk['tp_required_mm']:7.1f}")
    A1_min = Pu * 1e3 / (0.65 * 0.85 * 28.0)
    print(f"\nÁrea mínima sin confinamiento: A1 = Pu/(0,65·0,85·f′c) = {A1_min:.0f} mm² → placa cuadrada de {sqrt(A1_min):.0f} mm.")
    r = BasePlate(Pu=Pu, plate_B=450, plate_N=450, plate_Fy=250.0, fc_concrete=28.0, **COL).required_thickness()
    fp = Pu * 1e3 / 450 ** 2
    print(f"A mano, placa de 450 mm: m = (450 − 0,95·310)/2 = {(450 - 0.95 * 310) / 2:.1f}, n = (450 − 0,8·305)/2 = {(450 - 0.8 * 305) / 2:.1f} mm; "
          f"tp = {r['l_crit_mm']:.1f}·√(2·{fp:.2f}/(0,9·250)) = {r['l_crit_mm'] * sqrt(2 * fp / 225):.1f} mm")
    print("\nServicio (con espesor dado):")
    for tp in (25.0, 32.0, 40.0):
        s = design_base_plate(BasePlateInput(Bp_mm=450, Np_mm=450, tp_mm=tp, d_col_mm=310, bf_col_mm=305, fc_MPa=28.0, fy_plate_MPa=250.0, Pu_kN=Pu))
        print(f"  tp = {tp:4.0f} mm → tp,req = {s.tp_required_mm:.1f} mm, DCR = {s.DCR:.2f}")
    print("\nConfinar el hormigón (pedestal mayor que la placa) sube Fp hasta el doble y deja usar una placa más pequeña, pero el espesor lo fija el voladizo mayor. "
          "Pasa √(A2/A1), no A2/A1: con una zapata cuatro veces mayor que la placa el valor es 2,0.")


if __name__ == "__main__":
    main()
