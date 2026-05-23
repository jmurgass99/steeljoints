"""Servicio: RBS (Reduced Beam Section) AISC 358-22 cap. 5."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RBSInput:
    d_mm: float               # peralte viga
    bf_mm: float              # ancho ala viga
    tf_mm: float              # espesor ala viga
    tw_mm: float              # espesor alma viga
    Zx_mm3: float             # modulo plastico seccion completa
    Fy_MPa: float             # limite elastico
    Fu_MPa: float             # resistencia a traccion
    a_mm: float               # distancia cara columna a inicio corte
    b_mm: float               # longitud zona reducida
    c_mm: float               # profundidad corte cada lado
    L_clear_m: float = 6.0    # luz libre entre caras de columna
    wu_kN_per_m: float = 0.0  # carga gravitacional uniforme factorada
    Ry: float = 1.1           # factor expected/nominal AISC 341 Tabla A3.1
    Mu_demand_kNm: float = 0.0  # momento de demanda para calculo DCR


@dataclass(frozen=True)
class RBSResult:
    Z_RBS_mm3: float          # modulo plastico reducido
    M_pr_kNm: float           # momento probable en rotula plastica
    V_pr_kN: float            # cortante probable en rotula plastica
    M_f_kNm: float            # momento en cara de columna
    DCR: float                # demand-capacity ratio
    status: str               # "OK" | "NG"
    is_geometry_ok: bool       # cumple limites a, b, c AISC 358 s5.8
    notes: list[str] = field(default_factory=list)


def design_rbs(inp: RBSInput) -> RBSResult:
    """Diseno RBS segun AISC 358-22 s5.8.

    Z_RBS = Z_x - 2*c*t_f*(d - t_f)       Eq. 5.8-4
    M_pr  = C_pr * R_y * F_y * Z_RBS       C_pr = 1.15
    V_pr  = 2*M_pr / L_h + wu*L_clear/2
    M_f   = M_pr + V_pr * S_h
    """
    if inp.d_mm <= 0 or inp.bf_mm <= 0 or inp.tf_mm <= 0:
        raise ValueError("d, bf, tf deben ser positivos")
    if inp.Zx_mm3 <= 0:
        raise ValueError("Zx debe ser positivo")
    if inp.b_mm <= 0 or inp.c_mm <= 0:
        raise ValueError("b y c deben ser positivos")
    if inp.a_mm < 0:
        raise ValueError("a debe ser >= 0")
    if inp.Fy_MPa <= 0 or inp.Fu_MPa <= 0:
        raise ValueError("Fy y Fu deben ser positivos")
    if inp.L_clear_m <= 0:
        raise ValueError("L_clear debe ser positivo")

    # Modulo plastico reducido  AISC 358 Eq. 5.8-4
    Z_RBS = inp.Zx_mm3 - 2.0 * inp.c_mm * inp.tf_mm * (inp.d_mm - inp.tf_mm)

    # Momento probable  C_pr = 1.15 (AISC 358 s2.4.3)
    C_pr = 1.15
    M_pr_Nmm = C_pr * inp.Ry * inp.Fy_MPa * Z_RBS  # N*mm
    M_pr_kNm = M_pr_Nmm / 1e6  # kN*m

    # Distancia centro RBS desde cara columna
    S_h_mm = inp.a_mm + inp.b_mm / 2.0
    # Distancia entre centros de rotulas plasticas
    L_h_m = inp.L_clear_m - 2.0 * S_h_mm / 1000.0

    # Cortante probable en rotula plastica
    if L_h_m > 0:
        V_pr_kN = 2.0 * M_pr_kNm / L_h_m + inp.wu_kN_per_m * inp.L_clear_m / 2.0
    else:
        V_pr_kN = 2.0 * M_pr_kNm / 0.5 + inp.wu_kN_per_m * inp.L_clear_m / 2.0

    # Momento en cara de columna
    M_f_kNm = M_pr_kNm + V_pr_kN * (S_h_mm / 1000.0)

    # DCR basado en demanda suministrada
    if inp.Mu_demand_kNm > 0:
        DCR = inp.Mu_demand_kNm / M_f_kNm if M_f_kNm > 0 else 99.0
    else:
        DCR = 0.0

    status = "OK" if DCR <= 1.0 else "NG"

    # Verificacion geometria AISC 358 s5.8.1
    a_min, a_max = 0.5 * inp.bf_mm, 0.75 * inp.bf_mm
    b_min, b_max = 0.65 * inp.d_mm, 0.85 * inp.d_mm
    c_min, c_max = 0.10 * inp.bf_mm, 0.25 * inp.bf_mm
    is_geometry_ok = (
        a_min <= inp.a_mm <= a_max
        and b_min <= inp.b_mm <= b_max
        and c_min <= inp.c_mm <= c_max
    )

    notes = [
        f"Z_RBS = {Z_RBS:.0f} mm3 ({Z_RBS / inp.Zx_mm3 * 100:.1f}% Z_x)",
        f"M_pr = {M_pr_kNm:.1f} kN.m (C_pr={C_pr}, Ry={inp.Ry})",
        f"V_pr = {V_pr_kN:.1f} kN",
        f"M_f (cara columna) = {M_f_kNm:.1f} kN.m",
        f"Geometria s5.8.1: {'OK' if is_geometry_ok else 'FUERA DE LIMITES'}",
    ]

    return RBSResult(
        Z_RBS_mm3=Z_RBS,
        M_pr_kNm=M_pr_kNm,
        V_pr_kN=V_pr_kN,
        M_f_kNm=M_f_kNm,
        DCR=DCR,
        status=status,
        is_geometry_ok=is_geometry_ok,
        notes=notes,
    )
