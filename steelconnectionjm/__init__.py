"""
SteelConnectionJm — Steel Connection Design Library
=====================================================
Multi-code design: AISC 360-22, EN 1993-1-8, NSR-10 F.2

Usage
-----
>>> from steelconnectionjm import BoltGroup, FilletWeld, ShearTab, BasePlate
>>> tab = ShearTab(Vu=120.0, bolt_diameter=19.05, n_bolts=3,
...                plate_thickness=9.5, plate_width=75.0)
>>> result = tab.design()
"""
from ._brand import NAME, SLUG, EXE, APPDATA_DIR, ORG, REPO, URL, TAGLINE
from .bolts import Bolt, BoltGroup
from .welds import FilletWeld, WeldGroup
from .shear_tab import ShearTab
from .end_plate import EndPlate
from .base_plate import BasePlate
from .block_shear import block_shear_strength

# Nuevos módulos
from .bolt_group import BoltGroupICR, rectangular_pattern
from .weld_group import WeldSegment, WeldGroupElastic, WeldGroupICR
from .clip_angle import ClipAngle
from .panel_zone import PanelZone, PanelZoneInput, PanelZoneResult, shear_capacity
from . import catalog
from . import codes

# DXF (opcional — sólo si ezdxf disponible)
try:
    from . import dxf_detail
except ImportError:  # pragma: no cover
    dxf_detail = None  # type: ignore

__all__ = [
    "Bolt", "BoltGroup",
    "FilletWeld", "WeldGroup",
    "ShearTab",
    "EndPlate",
    "BasePlate",
    "block_shear_strength",
    # New
    "BoltGroupICR", "rectangular_pattern",
    "WeldSegment", "WeldGroupElastic", "WeldGroupICR",
    "ClipAngle",
    "PanelZone", "PanelZoneInput", "PanelZoneResult", "shear_capacity",
    "catalog", "codes", "dxf_detail",
    # Brand
    "NAME", "SLUG", "EXE", "APPDATA_DIR", "ORG", "REPO", "URL", "TAGLINE",
]
__version__ = "1.1.0"

# Exception hierarchy (Mejora B)
from .exceptions import (
    ConnectionError as SteelConnectionError,
    GeometryError, CodeError, DesignError,
    ConvergenceError, DependencyError, ConfigurationError,
)
# Note: re-exportado como SteelConnectionError para evitar colisión con
# el builtin ConnectionError.
__all__ += [
    "SteelConnectionError",
    "GeometryError", "CodeError", "DesignError",
    "ConvergenceError", "DependencyError", "ConfigurationError",
]

from .steelnode import generate_inp_deck
from .steelnode_schemas import PlateDeckIn, InpDeckOut
