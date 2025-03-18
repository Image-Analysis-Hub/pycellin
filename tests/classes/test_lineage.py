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
def cell_lin_gap(cell_lin):
    # Gap in the lineage.
    cell_lin.remove_nodes_from([5, 7, 12, 13])
    cell_lin.add_edges_from([(4, 6), (4, 8), (11, 14)])
    return cell_lin


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


def test_get_root_gap(cell_lin_gap):
    assert cell_lin_gap.get_root() == 1


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


def test_get_leaves_gap(cell_lin_gap):
    assert cell_lin_gap.get_leaves() == [6, 9, 10, 15, 16]


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
    assert cell_lin.get_ancestors(1) == []
    assert cell_lin.get_ancestors(1, sorted=False) == []
    # Division.
    assert cell_lin.get_ancestors(2) == [1]
    assert cell_lin.get_ancestors(2, sorted=False) == [1]
    assert cell_lin.get_ancestors(4) == [1, 2, 3]
    assert sorted(cell_lin.get_ancestors(4, sorted=False)) == [1, 2, 3]
    assert cell_lin.get_ancestors(14) == [1, 2, 11, 12, 13]
    assert sorted(cell_lin.get_ancestors(14, sorted=False)) == [1, 2, 11, 12, 13]
    # Just after division.
    assert cell_lin.get_ancestors(3) == [1, 2]
    assert sorted(cell_lin.get_ancestors(3, sorted=False)) == [1, 2]
    assert cell_lin.get_ancestors(11) == [1, 2]
    assert sorted(cell_lin.get_ancestors(11, sorted=False)) == [1, 2]
    assert cell_lin.get_ancestors(5) == [1, 2, 3, 4]
    assert sorted(cell_lin.get_ancestors(5, sorted=False)) == [1, 2, 3, 4]
    assert cell_lin.get_ancestors(9) == [1, 2, 3, 4, 7, 8]
    assert sorted(cell_lin.get_ancestors(9, sorted=False)) == [1, 2, 3, 4, 7, 8]
    # Leaves.
    assert cell_lin.get_ancestors(6) == [1, 2, 3, 4, 5]
    assert sorted(cell_lin.get_ancestors(6, sorted=False)) == [1, 2, 3, 4, 5]
    assert cell_lin.get_ancestors(9) == [1, 2, 3, 4, 7, 8]
    assert sorted(cell_lin.get_ancestors(9, sorted=False)) == [1, 2, 3, 4, 7, 8]
    assert cell_lin.get_ancestors(10) == [1, 2, 3, 4, 7, 8]
    assert sorted(cell_lin.get_ancestors(10, sorted=False)) == [1, 2, 3, 4, 7, 8]
    # Other.
    assert cell_lin.get_ancestors(12) == [1, 2, 11]
    assert sorted(cell_lin.get_ancestors(12, sorted=False)) == [1, 2, 11]
    assert cell_lin.get_ancestors(13) == [1, 2, 11, 12]
    assert sorted(cell_lin.get_ancestors(13, sorted=False)) == [1, 2, 11, 12]
    assert cell_lin.get_ancestors(14) == [1, 2, 11, 12, 13]
    assert sorted(cell_lin.get_ancestors(14, sorted=False)) == [1, 2, 11, 12, 13]


def test_get_ancestors_normal_cycle_lin(cycle_lin):
    # Root.
    assert cycle_lin.get_ancestors(1) == []
    assert cycle_lin.get_ancestors(1, sorted=False) == []
    # Leaves.
    assert cycle_lin.get_ancestors(4) == [1, 2]
    assert sorted(cycle_lin.get_ancestors(4, sorted=False)) == [1, 2]
    assert cycle_lin.get_ancestors(5) == [1, 2]
    assert sorted(cycle_lin.get_ancestors(5, sorted=False)) == [1, 2]
    # Other.
    assert cycle_lin.get_ancestors(2) == [1]
    assert cycle_lin.get_ancestors(2, sorted=False) == [1]


def test_get_ancestors_single_node(one_node_cell_lin, one_node_cycle_lin):
    # CellLineage
    assert one_node_cell_lin.get_ancestors(1) == []
    assert one_node_cell_lin.get_ancestors(1, sorted=False) == []
    # CycleLineage
    assert one_node_cycle_lin.get_ancestors(1) == []
    assert one_node_cycle_lin.get_ancestors(1, sorted=False) == []


def test_get_ancestors_gap(cell_lin_gap):
    # Root.
    assert cell_lin_gap.get_ancestors(1) == []
    assert cell_lin_gap.get_ancestors(1, sorted=False) == []
    # Division.
    assert cell_lin_gap.get_ancestors(4) == [1, 2, 3]
    assert cell_lin_gap.get_ancestors(4, sorted=False) == [1, 2, 3]
    assert cell_lin_gap.get_ancestors(8) == [1, 2, 3, 4]
    assert sorted(cell_lin_gap.get_ancestors(8, sorted=False)) == [1, 2, 3, 4]
    assert cell_lin_gap.get_ancestors(14) == [1, 2, 11]
    assert sorted(cell_lin_gap.get_ancestors(14, sorted=False)) == [1, 2, 11]
    # Just after division.
    assert cell_lin_gap.get_ancestors(3) == [1, 2]
    assert sorted(cell_lin_gap.get_ancestors(3, sorted=False)) == [1, 2]
    assert cell_lin_gap.get_ancestors(11) == [1, 2]
    assert sorted(cell_lin_gap.get_ancestors(11, sorted=False)) == [1, 2]
    # Leaves.
    assert cell_lin_gap.get_ancestors(6) == [1, 2, 3, 4]
    assert sorted(cell_lin_gap.get_ancestors(6, sorted=False)) == [1, 2, 3, 4]
    assert cell_lin_gap.get_ancestors(9) == [1, 2, 3, 4, 8]
    assert sorted(cell_lin_gap.get_ancestors(9, sorted=False)) == [1, 2, 3, 4, 8]
    assert cell_lin_gap.get_ancestors(15) == [1, 2, 11, 14]
    assert sorted(cell_lin_gap.get_ancestors(15, sorted=False)) == [1, 2, 11, 14]


def test_get_ancestors_div_root(cell_lin_div_root):
    assert cell_lin_div_root.get_ancestors(1) == []
    assert sorted(cell_lin_div_root.get_ancestors(1, sorted=False)) == []
    assert cell_lin_div_root.get_ancestors(2) == [1]
    assert sorted(cell_lin_div_root.get_ancestors(2, sorted=False)) == [1]
    assert cell_lin_div_root.get_ancestors(17) == [1]
    assert sorted(cell_lin_div_root.get_ancestors(17, sorted=False)) == [1]


def test_get_ancestors_successive_divs_and_root(cell_lin_successive_divs_and_root):
    lin = cell_lin_successive_divs_and_root
    # Root.
    assert lin.get_ancestors(2) == []
    assert lin.get_ancestors(2, sorted=False) == []
    # Divisions.
    assert lin.get_ancestors(3) == [2]
    assert lin.get_ancestors(3, sorted=False) == [2]
    assert lin.get_ancestors(5) == [2, 3, 4]
    assert sorted(lin.get_ancestors(5, sorted=False)) == [2, 3, 4]
    assert lin.get_ancestors(8) == [2, 3]
    assert sorted(lin.get_ancestors(8, sorted=False)) == [2, 3]
    # Leaves.
    assert lin.get_ancestors(6) == [2, 3, 4, 5]
    assert sorted(lin.get_ancestors(6, sorted=False)) == [2, 3, 4, 5]
    assert lin.get_ancestors(7) == [2, 3, 4, 5]
    assert sorted(lin.get_ancestors(7, sorted=False)) == [2, 3, 4, 5]
    assert lin.get_ancestors(9) == [2, 3, 8]
    assert sorted(lin.get_ancestors(9, sorted=False)) == [2, 3, 8]
    assert lin.get_ancestors(10) == [2, 3, 8]
    assert sorted(lin.get_ancestors(10, sorted=False)) == [2, 3, 8]
    assert lin.get_ancestors(11) == [2]
    assert lin.get_ancestors(11, sorted=False) == [2]


def test_get_ancestors_triple_div(cell_lin_triple_div, cycle_lin_triple_div):
    # CellLineage
    lin = cell_lin_triple_div
    assert lin.get_ancestors(4) == [1, 2, 3]
    assert sorted(lin.get_ancestors(4, sorted=False)) == [1, 2, 3]
    assert lin.get_ancestors(5) == [1, 2, 3, 4]
    assert sorted(lin.get_ancestors(5, sorted=False)) == [1, 2, 3, 4]
    assert lin.get_ancestors(7) == [1, 2, 3, 4]
    assert sorted(lin.get_ancestors(7, sorted=False)) == [1, 2, 3, 4]
    assert lin.get_ancestors(18) == [1, 2, 3, 4, 17]
    assert sorted(lin.get_ancestors(18, sorted=False)) == [1, 2, 3, 4, 17]
    # CycleLineage
    lin = cycle_lin_triple_div
    assert lin.get_ancestors(4) == [1, 2]
    assert lin.get_ancestors(4, sorted=False) == [1, 2]
    assert lin.get_ancestors(6) == [1, 2]
    assert lin.get_ancestors(6, sorted=False) == [1, 2]


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


def test_get_descendants_gap(cell_lin_gap):
    lin = cell_lin_gap
    # Root.
    assert sorted(lin.get_descendants(1)) == [2, 3, 4, 6, 8, 9, 10, 11, 14, 15, 16]
    # Division.
    assert sorted(lin.get_descendants(2)) == [3, 4, 6, 8, 9, 10, 11, 14, 15, 16]
    assert sorted(lin.get_descendants(4)) == [6, 8, 9, 10]
    assert sorted(lin.get_descendants(8)) == [9, 10]
    assert sorted(lin.get_descendants(14)) == [15, 16]
    # Just after division.
    assert sorted(lin.get_descendants(3)) == [4, 6, 8, 9, 10]
    assert sorted(lin.get_descendants(11)) == [14, 15, 16]
    # Leaves.
    assert lin.get_descendants(6) == []
    assert lin.get_descendants(9) == []
    assert lin.get_descendants(15) == []


def test_get_descendants_div_root(cell_lin_div_root):
    assert sorted(cell_lin_div_root.get_descendants(1)) == list(range(2, 18))


def test_get_descendants_successive_divs_and_root(cell_lin_successive_divs_and_root):
    lin = cell_lin_successive_divs_and_root
    # Root.
    assert sorted(lin.get_descendants(2)) == list(range(3, 12))
    # Divisions.
    assert sorted(lin.get_descendants(3)) == list(range(4, 11))
    assert sorted(lin.get_descendants(5)) == [6, 7]
    assert sorted(lin.get_descendants(8)) == [9, 10]
    # Leaves.
    assert lin.get_descendants(6) == []
    assert lin.get_descendants(9) == []
    assert lin.get_descendants(11) == []
    # Other.
    assert sorted(lin.get_descendants(4)) == [5, 6, 7]


def test_get_descendants_triple_div(cell_lin_triple_div, cycle_lin_triple_div):
    # CellLineage
    lin = cell_lin_triple_div
    assert sorted(lin.get_descendants(4)) == list(range(5, 11)) + [17, 18]
    assert lin.get_descendants(17) == [18]
    assert lin.get_descendants(18) == []
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


def test_is_root_gap(cell_lin_gap):
    assert cell_lin_gap.is_root(1)
    assert not cell_lin_gap.is_root(2)
    assert not cell_lin_gap.is_root(6)


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


def test_is_leaf_gap(cell_lin_gap):
    assert not cell_lin_gap.is_leaf(1)
    assert not cell_lin_gap.is_leaf(4)
    assert cell_lin_gap.is_leaf(6)
    assert cell_lin_gap.is_leaf(9)
    assert cell_lin_gap.is_leaf(15)


def test_is_leaf_unconnected_node(cell_lin_unconnected_node):
    assert cell_lin_unconnected_node.is_leaf(17)


def test_is_leaf_unconnected_component(cell_lin_unconnected_component):
    assert not cell_lin_unconnected_component.is_leaf(17)
    assert cell_lin_unconnected_component.is_leaf(18)


# get_fusions() ###############################################################


def test_get_fusions_normal_lin(cell_lin):
    # No fusions.
    assert cell_lin.get_fusions() == []
    # Fusion.
    cell_lin.add_edge(3, 12)
    assert cell_lin.get_fusions() == [12]
    # Multiple fusions.
    cell_lin.add_edge(5, 8)
    cell_lin.add_edge(4, 14)
    assert sorted(cell_lin.get_fusions()) == [8, 12, 14]


def test_get_fusions_empty_lin(empty_cell_lin):
    # No fusions.
    assert empty_cell_lin.get_fusions() == []


def test_get_fusions_single_node(one_node_cell_lin):
    # No fusions.
    assert one_node_cell_lin.get_fusions() == []


def test_get_fusions_gap(cell_lin_gap):
    # No fusions.
    assert cell_lin_gap.get_fusions() == []
    # Fusion.
    cell_lin_gap.add_edge(3, 14)
    assert cell_lin_gap.get_fusions() == [14]
    # Multiple fusions.
    cell_lin_gap.add_edge(8, 15)
    assert sorted(cell_lin_gap.get_fusions()) == [14, 15]


def test_get_fusions_div_root(cell_lin_div_root):
    # No fusions.
    assert cell_lin_div_root.get_fusions() == []
    # Fusion.
    cell_lin_div_root.add_edge(17, 11)
    assert cell_lin_div_root.get_fusions() == [11]


def test_get_fusions_successive_divs_and_root(cell_lin_successive_divs_and_root):
    # No fusions.
    assert cell_lin_successive_divs_and_root.get_fusions() == []
    # Fusion.
    cell_lin_successive_divs_and_root.add_edge(4, 9)
    assert cell_lin_successive_divs_and_root.get_fusions() == [9]


def test_get_fusions_triple_fusion(cell_lin_triple_div):
    # No fusions.
    assert cell_lin_triple_div.get_fusions() == []
    # Fusion.
    cell_lin_triple_div.add_edges_from([(6, 9), (18, 9)])
    assert cell_lin_triple_div.get_fusions() == [9]


def test_get_fusions_unconnected_node(cell_lin_unconnected_node):
    # No fusions.
    assert cell_lin_unconnected_node.get_fusions() == []
    # Multiple fusions.
    cell_lin_unconnected_node.add_edge(5, 8)
    cell_lin_unconnected_node.add_edge(4, 14)
    assert sorted(cell_lin_unconnected_node.get_fusions()) == [8, 14]


def test_get_fusions_unconnected_component(cell_lin_unconnected_component):
    # No fusions.
    assert cell_lin_unconnected_component.get_fusions() == []
    # Fusion.
    cell_lin_unconnected_component.add_edges_from([(17, 19), (18, 20), (19, 20)])
    assert cell_lin_unconnected_component.get_fusions() == [20]


# _get_next_available_node_ID() ###############################################


def test_get_next_available_node_ID_normal_lin(cell_lin):
    assert cell_lin._get_next_available_node_ID() == 17


def test_get_next_available_node_ID_empty_lin(empty_cell_lin):
    assert empty_cell_lin._get_next_available_node_ID() == 0


def test_get_next_available_node_ID_single_node(one_node_cell_lin):
    assert one_node_cell_lin._get_next_available_node_ID() == 2


def test_get_next_available_node_ID_gap(cell_lin_gap):
    assert cell_lin_gap._get_next_available_node_ID() == 17


def test_get_next_available_node_ID__unconnected_node(cell_lin_unconnected_node):
    assert cell_lin_unconnected_node._get_next_available_node_ID() == 18


def test_get_next_available_node_ID_unconnected_component(
    cell_lin_unconnected_component,
):
    assert cell_lin_unconnected_component._get_next_available_node_ID() == 19


# _add_cell() #################################################################

# _remove_cell() ##############################################################

# _add_link() #################################################################

# _remove_link() ##############################################################

# _split_from_cell() ##########################################################

# get_divisions() #############################################################

# get_cell_cycle() ############################################################

# get_cell_cycles() ###########################################################

# get_sister_cells() ##########################################################

# is_division() ###############################################################

# get_edges_within_cycle() ###################################################

# yield_edges_within_cycle() #################################################
