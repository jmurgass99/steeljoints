"""
Block shear (resistencia al desgarro en bloque) — 5 códigos.

Modelos:
    AISC 360-22 §J4.3:  φ·R_n = min(0.6·Fu·Anv + Ubs·Fu·Ant ;
                                     0.6·Fy·Agv + Ubs·Fu·Ant) · φ=0.75

    EN 1993-1-8 §3.10.2 (idéntico SG):
       Veff,1,Rd = Fu·Ant/γM2 + (1/√3)·Fy·Anv/γM0  (simétrica)

    AS 4100 §9.1.9 (enmienda de 2012, misma forma que AISC):
       φ·R_bs = 0.75·min(0.6·fu·Anv + kbs·fu·Ant ; 0.6·fy·Agv + kbs·fu·Ant),  kbs = Ubs

    NSR-10 §F.2 (idéntico AISC con notación):
       φ·R_n con φ=0.75
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class BlockShearInput:
    Agv_mm2: float          # gross shear area
    Anv_mm2: float          # net shear area
    Ant_mm2: float          # net tension area
    Fy_MPa: float = 345
    Fu_MPa: float = 450
    Ubs: float = 1.0        # 1.0 tensión uniforme, 0.5 no uniforme


@dataclass(frozen=True)
class BlockShearResult:
    Rn_kN: float            # resistencia nominal
    phi_or_gamma: float
    Rd_kN: float            # resistencia de diseño
    governing: Literal["fracture", "yield"]
    code: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "Rn_kN": self.Rn_kN, "phi_or_gamma": self.phi_or_gamma,
            "Rd_kN": self.Rd_kN, "governing": self.governing, "code": self.code,
        }


def _aisc_block(inp: BlockShearInput) -> tuple[float, str]:
    Rn1 = 0.6 * inp.Fu_MPa * inp.Anv_mm2 + inp.Ubs * inp.Fu_MPa * inp.Ant_mm2
    Rn2 = 0.6 * inp.Fy_MPa * inp.Agv_mm2 + inp.Ubs * inp.Fu_MPa * inp.Ant_mm2
    Rn = min(Rn1, Rn2) / 1000.0
    gov = "fracture" if Rn1 < Rn2 else "yield"
    return Rn, gov


def _en1993_block(inp: BlockShearInput) -> tuple[float, float, str]:
    """EC3-1-8 Sec 3.10.2: los DOS terminos llevan factores parciales
    DISTINTOS — traccion sobre gamma_M2, cortante sobre gamma_M0 (=1.0) — no
    se puede resumir en un unico Rn dividido por un unico gamma. Devuelve
    (Rn_kN sin factorizar, Rd_kN correctamente factorizado, modo).
    """
    import math
    sqrt3 = math.sqrt(3.0)
    gamma_M2 = 1.25
    gamma_M0 = 1.0
    term_tension = inp.Fu_MPa * inp.Ant_mm2
    term_shear = (1.0 / sqrt3) * inp.Fy_MPa * inp.Anv_mm2
    Rn = (term_tension + term_shear) / 1000.0
    Rd = (term_tension / gamma_M2 + term_shear / gamma_M0) / 1000.0
    return Rn, Rd, "fracture"


def _as4100_block(inp: BlockShearInput) -> tuple[float, str]:
    """AS 4100 §9.1.9 (enmienda de 2012): misma forma que AISC 360 §J4.3, con kbs = Ubs y el tope
    de fluencia por cortante 0,6·fy·Agv. Hasta la versión 1.1 faltaban el tope y kbs, del lado inseguro
    cuando gobierna la fluencia o la tracción no es uniforme."""
    return _aisc_block(inp)


def block_shear(inp: BlockShearInput, code: str = "US") -> BlockShearResult:
    code = code.upper()
    if code in ("US", "CO"):
        Rn, gov = _aisc_block(inp)
        phi = 0.75
        Rd = phi * Rn
    elif code in ("EU", "SG"):
        Rn, Rd, gov = _en1993_block(inp)
        # factor EFECTIVO Rd/Rn: informativo solamente. Los dos terminos de
        # este modelo llevan gamma distinto (M2 traccion, M0 cortante), asi
        # que NO es un unico gamma normativo — no lo uses como tal.
        phi = Rd / Rn if Rn > 0.0 else 0.0
    elif code == "AU":
        Rn, gov = _as4100_block(inp)
        phi = 0.75
        Rd = phi * Rn
    else:
        raise ValueError(f"código '{code}' no soportado")

    return BlockShearResult(
        Rn_kN=Rn, phi_or_gamma=phi, Rd_kN=Rd,
        governing=gov, code=code,
    )


__all__ = ["BlockShearInput", "BlockShearResult", "block_shear"]
