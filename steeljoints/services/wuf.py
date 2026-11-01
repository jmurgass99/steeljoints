"""Servicio: WUF-W (Welded Unreinforced Flange-Welded Web) AISC 358-22 s8."""
from __future__ import annotations
import math
from dataclasses import dataclass, field

from steeljoints._common.audit_status import CalculationStatus, resolve_status

from ._demanda import clasificar_momento, estado_heredado, nota_de_signo

#: Campos de la columna. Sin ellos no hay SCWB ni zona de panel: antes tenian
#: DEFAULTS (d=350, bf=350, tf=18, tw=11, Zx=4e6, Fy=345) y un cliente que mandaba
#: solo la viga recibia un veredicto sobre una columna que no existia.
_COLUMNA = ("col_d_mm", "col_bf_mm", "col_tf_mm", "col_tw_mm", "col_Zx_mm3", "col_Fy_MPa")


@dataclass(frozen=True)
class WUFInput:
    # Beam properties
    beam_d_mm: float              # peralte viga
    beam_bf_mm: float             # ancho ala viga
    beam_tf_mm: float             # espesor ala viga
    beam_tw_mm: float             # espesor alma viga
    beam_Zx_mm3: float            # modulo plastico viga
    beam_Fy_MPa: float = 345.0   # limite elastico viga
    beam_Fu_MPa: float = 450.0   # resistencia traccion viga
    # Column properties -- SIN defaults: una columna por defecto es una capacidad
    # inventada. `None` = no declarada -> SCWB y zona de panel no evaluables.
    col_d_mm: float | None = None       # peralte columna
    col_bf_mm: float | None = None      # ancho ala columna
    col_tf_mm: float | None = None      # espesor ala columna
    col_tw_mm: float | None = None      # espesor alma columna
    col_Zx_mm3: float | None = None     # modulo plastico columna
    col_Fy_MPa: float | None = None     # limite elastico columna
    # Connection
    beam_length_m: float = 6.0    # longitud total viga
    Ry: float = 1.1               # factor expected/nominal
    # Momento de demanda para el DCR. `None` = no suministrado (contrato AC-03,
    # ver `_demanda`): antes 0.0, y ausente/cero/negativo/NaN daban DCR 0.0.
    Mu_demand_kNm: float | None = None
    # Cortante de demanda: este servicio NO comprueba cortante. Se acepta por
    # compatibilidad y, si llega, la nota lo dice; no participa en nada.
    Vu_demand_kN: float | None = None
    # Axil de columna para la reduccion de M*pc en el SCWB (AISC 341 E3-1):
    # M*pc = Zc (Fyc - Pu/Ag) = Zc Fyc (1 - Pu/Py). Antes existian y NUNCA se
    # leian: el SCWB salia con Pu = 0, la cota superior mas favorable. Sin los dos
    # declarados el ratio publicado es esa cota, que solo puede probar un FALLO.
    Pu_col_kN: float | None = None      # axial columna (compresion positiva)
    Py_col_kN: float | None = None      # axial yield columna A*Fy


@dataclass(frozen=True)
class WUFResult:
    M_pr_kNm: float               # momento probable
    V_pr_kN: float                # cortante probable
    is_compact: bool              # cumple compactness AISC 341 s D1
    scwb_ratio: float | None      # strong-column weak-beam; None sin columna
    pz_Vn_kN: float | None        # capacidad panel zone; None sin columna
    pz_DCR: float | None          # DCR panel zone; None sin columna
    weld_capacity_kN: float       # capacidad CJP soldadura ala
    DCR: float | None             # |Mu| / M_pr; None sin demanda evaluable
    status: str                   # "OK" | "NG" | "UNKNOWN" (heredado; sigue al canonico)
    notes: list[str] = field(default_factory=list)
    # Veredicto canonico (Proof Obligation closed-by-default). Nace NO_CALCULADO.
    calculation_status: CalculationStatus = CalculationStatus.NO_CALCULADO
    missing_inputs: list[str] = field(default_factory=list)


def _columna_declarada(inp: WUFInput) -> list[str]:
    """Campos de columna ausentes o no positivos, con nombre."""
    faltan = []
    for campo in _COLUMNA:
        v = getattr(inp, campo)
        if v is None:
            faltan.append(f"{campo} (columna) ausente")
        elif not (isinstance(v, (int, float)) and math.isfinite(v) and v > 0):
            faltan.append(f"{campo} = {v!r} no es una magnitud positiva")
    return faltan


def design_wuf(inp: WUFInput) -> WUFResult:
    """Diseno WUF-W segun AISC 358-22 s8.

    M_pr = C_pr * R_y * F_y * Z_x      C_pr = 1.15
    Verifica: compactness, SCWB (con axil), panel zone, soldadura CJP, y el DCR
    de momento |Mu| / M_pr.

    Veredicto: CALCULADO_FALLA si CUALQUIER comprobacion evaluada falla, aunque
    otra no sea evaluable (un fallo probado es un hecho sobre la conexion).
    CALCULADO_CUMPLE solo con las cuatro evaluadas y aprobadas: columna y axil
    declarados, demanda finita y no nula. Lo demas: NO_CALCULADO (falta algo) o
    REQUIERE_REVISION (algo no es un numero, o Pu >= Py).
    """
    if inp.beam_d_mm <= 0 or inp.beam_Zx_mm3 <= 0:
        raise ValueError("beam_d y beam_Zx deben ser positivos")
    if inp.beam_Fy_MPa <= 0:
        raise ValueError("beam_Fy debe ser positivo")
    if inp.beam_bf_mm <= 0 or inp.beam_tf_mm <= 0 or inp.beam_tw_mm <= 0:
        raise ValueError("beam_bf, beam_tf y beam_tw deben ser positivos")

    C_pr = 1.15
    Ry = inp.Ry

    # ------- Momento probable (AISC 358 s8) -------
    M_pr_Nmm = C_pr * Ry * inp.beam_Fy_MPa * inp.beam_Zx_mm3  # N*mm
    M_pr_kNm = M_pr_Nmm / 1e6  # kN*m

    # Cortante probable (Lp = d_b para WUF-W)
    Lp = inp.beam_d_mm / 1000.0
    L_clear = inp.beam_length_m - 2.0 * Lp
    if L_clear > 0:
        V_pr_kN = 2.0 * M_pr_kNm / L_clear
    else:
        V_pr_kN = 2.0 * M_pr_kNm / 0.5

    notes: list[str] = []
    missing_inputs: list[str] = []
    fallos: list[str] = []          # comprobaciones EVALUADAS que fallan
    revision: list[str] = []        # valores que no son evaluables

    # ------- Compactness AISC 341 sD1 (highly ductile) -------
    E = 200_000.0  # MPa
    lam_p_flange = 0.30 * (E / inp.beam_Fy_MPa) ** 0.5
    flange_ratio = (inp.beam_bf_mm / 2.0) / inp.beam_tf_mm
    flange_ok = flange_ratio <= lam_p_flange

    h_web = inp.beam_d_mm - 2.0 * inp.beam_tf_mm
    web_ratio = h_web / inp.beam_tw_mm
    lam_p_web = 2.45 * (E / inp.beam_Fy_MPa) ** 0.5
    web_ok = web_ratio <= lam_p_web

    is_compact = flange_ok and web_ok
    if not flange_ok:
        notes.append(f"Ala viga b/2tf={flange_ratio:.1f} > lam_p={lam_p_flange:.1f}")
    if not web_ok:
        notes.append(f"Alma viga h/tw={web_ratio:.1f} > lam_p={lam_p_web:.1f}")
    if not is_compact:
        fallos.append("compacidad AISC 341 D1")

    # ------- Columna: declarada o nada -------
    faltan_columna = _columna_declarada(inp)
    missing_inputs.extend(faltan_columna)
    scwb_ratio: float | None = None
    pz_Vn_kN: float | None = None
    pz_DCR: float | None = None

    if not faltan_columna:
        # ------- Strong-Column Weak-Beam (AISC 341 sE3.4a) -------
        # ΣM*pb de AISC 341 §E3.4a: momento probable de la viga proyectado al eje del pilar,
        # Mpr + Vpr·dc/2 (rótula en la cara del pilar en WUF-W). Hasta la versión 1.1 se usaba
        # Zb·Fyb nominal, sin Cpr·Ry ni el momento adicional del cortante: el SCWB salía un 35-40 % alto.
        M_pb = M_pr_kNm + V_pr_kN * (inp.col_d_mm / 2.0) / 1000.0  # kN*m
        notes.append(f"SCWB: M*pb = Mpr + Vpr·dc/2 = {M_pb:.1f} kN.m")
        M_pc_bruto = inp.col_Zx_mm3 * inp.col_Fy_MPa / 1e6  # kN*m, Pu = 0
        axil_declarado = inp.Pu_col_kN is not None and inp.Py_col_kN is not None
        if axil_declarado:
            pu, py = float(inp.Pu_col_kN), float(inp.Py_col_kN)
            if not (math.isfinite(pu) and math.isfinite(py)) or py <= 0 or pu < 0:
                revision.append(f"Pu_col_kN={inp.Pu_col_kN!r} / Py_col_kN={inp.Py_col_kN!r} "
                                f"no son un axil evaluable")
                scwb_ratio = None
            elif pu >= py:
                revision.append(f"Pu_col_kN={pu:.0f} >= Py_col_kN={py:.0f}: la columna esta "
                                f"agotada a axil, el SCWB no es evaluable")
                scwb_ratio = None
            else:
                scwb_ratio = M_pc_bruto * (1.0 - pu / py) / max(M_pb, 1e-9)
                notes.append(f"SCWB con axil: M*pc = Zc Fyc (1 - Pu/Py), Pu/Py = {pu / py:.3f}")
        else:
            # Cota superior (Pu = 0): solo puede probar un fallo.
            scwb_ratio = M_pc_bruto / max(M_pb, 1e-9)
            if scwb_ratio >= 1.0:
                missing_inputs.append(
                    f"Pu_col_kN y Py_col_kN (axil de columna para SCWB) ausentes: "
                    f"SCWB = {scwb_ratio:.2f} es una cota superior con Pu = 0 y no prueba nada")
            else:
                notes.append(f"SCWB = {scwb_ratio:.2f} < 1.0 incluso con Pu = 0: fallo probado "
                             f"sin necesitar el axil")
        if scwb_ratio is not None and scwb_ratio < 1.0:
            notes.append(f"SCWB = {scwb_ratio:.2f} < 1.0 - NO CUMPLE")
            fallos.append(f"SCWB {scwb_ratio:.2f} < 1.0")

        # ------- Panel Zone (AISC 360 sJ10.6 simplificado) -------
        Fy_c = inp.col_Fy_MPa
        d_c = inp.col_d_mm   # mm
        t_w = inp.col_tw_mm  # mm
        d_b = inp.beam_d_mm  # mm
        b_fc = inp.col_bf_mm  # mm
        t_fc = inp.col_tf_mm  # mm

        Vn_elastic = 0.60 * Fy_c * d_c * t_w  # N (MPa * mm * mm = N)
        factor = 1.0 + (3.0 * b_fc * t_fc ** 2) / (d_b * d_c * t_w)
        Vn_pz = Vn_elastic * factor  # N
        phi_pz = 0.90
        pz_Vn_kN = phi_pz * Vn_pz / 1e3  # kN

        # Demanda panel zone: V_pz ~ M_pr / (d_b - t_f)
        arm_mm = d_b - inp.beam_tf_mm
        if arm_mm > 0 and pz_Vn_kN > 0:
            V_demand_pz_kN = M_pr_kNm * 1e3 / arm_mm  # kN
            pz_DCR = V_demand_pz_kN / pz_Vn_kN
            if pz_DCR > 1.0:
                fallos.append(f"zona de panel DCR {pz_DCR:.2f}")
        else:
            # Antes: `else 99.0`, un numero fabricado.
            revision.append(f"zona de panel no evaluable: brazo {arm_mm:.1f} mm, "
                            f"phiVn {pz_Vn_kN:.1f} kN")
            pz_DCR = None

    # ------- Soldadura CJP alas (capacidad) -------
    # CJP full penetration: capacidad = Fy_weld * A_flange
    # Para E70xx: FEXX = 482 MPa, pero CJP matched -> controlado por base metal
    A_flange_mm2 = inp.beam_bf_mm * inp.beam_tf_mm
    weld_capacity_N = inp.beam_Fy_MPa * A_flange_mm2  # N
    weld_capacity_kN = weld_capacity_N / 1e3

    # ------- DCR de momento: estado de la demanda declarado junto al calculo -------
    dem = clasificar_momento(inp.Mu_demand_kNm, nombre="Mu_demand_kNm")
    if not dem.presente:
        missing_inputs.append(dem.motivo)
    if dem.es_evaluable and M_pr_kNm > 0:
        util: float | None = dem.magnitud / M_pr_kNm
        DCR: float | None = util
        if DCR > 1.0:
            fallos.append(f"momento DCR {DCR:.2f}")
    elif dem.estado == "INVALID":
        util, DCR = float("nan"), None
        revision.append(dem.motivo)
    else:
        util, DCR = None, None
    if inp.Vu_demand_kN is not None:
        notes.append(f"Vu_demand_kN = {inp.Vu_demand_kN!r} recibido: este servicio no "
                     f"comprueba cortante, no participa en el veredicto")

    # ------- Veredicto -------
    if fallos:
        # Un fallo en una comprobacion EVALUADA (con sus datos declarados y
        # validados) es un hecho sobre la conexion, aunque otra no sea evaluable.
        calculation_status = CalculationStatus.CALCULADO_FALLA
    else:
        # Proof Obligation closed-by-default. `reinforcement_present=True`
        # documentado: conexion de acero, sin armadura. La columna declarada es
        # la geometria y el material de la capacidad; el axil declarado y la
        # zona de panel evaluada son la capacidad.
        # Lo no evaluable llega como utilizacion NaN (regla 4 -> REQUIERE_REVISION)
        # o como missing_inputs (regla 2 -> NO_CALCULADO); `capacity_present` es
        # que los datos de la capacidad esten declarados y validados.
        columna_ok = not faltan_columna
        calculation_status = resolve_status(
            util if not revision else float("nan"),
            missing_inputs=missing_inputs,
            demand_present=dem.presente,
            capacity_present=columna_ok and M_pr_kNm > 0,
            analysis_executed=True,
            geometry_present=columna_ok,
            material_present=columna_ok,
            reinforcement_present=True,
        )
    status = estado_heredado(calculation_status)

    notes.extend([
        f"M_pr = {M_pr_kNm:.1f} kN.m (C_pr={C_pr}, Ry={Ry})",
        f"V_pr = {V_pr_kN:.1f} kN",
        (f"Panel zone: phiVn={pz_Vn_kN:.1f} kN, DCR={pz_DCR:.2f}" if pz_DCR is not None
         else "Panel zone: no evaluable"),
        (f"SCWB ratio = {scwb_ratio:.2f}" if scwb_ratio is not None else "SCWB: no evaluable"),
        f"CJP weld capacity = {weld_capacity_kN:.1f} kN",
        *nota_de_signo(dem, nombre="Mu_demand_kNm"),
        *[f"Sin veredicto: {m}" for m in missing_inputs],
        *[f"Requiere revision: {m}" for m in revision],
        *[f"Incumple: {f}" for f in fallos],
    ])

    return WUFResult(
        M_pr_kNm=M_pr_kNm,
        V_pr_kN=V_pr_kN,
        is_compact=is_compact,
        scwb_ratio=scwb_ratio,
        pz_Vn_kN=pz_Vn_kN,
        pz_DCR=pz_DCR,
        weld_capacity_kN=weld_capacity_kN,
        DCR=DCR,
        status=status,
        notes=notes,
        calculation_status=calculation_status,
        missing_inputs=missing_inputs,
    )
