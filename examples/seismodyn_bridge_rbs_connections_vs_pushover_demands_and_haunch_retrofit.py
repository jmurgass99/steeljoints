"""Comprobación de un pórtico entero: las uniones RBS de tres vigas contra los momentos de un análisis pushover (puente con seismodyn), con una viga sin demanda, y una cartela (haunch) como refuerzo de la viga que no cumple.

`integration.seismodyn_bridge.verify_connections_vs_demand(conexiones, demandas)` devuelve un informe con una fila
por viga, veredicto canónico y viga crítica; una viga sin demanda queda «sin veredicto», nunca segura.
`haunch_connection.design_haunch(HaunchInput(...))` es un modelo simplificado: ΔZ = bf·tf·(d + h/2) de la cartela.

Ejecutar:  python examples/seismodyn_bridge_rbs_connections_vs_pushover_demands_and_haunch_retrofit.py
"""
from steeljoints.haunch_connection import HaunchInput, design_haunch
from steeljoints.integration.seismodyn_bridge import BeamDynamicDemand, RBSConnectionDefinition, verify_connections_vs_demand


def main() -> None:
    conns = [
        RBSConnectionDefinition("V-101", beam_d=612, beam_bf=229, beam_tf=19.6, beam_Z_x=3.67e6, a=143, b=459, c=45, L_clear=7.0, wu=30.0),
        RBSConnectionDefinition("V-102", beam_d=530, beam_bf=209, beam_tf=15.6, beam_Z_x=2.39e6, a=130, b=400, c=40, L_clear=7.0, wu=30.0),
        RBSConnectionDefinition("V-103", beam_d=460, beam_bf=191, beam_tf=14.5, beam_Z_x=1.62e6, a=120, b=345, c=60, L_clear=6.0, wu=25.0),
        RBSConnectionDefinition("V-104", beam_d=460, beam_bf=191, beam_tf=14.5, beam_Z_x=1.62e6, a=120, b=345, c=38, L_clear=6.0, wu=25.0),
    ]
    dem = [
        BeamDynamicDemand("V-101", M_Ed_kNm=980.0, V_Ed_kN=420.0, analysis_label="pushover"),
        BeamDynamicDemand("V-102", M_Ed_kNm=-640.0, V_Ed_kN=300.0, analysis_label="pushover"),
        BeamDynamicDemand("V-103", M_Ed_kNm=520.0, V_Ed_kN=260.0, analysis_label="pushover"),
    ]
    rep = verify_connections_vs_demand(conns, dem)
    print(f"{rep.n_total} uniones: {rep.n_safe} seguras, {rep.n_unsafe} que no cumplen, {rep.n_sin_veredicto} sin veredicto, {rep.n_geometry_violations} con geometría fuera de §5.8")
    print(f"  {'viga':6} {'M demanda':>9} {'Mpr':>7} {'util.':>6} {'geometría':>9} {'estado':>18}")
    for r in rep.rows:
        u = "—" if r.utilization_ratio is None else f"{r.utilization_ratio:.3f}"
        m = "—" if r.M_demand_kNm is None else f"{r.M_demand_kNm:.0f}"
        cap = "—" if r.M_pr_capacity_kNm is None else f"{r.M_pr_capacity_kNm:.0f}"
        print(f"  {r.beam_id:6} {m:>9} {cap:>7} {u:>6} {'OK' if r.geometry_ok else 'fuera':>9} {r.calculation_status.value:>18}")
    print(f"  Viga crítica: {rep.critical_beam} (utilización {rep.max_utilization:.3f})")
    for r in rep.rows:
        if r.missing_inputs:
            print(f"  {r.beam_id}: falta {r.missing_inputs}")
    print("\nCartela de refuerzo bajo la viga de 460 mm (ala 191 × 14,5, Zx 1,62e6 mm³), cartela de 250 × 600 mm con ala 180 × 15 mm:")
    for code in ("USA", "EU"):
        h = design_haunch(HaunchInput(beam_depth_mm=460, beam_flange_b_mm=191, beam_flange_tf_mm=14.5, beam_Zx_mm3=1.62e6,
                                      haunch_depth_mm=250, haunch_length_mm=600, haunch_tf_mm=15, haunch_bf_mm=180, Fy_MPa=345.0, code=code))
        print(f"  {code:3}: resistencia {h.Mn_kNm:.0f} kN·m (factor {h.phi:.2f}), ángulo {h.angle_deg:.1f}°, fuerza vertical {h.vertical_force_kN_per_kNm:.3f} kN por kN·m, "
              f"ala b/2t = {h.flange_slenderness_ratio:.1f} {'compacta' if h.flange_compact else 'NO compacta'}")
    base = 345.0 * 1.62e6 / 1e6 * 0.9
    print(f"  Viga sola: φ·Fy·Zx = {base:.0f} kN·m.")
    print("\nEl signo del momento se descarta (|M|). V-103 tiene un corte de 60 mm, más de 0,25·bf: queda fuera de la precalificación y pide revisión aunque su utilización sea conocida. "
          "V-104 no tiene demanda en el análisis y sale sin veredicto (hasta la versión 1.1 desaparecía del informe). La resistencia de la cartela es un modelo simplificado sin contrastar con AISC Design Guide 21 ni con la FEMA 355D: "
          "úsala para predimensionar, no para verificar. El valor devuelto ya incluye φ, aunque el campo se llame Mn_kNm.")


if __name__ == "__main__":
    main()
