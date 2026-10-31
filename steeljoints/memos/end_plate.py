"""
Memoria handcalcs — conexion End-Plate atornillada (viga-pilar a momento).

MODELO DE RESISTENCIA A FLEXION
------------------------------
La resistencia a flexion de una end plate NO es el momento plastico de la
seccion transversal de la chapa (b·t^2/4·Fy): eso es una magnitud de la CHAPA,
no de la CONEXION, y compararla contra el momento de la viga declara fallo en
conexiones perfectamente holgadas. La formulacion correcta es la de
EN 1993-1-8:2005 §6.2.7.2, Ec. (6.25):

    Mj,Rd = SUM_r ( h_r · Ft,r,Rd )

con Ft,r,Rd la resistencia de cada fila de tornillos obtenida del T-stub
equivalente (§6.2.4.1, Tabla 6.2, modos 1/2/3) y h_r el brazo de la fila al
centro de compresion. La misma estructura tiene AISC Design Guide 4 (2.a ed.,
Ec. 3.1).

El T-stub NO se reimplementa aqui: se usa la funcion canonica del repo
``steeljoints.codes.ec3_1_8.t_stub_FT_Rd`` (goldens propios en
tests/test_ec3_1_8_golden.py, clase TestTStubGolden).

Mj,Rd DEVUELTA = COTA SUPERIOR — LIMITACION VIGENTE
---------------------------------------------------
El sumatorio de arriba limita la fuerza de cada fila SOLO por el T-stub del
LADO DE LA CHAPA FRONTAL. EN 1993-1-8 §6.2.7.2 la limita ademas por el resto
de componentes del nudo: ala del pilar a flexion (§6.2.6.4), alma del pilar a
traccion (§6.2.6.3), a cortante (§6.2.6.1) y a compresion (§6.2.6.2), alma de
la viga a traccion (§6.2.6.8), la resistencia del lado comprimido, los limites
de GRUPO de filas (§6.2.7.2(8)) y la redistribucion triangular. Ninguno de
ellos entra aqui: la entrada no tiene geometria de pilar y deducirla seria
inventar una hipotesis. Por tanto ``M_resistance_kNm`` es una COTA SUPERIOR de
la resistencia real del nudo — el mismo sentido de error que el defecto que se
ha corregido, pero de magnitud mucho menor y acotada a los componentes
listados. Uselo sabiendolo; NO es una Mj,Rd completa de EN 1993-1-8.

FORMATO DE SEGURIDAD — DECISION EXPLICITA
-----------------------------------------
Este memo trabaja en formato LRFD/AISC de principio a fin; no se mezclan phi y
gamma_M dentro de un mismo producto:

  * Tornillos en traccion: Rn = 0.75·Fu·Ab (modelo historico del modulo,
    equivalente a Fnt de AISC 360-22 Tabla J3.2 salvo redondeo ksi->MPa),
    con phi = 0.75 (§J3.7)  ->  phi·Rn.
  * Chapa en flexion (Mpl,Rd del T-stub): phi = 0.90. La chapa es un elemento
    de union, no un miembro: la referencia es AISC 360-22 §J4.1(a) (fluencia
    de elementos de union, phi = 0.90) — coincide con el phi_b = 0.90 que
    AISC Design Guide 4 (2.a ed.) §3.3 aplica al momento de lineas de
    fluencia de la end plate. NO es §F1, que es flexion de MIEMBROS. Se
    introduce en ``t_stub_FT_Rd`` a traves de su parametro ``gamma_M0``
    pasando 1/0.90, que es exactamente el sitio donde el factor divide a
    Mpl,Rd; asi se reutiliza la funcion sin tocarla.

Se exponen POR SEPARADO los valores nominales y los de diseno. ``DCR_moment``
y ``is_safe`` se construyen sobre los de DISENO.

DATOS REQUERIDOS — SIN VALORES INVENTADOS
-----------------------------------------
Mj,Rd exige geometria de filas (brazo h_r y parametros de T-stub leff, m, n).
``leff`` depende de los patrones de lineas de fluencia de EN 1993-1-8
Tabla 6.6 / AISC 358 Tabla 6.2; deducirlo aqui seria inventar una hipotesis.
Por eso ``bolt_rows`` es una entrada EXPLICITA y, si falta, la resistencia a
flexion se declara NO CALCULADA (``M_resistance_kNm is None``,
``DCR_moment is None``, ``is_safe is None``) en vez de sustituirse por un
sucedaneo.

RETIRADO: ``arm_m = 5·bolt_pitch``, heuristica sin norma que no dependia del
canto de la viga — precisamente la variable que fija el brazo.
``bolt_pitch_mm`` se conserva en la entrada por compatibilidad pero YA NO
interviene en ningun calculo. Con el desaparece la definicion de
``T_bolts_required_kN``: ahora se calcula como M_demand/h_max (brazo mayor) y
se marca explicitamente como PROXY INFORMATIVO, no como la verificacion que
gobierna. La traccion de los tornillos ya esta cubierta dentro de Mj,Rd por el
modo 3 del T-stub, que es quien gobierna ``is_safe``.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Any

from steeljoints.codes.ec3_1_8 import t_stub_FT_Rd

#: AISC 360-22 §J3.7 — traccion de tornillos.
PHI_BOLT_TENSION = 0.75
#: AISC 360-22 §J4.1(a) — fluencia de elementos de union (= phi_b de AISC
#: Design Guide 4 §3.3). Aplicado a Mpl,Rd del T-stub de la chapa.
PHI_PLATE_BENDING = 0.90


@dataclass(frozen=True)
class BoltRow:
    """Una fila de tornillos traccionados de la end plate.

    h_mm    brazo de la fila al centro de compresion (EN 1993-1-8 §6.2.7.2).
    leff_mm longitud eficaz del T-stub equivalente (Tabla 6.6 / AISC 358
            Tabla 6.2). Dato de entrada: NO se deduce aqui.
    m_mm    distancia del eje del tornillo a la cara del alma/ala menos 0.8·r.
    n_mm    min(e, 1.25·m).
    n_bolts numero de tornillos de la fila.
    """
    h_mm: float
    leff_mm: float
    m_mm: float
    n_mm: float
    n_bolts: int = 2


@dataclass(frozen=True)
class RowResult:
    h_mm: float
    Ft_Rd_nominal_kN: float
    Ft_Rd_design_kN: float
    governing_mode: str


@dataclass(frozen=True)
class EndPlateInput:
    M_demand_kNm: float
    bolt_diameter_mm: float       # d_b
    bolt_grade_Fu_MPa: float = 800.0    # ASTM A325/A490 default
    n_bolts: int = 8              # 4 filas × 2 columnas típico
    plate_thickness_mm: float = 25.0
    plate_Fy_MPa: float = 345.0
    plate_width_mm: float = 250.0
    #: OBSOLETO — conservado por compatibilidad de firma; no se usa.
    bolt_pitch_mm: float = 80.0
    #: Filas traccionadas. Sin ellas, Mj,Rd se declara NO CALCULADA.
    bolt_rows: tuple[BoltRow, ...] | None = None


@dataclass(frozen=True)
class EndPlateResult:
    #: Mj,Rd de DISENO [kN·m] (Ec. 6.25 con phi). None si no hay bolt_rows.
    M_resistance_kNm: float | None
    #: Mj,Rd NOMINAL [kN·m] (sin phi). None si no hay bolt_rows.
    M_resistance_nominal_kNm: float | None
    #: PROXY informativo M_demand/h_max [kN]. None si no hay bolt_rows.
    T_bolts_required_kN: float | None
    #: Rn NOMINAL de los tornillos traccionados [kN] (sin phi).
    T_bolts_capacity_kN: float
    #: phi·Rn de los tornillos traccionados [kN], phi = 0.75 (§J3.7).
    T_bolts_capacity_design_kN: float
    DCR_moment: float | None
    #: DCR del proxy de traccion. Informativo, NO gobierna is_safe.
    DCR_bolts: float | None
    #: None = NO CALCULADO (faltan bolt_rows).
    is_safe: bool | None
    rows: tuple[RowResult, ...]
    markdown: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "M_resistance_kNm": self.M_resistance_kNm,
            "M_resistance_nominal_kNm": self.M_resistance_nominal_kNm,
            "T_bolts_required_kN": self.T_bolts_required_kN,
            "T_bolts_capacity_kN": self.T_bolts_capacity_kN,
            "T_bolts_capacity_design_kN": self.T_bolts_capacity_design_kN,
            "DCR_moment": self.DCR_moment,
            "DCR_bolts": self.DCR_bolts,
            "is_safe": self.is_safe,
        }


def render_end_plate_memo(inp: EndPlateInput) -> EndPlateResult:
    A_b = pi * inp.bolt_diameter_mm ** 2 / 4.0
    # Rn por tornillo, AISC 360-22 Ec. (J3-1) con Fnt ~ 0.75·Fu (Tabla J3.2).
    Rn_bolt_N = 0.75 * inp.bolt_grade_Fu_MPa * A_b
    phiRn_bolt_N = PHI_BOLT_TENSION * Rn_bolt_N

    rows = inp.bolt_rows
    if rows:
        n_tension = sum(r.n_bolts for r in rows)
    else:
        # Compatibilidad: sin filas explicitas se asume la mitad de los
        # tornillos en traccion, como hacia la version anterior.
        n_tension = max(inp.n_bolts // 2, 1)

    T_capacity_kN = Rn_bolt_N * n_tension / 1000.0
    T_capacity_design_kN = phiRn_bolt_N * n_tension / 1000.0

    row_results: list[RowResult] = []
    M_design_kNm: float | None = None
    M_nominal_kNm: float | None = None
    T_required_kN: float | None = None
    DCR_M: float | None = None
    DCR_B: float | None = None
    is_safe: bool | None = None

    if rows:
        Mj_design_Nmm = 0.0
        Mj_nominal_Nmm = 0.0
        for r in rows:
            sum_Ft_nom = r.n_bolts * Rn_bolt_N
            sum_Ft_des = r.n_bolts * phiRn_bolt_N
            nom = t_stub_FT_Rd(
                leff_mm=r.leff_mm, tp_mm=inp.plate_thickness_mm,
                fy_plate_MPa=inp.plate_Fy_MPa, Ft_Rd_bolt_N=sum_Ft_nom,
                n_mm=r.n_mm, m_mm=r.m_mm, gamma_M0=1.0,
            )
            des = t_stub_FT_Rd(
                leff_mm=r.leff_mm, tp_mm=inp.plate_thickness_mm,
                fy_plate_MPa=inp.plate_Fy_MPa, Ft_Rd_bolt_N=sum_Ft_des,
                n_mm=r.n_mm, m_mm=r.m_mm,
                gamma_M0=1.0 / PHI_PLATE_BENDING,
            )
            Mj_nominal_Nmm += nom["FT_Rd_N"] * r.h_mm
            Mj_design_Nmm += des["FT_Rd_N"] * r.h_mm
            row_results.append(RowResult(
                h_mm=r.h_mm,
                Ft_Rd_nominal_kN=nom["FT_Rd_N"] / 1000.0,
                Ft_Rd_design_kN=des["FT_Rd_N"] / 1000.0,
                governing_mode=des["governing_mode"],
            ))
        M_design_kNm = Mj_design_Nmm / 1e6
        M_nominal_kNm = Mj_nominal_Nmm / 1e6
        DCR_M = inp.M_demand_kNm / M_design_kNm
        is_safe = DCR_M <= 1.0

        h_max_m = max(r.h_mm for r in rows) / 1000.0
        T_required_kN = inp.M_demand_kNm / h_max_m
        DCR_B = T_required_kN / T_capacity_design_kN

    md_head = (
        "# Memoria — Conexión End-Plate (EN 1993-1-8 §6.2.7.2 / AISC 360-22)\n\n"
        f"**Demanda:** M = {inp.M_demand_kNm:.1f} kN·m\n\n"
        "## Paso 1 — Resistencia a flexión de la CONEXIÓN\n"
        "Mj,Rd = Σ_r h_r·Ft,r,Rd  (EN 1993-1-8 Ec. 6.25), con Ft,r,Rd del "
        "T-stub equivalente §6.2.4.1 (modos 1/2/3).\n\n"
    )
    if rows:
        md_rows = "".join(
            f"- fila h = {rr.h_mm:.0f} mm → Ft,Rd = {rr.Ft_Rd_design_kN:.1f} kN "
            f"(diseño; nominal {rr.Ft_Rd_nominal_kN:.1f} kN; gobierna "
            f"{rr.governing_mode})\n"
            for rr in row_results
        )
        md_moment = (
            md_rows
            + f"\nMj,Rd (nominal) = {M_nominal_kNm:.1f} kN·m\n"
            + f"Mj,Rd (diseño)  = **{M_design_kNm:.1f} kN·m**\n\n"
        )
    else:
        md_moment = (
            "**NO CALCULADO** — falta `bolt_rows` (brazo h_r y geometría de "
            "T-stub leff/m/n de cada fila). No se sustituye por ningún "
            "sucedáneo.\n\n"
        )

    md_bolts = (
        "## Paso 2 — Capacidad de los pernos en tracción\n"
        f"A_b = π·d²/4 = {A_b:.1f} mm²\n"
        f"Rn = 0.75·Fu·Ab·n = {T_capacity_kN:.1f} kN (nominal, {n_tension} "
        "pernos traccionados)\n"
        f"φRn = 0.75·Rn = **{T_capacity_design_kN:.1f} kN** (diseño, §J3.7)\n\n"
        "## Paso 3 — Verificación\n"
    )
    if rows:
        md_check = (
            f"DCR_M = M / Mj,Rd(diseño) = {DCR_M:.2f}   ← GOBIERNA\n"
            f"DCR_bolts = {DCR_B:.2f}  (PROXY informativo: M/h_max frente a "
            "φRn; la tracción de los pernos ya está dentro de Mj,Rd por el "
            "modo 3 del T-stub)\n"
            f"{'✅ PASS' if is_safe else '❌ FAIL'}\n"
        )
    else:
        md_check = "DCR_M = NO CALCULADO → veredicto NO EMITIDO\n"

    return EndPlateResult(
        M_resistance_kNm=M_design_kNm,
        M_resistance_nominal_kNm=M_nominal_kNm,
        T_bolts_required_kN=T_required_kN,
        T_bolts_capacity_kN=T_capacity_kN,
        T_bolts_capacity_design_kN=T_capacity_design_kN,
        DCR_moment=DCR_M, DCR_bolts=DCR_B, is_safe=is_safe,
        rows=tuple(row_results),
        markdown=md_head + md_moment + md_bolts + md_check,
    )


__all__ = ["EndPlateInput", "EndPlateResult", "BoltRow", "RowResult",
           "render_end_plate_memo", "PHI_BOLT_TENSION", "PHI_PLATE_BENDING"]
