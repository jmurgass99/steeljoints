"""API REST de steeljoints (FastAPI) llamada en proceso con TestClient: rutas disponibles, perno individual, grupo de pernos, cordón, placa base, RBS y WUF-W, y lo que devuelve con datos incompletos o inválidos.

`steeljoints.api.app.app` (extra `api`). En producción: `uvicorn steeljoints.api.app:app`. Las rutas delegan en
`steeljoints.services`; los veredictos ausentes salen como NO_CALCULADO, no como cero.

Ejecutar:  python examples/rest_api_fastapi_testclient_bolts_welds_base_plate_rbs_wuf_and_validation_errors.py
"""
import warnings


def main() -> None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")   # avisos de deprecación de starlette/httpx al importar el TestClient
            from fastapi.testclient import TestClient
            from steeljoints.api.app import app
    except ImportError as exc:
        print(f"Falta el extra api: pip install steeljoints[api] ({exc})")
        return
    c = TestClient(app)
    paths = sorted(p for p in app.openapi()["paths"] if p.startswith("/api"))
    print(f"{app.title} {app.version}: {len(paths)} rutas")
    for p in paths:
        print(f"  POST {p}")
    llamadas = (
        ("/api/connections/bolts/single", {"grade": "A325", "diameter_mm": 19.05, "edge_distance_mm": 30.0}),
        ("/api/connections/bolts/single", {"grade": "8.8", "diameter_mm": 20.0, "standard": "EC3", "edge_distance_mm": 40.0}),
        ("/api/connections/bolts/group", {"n_bolts": 4, "diameter_mm": 19.05, "Vu_kN": 150.0, "Mu_kNm": 10.0}),
        ("/api/connections/welds/fillet", {"leg_size_mm": 8.0, "length_mm": 150.0, "angle_load_deg": 90.0}),
        ("/api/connections/base_plate", {"Bp_mm": 450, "Np_mm": 450, "tp_mm": 32, "d_col_mm": 310, "bf_col_mm": 305, "fc_MPa": 28.0, "fy_plate_MPa": 250.0, "Pu_kN": 2000.0}),
        ("/api/connections/rbs", {"d_mm": 612, "bf_mm": 229, "tf_mm": 19.6, "tw_mm": 11.9, "Zx_mm3": 3.67e6, "Fy_MPa": 345, "Fu_MPa": 450, "a_mm": 143, "b_mm": 459, "c_mm": 45, "L_clear_m": 7.0, "wu_kN_per_m": 30.0, "Mu_demand_kNm": 900.0}),
        ("/api/connections/wuf", {"beam_d_mm": 612, "beam_bf_mm": 229, "beam_tf_mm": 19.6, "beam_tw_mm": 11.9, "beam_Zx_mm3": 3.67e6, "beam_length_m": 7.0, "Mu_demand_kNm": 1000.0}),
    )
    print()
    for path, body in llamadas:
        r = c.post(path, json=body)
        data = r.json()
        resumen = {k: (round(v, 2) if isinstance(v, float) else v) for k, v in data.items() if k not in ("notes", "missing_inputs")}
        print(f"POST {path.replace('/api/connections', '')} → {r.status_code}: {str(resumen)[:180]}")
    print("\nDatos inválidos:")
    r = c.post("/api/connections/bolts/single", json={"grade": "A325", "diameter_mm": -5})
    print(f"  diámetro negativo → {r.status_code}: {r.json()['detail'][0]['msg']}")
    r = c.post("/api/connections/welds/fillet", json={"length_mm": 100})
    print(f"  falta leg_size_mm → {r.status_code}: {r.json()['detail'][0]['loc']} {r.json()['detail'][0]['msg']}")
    r = c.post("/api/connections/wuf", json={"beam_d_mm": 612, "beam_bf_mm": 229, "beam_tf_mm": 19.6, "beam_tw_mm": 11.9, "beam_Zx_mm3": 3.67e6})
    d = r.json()
    print(f"  WUF-W sin pilar ni demanda → {r.status_code}, estado {d.get('calculation_status', d.get('status'))}, faltan {len(d.get('missing_inputs', []))} datos")
    print("\nLos errores de tipo y rango los rechaza pydantic con 422; la falta de datos de ingeniería sale con 200 y un veredicto NO_CALCULADO que nombra lo que falta.")


if __name__ == "__main__":
    main()
