"""Generador TEXTO de un deck CalculiX (.inp) - SteelNodeFEAJm (backlog #8).

Construye, como cadena de texto, un deck CalculiX (.inp) de una placa de conexion
rectangular discretizada en una malla estructurada de nx x ny celdas con elementos
shell S4. NO ejecuta CalculiX ni lo importa -> CI-safe.

Convencion de numeracion (1-based, requerido por CalculiX):
  - nodo (i,j) con i en [0,ny], j en [0,nx]:  n_id = i*(nx+1) + j + 1
    (j recorre X, i recorre Y; recorrido fila a fila)
  - elemento de la celda (i,j) con i en [0,ny), j en [0,nx):
    e_id = i*nx + j + 1, conectividad CCW = (n00, n01, n11, n10)
      n00 = nodo (i,   j  )  -> inferior-izquierda
      n01 = nodo (i,   j+1)  -> inferior-derecha
      n11 = nodo (i+1, j+1)  -> superior-derecha
      n10 = nodo (i+1, j  )  -> superior-izquierda

Borde empotrado: la fila y=0 (i=0)  -> *NSET FIXED, *BOUNDARY FIXED,1,6.
Carga: nodo medio del borde libre y=width (i=ny)  -> *CLOAD en gl. 2 (direccion Y).
"""
from __future__ import annotations

from .steelnode_schemas import PlateDeckIn, InpDeckOut

_ELSET = "EALL"
_NSET_FIXED = "FIXED"
_MAT = "STEEL"


def _node_id(i: int, j: int, nx: int) -> int:
    """Tag 1-based del nodo en fila i (Y), columna j (X)."""
    return i * (nx + 1) + j + 1


def generate_inp_deck(deck: PlateDeckIn) -> InpDeckOut:
    """Genera el deck CalculiX (.inp) de la placa como texto. No ejecuta nada."""
    if deck.nx < 1 or deck.ny < 1:
        raise ValueError("nx and ny must be >= 1")
    if deck.length <= 0 or deck.width <= 0 or deck.thickness <= 0:
        raise ValueError("length, width and thickness must be positive")
    if deck.E <= 0:
        raise ValueError("E must be positive")
    if not (0.0 < deck.nu < 0.5):
        raise ValueError("nu must be in (0, 0.5)")

    nx, ny = deck.nx, deck.ny
    L, W = deck.length, deck.width
    dx = L / nx
    dy = W / ny

    n_nodes = (nx + 1) * (ny + 1)
    n_elements = nx * ny

    lines: list[str] = [
        "** CalculiX input deck - steel connection plate (S4 shells)",
        "** Generado por SteelNodeFEAJm (texto, no ejecutado)",
        f"** Malla estructurada: nx={nx}, ny={ny} -> {n_nodes} nodos, {n_elements} elementos",
        "*HEADING",
        "Steel connection plate - linear static (S4)",
        "*NODE, NSET=NALL",
    ]

    # --- Nodos: fila a fila (i = Y), columna a columna (j = X) ---
    for i in range(ny + 1):
        y = i * dy
        for j in range(nx + 1):
            x = j * dx
            lines.append(f"{_node_id(i, j, nx)}, {x:.6f}, {y:.6f}, 0.000000")

    # --- Elementos shell S4 (conectividad CCW) ---
    lines.append(f"*ELEMENT, TYPE=S4, ELSET={_ELSET}")
    for i in range(ny):
        for j in range(nx):
            e_id = i * nx + j + 1
            n00 = _node_id(i, j, nx)
            n01 = _node_id(i, j + 1, nx)
            n11 = _node_id(i + 1, j + 1, nx)
            n10 = _node_id(i + 1, j, nx)
            lines.append(f"{e_id}, {n00}, {n01}, {n11}, {n10}")

    # --- Material elastico ---
    lines += [
        f"*MATERIAL, NAME={_MAT}",
        "*ELASTIC",
        f"{deck.E:g}, {deck.nu:g}",
    ]

    # --- Seccion shell (espesor) ---
    lines += [
        f"*SHELL SECTION, ELSET={_ELSET}, MATERIAL={_MAT}",
        f"{deck.thickness:g}",
    ]

    # --- Borde empotrado: fila y=0 (i=0) ---
    fixed_ids = [_node_id(0, j, nx) for j in range(nx + 1)]
    lines.append(f"*NSET, NSET={_NSET_FIXED}")
    lines.append(", ".join(str(nid) for nid in fixed_ids))
    lines += [
        "*BOUNDARY",
        f"{_NSET_FIXED}, 1, 6",
    ]

    # --- Step estatico lineal con carga puntual en el borde libre ---
    load_node = _node_id(ny, nx // 2, nx)  # nodo medio del borde y=W
    lines += [
        "*STEP",
        "*STATIC",
        "*CLOAD",
        f"{load_node}, 2, {-deck.load:g}",   # gl. 2 = direccion Y (hacia -Y)
        "*EL PRINT, ELSET=" + _ELSET,
        "S",                                  # tensiones (incl. Von Mises) en el .dat
        "*NODE PRINT, NSET=NALL",
        "U",
        "*END STEP",
        "",
    ]

    return InpDeckOut(
        inp="\n".join(lines),
        n_nodes=n_nodes,
        n_elements=n_elements,
    )


__all__ = ["generate_inp_deck"]
