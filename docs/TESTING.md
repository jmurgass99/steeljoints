# SteelConnectionJm - Testing Guide

## Filosofia

Diseno de conexiones de acero implica seguridad estructural directa.
Gate inicial **80%** (mas alto que otros satelites). Property tests
con hypothesis para invariantes (capacidad > 0, escala con n_bolts, etc.).

## Markers

| Marker | Aplicar cuando |
|---|---|
| `unit` | Test rapido sin deps externas |
| `integration` | Requiere stack completo |
| `slow` | Duracion > 5s |
| `property` | Property-based con hypothesis |
| `fastsap` | Requiere puente FastSAP |
| `dxf` | Requiere DXFStructuralJm o ezdxf |

## Comandos

```bash
# Suite rapida diaria
pytest -m "not slow and not fastsap and not dxf"

# Solo property tests
pytest -m property

# Coverage con HTML
.\scripts\run_coverage.ps1 -Open
```

## Invariantes hypothesis verificadas

- `Rn_single_bolt > 0` siempre
- `Rn(d2) > Rn(d1)` si d2 > d1 (mismo grade)
- `Rn_bolt_group = n . Rn_single` (concentrico)
- `Rn_bolt_group_eccentric <= Rn_concentric`
- `Rn_weld_transverse >= Rn_weld_longitudinal`
- `Rn_weld(leg2) > Rn_weld(leg1)` si leg2 > leg1
- `Mn_end_plate(tp+50%) > Mn_end_plate(tp)`
- `fp_allow_base_plate ^ con f'c`

## DXF integration

`dxf_detail.py` detecta automaticamente si DXFStructuralJm esta
disponible y prefiere sus primitivas (cuadros de armado, hatches
estandarizados). Si no, fallback al impl local.

Para habilitar:

```bash
pip install -e "C:/Users/jesus/OneDrive/Escritorio/NEW CODES/STRUCTURAL/APIS/EN PROYECTO/DXFStructuralJm"
```
