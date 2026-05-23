"""
dxf_detail.py — Generador básico de planos DXF de conexiones (usando ezdxf).

Funciones:
  - shear_tab_dxf(tab, path)     — dibujo planta + elevación + tabla
  - clip_angle_dxf(clip, path)
  - base_plate_dxf(bp, path)
  - end_plate_dxf(ep, path)

Si ezdxf no está instalado, las funciones lanzan ImportError con instrucciones.

Las vistas son esquemáticas (no a escala normativa) pero suficientes para
incluir en una memoria de cálculo o para detalle de taller posterior.
"""
from __future__ import annotations
from typing import Any
import logging

log = logging.getLogger("steelconnectionjm.dxf_detail")

try:
    import ezdxf
    from ezdxf.enums import TextEntityAlignment
    _HAS_EZDXF = True
except ImportError:
    _HAS_EZDXF = False


# --- Mejora C: integration opcional con DXFStructuralJm ---
_USE_DXFSTRUCTURAL = False
try:
    import dxfstructuraljm as _dxfstr  # noqa: F401
    _USE_DXFSTRUCTURAL = True
    log.info("DXFStructuralJm detectado - primitivas avanzadas disponibles")
except ImportError:
    log.debug("DXFStructuralJm no disponible - usando primitivas locales")


def _require_ezdxf() -> None:
    if not _HAS_EZDXF:
        raise ImportError(
            "ezdxf no esta instalado. Instale con:  pip install ezdxf"
        )


# ---------------------------------------------------------------------------
# Skeletons de delegacion a DXFStructuralJm (placeholders por ahora)
# ---------------------------------------------------------------------------
def _shear_tab_dxf_via_dxfstructural(tab: Any, path: str):  # pragma: no cover
    """Placeholder: cuando DXFStructuralJm exponga API equivalente,
    reemplazar este return None por la delegacion real."""
    return None


def _clip_angle_dxf_via_dxfstructural(clip: Any, path: str):  # pragma: no cover
    return None


def _base_plate_dxf_via_dxfstructural(bp: Any, path: str):  # pragma: no cover
    return None


def _end_plate_dxf_via_dxfstructural(ep: Any, path: str):  # pragma: no cover
    return None


def _new_doc():
    doc = ezdxf.new(dxfversion="R2010", setup=True)
    msp = doc.modelspace()
    # Crear capas
    for name, color in [("STEEL", 1), ("BOLTS", 5), ("WELDS", 3),
                         ("DIM", 7), ("TEXT", 7), ("TABLE", 8)]:
        if name not in doc.layers:
            doc.layers.add(name=name, color=color)
    return doc, msp


def _draw_bolt(msp, x: float, y: float, d_mm: float, layer: str = "BOLTS") -> None:
    """Dibuja un perno (círculo + cruz)."""
    r = d_mm / 2.0
    msp.add_circle(center=(x, y), radius=r, dxfattribs={"layer": layer})
    msp.add_line((x - r, y), (x + r, y), dxfattribs={"layer": layer})
    msp.add_line((x, y - r), (x, y + r), dxfattribs={"layer": layer})


def _draw_rect(msp, x: float, y: float, w: float, h: float, layer: str = "STEEL") -> None:
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
    msp.add_lwpolyline(pts, dxfattribs={"layer": layer})


def _draw_table(msp, x0: float, y0: float, rows: list[list[str]],
                 col_widths: list[float], row_h: float = 8.0) -> None:
    """Tabla de materiales simple."""
    n_rows = len(rows)
    n_cols = len(col_widths)
    total_w = sum(col_widths)
    # Bordes horizontales
    for i in range(n_rows + 1):
        y = y0 - i * row_h
        msp.add_line((x0, y), (x0 + total_w, y), dxfattribs={"layer": "TABLE"})
    # Bordes verticales
    x = x0
    msp.add_line((x, y0), (x, y0 - n_rows * row_h), dxfattribs={"layer": "TABLE"})
    for w in col_widths:
        x += w
        msp.add_line((x, y0), (x, y0 - n_rows * row_h), dxfattribs={"layer": "TABLE"})
    # Texto
    for i, row in enumerate(rows):
        y = y0 - i * row_h - row_h * 0.7
        x = x0 + 2.0
        for j, cell in enumerate(row):
            msp.add_text(
                str(cell),
                dxfattribs={"layer": "TEXT", "height": row_h * 0.45},
            ).set_placement((x, y))
            x += col_widths[j]


# ---------------------------------------------------------------------------
# Shear tab
# ---------------------------------------------------------------------------
def shear_tab_dxf(tab: Any, path: str) -> str:
    """
    Dibuja un detalle simplificado de una shear tab.

    Parameters
    ----------
    tab  : ShearTab instance
    path : ruta de salida .dxf

    Returns
    -------
    str  : ruta del archivo escrito.
    """
    if _USE_DXFSTRUCTURAL:
        try:
            result = _shear_tab_dxf_via_dxfstructural(tab, path)
            if result is not None:
                return result
        except Exception as exc:  # pragma: no cover
            log.warning("Delegacion a DXFStructuralJm fallo: %s; usando local", exc)
    _require_ezdxf()
    doc, msp = _new_doc()
    # Vista frontal (elevación) de la placa
    tp = tab.plate_thickness
    h  = tab.plate_height
    w  = tab.plate_width
    # Placa rectangular (elevación)
    _draw_rect(msp, 0, 0, w, h, layer="STEEL")
    # Pernos en columna vertical (centrados horizontalmente)
    x_b = w / 2.0
    for i in range(tab.n_bolts):
        y_b = tab.edge_dist_v + i * tab.bolt_spacing
        _draw_bolt(msp, x_b, y_b, tab.bolt_diameter)
    # Texto
    msp.add_text(
        f"Shear Tab  Vu={tab.Vu} kN",
        dxfattribs={"layer": "TEXT", "height": 5.0}
    ).set_placement((0, h + 15))
    msp.add_text(
        f"Placa {w}x{tab.plate_height:.0f}x{tp} mm",
        dxfattribs={"layer": "TEXT", "height": 4.0}
    ).set_placement((0, h + 6))
    # Tabla de materiales
    rows = [
        ["ITEM", "DESCRIPCIÓN", "CANTIDAD"],
        ["1", f"Placa PL {tp}x{w:.0f}x{h:.0f} mm", "1"],
        ["2", f"Perno {tab.bolt_grade} Ø{tab.bolt_diameter} mm", str(tab.n_bolts)],
    ]
    _draw_table(msp, w + 30, h, rows, col_widths=[15, 70, 25])
    doc.saveas(path)
    return path


# ---------------------------------------------------------------------------
# Clip angle
# ---------------------------------------------------------------------------
def clip_angle_dxf(clip: Any, path: str) -> str:
    if _USE_DXFSTRUCTURAL:
        try:
            result = _clip_angle_dxf_via_dxfstructural(clip, path)
            if result is not None:
                return result
        except Exception as exc:  # pragma: no cover
            log.warning("Delegacion a DXFStructuralJm fallo: %s; usando local", exc)
    _require_ezdxf()
    doc, msp = _new_doc()
    t  = clip.angle_thickness
    L  = clip.angle_leg
    h  = clip.angle_height
    # Elevación: dos ángulos (representados como dos rectángulos abrazando
    # el alma de la viga). Vista en planta (top view).
    # Planta: dos L espalda con espalda
    # Ángulo 1
    _draw_rect(msp, 0, 0, L, t, layer="STEEL")
    _draw_rect(msp, 0, 0, t, L, layer="STEEL")
    # Ángulo 2 (espejo en X)
    _draw_rect(msp, 0, -t, L, t, layer="STEEL")
    _draw_rect(msp, 0, -L, t, L, layer="STEEL")
    # Vista frontal (elevación), debajo, con pernos
    y_off = -L - 30
    _draw_rect(msp, 0, y_off, L, h, layer="STEEL")
    x_b = L / 2.0
    for i in range(clip.n_bolts):
        y_b = y_off + clip.edge_dist_v + i * clip.bolt_spacing
        _draw_bolt(msp, x_b, y_b, clip.bolt_diameter)
    # Texto
    msp.add_text(f"Clip Angle (Doble L)  Vu={clip.Vu} kN",
                 dxfattribs={"layer": "TEXT", "height": 5.0}
                ).set_placement((0, 30))
    rows = [
        ["ITEM", "DESCRIPCIÓN", "CANTIDAD"],
        ["1", f"L {L:.0f}x{L:.0f}x{t} mm, h={h:.0f}", "2"],
        ["2", f"Perno {clip.bolt_grade} Ø{clip.bolt_diameter} mm", str(clip.n_bolts * 4)],
    ]
    _draw_table(msp, L + 40, 0, rows, col_widths=[15, 70, 25])
    doc.saveas(path)
    return path


# ---------------------------------------------------------------------------
# Base plate
# ---------------------------------------------------------------------------
def base_plate_dxf(bp: Any, path: str) -> str:
    """
    Dibuja la planta de la base plate. Se asume que `bp` tiene atributos
    N (largo), B (ancho), tp (espesor), n_anchors, anchor_diameter,
    anchor_positions (lista de (x,y)).

    Si DXFStructuralJm esta disponible, prefiere usar sus capacidades
    avanzadas (capas estandar, hatches, cuadro de materiales). Si no,
    fallback al impl local.
    """
    if _USE_DXFSTRUCTURAL:
        try:
            result = _base_plate_dxf_via_dxfstructural(bp, path)
            if result is not None:
                return result
        except Exception as exc:  # pragma: no cover
            log.warning("Delegacion a DXFStructuralJm fallo: %s; usando local", exc)
    _require_ezdxf()
    doc, msp = _new_doc()
    N = getattr(bp, "N", None) or getattr(bp, "plate_length", 400.0)
    B = getattr(bp, "B", None) or getattr(bp, "plate_width", 400.0)
    tp = getattr(bp, "plate_thickness", getattr(bp, "tp", 25.0))
    # Planta de la placa
    _draw_rect(msp, 0, 0, N, B, layer="STEEL")
    # Anclajes (si están definidos)
    anchors = getattr(bp, "anchor_positions", None)
    d_anc = getattr(bp, "anchor_diameter", 25.0)
    if anchors:
        for (x, y) in anchors:
            _draw_bolt(msp, x, y, d_anc, layer="BOLTS")
    else:
        # 4 anclajes en esquinas, a 50 mm del borde
        e = 50.0
        for (x, y) in [(e, e), (N - e, e), (e, B - e), (N - e, B - e)]:
            _draw_bolt(msp, x, y, d_anc, layer="BOLTS")
    msp.add_text(f"Base Plate {N:.0f}x{B:.0f}x{tp:.0f} mm",
                 dxfattribs={"layer": "TEXT", "height": 6.0}
                ).set_placement((0, B + 15))
    doc.saveas(path)
    return path


# ---------------------------------------------------------------------------
# End plate (extended end-plate moment connection)
# ---------------------------------------------------------------------------
def _draw_dim_label(msp, x1: float, y1: float, x2: float, y2: float,
                    text: str, offset: float = 8.0) -> None:
    """Línea de cota simple + texto (no usa DIMENSION nativo para evitar
    dependencia de DIMSTYLE)."""
    msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "DIM"})
    # Marcas de extremo
    msp.add_line((x1, y1 - 1.5), (x1, y1 + 1.5), dxfattribs={"layer": "DIM"})
    msp.add_line((x2, y2 - 1.5), (x2, y2 + 1.5), dxfattribs={"layer": "DIM"})
    xm = (x1 + x2) / 2.0
    ym = (y1 + y2) / 2.0 + offset * 0.4
    msp.add_text(text, dxfattribs={"layer": "DIM", "height": 3.0}
                 ).set_placement((xm, ym))


def _draw_weld_symbol(msp, x: float, y: float, size: float, label: str) -> None:
    """Simbología AWS simplificada: línea de referencia + triángulo +
    cola con tag de electrodo."""
    # Línea de referencia horizontal
    msp.add_line((x, y), (x + 30, y), dxfattribs={"layer": "WELDS"})
    # Triángulo filete (debajo de la línea = lado opuesto / arriba = lado flecha)
    msp.add_lwpolyline(
        [(x + 10, y), (x + 14, y + 5), (x + 18, y), (x + 10, y)],
        dxfattribs={"layer": "WELDS"},
    )
    # Cola
    msp.add_line((x + 30, y), (x + 36, y + 4), dxfattribs={"layer": "WELDS"})
    msp.add_line((x + 30, y), (x + 36, y - 4), dxfattribs={"layer": "WELDS"})
    # Tamaño + electrodo
    msp.add_text(f"{size:g}", dxfattribs={"layer": "WELDS", "height": 2.5}
                 ).set_placement((x + 1, y + 1))
    msp.add_text(label, dxfattribs={"layer": "WELDS", "height": 2.5}
                 ).set_placement((x + 37, y - 1))


def end_plate_dxf(end_plate: Any, output_path: str) -> str:
    """
    Dibuja un detalle 2D de una conexión End-Plate extendida.

    Genera tres vistas:
      1. Vista lateral (elevación): columna + end-plate + viga, con notch
         opcional en alas inferiores si la viga es más profunda.
      2. Vista en planta del end-plate con outline + pernos en sus posiciones
         (4 pernos si ``n_bolt_rows == 2``, 8 si ``n_bolt_rows == 4``).
      3. Tabla de materiales (viga, plate, bolts, electrode).

    Cotas: tp, pfo, pfi, g (gage), bolt Ø.
    Simbología de soldadura ala/alma AWS.

    Parameters
    ----------
    end_plate : EndPlate instance
    output_path : ruta de salida .dxf

    Returns
    -------
    str : ruta del archivo escrito.
    """
    if _USE_DXFSTRUCTURAL:
        try:
            result = _end_plate_dxf_via_dxfstructural(end_plate, output_path)
            if result is not None:
                return result
        except Exception as exc:  # pragma: no cover
            log.warning("Delegacion a DXFStructuralJm fallo: %s; usando local", exc)
    _require_ezdxf()
    ep = end_plate
    doc, msp = _new_doc()

    # ---------- Geometría base -----------------------------------------
    db = ep.beam_depth
    tf = ep.beam_tf
    bf = ep.beam_bf
    tp = ep.plate_thickness
    bp = ep.plate_width or (bf + 25.0)
    pfo = ep.pfo
    pfi = ep.pfi
    g = ep.g
    n_rows = ep.n_bolt_rows
    d_bolt = ep.bolt_diameter
    # Altura total del end-plate (extendido fuera de ambas alas)
    plate_height = db + 2 * pfo + 2 * (d_bolt * 1.5)  # extensión razonable

    # =============================================================
    # VISTA 1 — ELEVACIÓN LATERAL  (columna | end-plate | viga)
    # =============================================================
    # Columna a la izquierda — representada por un rectángulo vertical
    col_w = 250.0   # ancho aparente del ala columna (en mm de papel)
    col_h = plate_height + 200.0
    col_x = 0.0
    col_y = -100.0
    _draw_rect(msp, col_x, col_y, col_w, col_h, layer="STEEL")
    # Alma columna (línea fina central)
    msp.add_line((col_x + col_w / 2, col_y),
                 (col_x + col_w / 2, col_y + col_h),
                 dxfattribs={"layer": "STEEL"})

    # End-plate
    plate_x = col_x + col_w
    plate_y = col_y + (col_h - plate_height) / 2.0
    _draw_rect(msp, plate_x, plate_y, tp, plate_height, layer="STEEL")

    # Viga — ala superior, alma, ala inferior
    beam_x = plate_x + tp
    beam_len = 400.0
    beam_y_top = plate_y + plate_height / 2.0 + db / 2.0
    beam_y_bot = plate_y + plate_height / 2.0 - db / 2.0
    # Ala superior
    _draw_rect(msp, beam_x, beam_y_top - tf, beam_len, tf, layer="STEEL")
    # Ala inferior
    _draw_rect(msp, beam_x, beam_y_bot, beam_len, tf, layer="STEEL")
    # Alma (línea representativa)
    tw_repr = max(tf * 0.6, 6.0)
    web_y0 = beam_y_bot + tf
    web_y1 = beam_y_top - tf
    _draw_rect(msp, beam_x, web_y0, beam_len, web_y1 - web_y0, layer="STEEL")
    # Notch opcional (si pfi muy reducido — esquemático)
    if pfi < 30.0:
        notch_size = 15.0
        _draw_rect(msp, beam_x, beam_y_bot, notch_size, notch_size,
                   layer="STEEL")

    # Pernos en elevación (líneas centrales horizontales que cruzan la placa)
    # Filas: outer y inner para cada ala. Para n_rows == 4 → dos extras.
    bolt_ys: list[float] = [
        beam_y_top + pfo,         # outer superior
        beam_y_top - pfi,         # inner superior
        beam_y_bot + pfi,         # inner inferior
        beam_y_bot - pfo,         # outer inferior
    ]
    if n_rows == 4:
        # añadir 2 filas adicionales internas (8ES)
        extra = d_bolt * 2.5
        bolt_ys.insert(2, beam_y_top - pfi - extra)
        bolt_ys.insert(-1, beam_y_bot + pfi + extra)

    for yb in bolt_ys:
        # Perno representado como elipse fina sobre el plate
        msp.add_line((plate_x - 5, yb), (plate_x + tp + 5, yb),
                     dxfattribs={"layer": "BOLTS"})
        # Cabeza/tuerca esquemática
        msp.add_circle(center=(plate_x - 8, yb), radius=d_bolt / 2.0,
                       dxfattribs={"layer": "BOLTS"})

    # Soldadura ala/alma — símbolos AWS
    elec_label = str(getattr(ep, "electrode", "E70XX"))
    _draw_weld_symbol(msp, beam_x + 60, beam_y_top + 10, 8, elec_label)
    _draw_weld_symbol(msp, beam_x + 60, beam_y_bot - 18, 8, elec_label)

    # Cotas elevación: tp, pfo, pfi
    _draw_dim_label(msp, plate_x, plate_y - 20, plate_x + tp, plate_y - 20,
                    f"tp={tp:g}")
    _draw_dim_label(msp, plate_x - 25, beam_y_top, plate_x - 25, beam_y_top + pfo,
                    f"pfo={pfo:g}")
    _draw_dim_label(msp, plate_x - 25, beam_y_top - pfi, plate_x - 25, beam_y_top,
                    f"pfi={pfi:g}")

    # Título vista 1
    msp.add_text("VISTA LATERAL — Extended End-Plate",
                 dxfattribs={"layer": "TEXT", "height": 8.0}
                 ).set_placement((col_x, col_y + col_h + 30))

    # =============================================================
    # VISTA 2 — PLANTA DEL END-PLATE
    # =============================================================
    pv_x0 = beam_x + beam_len + 120
    pv_y0 = col_y
    # Outline del plate (bp × plate_height)
    _draw_rect(msp, pv_x0, pv_y0, bp, plate_height, layer="STEEL")

    # Bolts en planta: dos columnas a gage g/2 desde centerline
    x_cl = pv_x0 + bp / 2.0
    x_left = x_cl - g / 2.0
    x_right = x_cl + g / 2.0
    # Posiciones verticales en el plate: misma serie de bolt_ys pero
    # desplazadas al origen de la vista en planta
    dy = plate_y - pv_y0
    for yb in bolt_ys:
        y_planta = yb - dy
        _draw_bolt(msp, x_left, y_planta, d_bolt)
        _draw_bolt(msp, x_right, y_planta, d_bolt)

    # Cotas planta: g (gage), bolt diameter
    _draw_dim_label(msp, x_left, pv_y0 - 15, x_right, pv_y0 - 15,
                    f"g={g:g}")
    msp.add_text(f"Ø{d_bolt:g} (typ.) — {ep.bolt_grade}",
                 dxfattribs={"layer": "TEXT", "height": 4.0}
                 ).set_placement((pv_x0, pv_y0 - 30))

    msp.add_text("PLANTA END-PLATE",
                 dxfattribs={"layer": "TEXT", "height": 8.0}
                 ).set_placement((pv_x0, pv_y0 + plate_height + 30))

    # =============================================================
    # TABLA DE MATERIALES
    # =============================================================
    n_bolts_total = n_rows * 2
    rows = [
        ["ITEM", "DESCRIPCIÓN", "CANTIDAD"],
        ["1", f"Viga db={db:.0f} tf={tf:.0f} bf={bf:.0f} mm", "1"],
        ["2", f"End-Plate PL {tp:g}x{bp:.0f}x{plate_height:.0f} mm", "1"],
        ["3", f"Perno {ep.bolt_grade} Ø{d_bolt:g} mm", str(n_bolts_total)],
        ["4", f"Electrodo {elec_label}", "-"],
    ]
    tab_x = pv_x0
    tab_y = pv_y0 - 60
    _draw_table(msp, tab_x, tab_y, rows, col_widths=[18, 110, 28], row_h=9.0)

    # Encabezado general
    Mu = getattr(ep, "Mu", 0.0)
    Vu = getattr(ep, "Vu", 0.0)
    msp.add_text(
        f"EXTENDED END-PLATE  Mu={Mu} kN·m  Vu={Vu} kN  ({n_bolts_total}-bolt)",
        dxfattribs={"layer": "TEXT", "height": 10.0}
    ).set_placement((col_x, col_y + col_h + 60))

    doc.saveas(output_path)
    return output_path
