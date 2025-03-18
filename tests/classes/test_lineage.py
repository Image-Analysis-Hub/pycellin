#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for CellLineage and CycleLineage classes from lineage.py module."""

import pytest

import networkx as nx

from pycellin.classes import CellLineage, CycleLineage


# CellLineage fixtures ########################################################


@pytest.fixture
def empty_cell_lin():
    return CellLineage()


@pytest.fixture
def one_node_cell_lin():
    lineage = CellLineage()
    lineage.add_node(1, frame=0)
    return lineage


@pytest.fixture
def cell_lin():
    # Nothing special, just a lineage.
    lineage = CellLineage()
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
            (12, 13),
            (13, 14),
            (14, 15),
            (14, 16),
        ]
    )
    for n in lineage.nodes:
        lineage.nodes[n]["frame"] = nx.shortest_path_length(lineage, 1, n)
    return lineage


@pytest.fixture
def cell_lin_div_root(cell_lin):
    # The root is a division.
    cell_lin.add_node(17, frame=1)
    cell_lin.add_edge(1, 17)
    return cell_lin


@pytest.fixture
def cell_lin_successive_divs_and_root():
    # Successive divisions and root division.
    lineage = CellLineage()
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
    for n in lineage.nodes:
        lineage.nodes[n]["frame"] = nx.shortest_path_length(lineage, 2, n)
    return lineage


@pytest.fixture
def cell_lin_triple_div(cell_lin):
    # Triple division.
    cell_lin.add_node(17, frame=4)
    cell_lin.add_node(18, frame=5)
    cell_lin.add_edges_from([(4, 17), (17, 18)])
    return cell_lin


@pytest.fixture
def cell_lin_unconnected_node(cell_lin):
    cell_lin.add_node(17, frame=0)
    return cell_lin


@pytest.fixture
def cell_lin_unconnected_component(cell_lin):
    cell_lin.add_node(17, frame=0)
    cell_lin.add_node(18, frame=1)
    cell_lin.add_edge(17, 18)
    return cell_lin


# CycleLineage fixtures #######################################################


@pytest.fixture
def empty_cycle_lin():
    return CycleLineage()


@pytest.fixture
def one_node_cycle_lin():
    lineage = CycleLineage()
    lineage.add_node(1, level=0)
    return lineage


@pytest.fixture
def cycle_lin():
    # Nothing special, just a lineage.
    lineage = CycleLineage()
    lineage.add_edges_from(
        [
            (1, 2),
            (1, 3),
            (2, 4),
            (2, 5),
        ]
    )
    for n in lineage.nodes:
        lineage.nodes[n]["level"] = nx.shortest_path_length(lineage, 1, n)
    return lineage


@pytest.fixture
def cycle_lin_triple_div(cycle_lin):
    # Triple division.
    cycle_lin.add_node(6, level=2)
    cycle_lin.add_edge(2, 6)
    return cycle_lin


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
    assert cell_lin_unconnected_node.get_root() == [1, 17]
    assert cell_lin_unconnected_node.get_root(ignore_lone_nodes=True) == 1


def test_get_root_unconnected_component(cell_lin_unconnected_component):
    assert cell_lin_unconnected_component.get_root() == [1, 17]
    assert cell_lin_unconnected_component.get_root(ignore_lone_nodes=True) == [1, 17]


# get_leaves() ################################################################


def test_get_leaves_normal_lin(cell_lin):
    assert cell_lin.get_leaves() == [6, 9, 10, 15, 16]
    assert cell_lin.get_leaves(ignore_lone_nodes=True) == [6, 9, 10, 15, 16]


def test_get_leaves_empty_lin(empty_cell_lin):
    assert empty_cell_lin.get_leaves() == []
    assert empty_cell_lin.get_leaves(ignore_lone_nodes=True) == []


def test_get_leaves_single_node(one_node_cell_lin):
    assert one_node_cell_lin.get_leaves() == [1]
    assert one_node_cell_lin.get_leaves(ignore_lone_nodes=True) == []


def test_get_leaves_unconnected_node(cell_lin_unconnected_node):
    res = cell_lin_unconnected_node.get_leaves()
    assert res == [6, 9, 10, 15, 16, 17]
    res = cell_lin_unconnected_node.get_leaves(ignore_lone_nodes=True)
    assert res == [6, 9, 10, 15, 16]


def test_get_leaves_unconnected_component(cell_lin_unconnected_component):
    res = cell_lin_unconnected_component.get_leaves()
    assert res == [6, 9, 10, 15, 16, 18]
    res = cell_lin_unconnected_component.get_leaves(ignore_lone_nodes=True)
    assert res == [6, 9, 10, 15, 16, 18]


# get_ancestors() #############################################################


def test_get_ancestors_normal_cell_lin(cell_lin):
    # Root.
    expected = []
    assert cell_lin.get_ancestors(1) == expected
    assert cell_lin.get_ancestors(1, sorted=False) == expected
    # Division.
    expected = [1]
    assert cell_lin.get_ancestors(2) == expected
    assert cell_lin.get_ancestors(2, sorted=False) == expected
    expected = [1, 2, 3]
    assert cell_lin.get_ancestors(4) == expected
    assert sorted(cell_lin.get_ancestors(4, sorted=False)) == expected
    expected = [1, 2, 3, 4, 7]
    assert cell_lin.get_ancestors(8) == expected
    assert sorted(cell_lin.get_ancestors(8, sorted=False)) == expected
    expected = [1, 2, 11, 12, 13]
    assert cell_lin.get_ancestors(14) == expected
    assert sorted(cell_lin.get_ancestors(14, sorted=False)) == expected
    # Just after division.
    expected = [1, 2]
    assert cell_lin.get_ancestors(3) == expected
    assert sorted(cell_lin.get_ancestors(3, sorted=False)) == expected
    assert cell_lin.get_ancestors(11) == expected
    assert sorted(cell_lin.get_ancestors(11, sorted=False)) == expected
    expected = [1, 2, 3, 4]
    assert cell_lin.get_ancestors(5) == expected
    assert sorted(cell_lin.get_ancestors(5, sorted=False)) == expected
    assert cell_lin.get_ancestors(7) == expected
    assert sorted(cell_lin.get_ancestors(7, sorted=False)) == expected
    expected = [1, 2, 3, 4, 7, 8]
    assert cell_lin.get_ancestors(9) == expected
    assert sorted(cell_lin.get_ancestors(9, sorted=False)) == expected
    assert cell_lin.get_ancestors(10) == expected
    assert sorted(cell_lin.get_ancestors(10, sorted=False)) == expected
    # Leaves.
    expected = [1, 2, 3, 4, 5]
    assert cell_lin.get_ancestors(6) == expected
    assert sorted(cell_lin.get_ancestors(6, sorted=False)) == expected
    expected = [1, 2, 3, 4, 7, 8]
    assert cell_lin.get_ancestors(9) == expected
    assert sorted(cell_lin.get_ancestors(9, sorted=False)) == expected
    assert cell_lin.get_ancestors(10) == expected
    assert sorted(cell_lin.get_ancestors(10, sorted=False)) == expected
    expected = [1, 2, 11, 12, 13, 14]
    assert cell_lin.get_ancestors(15) == expected
    assert sorted(cell_lin.get_ancestors(15, sorted=False)) == expected
    assert cell_lin.get_ancestors(16) == expected
    assert sorted(cell_lin.get_ancestors(16, sorted=False)) == expected
    # Other.
    expected = [1, 2, 11]
    assert cell_lin.get_ancestors(12) == expected
    assert sorted(cell_lin.get_ancestors(12, sorted=False)) == expected
    expected = [1, 2, 11, 12]
    assert cell_lin.get_ancestors(13) == expected
    assert sorted(cell_lin.get_ancestors(13, sorted=False)) == expected
    expected = [1, 2, 11, 12, 13]
    assert cell_lin.get_ancestors(14) == expected
    assert sorted(cell_lin.get_ancestors(14, sorted=False)) == expected


def test_get_ancestors_normal_cycle_lin(cycle_lin):
    # Root.
    expected = []
    assert cycle_lin.get_ancestors(1) == expected
    assert cycle_lin.get_ancestors(1, sorted=False) == expected
    # Leaves.
    expected = [1, 2]
    assert cycle_lin.get_ancestors(4) == expected
    assert sorted(cycle_lin.get_ancestors(4, sorted=False)) == expected
    assert cycle_lin.get_ancestors(5) == expected
    assert sorted(cycle_lin.get_ancestors(5, sorted=False)) == expected
    # Other.
    expected = [1]
    assert cycle_lin.get_ancestors(2) == expected
    assert cycle_lin.get_ancestors(2, sorted=False) == expected


def test_get_ancestors_single_node(one_node_cell_lin, one_node_cycle_lin):
    # CellLineage
    assert one_node_cell_lin.get_ancestors(1) == []
    assert one_node_cell_lin.get_ancestors(1, sorted=False) == []
    # CycleLineage
    assert one_node_cycle_lin.get_ancestors(1) == []
    assert one_node_cycle_lin.get_ancestors(1, sorted=False) == []


def test_get_ancestors_div_root(cell_lin_div_root):
    assert cell_lin_div_root.get_ancestors(1) == []
    assert sorted(cell_lin_div_root.get_ancestors(1, sorted=False)) == []
    expected = [1]
    assert cell_lin_div_root.get_ancestors(2) == expected
    assert sorted(cell_lin_div_root.get_ancestors(2, sorted=False)) == expected
    assert cell_lin_div_root.get_ancestors(17) == expected
    assert sorted(cell_lin_div_root.get_ancestors(17, sorted=False)) == expected


def test_get_ancestors_successive_divs_and_root(cell_lin_successive_divs_and_root):
    # Root.
    assert cell_lin_successive_divs_and_root.get_ancestors(2) == []
    assert cell_lin_successive_divs_and_root.get_ancestors(2, sorted=False) == []
    # Divisions.
    expected = [2]
    assert cell_lin_successive_divs_and_root.get_ancestors(3) == expected
    assert cell_lin_successive_divs_and_root.get_ancestors(3, sorted=False) == expected
    expected = [2, 3, 4]
    assert cell_lin_successive_divs_and_root.get_ancestors(5) == expected
    assert (
        sorted(cell_lin_successive_divs_and_root.get_ancestors(5, sorted=False))
        == expected
    )
    expected = [2, 3]
    assert cell_lin_successive_divs_and_root.get_ancestors(8) == expected
    assert (
        sorted(cell_lin_successive_divs_and_root.get_ancestors(8, sorted=False))
        == expected
    )
    # Leaves.
    expected = [2, 3, 4, 5]
    assert cell_lin_successive_divs_and_root.get_ancestors(6) == expected
    assert (
        sorted(cell_lin_successive_divs_and_root.get_ancestors(6, sorted=False))
        == expected
    )
    assert cell_lin_successive_divs_and_root.get_ancestors(7) == expected
    assert (
        sorted(cell_lin_successive_divs_and_root.get_ancestors(7, sorted=False))
        == expected
    )
    expected = [2, 3, 8]
    assert cell_lin_successive_divs_and_root.get_ancestors(9) == expected
    assert (
        sorted(cell_lin_successive_divs_and_root.get_ancestors(9, sorted=False))
        == expected
    )
    assert cell_lin_successive_divs_and_root.get_ancestors(10) == expected
    assert (
        sorted(cell_lin_successive_divs_and_root.get_ancestors(10, sorted=False))
        == expected
    )
    expected = [2]
    assert cell_lin_successive_divs_and_root.get_ancestors(11) == expected
    assert cell_lin_successive_divs_and_root.get_ancestors(11, sorted=False) == expected


def test_get_ancestors_triple_div(cell_lin_triple_div, cycle_lin_triple_div):
    # CellLineage
    expected = [1, 2, 3]
    assert cell_lin_triple_div.get_ancestors(4) == expected
    assert sorted(cell_lin_triple_div.get_ancestors(4, sorted=False)) == expected
    expected = [1, 2, 3, 4]
    assert cell_lin_triple_div.get_ancestors(5) == expected
    assert sorted(cell_lin_triple_div.get_ancestors(5, sorted=False)) == expected
    assert cell_lin_triple_div.get_ancestors(7) == expected
    assert sorted(cell_lin_triple_div.get_ancestors(7, sorted=False)) == expected
    expected = [1, 2, 3, 4, 17]
    assert cell_lin_triple_div.get_ancestors(18) == expected
    assert sorted(cell_lin_triple_div.get_ancestors(18, sorted=False)) == expected
    # CycleLineage
    expected = [1, 2]
    assert cycle_lin_triple_div.get_ancestors(4) == expected
    assert cycle_lin_triple_div.get_ancestors(4, sorted=False) == expected
    assert cycle_lin_triple_div.get_ancestors(6) == expected
    assert cycle_lin_triple_div.get_ancestors(6, sorted=False) == expected


def test_get_ancestors_unconnected_node(cell_lin_unconnected_node):
    assert cell_lin_unconnected_node.get_ancestors(17) == []
    assert cell_lin_unconnected_node.get_ancestors(17, sorted=False) == []


def test_get_ancestors_unconnected_component(cell_lin_unconnected_component):
    assert cell_lin_unconnected_component.get_ancestors(17) == []
    assert cell_lin_unconnected_component.get_ancestors(17, sorted=False) == []
    assert cell_lin_unconnected_component.get_ancestors(18) == [17]
    assert cell_lin_unconnected_component.get_ancestors(18, sorted=False) == [17]


def test_get_ancestors_node_ID_error(cell_lin, cycle_lin):
    with pytest.raises(KeyError):
        cell_lin.get_ancestors(0)
    with pytest.raises(KeyError):
        cycle_lin.get_ancestors(0)


# get_descendants() ###########################################################


def test_get_descendants_normal_cell_lin(cell_lin):
    # Root.
    assert sorted(cell_lin.get_descendants(1)) == list(range(2, 17))
    # Division.
    assert sorted(cell_lin.get_descendants(2)) == list(range(3, 17))
    assert sorted(cell_lin.get_descendants(4)) == list(range(5, 11))
    assert sorted(cell_lin.get_descendants(8)) == [9, 10]
    assert sorted(cell_lin.get_descendants(14)) == [15, 16]
    # Just after division.
    assert sorted(cell_lin.get_descendants(3)) == list(range(4, 11))
    assert sorted(cell_lin.get_descendants(5)) == [6]
    assert sorted(cell_lin.get_descendants(7)) == [8, 9, 10]
    assert sorted(cell_lin.get_descendants(11)) == list(range(12, 17))
    # Leaves.
    assert cell_lin.get_descendants(6) == []
    assert cell_lin.get_descendants(9) == []
    assert cell_lin.get_descendants(15) == []
    # Other.
    assert sorted(cell_lin.get_descendants(12)) == list(range(13, 17))


def test_get_descendants_normal_cycle_lin(cycle_lin):
    # Root.
    assert sorted(cycle_lin.get_descendants(1)) == [2, 3, 4, 5]
    # Leaves.
    assert cycle_lin.get_descendants(3) == []
    assert cycle_lin.get_descendants(5) == []
    # Other.
    assert cycle_lin.get_descendants(2) == [4, 5]


def test_get_descendants_single_node(one_node_cell_lin, one_node_cycle_lin):
    # CellLineage
    assert one_node_cell_lin.get_descendants(1) == []
    # CycleLineage
    assert one_node_cycle_lin.get_descendants(1) == []


def test_get_descendants_div_root(cell_lin_div_root):
    assert sorted(cell_lin_div_root.get_descendants(1)) == list(range(2, 18))


def test_get_descendants_successive_divs_and_root(cell_lin_successive_divs_and_root):
    # Root.
    expected = list(range(3, 12))
    assert sorted(cell_lin_successive_divs_and_root.get_descendants(2)) == expected
    # Divisions.
    expected = list(range(4, 11))
    assert sorted(cell_lin_successive_divs_and_root.get_descendants(3)) == expected
    assert sorted(cell_lin_successive_divs_and_root.get_descendants(5)) == [6, 7]
    assert sorted(cell_lin_successive_divs_and_root.get_descendants(8)) == [9, 10]
    # Leaves.
    assert cell_lin_successive_divs_and_root.get_descendants(6) == []
    assert cell_lin_successive_divs_and_root.get_descendants(9) == []
    assert cell_lin_successive_divs_and_root.get_descendants(11) == []
    # Other.
    assert sorted(cell_lin_successive_divs_and_root.get_descendants(4)) == [5, 6, 7]


def test_get_descendants_triple_div(cell_lin_triple_div, cycle_lin_triple_div):
    # CellLineage
    expected = list(range(5, 11)) + [17, 18]
    assert sorted(cell_lin_triple_div.get_descendants(4)) == expected
    assert cell_lin_triple_div.get_descendants(17) == [18]
    assert cell_lin_triple_div.get_descendants(18) == []
    # CycleLineage
    assert sorted(cycle_lin_triple_div.get_descendants(2)) == [4, 5, 6]
    assert cycle_lin_triple_div.get_descendants(6) == []


def test_get_descendants_unconnected_node(cell_lin_unconnected_node):
    assert cell_lin_unconnected_node.get_descendants(17) == []


def test_get_descendants_unconnected_component(cell_lin_unconnected_component):
    assert cell_lin_unconnected_component.get_descendants(17) == [18]
    assert cell_lin_unconnected_component.get_descendants(18) == []


# is_root() ###################################################################

# TODO: when keyerror on noi


def test_is_root_normal_lin(cell_lin, cycle_lin):
    # CellLineage
    assert cell_lin.is_root(1)
    assert not cell_lin.is_root(2)
    assert not cell_lin.is_root(6)
    # CycleLineage
    assert cycle_lin.is_root(1)
    assert not cycle_lin.is_root(2)
    assert not cycle_lin.is_root(4)


def test_is_root_single_node(one_node_cell_lin, one_node_cycle_lin):
    # CellLineage
    assert one_node_cell_lin.is_root(1)
    # CycleLineage
    assert one_node_cycle_lin.is_root(1)


def test_is_root_div_root(cell_lin_div_root):
    assert cell_lin_div_root.is_root(1)
    assert not cell_lin_div_root.is_root(2)
    assert not cell_lin_div_root.is_root(17)


def test_is_root_unconnected_node(cell_lin_unconnected_node):
    assert cell_lin_unconnected_node.is_root(17)


def test_is_root_unconnected_component(cell_lin_unconnected_component):
    assert cell_lin_unconnected_component.is_root(17)
    assert not cell_lin_unconnected_component.is_root(18)


# is_leaf() ###################################################################


def test_is_leaf_normal_lin(cell_lin, cycle_lin):
    # CellLineage
    assert not cell_lin.is_leaf(1)
    assert not cell_lin.is_leaf(2)
    assert not cell_lin.is_leaf(4)
    assert cell_lin.is_leaf(9)
    assert cell_lin.is_leaf(10)
    assert cell_lin.is_leaf(16)
    # CycleLineage
    assert not cycle_lin.is_leaf(1)
    assert not cycle_lin.is_leaf(2)
    assert cycle_lin.is_leaf(3)
    assert cycle_lin.is_leaf(4)


def test_is_leaf_single_node(one_node_cell_lin, one_node_cycle_lin):
    # CellLineage
    assert one_node_cell_lin.is_leaf(1)
    # CycleLineage
    assert one_node_cycle_lin.is_leaf(1)


def test_is_leaf_unconnected_node(cell_lin_unconnected_node):
    assert cell_lin_unconnected_node.is_leaf(17)


def test_is_leaf_unconnected_component(cell_lin_unconnected_component):
    assert not cell_lin_unconnected_component.is_leaf(17)
    assert cell_lin_unconnected_component.is_leaf(18)


# get_fusions() ###############################################################
