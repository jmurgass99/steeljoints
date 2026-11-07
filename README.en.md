# steeljoints

[Español](README.md) · **English**

Steel connections in Python: bolts, welds, plates, base plates and seismic connections.

[![CI](https://github.com/jmurgass99/steeljoints/actions/workflows/ci.yml/badge.svg)](https://github.com/jmurgass99/steeljoints/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## What it does

- Bolts and bolt groups (elastic and instantaneous center methods), prying action and block shear in four codes.
- Fillet and butt welds, and weld groups.
- Shear tabs, double angles, end plates (yield lines and EN 1993-1-8 T-stub), base plates and panel zone.
- RBS and WUF-W seismic connections (AISC 358), anchors, cables (EN 1993-1-11) and flexural-torsional buckling.
- Export to IDEA StatiCa, CalculiX and DXF, and an optional REST API.

## Install

```bash
pip install git+https://github.com/jmurgass99/steeljoints.git
```

Optional extras: `api`, `dxf`, `numeric`. Base dependencies: `numpy` and `pydantic`.

## Example

Design strength of a 3/4" (19.05 mm) A325 bolt with the threads in the shear plane, per NSR-10 F.2:

```python
from steeljoints.codes.nsr10_f2 import NSR10BoltInput, design_bolt_nsr10

r = design_bolt_nsr10(NSR10BoltInput("A325", 19.05, "N"))
print(round(r.Rd_shear_kN, 1), round(r.Rd_tension_kN, 1))   # 79.5 132.5
```

More cases in [`examples/`](examples).

## What it does not do

- Verify a whole connection without review: for example, the shear tab does not check plate bending or bolt eccentricity.
- Component-based finite element models (IDEA StatiCa, CBFEM): everything here is code-based hand calculation.
- Import into IDEA StatiCa: the IOM XML it writes is not the format IDEA StatiCa 21.1 accepts.
- Codes marked as not cross-checked (ACI 318-25 arching effect, EN 1993-1-11 cable coefficients).

Details are in [docs/LIMITACIONES.md](docs/LIMITACIONES.md) (in Spanish).

## Tests

```bash
pip install -e ".[test]"
pytest -q
```

## License

MIT. See [LICENSE](LICENSE). Author: [Jesús Murgas](https://github.com/jmurgass99).
