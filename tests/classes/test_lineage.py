#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for CellLineage and CycleLineage classes from lineage.py module."""

import pytest

from pycellin.classes import CellLineage, CycleLineage


# CellLineage fixtures ########################################################


@pytest.fixture
def empty_cell_lin():
    return CellLineage()


@pytest.fixture
def one_node_cell_lin():
    lineage = CellLineage()
    lineage.add_node(1)
    return lineage


@pytest.fixture
def cell_lin():
    # Nothing special, just a lineage.
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


@pytest.fixture
def cell_lin_div_root(cell_lin):
    # The root is a division.
    cell_lin.add_node(13)
    cell_lin.add_edge(1, 13)
    return cell_lin


@pytest.fixture
def cell_lin_successive_divs_and_root():
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


@pytest.fixture
def cell_lin_triple_div(cell_lin):
    # Triple division.
    cell_lin.add_nodes_from([13, 14])
    cell_lin.add_edges_from([(4, 13), (13, 14)])
    return cell_lin


@pytest.fixture
def cell_lin_unconnected_node(cell_lin):
    cell_lin.add_node(13)
    return cell_lin


@pytest.fixture
def cell_lin_unconnected_component(cell_lin):
    cell_lin.add_nodes_from([13, 14])
    cell_lin.add_edges_from([(13, 14)])
    return cell_lin


# get_root() ##################################################################


def test_get_normal_lin(cell_lin):
    assert cell_lin.get_root() == 1
    assert cell_lin.get_root(ignore_lone_nodes=True) == 1


def test_get_root_empty_lin(empty_cell_lin):
    assert empty_cell_lin.get_root() == []
    assert empty_cell_lin.get_root(ignore_lone_nodes=True) == []


def test_get_root_single_node(one_node_cell_lin):
    assert one_node_cell_lin.get_root() == 1
    assert one_node_cell_lin.get_root(ignore_lone_nodes=True) == []


def test_get_root_div_root(cell_lin_div_root):
    assert cell_lin_div_root.get_root() == 1
    assert cell_lin_div_root.get_root(ignore_lone_nodes=True) == 1


def test_get_root_unconnected_node(cell_lin_unconnected_node):
    assert cell_lin_unconnected_node.get_root() == [1, 13]
    assert cell_lin_unconnected_node.get_root(ignore_lone_nodes=True) == 1


def test_get_root_unconnected_component(cell_lin_unconnected_component):
    assert cell_lin_unconnected_component.get_root() == [1, 13]
    assert cell_lin_unconnected_component.get_root(ignore_lone_nodes=True) == [1, 13]


# get_leaves() ################################################################


def test_get_leaves_normal_lin(cell_lin):
    assert cell_lin.get_leaves() == [6, 9, 10, 12]
    assert cell_lin.get_leaves(ignore_lone_nodes=True) == [6, 9, 10, 12]


def test_get_leaves_empty_lin(empty_cell_lin):
    assert empty_cell_lin.get_leaves() == []
    assert empty_cell_lin.get_leaves(ignore_lone_nodes=True) == []


def test_get_leaves_single_node(one_node_cell_lin):
    assert one_node_cell_lin.get_leaves() == [1]
    assert one_node_cell_lin.get_leaves(ignore_lone_nodes=True) == []


def test_get_leaves_unconnected_node(cell_lin_unconnected_node):
    res = cell_lin_unconnected_node.get_leaves()
    assert res == [6, 9, 10, 12, 13]
    res = cell_lin_unconnected_node.get_leaves(ignore_lone_nodes=True)
    assert res == [6, 9, 10, 12]


def test_get_leaves_unconnected_component(cell_lin_unconnected_component):
    res = cell_lin_unconnected_component.get_leaves()
    assert res == [6, 9, 10, 12, 14]
    res = cell_lin_unconnected_component.get_leaves(ignore_lone_nodes=True)
    assert res == [6, 9, 10, 12, 14]
