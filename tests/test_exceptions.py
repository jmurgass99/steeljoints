"""Tests de la jerarquía de excepciones."""
from __future__ import annotations
import pytest

from steelconnectionjm.exceptions import (
    ConnectionError, GeometryError, CodeError, DesignError,
    ConvergenceError, DependencyError, ConfigurationError,
)


def test_hierarchy():
    for cls in (GeometryError, CodeError, DesignError,
                DependencyError, ConfigurationError):
        assert issubclass(cls, ConnectionError)


def test_convergence_metadata():
    exc = ConvergenceError("ICR no convergió", iteration=42, residual=0.01)
    assert exc.iteration == 42
    assert exc.residual == 0.01


def test_backward_compat_value_error():
    """GeometryError/CodeError/etc. heredan de ValueError → backward compat."""
    with pytest.raises(ValueError):
        raise GeometryError("invalid geom")
    with pytest.raises(ValueError):
        raise CodeError("out of range")


def test_can_catch_via_specific():
    with pytest.raises(GeometryError):
        raise GeometryError("x")
    with pytest.raises(CodeError):
        raise CodeError("x")


def test_can_catch_via_base():
    with pytest.raises(ConnectionError):
        raise GeometryError("x")


def test_dependency_error_also_import_error():
    """DependencyError multi-hereda de ImportError."""
    with pytest.raises(ImportError):
        raise DependencyError("ezdxf no instalado")


def test_reexport_from_package():
    import steelconnectionjm as scj
    assert scj.GeometryError is GeometryError
    assert scj.ConvergenceError is ConvergenceError
