#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for CellLineage and CycleLineage classes from lineage.py module."""

import pytest

from pycellin.classes import CellLineage, CycleLineage


# CellLineage fixtures ########################################################


@pytest.fixture(scope="module")
def empty_cell_lin():
    return CellLineage()


@pytest.fixture(scope="module")
def one_node_cell_lin():
    lineage = CellLineage()
    lineage.add_node(1)
    return lineage


@pytest.fixture(scope="module")
def cell_lin1():
    lineage = CellLineage()
    lineage.add_nodes_from(range(1, 13))
    lineage.add_edges_from(
        [
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (4, 7),
            (7, 8),
            (8, 9),
            (8, 10),
            (2, 11),
            (11, 12),
        ]
    )
    return lineage


@pytest.fixture(scope="module")
def cell_lin2():
    # The root is a division.
    lineage = CellLineage()
    lineage.add_nodes_from(range(1, 12))
    lineage.add_edges_from(
        [
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (3, 6),
            (6, 7),
            (7, 8),
            (7, 9),
            (1, 10),
            (10, 11),
        ]
    )
    return lineage


@pytest.fixture(scope="module")
def cell_lin3():
    # Successive divisions and root division.
    lineage = CellLineage()
    lineage.add_nodes_from(range(2, 12))
    lineage.add_edges_from(
        [
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (5, 7),
            (3, 8),
            (8, 9),
            (8, 10),
            (2, 11),
        ]
    )
    return lineage


# get_root() ##################################################################


def test_get_root_empty_lin():
    lineage = CellLineage()
    assert lineage.get_root() == []
    assert lineage.get_root(ignore_lone_nodes=True) == []


def test_get_root_single_node():
    lineage = CellLineage()
    lineage.add_node(1)
    assert lineage.get_root() == 1
    assert lineage.get_root(ignore_lone_nodes=True) == []


def test_get_root_unconnected_node(cell_lin1):
    cell_lin1.add_node(13)
    assert cell_lin1.get_root() == [1, 13]
    assert cell_lin1.get_root(ignore_lone_nodes=True) == 1


def test_get_root_unconnected_component(cell_lin1):
    cell_lin1.add_nodes_from([13, 14])
    cell_lin1.add_edges_from([(13, 14)])
    assert cell_lin1.get_root() == [1, 13]
    assert cell_lin1.get_root(ignore_lone_nodes=True) == [1, 13]
    
