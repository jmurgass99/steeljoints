// C++ / WebAssembly kernel para componente de corte excéntrico y momento flector en chapa de unión
extern "C" {
  double boltShearComponent(double v_dir, double n_bolts, double mz, double coord_over_j) {
    return (v_dir / n_bolts) + (mz * coord_over_j);
  }

  double plateBendingMoment(double ft, double m_arm) {
    return ft * m_arm * 0.5;
  }
}
