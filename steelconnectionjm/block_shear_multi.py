"""
Block shear (resistencia al desgarro en bloque) — 5 códigos.

Modelos:
    AISC 360-22 §J4.3:  φ·R_n = min(0.6·Fu·Anv + Ubs·Fu·Ant ;
                                     0.6·Fy·Agv + Ubs·Fu·Ant) · φ=0.75

    EN 1993-1-8 §3.10.2 (idéntico SG):
       Veff,1,Rd = Fu·Ant/γM2 + (1/√3)·Fy·Anv/γM0  (simétrica)

    AS 4100 §9.2:
       R_d = 0.75·(0.6·Fu·Anv + Fu·Ant)            (φ=0.75)

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


def _en1993_block(inp: BlockShearInput) -> tuple[float, str]:
    import math
    sqrt3 = math.sqrt(3.0)
    Rn = (inp.Fu_MPa * inp.Ant_mm2
          + (1.0 / sqrt3) * inp.Fy_MPa * inp.Anv_mm2) / 1000.0
    return Rn, "fracture"


def _as4100_block(inp: BlockShearInput) -> tuple[float, str]:
    Rn = (0.6 * inp.Fu_MPa * inp.Anv_mm2 + inp.Fu_MPa * inp.Ant_mm2) / 1000.0
    return Rn, "fracture"


def block_shear(inp: BlockShearInput, code: str = "US") -> BlockShearResult:
    code = code.upper()
    if code in ("US", "CO"):
        Rn, gov = _aisc_block(inp)
        phi = 0.75
        Rd = phi * Rn
    elif code in ("EU", "SG"):
        Rn, gov = _en1993_block(inp)
        gamma_M2 = 1.25
        phi = 1.0 / gamma_M2
        Rd = Rn / gamma_M2
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
