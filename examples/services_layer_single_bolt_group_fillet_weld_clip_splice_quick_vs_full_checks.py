"""La capa de servicios (`steeljoints.services`): funciones con entrada y salida en dataclasses, pensadas para la API REST y la serialización a JSON. Perno individual AISC y EC3 con la distancia al borde, línea de pernos con momento, cordón de filete, y el doble angular y el empalme en modo rápido frente a su comprobación completa (`full_aisc_checks=True` delega en `ClipAngle`; `n_bolts_web > 0` añade el grupo de pernos del alma con `SpliceConnection`).

`design_single_bolt`, `design_bolt_group`, `design_fillet_weld`, `design_clip_angle`, `design_splice`.

Ejecutar:  python examples/services_layer_single_bolt_group_fillet_weld_clip_splice_quick_vs_full_checks.py
"""
from dataclasses import asdict

from steeljoints import Bolt
from steeljoints.services.bolts import BoltGroupInput, SingleBoltInput, design_bolt_group, design_single_bolt
from steeljoints.services.clip_angle import ClipAngleInput, design_clip_angle
from steeljoints.services.splice import SpliceInput, design_splice
from steeljoints.services.welds import FilletWeldInput, design_fillet_weld


def main() -> None:
    print("Perno individual en chapa de 10 mm (Fu 400 MPa), distancia al borde variable:")
    for std, grade, d in (("AISC", "A325", 19.05), ("EC3", "8.8", 20.0)):
        for e in (25.0, 30.0, 40.0, 60.0):
            r = design_single_bolt(SingleBoltInput(grade, d, standard=std, plate_thickness_mm=10.0, plate_fu_MPa=400.0, edge_distance_mm=e))
            print(f"  {std:4} {grade:4} e = {e:4.0f} mm → Rn corte {r.Rn_shear_kN:6.1f} | aplastamiento {r.Rn_bearing_kN:6.1f} kN → gobierna {r.governs}")
    r = design_single_bolt(SingleBoltInput("A325", 19.05, edge_distance_mm=30.0))
    b = Bolt(19.05, "A325", "AISC").aisc_shear_strength() / 1e3
    print(f"  φRn corte del servicio {r.Rd_shear_kN:.1f} kN frente a {b:.1f} kN de la clase Bolt (el servicio usa Fnv = 0,45·Fu en vez de la Tabla J3.2)")
    print(f"  Notas: {r.notes[1:]}")
    print("\nLínea de 4 pernos A325 de 3/4\" a 76 mm con Vu = 150 kN y momento:")
    for M in (0.0, 5.0, 10.0, 20.0):
        g = design_bolt_group(BoltGroupInput(4, 19.05, Vu_kN=150.0, Mu_kNm=M))
        print(f"  Mu = {M:4.0f} kN·m → Rn grupo {g.Rn_group_kN:6.1f} kN, DCR {g.DCR_shear:.2f}")
    print("\nCordón de 8 × 150 mm, FEXX 482 MPa:")
    for ang in (0.0, 90.0):
        w = design_fillet_weld(FilletWeldInput(8.0, 150.0, angle_load_deg=ang))
        print(f"  θ = {ang:3.0f}° → φRn = {w.Rd_kN:.1f} kN (factor {w.directional_factor:.3f})")
    print("\nDoble angular 2L 100 × 100 × 9,5 con Vu = 250 kN, modo rápido y comprobación completa:")
    c = design_clip_angle(ClipAngleInput(100, 100, 9.5, 250.0))
    cf = design_clip_angle(ClipAngleInput(100, 100, 9.5, 250.0, full_aisc_checks=True))
    print(f"  rápido   → DCR {c.DCR:.2f} ({c.governing_check}); {c.notes[-1]}")
    print(f"  completo → DCR {cf.DCR:.2f} ({cf.governing_check}); {cf.notes[-1]}")
    print("Empalme con Mu = 150 kN·m y Vu = 80 kN:")
    s = design_splice(SpliceInput(Mu_kNm=150.0, Vu_kN=80.0))
    sb = design_splice(SpliceInput(Mu_kNm=150.0, Vu_kN=80.0, beam_depth_mm=450.0, n_bolts_web=4))
    print(f"  solo alas, canto por defecto → Mn {s.Mn_kNm:.0f} kN·m, DCR {s.DCR:.2f}; {s.notes[0]}")
    print(f"  canto 450 mm y 4 pernos de alma → Mn {sb.Mn_kNm:.0f} kN·m, DCR {sb.DCR:.2f}, perno más cargado {sb.bolt_demand_max_kN:.1f} kN (DCR {sb.bolt_dcr:.2f})")
    print(f"\nSalida serializable: {sorted(asdict(r).keys())}")
    print(f"El modo rápido del doble angular da DCR {c.DCR:.2f} frente a {cf.DCR:.2f} del completo: "
          f"{'subestima' if c.DCR < cf.DCR else 'no subestima'} la demanda. Para proyecto, full_aisc_checks=True o la clase ClipAngle.")


if __name__ == "__main__":
    main()
