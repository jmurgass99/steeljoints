"""Servicio: WUF-W (Welded Unreinforced Flange-Welded Web) AISC 358-22 s8."""
from __future__ import annotations
from dataclasses import dataclass, field


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
    # Column properties
    col_d_mm: float = 350.0       # peralte columna
    col_bf_mm: float = 350.0      # ancho ala columna
    col_tf_mm: float = 18.0       # espesor ala columna
    col_tw_mm: float = 11.0       # espesor alma columna
    col_Zx_mm3: float = 4_000_000.0  # modulo plastico columna
    col_Fy_MPa: float = 345.0    # limite elastico columna
    # Connection
    beam_length_m: float = 6.0    # longitud total viga
    Ry: float = 1.1               # factor expected/nominal
    Mu_demand_kNm: float = 0.0    # momento demanda para DCR
    Vu_demand_kN: float = 0.0     # cortante demanda
    Pu_col_kN: float = 0.0        # axial columna (compresion positiva)
    Py_col_kN: float = 5000.0     # axial yield columna A*Fy


@dataclass(frozen=True)
class WUFResult:
    M_pr_kNm: float               # momento probable
    V_pr_kN: float                # cortante probable
    is_compact: bool              # cumple compactness AISC 341 s D1
    scwb_ratio: float             # strong-column weak-beam ratio
    pz_Vn_kN: float               # capacidad panel zone
    pz_DCR: float                 # DCR panel zone
    weld_capacity_kN: float       # capacidad CJP soldadura ala
    DCR: float                    # demand/capacity ratio global
    status: str                   # "OK" | "NG"
    notes: list[str] = field(default_factory=list)


def design_wuf(inp: WUFInput) -> WUFResult:
    """Diseno WUF-W segun AISC 358-22 s8.

    M_pr = C_pr * R_y * F_y * Z_x      C_pr = 1.15
    Verifica: compactness, SCWB, panel zone, soldadura CJP.
    """
    if inp.beam_d_mm <= 0 or inp.beam_Zx_mm3 <= 0:
        raise ValueError("beam_d y beam_Zx deben ser positivos")
    if inp.beam_Fy_MPa <= 0:
        raise ValueError("beam_Fy debe ser positivo")
    if inp.col_d_mm <= 0 or inp.col_Zx_mm3 <= 0:
        raise ValueError("col_d y col_Zx deben ser positivos")

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
        notes.append(
            f"Ala viga b/2tf={flange_ratio:.1f} > lam_p={lam_p_flange:.1f}"
        )
    if not web_ok:
        notes.append(
            f"Alma viga h/tw={web_ratio:.1f} > lam_p={lam_p_web:.1f}"
        )

    # ------- Strong-Column Weak-Beam (AISC 341 sE3.4a) -------
    M_pc = inp.col_Zx_mm3 * inp.col_Fy_MPa / 1e6  # kN*m
    M_pb = inp.beam_Zx_mm3 * inp.beam_Fy_MPa / 1e6  # kN*m
    scwb_ratio = M_pc / max(M_pb, 1e-9)
    if scwb_ratio < 1.0:
        notes.append(f"SCWB = {scwb_ratio:.2f} < 1.0 - NO CUMPLE")

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
    V_demand_pz_kN = M_pr_kNm * 1e3 / arm_mm if arm_mm > 0 else 0.0  # kN
    pz_DCR = V_demand_pz_kN / pz_Vn_kN if pz_Vn_kN > 0 else 99.0

    # ------- Soldadura CJP alas (capacidad) -------
    # CJP full penetration: capacidad = Fy_weld * A_flange
    # Para E70xx: FEXX = 482 MPa, pero CJP matched -> controlado por base metal
    A_flange_mm2 = inp.beam_bf_mm * inp.beam_tf_mm
    weld_capacity_N = inp.beam_Fy_MPa * A_flange_mm2  # N
    weld_capacity_kN = weld_capacity_N / 1e3

    # ------- DCR global -------
    if inp.Mu_demand_kNm > 0:
        DCR = inp.Mu_demand_kNm / M_pr_kNm if M_pr_kNm > 0 else 99.0
    else:
        DCR = 0.0

    status = "OK" if (DCR <= 1.0 and pz_DCR <= 1.0 and is_compact
                      and scwb_ratio >= 1.0) else "NG"

    notes.extend([
        f"M_pr = {M_pr_kNm:.1f} kN.m (C_pr={C_pr}, Ry={Ry})",
        f"V_pr = {V_pr_kN:.1f} kN",
        f"Panel zone: phiVn={pz_Vn_kN:.1f} kN, DCR={pz_DCR:.2f}",
        f"SCWB ratio = {scwb_ratio:.2f}",
        f"CJP weld capacity = {weld_capacity_kN:.1f} kN",
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
    )
