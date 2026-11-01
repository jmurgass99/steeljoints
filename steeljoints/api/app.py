"""FastAPI app para diseno de conexiones de acero."""
from __future__ import annotations

try:
    from fastapi import APIRouter, FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
except ImportError as exc:
    raise ImportError(
        "fastapi requerido: pip install steeljoints[api]"
    ) from exc

from .._brand import NAME as _BRAND_NAME
from .. import __version__ as _VERSION
from ..services import (
    bolts, welds, end_plate, base_plate,
    panel_zone, splice, clip_angle, rbs, wuf,
)


# --- Modelos Pydantic (espejo de los dataclasses de services/) ---
# Tipan los endpoints → schema OpenAPI + validación. model_dump() reproduce
# exactamente los kwargs del dataclass, así que el comportamiento no cambia.

class SingleBoltPayload(BaseModel):
    grade: str = Field(..., description="A325/A490/A307 (AISC) | 8.8/10.9 (EC3)")
    diameter_mm: float = Field(..., gt=0)
    thread_condition: str = "N"          # "N" rosca incluida | "X" excluida
    standard: str = "AISC"               # "AISC" | "EC3"
    plate_thickness_mm: float = 10.0
    plate_fu_MPa: float = 400.0
    edge_distance_mm: float = 30.0


class BoltGroupPayload(BaseModel):
    n_bolts: int = Field(..., ge=1)
    diameter_mm: float = Field(..., gt=0)
    grade: str = "A325"
    spacing_mm: float = 76.0
    layout: str = "linear"
    Vu_kN: float = 0.0
    Mu_kNm: float = 0.0


class FilletWeldPayload(BaseModel):
    leg_size_mm: float = Field(..., gt=0)
    length_mm: float = Field(..., gt=0)
    electrode_FEXX_MPa: float = 482.0
    angle_load_deg: float = 0.0


class EndPlatePayload(BaseModel):
    bp_mm: float = Field(..., gt=0)
    tp_mm: float = Field(..., gt=0)
    db_mm: float = Field(..., gt=0)
    bf_mm: float = Field(..., gt=0)
    tf_mm: float = Field(..., gt=0)
    bolt_diameter_mm: float = Field(..., gt=0)
    bolt_grade: str = "A325"
    fy_plate_MPa: float = 345.0
    Mu_kNm: float = 100.0


class EndPlateMemberForcesPayload(BaseModel):
    N_kN: float = Field(0.0, description="Esfuerzo axial mayorado (+ tracción, - compresión)")
    V_kN: float = Field(..., description="Cortante mayorado en el extremo en kN")
    M_kNm: float = Field(..., description="Momento flector mayorado en el extremo en kNm")
    beam_depth_mm: float = Field(..., gt=0)
    beam_tf_mm: float = Field(..., gt=0)
    beam_bf_mm: float = Field(..., gt=0)
    bolt_grade: str = "A325"
    bolt_size: str | None = None
    plate_thickness_mm: float = 20.0
    plate_Fy_MPa: float = 345.0
    plate_Fu_MPa: float = 450.0
    n_bolt_rows: int = 2
    pfo_mm: float = 40.0
    pfi_mm: float = 40.0
    gage_g_mm: float = 140.0
    electrode: str = "E70XX"
    code: str = "AISC"


class BasePlatePayload(BaseModel):
    Bp_mm: float = Field(..., gt=0)
    Np_mm: float = Field(..., gt=0)
    tp_mm: float = Field(..., gt=0)
    d_col_mm: float = Field(..., gt=0)
    bf_col_mm: float = Field(..., gt=0)
    fc_MPa: float = 25.0
    fy_plate_MPa: float = 250.0
    Pu_kN: float = 500.0
    Mu_kNm: float = 0.0


class PanelZonePayload(BaseModel):
    d_c_mm: float = Field(..., gt=0)
    t_w_mm: float = Field(..., gt=0)
    d_b_mm: float = Field(..., gt=0)
    b_f_c_mm: float = Field(..., gt=0)
    t_f_c_mm: float = Field(..., gt=0)
    Fy_c_MPa: float = 345.0
    Pu_kN: float = 0.0
    Py_kN: float = 1000.0
    V_demand_kN: float = 0.0
    consider_plastification: bool = True


class SplicePayload(BaseModel):
    Mu_kNm: float = Field(..., ge=0)
    Vu_kN: float = Field(..., ge=0)
    flange_plate_t_mm: float = 10.0
    flange_plate_b_mm: float = 200.0


class ClipAnglePayload(BaseModel):
    leg_a_mm: float = Field(..., gt=0)
    leg_b_mm: float = Field(..., gt=0)
    thickness_mm: float = Field(..., gt=0)
    Vu_kN: float = Field(..., ge=0)
    angle_type: str = "double"


class RBSPayload(BaseModel):
    d_mm: float = Field(..., gt=0)
    bf_mm: float = Field(..., gt=0)
    tf_mm: float = Field(..., gt=0)
    tw_mm: float = Field(..., gt=0)
    Zx_mm3: float = Field(..., gt=0)
    Fy_MPa: float = Field(..., gt=0)
    Fu_MPa: float = Field(..., gt=0)
    a_mm: float = Field(..., gt=0)
    b_mm: float = Field(..., gt=0)
    c_mm: float = Field(..., gt=0)
    L_clear_m: float = 6.0
    wu_kN_per_m: float = 0.0
    Ry: float = 1.1
    # AC-03: antes `float = 0.0`, y el schema publicado hacia que un cliente
    # generado mandase 0.0 sin haber medido nada -> DCR 0.0 -> "OK". Ausente
    # (`null` u omitido) es NO_CALCULADO; se acepta con signo (|Mu|).
    Mu_demand_kNm: float | None = Field(
        None,
        description=("Momento mayorado de demanda en cara de columna, kN.m. Omitido o "
                     "null = no suministrado (NO_CALCULADO). El signo se descarta: la "
                     "RBS es simetrica. 0.0 no es verificable. NaN/inf = REQUIERE_REVISION."),
    )


class WUFPayload(BaseModel):
    beam_d_mm: float = Field(..., gt=0)
    beam_bf_mm: float = Field(..., gt=0)
    beam_tf_mm: float = Field(..., gt=0)
    beam_tw_mm: float = Field(..., gt=0)
    beam_Zx_mm3: float = Field(..., gt=0)
    beam_Fy_MPa: float = 345.0
    beam_Fu_MPa: float = 450.0
    # Columna SIN defaults: antes el schema prometia d=350, bf=350, tf=18, tw=11,
    # Zx=4e6, Fy=345, y un cliente que mandaba solo la viga recibia SCWB y zona
    # de panel de una columna que no existia. Sin columna -> NO_CALCULADO.
    col_d_mm: float | None = Field(None, gt=0, description="Peralte de columna, mm")
    col_bf_mm: float | None = Field(None, gt=0, description="Ancho de ala de columna, mm")
    col_tf_mm: float | None = Field(None, gt=0, description="Espesor de ala de columna, mm")
    col_tw_mm: float | None = Field(None, gt=0, description="Espesor de alma de columna, mm")
    col_Zx_mm3: float | None = Field(None, gt=0, description="Modulo plastico de columna, mm3")
    col_Fy_MPa: float | None = Field(None, gt=0, description="Limite elastico de columna, MPa")
    beam_length_m: float = 6.0
    Ry: float = 1.1
    Mu_demand_kNm: float | None = Field(
        None,
        description=("Momento mayorado de demanda, kN.m. Omitido o null = no suministrado "
                     "(NO_CALCULADO). El signo se descarta: la conexion es simetrica. 0.0 no "
                     "es verificable. NaN/inf = REQUIERE_REVISION."),
    )
    Vu_demand_kN: float | None = Field(
        None, description="Cortante de demanda, kN. Este servicio NO comprueba cortante: "
                          "se acepta por compatibilidad y no participa en el veredicto.")
    # Axil de columna para el SCWB (AISC 341 E3-1): M*pc = Zc Fyc (1 - Pu/Py). Sin
    # los dos, el SCWB publicado es la cota superior con Pu = 0 y no puede firmar.
    Pu_col_kN: float | None = Field(None, ge=0, description="Axil mayorado de columna, kN (compresion +)")
    Py_col_kN: float | None = Field(None, gt=0, description="Axil de plastificacion de columna Ag*Fy, kN")


router = APIRouter()


@router.get("/")
def root():
    return {"name": _BRAND_NAME, "endpoints": [
        "/api/connections/bolts/single",
        "/api/connections/bolts/group",
        "/api/connections/welds/fillet",
        "/api/connections/end_plate",
        "/api/connections/end_plate/from_member_forces",
        "/api/connections/base_plate",
        "/api/connections/panel_zone",
        "/api/connections/splice",
        "/api/connections/clip_angle",
        "/api/connections/rbs",
        "/api/connections/wuf",
    ]}


@router.post("/api/connections/bolts/single", summary="Resistencia de tornillo individual a cortante, tracción y aplastamiento (EN 1993-1-8 / AISC 360)")
def api_single_bolt(payload: SingleBoltPayload):
    try:
        res = bolts.design_single_bolt(bolts.SingleBoltInput(**payload.model_dump()))
        return {"Rn_shear_kN": res.Rn_shear_kN, "Rn_tension_kN": res.Rn_tension_kN,
                "Rn_bearing_kN": res.Rn_bearing_kN, "Rd_shear_kN": res.Rd_shear_kN,
                "governs": res.governs, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/bolts/group", summary="Grupo de tornillos en una línea vertical con cortante y momento (método elástico, AISC Manual Parte 7)")
def api_bolt_group(payload: BoltGroupPayload):
    try:
        res = bolts.design_bolt_group(bolts.BoltGroupInput(**payload.model_dump()))
        return {"Rn_group_kN": res.Rn_group_kN, "DCR_shear": res.DCR_shear,
                "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/welds/fillet", summary="Soldadura en ángulo: resistencia direccional AISC 360-22 §J2.4 (φ = 0,75)")
def api_fillet_weld(payload: FilletWeldPayload):
    try:
        res = welds.design_fillet_weld(welds.FilletWeldInput(**payload.model_dump()))
        return {"throat_mm": res.throat_mm, "Rn_kN": res.Rn_kN,
                "Rd_kN": res.Rd_kN,
                "directional_factor": res.directional_factor,
                "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/end_plate", summary="Chapa frontal extendida: flexión de la chapa por líneas de rotura (AISC 358 §6 / Design Guide 4), delega en EndPlate")
def api_end_plate(payload: EndPlatePayload):
    try:
        res = end_plate.design_end_plate(end_plate.EndPlateInput(**payload.model_dump()))
        return {"Mn_kNm": res.Mn_kNm, "DCR": res.DCR,
                "plate_thickness_required_mm": res.plate_thickness_required_mm,
                "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/end_plate/from_member_forces", summary="Diseño de chapa frontal atornillada a partir de esfuerzos seccionales (N, V, M) según AISC 360 / AISC 358")
def api_end_plate_from_member_forces(payload: EndPlateMemberForcesPayload):
    from ..end_plate import design_end_plate_from_member_forces
    try:
        return design_end_plate_from_member_forces(**payload.model_dump())
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/base_plate", summary="Placa base de columna: aplastamiento y espesor por los voladizos m, n y λn' (AISC Design Guide 1), delega en BasePlate")
def api_base_plate(payload: BasePlatePayload):
    try:
        res = base_plate.design_base_plate(base_plate.BasePlateInput(**payload.model_dump()))
        return {"fp_actual_MPa": res.fp_actual_MPa, "fp_allow_MPa": res.fp_allow_MPa,
                "tp_required_mm": res.tp_required_mm, "DCR": res.DCR,
                "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/panel_zone", summary="Resistencia a cortante de la zona de panel del alma del pilar según AISC 360 / AISC 341")
def api_panel_zone(payload: PanelZonePayload):
    try:
        res = panel_zone.design_panel_zone(
            panel_zone.PanelZoneServiceInput(**payload.model_dump()))
        return {"Vn_kN": res.Vn_kN, "DCR": res.DCR,
                "governs": res.governs, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/splice", summary="Empalme con cubrejuntas de ala: comprobación simplificada con brazo fijo de 0,5 m (servicio provisional)")
def api_splice(payload: SplicePayload):
    try:
        res = splice.design_splice(splice.SpliceInput(**payload.model_dump()))
        return {"Mn_kNm": res.Mn_kNm, "DCR": res.DCR, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/clip_angle", summary="Angulares a cortante: solo fluencia por cortante bruto con Fy = 345 MPa (servicio provisional; ClipAngle hace las ocho comprobaciones)")
def api_clip_angle(payload: ClipAnglePayload):
    try:
        res = clip_angle.design_clip_angle(clip_angle.ClipAngleInput(**payload.model_dump()))
        return {"Rn_kN": res.Rn_kN, "DCR": res.DCR, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/rbs", summary="Conexión precalificada con sección reducida de viga (RBS / Dogbone) según ANSI/AISC 358-16")
def api_rbs(payload: RBSPayload):
    try:
        res = rbs.design_rbs(rbs.RBSInput(**payload.model_dump()))
        return {"Z_RBS_mm3": res.Z_RBS_mm3, "M_pr_kNm": res.M_pr_kNm,
                "V_pr_kN": res.V_pr_kN, "M_f_kNm": res.M_f_kNm,
                "DCR": res.DCR, "status": res.status,
                "calculation_status": str(res.calculation_status),
                "missing_inputs": list(res.missing_inputs),
                "is_geometry_ok": res.is_geometry_ok, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/wuf", summary="Conexión precalificada de ala soldada sin refuerzo (WUF-W) según ANSI/AISC 358-16")
def api_wuf(payload: WUFPayload):
    try:
        res = wuf.design_wuf(wuf.WUFInput(**payload.model_dump()))
        return {"M_pr_kNm": res.M_pr_kNm, "V_pr_kN": res.V_pr_kN,
                "is_compact": res.is_compact, "scwb_ratio": res.scwb_ratio,
                "pz_Vn_kN": res.pz_Vn_kN, "pz_DCR": res.pz_DCR,
                "weld_capacity_kN": res.weld_capacity_kN,
                "DCR": res.DCR, "status": res.status,
                "calculation_status": str(res.calculation_status),
                "missing_inputs": list(res.missing_inputs),
                "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


def create_router() -> APIRouter:
    """Devuelve el APIRouter (factory para uniformidad con otros repos)."""
    return router


# ---------------------------------------------------------------------------
# App standalone
# ---------------------------------------------------------------------------
app = FastAPI(title=f"{_BRAND_NAME} API", version=_VERSION)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)
