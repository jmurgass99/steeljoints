"""Memoria conexion RBS (Reduced Beam Section) AISC 358-22 cap. 5.

Calcula la capacidad probable de la rotula plastica en la zona reducida
y verifica que la conexion + columna sean capaces de resistir esa demanda
amplificada (capacity design).
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field

try:
    from handcalcs.decorator import handcalc
    _HAS_HANDCALCS = True
except ImportError:
    _HAS_HANDCALCS = False
    def handcalc(*args, **kwargs):
        def deco(f): return f
        return deco


@dataclass
class RBSDesignResult:
    """Resultado del calculo de capacidad RBS AISC 358."""
    Z_RBS_mm3: float          # modulo plastico reducido
    M_pr_kNm: float           # momento probable rotula plastica
    Vp_kN: float              # cortante en rotula plastica
    M_f_kNm: float            # momento en cara de columna
    is_geometry_ok: bool      # cumple a, b, c geometricos
    latex: str = ""
    notes: list[str] = field(default_factory=list)


@handcalc(override="long", precision=3)
def _rbs_geometry(bf, tf, a, b, c):
    """Geometria RBS AISC 358 §5.8 Eq. 5.8-1..3."""
    bf_RBS = bf - 2 * c
    Lh_mm = a + b / 2
    return bf_RBS, Lh_mm


@handcalc(override="long", precision=3)
def _rbs_moment_capacity(Z_x, c, tf, d, Fy, Ry, Cpr):
    """Momento probable en RBS AISC 358 §5.8 Eq. 5.8-4..5."""
    Z_RBS = Z_x - 2 * c * tf * (d - tf)
    M_pr = Cpr * Ry * Fy * Z_RBS
    return Z_RBS, M_pr


@handcalc(override="long", precision=3)
def _rbs_shear_and_face_moment(M_pr, Lh_mm, wu, L_clear):
    """Cortante en rotula plastica y momento en cara de columna."""
    Vp = (2 * M_pr) / (L_clear * 1000) + wu * L_clear / 2
    M_f = M_pr + Vp * (Lh_mm / 1000)
    return Vp, M_f


def rbs_aisc358_memo(beam_d, beam_bf, beam_tf, beam_Z_x,
                        a, b, c, L_clear, wu,
                        Fy=345.0, Ry=1.1, Cpr=1.15):
    """Genera memoria RBS AISC 358-22 capitulo 5.

    Args:
        beam_d: peralte viga (mm)
        beam_bf: ancho ala (mm)
        beam_tf: espesor ala (mm)
        beam_Z_x: modulo plastico viga sin reducir (mm3)
        a: distancia cara columna a inicio RBS (mm)
        b: longitud zona reducida (mm)
        c: profundidad recorte (mm)
        L_clear: luz libre entre caras de columnas (m)
        wu: carga gravitacional uniforme (kN/m) en LRFD
        Fy: limite elastico (MPa)
        Ry: factor expected/nominal AISC 341 Tabla A3.1
        Cpr: factor peak/yield AISC 358 Eq. 2.4-2

    Returns:
        (latex_str, RBSDesignResult)
    """
    # Validaciones (fuera del decorador)
    if any(v <= 0 for v in [beam_d, beam_bf, beam_tf, beam_Z_x, L_clear]):
        raise ValueError("geometria + L_clear deben ser positivos")
    if a < 0 or b <= 0 or c <= 0:
        raise ValueError("a >= 0, b > 0, c > 0")
    if Fy <= 0 or Ry < 1.0 or Cpr < 1.0:
        raise ValueError("Fy positivo, Ry y Cpr >= 1.0")

    # Geometria limits AISC 358 §5.8.1
    a_min = 0.5 * beam_bf
    a_max = 0.75 * beam_bf
    b_min = 0.65 * beam_d
    b_max = 0.85 * beam_d
    c_min = 0.1 * beam_bf
    c_max = 0.25 * beam_bf
    is_geometry_ok = (a_min <= a <= a_max and b_min <= b <= b_max
                      and c_min <= c <= c_max)

    latex_g, (bf_RBS, Lh_mm) = _rbs_geometry(beam_bf, beam_tf, a, b, c)
    # Convertir N*mm a kN*m: 1 N*mm = 1e-6 kN*m
    latex_m, (Z_RBS, M_pr_Nmm) = _rbs_moment_capacity(
        beam_Z_x, c, beam_tf, beam_d, Fy, Ry, Cpr,
    )
    M_pr_kNm = M_pr_Nmm / 1e6
    latex_v, (Vp, M_f_kNm) = _rbs_shear_and_face_moment(
        M_pr_kNm, Lh_mm, wu, L_clear,
    )

    full = latex_g + "\n\n" + latex_m + "\n\n" + latex_v

    return full, RBSDesignResult(
        Z_RBS_mm3=float(Z_RBS),
        M_pr_kNm=float(M_pr_kNm),
        Vp_kN=float(Vp),
        M_f_kNm=float(M_f_kNm),
        is_geometry_ok=bool(is_geometry_ok),
        latex=full,
        notes=[
            f"Z_RBS = {Z_RBS:.0f} mm3 ({Z_RBS/beam_Z_x*100:.1f}% del Z_x original)",
            f"M_pr = {M_pr_kNm:.1f} kN.m, V_p = {Vp:.1f} kN",
            f"M_f (cara columna) = {M_f_kNm:.1f} kN.m",
            f"Geometria AISC 358 §5.8.1: {'OK' if is_geometry_ok else 'FUERA DE LIMITES'}",
            f"  a en [{a_min:.0f},{a_max:.0f}] mm (real {a:.0f})",
            f"  b en [{b_min:.0f},{b_max:.0f}] mm (real {b:.0f})",
            f"  c en [{c_min:.0f},{c_max:.0f}] mm (real {c:.0f})",
        ],
    )
