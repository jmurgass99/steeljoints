"""Servicio: diseno de pernos y grupos de pernos."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SingleBoltInput:
    grade: str            # "A325", "A490", "A307" (AISC) | "8.8", "10.9" (EC3)
    diameter_mm: float    # diametro nominal del perno
    thread_condition: str = "N"   # "N" (rosca incluida) | "X" (rosca excluida)
    standard: str = "AISC"        # "AISC" | "EC3"
    plate_thickness_mm: float = 10.0
    plate_fu_MPa: float = 400.0   # resistencia a traccion de la placa
    edge_distance_mm: float = 30.0


@dataclass(frozen=True)
class BoltDesignResult:
    Rn_shear_kN: float            # resistencia al cortante (nominal)
    Rn_tension_kN: float
    Rn_bearing_kN: float           # bearing en la placa
    Rd_shear_kN: float             # phi*Rn (AISC) o Rn/gamma (EC3)
    governs: str
    notes: list[str]


def design_single_bolt(inp: SingleBoltInput) -> BoltDesignResult:
    """Diseno de un perno individual: cortante, tension, aplastamiento.

    Aplica formulas AISC J3 / EC3 3.6 directamente.
    """
    import math
    Ab = math.pi * (inp.diameter_mm / 1000) ** 2 / 4  # m^2

    fu_table = {
        "A307": 414e6, "A325": 825e6, "A490": 1035e6,
        "4.6": 400e6, "5.6": 500e6, "8.8": 800e6, "10.9": 1000e6,
    }
    fu = fu_table.get(inp.grade, 825e6)

    threads_in_plane = inp.thread_condition.upper() == "N"
    if inp.standard.upper() == "AISC":
        Fnv = 0.45 * fu if threads_in_plane else 0.563 * fu
        Fnt = 0.75 * fu
        phi_shear = 0.75
        phi_tension = 0.75
        gamma = 1.0
        A_shear = Ab
        A_tension = Ab
    else:
        # EN 1993-1-8 Tabla 3.4: αv depende del GRADO (0,6 para 4.6, 5.6 y 8.8; 0,5 para 4.8, 5.8,
        # 6.8 y 10.9) y el área es As cuando la rosca está en el plano de corte. Hasta la versión 1.1
        # αv dependía de la rosca y se usaba siempre el área bruta; la tracción también iba con Ab.
        from ..bolts import bolt_tensile_stress_area
        from ..catalog import EC3_BOLT_GRADES
        alpha_v = EC3_BOLT_GRADES.get(inp.grade, {"alpha_v": 0.5})["alpha_v"]
        Fnv = alpha_v * fu
        Fnt = 0.9 * fu
        phi_shear = 1.0
        phi_tension = 1.0
        gamma = 1.25
        As = bolt_tensile_stress_area(inp.diameter_mm) / 1e6
        A_shear = As if threads_in_plane else Ab
        A_tension = As

    Rn_shear = Fnv * A_shear
    Rn_tension = Fnt * A_tension
    # Aplastamiento del perno de borde con la distancia al borde de la entrada (hasta la v1.1 se ignoraba
    # y se tomaba siempre 2,4·d·t·Fu, también en EC3).
    d_mm, t_mm, e_mm, fu_p = inp.diameter_mm, inp.plate_thickness_mm, inp.edge_distance_mm, inp.plate_fu_MPa
    if inp.standard.upper() == "AISC":
        from ..catalog import standard_hole
        lc = e_mm - standard_hole(d_mm) / 2.0          # distancia libre al borde [mm]
        Rn_bearing = min(1.2 * max(lc, 0.0) * t_mm * fu_p, 2.4 * d_mm * t_mm * fu_p)   # N, §J3.10(a)
        bearing_note = f"Aplastamiento AISC §J3.10: lc = {lc:.1f} mm, mín(1,2·lc·t·Fu, 2,4·d·t·Fu)"
    else:
        from ..bolts import ec3_normal_hole_clearance
        d0 = d_mm + ec3_normal_hole_clearance(d_mm)
        alpha_b = min(e_mm / (3.0 * d0), fu / 1e6 / fu_p, 1.0)
        k1 = 2.5   # e2 no forma parte de la entrada: se supone e2 ≥ 1,5·d0
        Rn_bearing = k1 * alpha_b * fu_p * d_mm * t_mm   # N, EN 1993-1-8 Tabla 3.4 (sin γM2)
        bearing_note = f"Aplastamiento EC3 Tabla 3.4: d0 = {d0:.0f} mm, αb = {alpha_b:.3f}, k1 = 2,5 (supone e2 ≥ 1,5·d0)"
    if inp.standard.upper() == "AISC":
        Rd_shear = phi_shear * Rn_shear
    else:
        Rd_shear = Rn_shear / gamma
    governs = "shear" if Rn_shear < Rn_bearing else "bearing"
    return BoltDesignResult(
        Rn_shear_kN=Rn_shear / 1e3,
        Rn_tension_kN=Rn_tension / 1e3,
        Rn_bearing_kN=Rn_bearing / 1e3,
        Rd_shear_kN=Rd_shear / 1e3,
        governs=governs,
        notes=[
            f"Grade {inp.grade}, dia={inp.diameter_mm:.0f} mm, std={inp.standard}",
            f"Rn shear = {Rn_shear/1e3:.1f} kN | bearing = {Rn_bearing/1e3:.1f} kN",
            bearing_note,
            f"Gobierna: {governs}",
        ],
    )


@dataclass(frozen=True)
class BoltGroupInput:
    n_bolts: int
    diameter_mm: float
    grade: str = "A325"
    spacing_mm: float = 76.0
    layout: str = "linear"
    Vu_kN: float = 0.0
    Mu_kNm: float = 0.0


@dataclass(frozen=True)
class BoltGroupResult:
    Rn_group_kN: float
    DCR_shear: float
    notes: list[str]


def design_bolt_group(inp: BoltGroupInput) -> BoltGroupResult:
    """Grupo de pernos en UNA línea vertical con cortante vertical Vu y momento Mu (método elástico).

    Pernos a ``spacing_mm`` centrados en el centroide. El momento da en cada perno una fuerza
    horizontal M·y/Σy² (perpendicular a la del cortante, Vu/n), así que el perno extremo resiste
    √((Vu/n)² + (M·y_max/Σy²)²) (AISC Manual Parte 7, método elástico, conservador frente al ICR).

    * ``Rn_group_kN``: cortante NOMINAL que admite el grupo junto con el momento dado,
      n·√(Rn² − f_M²) con f_M la fuerza del momento en el perno extremo (Rn sin φ).
    * ``DCR_shear``: fuerza del perno extremo frente a la resistencia de DISEÑO del perno (φRn).

    Hasta la versión 1.1, con momento se multiplicaba la capacidad por 0,6 sin ningún método, y
    el DCR se comparaba con la resistencia nominal. Solo se admite ``layout="linear"``.
    """
    import math
    if inp.layout != "linear":
        raise ValueError(f"layout {inp.layout!r} no soportado: solo 'linear' (una línea vertical)")
    if inp.n_bolts < 1 or inp.spacing_mm <= 0:
        raise ValueError("n_bolts >= 1 y spacing_mm > 0")
    single = design_single_bolt(SingleBoltInput(
        grade=inp.grade, diameter_mm=inp.diameter_mm,
    ))
    n = inp.n_bolts
    ys = [(i - (n - 1) / 2.0) * inp.spacing_mm for i in range(n)]
    sum_y2 = sum(y * y for y in ys)
    y_max = max(abs(y) for y in ys)
    M_kNmm = abs(inp.Mu_kNm) * 1000.0
    if M_kNmm > 0 and sum_y2 <= 0:
        raise ValueError("un solo perno no resiste momento en este modelo (Σy² = 0)")
    f_M = M_kNmm * y_max / sum_y2 if M_kNmm > 0 else 0.0          # kN en el perno extremo
    f_V = abs(inp.Vu_kN) / n
    f_crit = math.hypot(f_V, f_M)
    Rn = single.Rn_shear_kN
    Rn_group = n * math.sqrt(Rn * Rn - f_M * f_M) if f_M < Rn else 0.0
    dcr = f_crit / single.Rd_shear_kN if single.Rd_shear_kN > 0 else float("inf")
    return BoltGroupResult(
        Rn_group_kN=Rn_group, DCR_shear=dcr,
        notes=[
            f"Grupo {n} pernos Ø{inp.diameter_mm:.0f} {inp.grade} en línea a {inp.spacing_mm:.0f} mm",
            f"Perno extremo: Vu/n = {f_V:.1f} kN, momento {f_M:.1f} kN → {f_crit:.1f} kN frente a φRn = {single.Rd_shear_kN:.1f} kN",
            f"Rn del grupo con este momento = {Rn_group:.1f} kN (nominal), DCR = {dcr:.2f}",
        ],
    )
