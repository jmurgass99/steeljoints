"""Salidas a otros programas: mazo de entrada de CalculiX (.inp) para una chapa en voladizo con elementos S4, y planos DXF de detalle de una chapa a cortante, un doble angular, una placa base y una chapa frontal, contando las entidades de cada capa al volver a leerlos.

`steelnode.generate_inp_deck(PlateDeckIn(length, width, thickness, nx, ny, E, nu, load))` y
`dxf_detail.shear_tab_dxf / clip_angle_dxf / base_plate_dxf / end_plate_dxf(objeto, ruta)` (necesita ezdxf, extra `dxf`).

Ejecutar:  python examples/calculix_plate_deck_inp_and_dxf_details_shear_tab_clip_angle_base_plate_end_plate.py
"""
import os
from collections import Counter
from pathlib import Path

from steeljoints import BasePlate, ShearTab
from steeljoints.clip_angle import ClipAngle
from steeljoints.end_plate import EndPlate
from steeljoints.steelnode import generate_inp_deck
from steeljoints.steelnode_schemas import PlateDeckIn

OUT = Path(os.environ.get("JM_EXAMPLES_OUT_DIR", Path(__file__).resolve().parent / "out"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    deck = generate_inp_deck(PlateDeckIn(length=300.0, width=150.0, thickness=12.0, nx=12, ny=6, E=210000.0, nu=0.3, load=5000.0))
    (OUT / "chapa_voladizo.inp").write_text(deck.inp, encoding="utf-8")
    kw = [ln.split(",")[0] for ln in deck.inp.splitlines() if ln.startswith("*") and not ln.startswith("**")]
    print(f"CalculiX: chapa 300 × 150 × 12 mm, malla 12 × 6 → {deck.n_nodes} nodos, {deck.n_elements} elementos S4")
    print(f"  Palabras clave: {' '.join(dict.fromkeys(kw))}")
    print(f"  Comprobación: (nx + 1)·(ny + 1) = {13 * 7}, nx·ny = {12 * 6}")
    try:
        import ezdxf
        from steeljoints.dxf_detail import base_plate_dxf, clip_angle_dxf, end_plate_dxf, shear_tab_dxf
    except ImportError:
        print("\nezdxf no está instalado: pip install steeljoints[dxf] para generar los planos.")
        return
    planos = (
        ("chapa_cortante.dxf", shear_tab_dxf, ShearTab(Vu=280.0, n_bolts=4, plate_thickness=9.5)),
        ("doble_angular.dxf", clip_angle_dxf, ClipAngle(Vu=250.0, n_bolts=3)),
        ("placa_base.dxf", base_plate_dxf, BasePlate(Pu=2000.0, column_d=310.0, column_bf=305.0, plate_B=450.0, plate_N=450.0)),
        ("chapa_frontal.dxf", end_plate_dxf, EndPlate(Mu=250.0, Vu=120.0, beam_depth=450.0, beam_tf=14.6, beam_bf=190.0, bolt_diameter=22.225, plate_thickness=22.0, plate_width=230.0)),
    )
    print("\nPlanos DXF (entidades por capa al releerlos con ezdxf):")
    for name, fn, obj in planos:
        path = OUT / name
        fn(obj, str(path))
        doc = ezdxf.readfile(str(path))
        capas = Counter(e.dxf.layer for e in doc.modelspace())
        print(f"  {name:20} {path.stat().st_size / 1024:5.1f} KiB, versión {doc.dxfversion}: " + ", ".join(f"{k} {v}" for k, v in sorted(capas.items())))
    print(f"\nFicheros en {OUT.name}/. El mazo de CalculiX es una chapa en voladizo con carga puntual en el borde libre: sirve para contrastar una placa a mano, "
          "no modela tornillos ni contacto. Los planos son esquemas de detalle con cotas y tabla de datos, no planos de taller.")


if __name__ == "__main__":
    main()
