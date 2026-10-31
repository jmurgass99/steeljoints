"""
Memoria handcalcs — Panel Zone (zona de panel nodal).

Capacidad a cortante del alma del pilar, ANSI/AISC 360-22 §J10.6, caso
alpha·Pr <= 0.4·Pc:

    (J10-11)  Rn = 0.60·Fy·dc·tw
              cuando el efecto de la deformacion de la zona de panel NO se
              considera en el analisis de estabilidad del portico.

    (J10-12)  Rn = 0.60·Fy·dc·tw · (1 + 3·bcf·tcf^2 / (db·dc·tw))
              cuando SI se considera.

    LRFD §J10.6:  phi = 0.90  ->  capacidad de diseno phi·Rn.

El termino de las alas del pilar (3·bcf·tcf^2/(db·dc·tw)) SOLO esta permitido
en el segundo caso; aplicarlo siempre sobreestima la capacidad (+22.9 % en el
caso de tests/test_memo_panel_zone.py). Por eso se selecciona con el parametro
explicito ``PanelZoneInput.include_panel_deformation``, cuyo DEFAULT ES False
(Ec. J10-11, la rama restrictiva): un default permisivo convertiria en
inseguro a todo llamante que no conozca el parametro.

DEMANDA — LIMITACION DOCUMENTADA (no corregida):
    V_pz = 0.8·(M_f1 + M_f2)/d_b - V_c
  * El coeficiente 0.8 NO ha podido situarse en AISC 341-22 §E3.6e: la norma
    obtiene el cortante requerido de la suma de momentos en las caras del
    pilar correspondientes a las rotulas plasticas proyectadas (Mpr), sin un
    coeficiente global 0.8.
  * El brazo empleado es d_b (canto de la viga) cuando la practica habitual es
    (d_b - t_f), la distancia entre centros de alas. Usar d_b subestima la
    fuerza de ala y por tanto la demanda (lado inseguro), pero no se cambia
    aqui: fijar el brazo correcto exige t_f de la viga, que la entrada no
    tiene, y sustituirlo sin dato seria inventar una hipotesis.
  La demanda queda anclada por un test de CARACTERIZACION, no por un golden.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Factor de resistencia LRFD para cortante de la zona de panel, AISC 360-22 §J10.6.
PHI_PANEL_ZONE = 0.90


@dataclass(frozen=True)
class PanelZoneInput:
    M_f1_kNm: float          # momento en cara 1 de columna
    M_f2_kNm: float
    d_beam_mm: float
    d_column_mm: float
    t_web_column_mm: float
    b_flange_column_mm: float
    t_flange_column_mm: float
    t_doubler_mm: float = 0.0
    Fy_MPa: float = 345.0
    V_column_kN: float = 0.0
    #: True  -> Ec. (J10-12): el analisis del portico INCLUYE la deformacion
    #:          inelastica de la zona de panel (§J10.6), se permite el termino
    #:          de las alas del pilar.
    #: False -> Ec. (J10-11), rama restrictiva. DEFAULT DELIBERADO.
    include_panel_deformation: bool = False


@dataclass(frozen=True)
class PanelZoneResult:
    #: Rn NOMINAL [kN] (sin phi), Ec. (J10-11) o (J10-12) segun la entrada.
    V_capacity_kN: float
    #: phi·Rn [kN] con phi = 0.90 (§J10.6). Es la capacidad de DISENO.
    phi_Rn_kN: float
    phi: float
    #: "J10-11" o "J10-12".
    equation: str
    V_demand_kN: float
    #: DCR = V_demand / phi·Rn  (sobre la capacidad de DISENO).
    DCR: float
    needs_doubler: bool
    markdown: str

    def to_dict(self) -> dict[str, float | bool | str]:
        return {
            "V_demand_kN": self.V_demand_kN,
            "V_capacity_kN": self.V_capacity_kN,
            "phi_Rn_kN": self.phi_Rn_kN,
            "phi": self.phi,
            "equation": self.equation,
            "DCR": self.DCR,
            "needs_doubler": self.needs_doubler,
        }


def render_panel_zone_memo(inp: PanelZoneInput) -> PanelZoneResult:
    db, dc = inp.d_beam_mm, inp.d_column_mm
    bcf, tcf = inp.b_flange_column_mm, inp.t_flange_column_mm
    tp = inp.t_web_column_mm + inp.t_doubler_mm

    if db <= 0.0 or dc <= 0.0 or tp <= 0.0:
        raise ValueError(
            "d_beam_mm, d_column_mm y (t_web_column_mm + t_doubler_mm) deben "
            f"ser > 0; recibido db={db}, dc={dc}, tp={tp}"
        )

    # --- Demanda (ver limitacion documentada en el docstring del modulo) ---
    V_demand_kN = 0.8 * (inp.M_f1_kNm + inp.M_f2_kNm) / (db / 1000.0) \
        - inp.V_column_kN

    # --- Capacidad nominal, AISC 360-22 §J10.6 ---
    Rn_base_N = 0.60 * inp.Fy_MPa * dc * tp
    if inp.include_panel_deformation:
        flange_term = (3.0 * bcf * tcf ** 2) / (db * dc * tp)
        Rn_N = Rn_base_N * (1.0 + flange_term)
        equation = "J10-12"
    else:
        flange_term = 0.0
        Rn_N = Rn_base_N
        equation = "J10-11"

    V_capacity_kN = Rn_N / 1000.0
    phi_Rn_kN = PHI_PANEL_ZONE * V_capacity_kN

    DCR = V_demand_kN / phi_Rn_kN
    needs = DCR > 1.0

    if inp.include_panel_deformation:
        cap_line = (
            "Ec. (J10-12) — el analisis del portico INCLUYE la deformacion de "
            "la zona de panel\n\n"
            f"Rn = 0.60·Fy·d_c·t_p·(1 + 3·b_cf·t_cf² / (d_b·d_c·t_p)) "
            f"= {V_capacity_kN:.1f} kN   (nominal; termino de alas = "
            f"{flange_term:.4f})\n"
        )
    else:
        cap_line = (
            "Ec. (J10-11) — el analisis del portico NO incluye la deformacion "
            "de la zona de panel;\nel termino de las alas del pilar NO esta "
            "permitido (§J10.6)\n\n"
            f"Rn = 0.60·Fy·d_c·t_p = {V_capacity_kN:.1f} kN   (nominal)\n"
        )

    md = (
        "# Memoria — Panel Zone AISC 360-22 §J10.6\n\n"
        "## Demanda\n"
        f"V_pz = 0.8·(M_f1+M_f2)/d_b - V_c = {V_demand_kN:.1f} kN\n\n"
        "> NOTA: el coeficiente 0.8 no esta trazado a norma y el brazo es d_b "
        "en vez de (d_b - t_f). Ver docstring del modulo.\n\n"
        "## Capacidad\n"
        f"{cap_line}"
        f"phi·Rn = {PHI_PANEL_ZONE:.2f}·{V_capacity_kN:.1f} = "
        f"**{phi_Rn_kN:.1f} kN**   (diseno, §J10.6)\n\n"
        "## Resultado\n"
        f"DCR = V_pz / (phi·Rn) = {DCR:.2f} → "
        f"{'❌ requiere doubler' if needs else '✅'}\n"
    )

    return PanelZoneResult(
        V_capacity_kN=V_capacity_kN, phi_Rn_kN=phi_Rn_kN,
        phi=PHI_PANEL_ZONE, equation=equation,
        V_demand_kN=V_demand_kN, DCR=DCR, needs_doubler=needs, markdown=md,
    )


__all__ = ["PanelZoneInput", "PanelZoneResult", "render_panel_zone_memo",
           "PHI_PANEL_ZONE"]
