"""
Conexión de momento con cartela (haunch) — idea #13.

Cartela triangular soldada al ala inferior de la viga para incrementar
brazo de palanca y reducir tensiones en la unión. Diseño basado en
SAC/FEMA-350 §3.6 + AISC 358 Appendix.

Verifica:
- Resistencia a momento del conjunto (Mn = Fy*Zx_aumentado)
- Tensión en el alma de la columna por componente vertical del haunch
- Esbeltez del ala del haunch (b/t <= 0.30*sqrt(E/Fy))

Multi-code:
- AISC (USA), EC3 (EU), AS 4100 (AU), NSR-10 (CO), SS EN (SG)
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class HaunchInput:
    beam_depth_mm: float
    beam_flange_b_mm: float
    beam_flange_tf_mm: float
    beam_Zx_mm3: float
    haunch_depth_mm: float          # altura cartela
    haunch_length_mm: float         # longitud (proyección horizontal)
    haunch_tf_mm: float             # espesor ala cartela
    haunch_bf_mm: float             # ancho ala cartela
    Fy_MPa: float = 350.0
    E_MPa: float = 200000.0
    code: str = "USA"


@dataclass(frozen=True)
class HaunchResult:
    Mn_kNm: float                 # capacidad nominal
    angle_deg: float
    vertical_force_kN_per_kNm: float   # Vh por unidad de M (componente vert)
    flange_slenderness_ratio: float
    flange_compact: bool
    phi: float
    code: str


_PHI = {
    "USA": 0.90, "AISC": 0.90,
    "EU": 1.0 / 1.0, "EUROCODE": 1.0 / 1.0,   # gamma_M0=1.0
    "AS": 0.90, "AU": 0.90,
    "NSR": 0.90, "CO": 0.90,
    "SG": 1.0, "SS": 1.0,
}


def design_haunch(inp: HaunchInput) -> HaunchResult:
    if inp.beam_depth_mm <= 0 or inp.haunch_depth_mm <= 0 or inp.haunch_length_mm <= 0:
        raise ValueError("dimensiones positivas requeridas")
    c = inp.code.upper()
    if c not in _PHI:
        raise ValueError(f"Código desconocido: {inp.code}")
    phi = _PHI[c]

    # Ángulo del haunch
    angle_rad = math.atan(inp.haunch_depth_mm / inp.haunch_length_mm)
    # Brazo aumentado ~ d_beam + h_haunch/2
    arm_mm = inp.beam_depth_mm + inp.haunch_depth_mm / 2.0
    # Mn nominal del conjunto: usar Zx beam + ΔZ por cartela
    delta_Z = inp.haunch_bf_mm * inp.haunch_tf_mm * (inp.beam_depth_mm + inp.haunch_depth_mm / 2.0)
    Zx_total = inp.beam_Zx_mm3 + delta_Z
    Mn_Nmm = inp.Fy_MPa * Zx_total
    Mn_kNm = Mn_Nmm / 1e6

    # Componente vertical en la cara columna: V_h = M / arm * tan(angle)
    V_per_M = (1.0 / (arm_mm / 1000.0)) * math.tan(angle_rad)  # kN_V / kNm_M

    # Esbeltez ala cartela
    if inp.haunch_tf_mm <= 0:
        slender_ratio = float("inf")
        compact = False
    else:
        slender_ratio = (inp.haunch_bf_mm / 2.0) / inp.haunch_tf_mm
        limit = 0.30 * math.sqrt(inp.E_MPa / inp.Fy_MPa)
        compact = slender_ratio <= limit

    return HaunchResult(
        Mn_kNm=phi * Mn_kNm,
        angle_deg=math.degrees(angle_rad),
        vertical_force_kN_per_kNm=V_per_M,
        flange_slenderness_ratio=slender_ratio,
        flange_compact=compact,
        phi=phi,
        code=inp.code,
    )
