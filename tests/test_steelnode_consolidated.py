# -*- coding: utf-8 -*-
"""Tests para la generacion de decks FEA de nudos de acero en SteelConnectionJm."""
from steelconnectionjm.steelnode import generate_inp_deck
from steelconnectionjm.steelnode_schemas import PlateDeckIn


def test_steelnode_deck_in_steelconnection():
    inp = PlateDeckIn(
        length=2.0,
        width=1.0,
        thickness=0.01,
        nx=4,
        ny=3,
        E=200e9,
        nu=0.3,
        load=1000.0,
    )
    res = generate_inp_deck(inp)
    assert res.inp != ""
    assert "*NODE" in res.inp
    assert "*ELEMENT" in res.inp
    assert res.n_nodes == 20
    assert res.n_elements == 12
