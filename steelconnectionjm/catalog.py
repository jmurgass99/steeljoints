"""
catalog.py — Catálogo de pernos y electrodos.

Pernos de alta resistencia AISC (A325, A490, F1852, F2280) y EC3 (8.8, 10.9, 4.6, 5.6).
Tamaños comunes Ø1/2" a Ø1-1/2" (imperial) y M12 a M30 (métrico).
Electrodos AWS E60XX a E110XX, FEXX en MPa.

Areas:
  Ab = pi*d²/4  (gross/nominal)
  At = area de esfuerzo a tensión (thread stress area) — para chequeo a tensión

Cita: AISC Manual Tables 7-1, 7-2; AISC 360-22 Table J3.2; EC3-1-8 Table 3.4.
"""
from __future__ import annotations
from math import pi
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Bolt grades — AISC Table J3.2 (Fnt, Fnv en MPa, threads NOT excluded "-N")
# ---------------------------------------------------------------------------
AISC_BOLT_GRADES: dict[str, dict] = {
    "A307":  {"Fnt": 310.0, "Fnv_N": 188.0, "Fnv_X": 188.0, "Fub": 414.0},
    "A325":  {"Fnt": 620.0, "Fnv_N": 372.0, "Fnv_X": 469.0, "Fub": 827.0},
    "A490":  {"Fnt": 779.0, "Fnv_N": 457.0, "Fnv_X": 579.0, "Fub": 1034.0},
    "F1852": {"Fnt": 620.0, "Fnv_N": 372.0, "Fnv_X": 469.0, "Fub": 827.0},
    "F2280": {"Fnt": 779.0, "Fnv_N": 457.0, "Fnv_X": 579.0, "Fub": 1034.0},
}

# ---------------------------------------------------------------------------
# Bolt grades — EC3-1-8 Table 3.1 (fyb, fub en MPa)
# ---------------------------------------------------------------------------
EC3_BOLT_GRADES: dict[str, dict] = {
    "4.6":  {"fyb": 240.0, "fub": 400.0,  "alpha_v": 0.6},
    "4.8":  {"fyb": 320.0, "fub": 400.0,  "alpha_v": 0.5},
    "5.6":  {"fyb": 300.0, "fub": 500.0,  "alpha_v": 0.6},
    "5.8":  {"fyb": 400.0, "fub": 500.0,  "alpha_v": 0.5},
    "6.8":  {"fyb": 480.0, "fub": 600.0,  "alpha_v": 0.5},
    "8.8":  {"fyb": 640.0, "fub": 800.0,  "alpha_v": 0.6},
    "10.9": {"fyb": 900.0, "fub": 1000.0, "alpha_v": 0.5},
}

# ---------------------------------------------------------------------------
# Bolt sizes — imperial (inches → mm) y métrico
# As (tensile stress area) per ISO 898-1 / ASME B1.1
# d_nominal [mm], As [mm²]
# ---------------------------------------------------------------------------
BOLT_SIZES_IMPERIAL: dict[str, dict] = {
    "1/2":   {"d_mm": 12.700, "As_mm2": 91.5},
    "5/8":   {"d_mm": 15.875, "As_mm2": 145.8},
    "3/4":   {"d_mm": 19.050, "As_mm2": 215.5},
    "7/8":   {"d_mm": 22.225, "As_mm2": 298.7},
    "1":     {"d_mm": 25.400, "As_mm2": 391.0},
    "1-1/8": {"d_mm": 28.575, "As_mm2": 491.6},
    "1-1/4": {"d_mm": 31.750, "As_mm2": 624.5},
    "1-3/8": {"d_mm": 34.925, "As_mm2": 749.7},
    "1-1/2": {"d_mm": 38.100, "As_mm2": 912.3},
}

BOLT_SIZES_METRIC: dict[str, dict] = {
    "M12": {"d_mm": 12.0, "As_mm2": 84.3},
    "M14": {"d_mm": 14.0, "As_mm2": 115.0},
    "M16": {"d_mm": 16.0, "As_mm2": 157.0},
    "M18": {"d_mm": 18.0, "As_mm2": 192.0},
    "M20": {"d_mm": 20.0, "As_mm2": 245.0},
    "M22": {"d_mm": 22.0, "As_mm2": 303.0},
    "M24": {"d_mm": 24.0, "As_mm2": 353.0},
    "M27": {"d_mm": 27.0, "As_mm2": 459.0},
    "M30": {"d_mm": 30.0, "As_mm2": 561.0},
}

# ---------------------------------------------------------------------------
# Standard hole sizes (AISC Table J3.3) [mm]
# d_h = d + clearance
# ---------------------------------------------------------------------------
def standard_hole(d_mm: float) -> float:
    """Diámetro estándar del agujero per AISC Table J3.3 [mm]."""
    if d_mm <= 22.0:
        return d_mm + 1.6   # +1/16"
    elif d_mm <= 25.4:
        return d_mm + 1.6
    else:
        return d_mm + 3.2   # +1/8" para Ø ≥ 1-1/8"

def oversized_hole(d_mm: float) -> float:
    """Agujero sobredimensionado per AISC Table J3.3 [mm]."""
    return d_mm + 4.8 if d_mm <= 22.0 else d_mm + 6.4


# ---------------------------------------------------------------------------
# Electrodos AWS — FEXX en MPa
# ---------------------------------------------------------------------------
ELECTRODES: dict[str, float] = {
    "E60XX":  413.7,   # 60 ksi
    "E70XX":  482.6,   # 70 ksi (más común)
    "E80XX":  551.6,
    "E90XX":  620.5,
    "E100XX": 689.5,
    "E110XX": 758.4,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_bolt_size(name: str) -> dict:
    """
    Obtiene datos de tamaño de perno por nombre ('3/4', 'M20', etc.)
    Devuelve dict con d_mm, As_mm2, Ab_mm2.
    """
    if name in BOLT_SIZES_IMPERIAL:
        data = dict(BOLT_SIZES_IMPERIAL[name])
    elif name.upper() in BOLT_SIZES_METRIC:
        data = dict(BOLT_SIZES_METRIC[name.upper()])
    else:
        raise KeyError(f"Tamaño desconocido '{name}'. "
                       f"Imperial: {list(BOLT_SIZES_IMPERIAL)}; "
                       f"Métrico: {list(BOLT_SIZES_METRIC)}")
    data["Ab_mm2"] = pi * data["d_mm"]**2 / 4.0
    return data


def get_bolt_grade(grade: str, code: str = "AISC") -> dict:
    """Datos de grado de perno por código."""
    code = code.upper()
    if code == "AISC":
        if grade not in AISC_BOLT_GRADES:
            raise KeyError(f"Grado AISC desconocido '{grade}'. "
                           f"Disponibles: {list(AISC_BOLT_GRADES)}")
        return dict(AISC_BOLT_GRADES[grade])
    elif code in ("EC3", "EN", "EN1993"):
        if grade not in EC3_BOLT_GRADES:
            raise KeyError(f"Grado EC3 desconocido '{grade}'. "
                           f"Disponibles: {list(EC3_BOLT_GRADES)}")
        return dict(EC3_BOLT_GRADES[grade])
    else:
        raise ValueError(f"Código no soportado: {code}")


def get_electrode_FEXX(name: str) -> float:
    """Resistencia FEXX [MPa] del electrodo.

    Parser laxo — acepta:
      * Claves canónicas:  ``"E70XX"``, ``"E80XX"`` ...
      * Sin sufijo XX:     ``"E70"``, ``"E80"`` ...
      * Con sufijo proceso:``"E70T-1"``, ``"E80T-X"`` ...
      * AWS A5.1 SMAW:     ``"E7018"``, ``"E7024"`` (2 dígitos iniciales = FEXX ksi)
      * Texto libre:       ``"70 ksi"``, ``"FEXX=70"`` (extrae el número)
      * Numérico:          ``70`` o ``"70"`` (asumido ksi si ≤120, si no MPa)

    Estrategia: normaliza con regex, busca clave canónica primero;
    si no, extrae dígitos y mapea a la grada más cercana (60/70/80/90/100/110).
    """
    import re

    # 1. Numérico directo -------------------------------------------------
    if isinstance(name, (int, float)):
        n = float(name)
        # > 200 → asumimos MPa directamente; si no, ksi
        return n if n > 200 else n * 6.895

    s = str(name).strip().upper()
    if not s:
        raise KeyError("Electrodo vacío")

    # 2. Match canónico exacto -------------------------------------------
    if s in ELECTRODES:
        return ELECTRODES[s]

    # 3. Match "EnnXX" con sufijo arbitrario (E70XX, E70T-1, E70-X, E7018, ...)
    m = re.match(r"^E\s*(\d{2,4})", s)
    if m:
        ksi = int(m.group(1))
        # Caso AWS A5.1: E7018, E7024 → 70 ksi (descartar últimos 2 dígitos
        # cuando son 3-4 dígitos y los últimos 2 son ≥10 y ≤99 código de
        # posición/revestimiento).
        if ksi >= 1000:                                # E7018 → 7018
            ksi = ksi // 100                           # → 70
        elif ksi >= 200:                               # raro (e.g. E308 inox)
            # No es electrodo de acero al carbono estándar: deja crudo
            pass
        canon = f"E{ksi}XX"
        if canon in ELECTRODES:
            return ELECTRODES[canon]
        # Caer a más cercano
        grades = [60, 70, 80, 90, 100, 110]
        nearest = min(grades, key=lambda g: abs(g - ksi))
        if abs(nearest - ksi) <= 5:
            return ELECTRODES[f"E{nearest}XX"]

    # 4. Texto libre con número (e.g. "70 ksi", "FEXX=70", "70") ----------
    # Buscar primer entero 2-3 dígitos
    m2 = re.search(r"(\d{2,3})", s)
    if m2:
        val = int(m2.group(1))
        # Heurística de unidades: si la cadena menciona MPa → MPa directo
        if "MPA" in s:
            return float(val)
        # Si menciona ksi o el valor está en rango típico de ksi (40-120) → ksi
        if "KSI" in s or 40 <= val <= 120:
            canon = f"E{val}XX"
            if canon in ELECTRODES:
                return ELECTRODES[canon]
            # Convertir ksi → MPa
            return val * 6.895
        # Valores grandes: asumir MPa
        return float(val)

    raise KeyError(f"Electrodo desconocido '{name}'. Disponibles: {list(ELECTRODES)}")
