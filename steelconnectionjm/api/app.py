"""FastAPI app para diseno de conexiones de acero."""
from __future__ import annotations

try:
    from fastapi import APIRouter, FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
except ImportError as exc:
    raise ImportError(
        "fastapi requerido: pip install steelconnectionjm[api]"
    ) from exc

from .._brand import NAME as _BRAND_NAME
from ..services import (
    bolts, welds, end_plate, base_plate,
    panel_zone, splice, clip_angle, rbs, wuf,
)


router = APIRouter()


@router.get("/")
def root():
    return {"name": _BRAND_NAME, "endpoints": [
        "/api/connections/bolts/single",
        "/api/connections/bolts/group",
        "/api/connections/welds/fillet",
        "/api/connections/end_plate",
        "/api/connections/base_plate",
        "/api/connections/panel_zone",
        "/api/connections/splice",
        "/api/connections/clip_angle",
        "/api/connections/rbs",
        "/api/connections/wuf",
    ]}


@router.post("/api/connections/bolts/single")
def api_single_bolt(inp: dict):
    try:
        res = bolts.design_single_bolt(bolts.SingleBoltInput(**inp))
        return {"Rn_shear_kN": res.Rn_shear_kN, "Rn_tension_kN": res.Rn_tension_kN,
                "Rn_bearing_kN": res.Rn_bearing_kN, "Rd_shear_kN": res.Rd_shear_kN,
                "governs": res.governs, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/bolts/group")
def api_bolt_group(inp: dict):
    try:
        res = bolts.design_bolt_group(bolts.BoltGroupInput(**inp))
        return {"Rn_group_kN": res.Rn_group_kN, "DCR_shear": res.DCR_shear,
                "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/welds/fillet")
def api_fillet_weld(inp: dict):
    try:
        res = welds.design_fillet_weld(welds.FilletWeldInput(**inp))
        return {"throat_mm": res.throat_mm, "Rn_kN": res.Rn_kN,
                "Rd_kN": res.Rd_kN,
                "directional_factor": res.directional_factor,
                "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/end_plate")
def api_end_plate(inp: dict):
    try:
        res = end_plate.design_end_plate(end_plate.EndPlateInput(**inp))
        return {"Mn_kNm": res.Mn_kNm, "DCR": res.DCR,
                "plate_thickness_required_mm": res.plate_thickness_required_mm,
                "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/base_plate")
def api_base_plate(inp: dict):
    try:
        res = base_plate.design_base_plate(base_plate.BasePlateInput(**inp))
        return {"fp_actual_MPa": res.fp_actual_MPa, "fp_allow_MPa": res.fp_allow_MPa,
                "tp_required_mm": res.tp_required_mm, "DCR": res.DCR,
                "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/panel_zone")
def api_panel_zone(inp: dict):
    try:
        res = panel_zone.design_panel_zone(
            panel_zone.PanelZoneServiceInput(**inp))
        return {"Vn_kN": res.Vn_kN, "DCR": res.DCR,
                "governs": res.governs, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/splice")
def api_splice(inp: dict):
    try:
        res = splice.design_splice(splice.SpliceInput(**inp))
        return {"Mn_kNm": res.Mn_kNm, "DCR": res.DCR, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/clip_angle")
def api_clip_angle(inp: dict):
    try:
        res = clip_angle.design_clip_angle(clip_angle.ClipAngleInput(**inp))
        return {"Rn_kN": res.Rn_kN, "DCR": res.DCR, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/rbs")
def api_rbs(inp: dict):
    try:
        res = rbs.design_rbs(rbs.RBSInput(**inp))
        return {"Z_RBS_mm3": res.Z_RBS_mm3, "M_pr_kNm": res.M_pr_kNm,
                "V_pr_kN": res.V_pr_kN, "M_f_kNm": res.M_f_kNm,
                "DCR": res.DCR, "status": res.status,
                "is_geometry_ok": res.is_geometry_ok, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@router.post("/api/connections/wuf")
def api_wuf(inp: dict):
    try:
        res = wuf.design_wuf(wuf.WUFInput(**inp))
        return {"M_pr_kNm": res.M_pr_kNm, "V_pr_kN": res.V_pr_kN,
                "is_compact": res.is_compact, "scwb_ratio": res.scwb_ratio,
                "pz_Vn_kN": res.pz_Vn_kN, "pz_DCR": res.pz_DCR,
                "weld_capacity_kN": res.weld_capacity_kN,
                "DCR": res.DCR, "status": res.status, "notes": res.notes}
    except Exception as exc:
        raise HTTPException(400, str(exc))


def create_router() -> APIRouter:
    """Devuelve el APIRouter (factory para uniformidad con otros repos)."""
    return router


# ---------------------------------------------------------------------------
# App standalone
# ---------------------------------------------------------------------------
app = FastAPI(title=f"{_BRAND_NAME} API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)
app.include_router(router)
