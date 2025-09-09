#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Unit test for CellLineage and CycleLineage classes from lineage.py module."""

import pytest

import networkx as nx

from pycellin.classes import CellLineage, CycleLineage
from pycellin.classes.exceptions import (
    FusionError,
    TimeFlowError,
    LineageStructureError,
)


# CellLineage fixtures ########################################################


@pytest.fixture
def empty_cell_lin():
    lineage = CellLineage()
    lineage.graph["lineage_ID"] = 1
    return lineage


@pytest.fixture
def one_node_cell_lin():
    lineage = CellLineage()
    lineage.add_node(1, frame=0)
    lineage.graph["lineage_ID"] = 1
    return lineage


@pytest.fixture
def cell_lin():
    # Nothing special, just a lineage.
    lineage = CellLineage()
    lineage.add_edges_from(
        [
            (1, 2, {"name": "1 -> 2"}),
            (2, 3, {"name": "2 -> 3"}),
            (3, 4, {"name": "3 -> 4"}),
            (4, 5, {"name": "4 -> 5"}),
            (5, 6, {"name": "5 -> 6"}),
            (4, 7, {"name": "4 -> 7"}),
            (7, 8, {"name": "7 -> 8"}),
            (8, 9, {"name": "8 -> 9"}),
            (8, 10, {"name": "8 -> 10"}),
            (2, 11, {"name": "2 -> 11"}),
            (11, 12, {"name": "11 -> 12"}),
            (12, 13, {"name": "12 -> 13"}),
            (13, 14, {"name": "13 -> 14"}),
            (14, 15, {"name": "14 -> 15"}),
            (14, 16, {"name": "14 -> 16"}),
        ]
    )
    for n in lineage.nodes:
        lineage.nodes[n]["frame"] = nx.shortest_path_length(lineage, 1, n)
        lineage.nodes[n]["cell_ID"] = n
    lineage.graph["lineage_ID"] = 1
    return lineage


@pytest.fixture
def cell_lin_gap(cell_lin):
    # Gap in the lineage.
    new_lin = cell_lin.copy()
    new_lin.remove_nodes_from([5, 7, 12, 13])
    new_lin.add_edges_from([(4, 6), (4, 8), (11, 14)])
    return new_lin


@pytest.fixture
def cell_lin_div_root(cell_lin):
    # The root is a division.
    new_lin = cell_lin.copy()
    new_lin.add_node(17, frame=1)
    new_lin.add_edge(1, 17)
    return new_lin


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
        lineage.nodes[n]["frame"] = nx.shortest_path_length(lineage, 2, n) + 1
        lineage.nodes[n]["cell_ID"] = n
    lineage.graph["lineage_ID"] = 2
    return lineage


@pytest.fixture
def cell_lin_triple_div(cell_lin):
    # Triple division.
    new_lin = cell_lin.copy()
    new_lin.add_node(17, frame=4)
    new_lin.add_node(18, frame=5)
    new_lin.add_edges_from([(4, 17), (17, 18)])
    return new_lin


@pytest.fixture
def cell_lin_unconnected_node(cell_lin):
    new_lin = cell_lin.copy()
    new_lin.add_node(17, frame=1, cell_ID=17)
    new_lin.graph["lineage_ID"] = 2
    return new_lin


@pytest.fixture
def cell_lin_unconnected_component(cell_lin):
    new_lin = cell_lin.copy()
    new_lin.add_node(17, frame=1, cell_ID=17)
    new_lin.add_node(18, frame=2, cell_ID=18)
    new_lin.add_edge(17, 18)
    new_lin.graph["lineage_ID"] = 2
    return new_lin


@pytest.fixture
def cell_lin_unconnected_component_div(cell_lin_unconnected_component):
    new_lin = cell_lin_unconnected_component.copy()
    new_lin.add_node(19, frame=2)
    new_lin.add_node(20, frame=3)
    new_lin.add_node(21, frame=4)
    new_lin.add_node(22, frame=3)
    new_lin.add_edges_from([(17, 19), (19, 20), (20, 21), (19, 22)])
    return new_lin


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


# _remove_prop() ###########################################################


def test_remove_prop_node(cell_lin):
    cell_lin._remove_prop("frame", "node")
    for node in cell_lin.nodes:
        assert "frame" not in cell_lin.nodes[node]


def test_remove_prop_edge(cell_lin):
    cell_lin._remove_prop("name", "edge")
    for edge in cell_lin.edges:
        assert "name" not in cell_lin.edges[edge]


def test_remove_prop_lineage(cell_lin):
    cell_lin._remove_prop("lineage_ID", "lineage")
    assert "lineage_ID" not in cell_lin.graph


def test_remove_prop_unknown_property(cell_lin):
    # Attempting to remove a property that does not exist should not raise an error.
    cell_lin._remove_prop("unknown_property", "node")
    cell_lin._remove_prop("unknown_property", "edge")
    cell_lin._remove_prop("unknown_property", "lineage")


def test_remove_prop_missing_property(cell_lin):
    # Attempting to remove a property not present in some elements should not raise
    # an error.
    cell_lin.add_edge(16, 17)
    cell_lin._remove_prop("frame", "node")
    cell_lin._remove_prop("name", "edge")


def test_remove_prop_invalid_type(cell_lin):
    with pytest.raises(
        ValueError,
        match="Invalid prop_type. Must be one of 'node', 'edge', or 'lineage'.",
    ):
        cell_lin._remove_prop("custom_property", "invalid_type")


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
    assert cell_lin_gap.get_root(ignore_lone_nodes=True) == 1


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


def test_get_ancestors_cannot_order(cell_lin):
    for n in cell_lin.nodes:
        del cell_lin.nodes[n]["frame"]
    with pytest.warns(UserWarning, match="No 'frame' property to order the cells."):
        cell_lin.get_ancestors(16)


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


def test_add_cell_no_no_arg(cell_lin):
    next_id = cell_lin._get_next_available_node_ID()
    assert cell_lin._add_cell() == next_id
    assert cell_lin.nodes[next_id]["cell_ID"] == next_id
    assert cell_lin.nodes[next_id]["frame"] == 0


def test_add_cell_with_id(cell_lin):
    assert cell_lin._add_cell(nid=20) == 20
    assert cell_lin.nodes[20]["cell_ID"] == 20
    assert cell_lin.nodes[20]["frame"] == 0


def test_add_cell_with_frame(cell_lin):
    next_id = cell_lin._get_next_available_node_ID()
    assert cell_lin._add_cell(frame=5) == next_id
    assert cell_lin.nodes[next_id]["cell_ID"] == next_id
    assert cell_lin.nodes[next_id]["frame"] == 5


def test_add_cell_with_propertys(cell_lin):
    cell_id = 20
    assert cell_lin._add_cell(20, color="red", size=10) == cell_id
    assert cell_lin.nodes[cell_id]["cell_ID"] == cell_id
    assert cell_lin.nodes[cell_id]["frame"] == 0
    assert cell_lin.nodes[cell_id]["color"] == "red"
    assert cell_lin.nodes[cell_id]["size"] == 10


def test_add_cell_existing_id(cell_lin):
    with pytest.raises(ValueError):
        cell_lin._add_cell(1)
    cell_lin.graph["lineage_ID"] = 1
    with pytest.raises(ValueError):
        cell_lin._add_cell(1)


def test_add_cell_empty_lin(empty_cell_lin):
    assert empty_cell_lin._add_cell() == 0
    assert empty_cell_lin.nodes[0]["cell_ID"] == 0
    assert empty_cell_lin.nodes[0]["frame"] == 0


def test_add_cell_single_node(one_node_cell_lin):
    assert one_node_cell_lin._add_cell() == 2
    assert one_node_cell_lin.nodes[2]["cell_ID"] == 2
    assert one_node_cell_lin.nodes[2]["frame"] == 0


# _remove_cell() ##############################################################


def check_correct_cell_removal(cell_lin, node_id):
    cell_feats = cell_lin.nodes[node_id]
    assert cell_lin._remove_cell(node_id) == cell_feats
    assert node_id not in cell_lin.nodes
    assert not any(node_id in edge for edge in cell_lin.edges)


def test_remove_cell_normal_lin(cell_lin):
    # Root.
    check_correct_cell_removal(cell_lin, 1)
    # Division.
    check_correct_cell_removal(cell_lin, 4)
    # Just after division.
    check_correct_cell_removal(cell_lin, 11)
    # Leaves.
    check_correct_cell_removal(cell_lin, 10)
    check_correct_cell_removal(cell_lin, 16)
    # Intermediate node.
    check_correct_cell_removal(cell_lin, 12)


def test_remove_cell_empty_lin(empty_cell_lin):
    with pytest.raises(KeyError):
        empty_cell_lin._remove_cell(0)


def test_remove_cell_single_node(one_node_cell_lin):
    check_correct_cell_removal(one_node_cell_lin, 1)


def test_remove_cell_gap(cell_lin_gap):
    # Root.
    check_correct_cell_removal(cell_lin_gap, 1)
    # Division.
    check_correct_cell_removal(cell_lin_gap, 4)
    check_correct_cell_removal(cell_lin_gap, 8)
    check_correct_cell_removal(cell_lin_gap, 14)
    # Just after division.
    check_correct_cell_removal(cell_lin_gap, 11)
    # Leaves.
    check_correct_cell_removal(cell_lin_gap, 6)
    check_correct_cell_removal(cell_lin_gap, 15)


def test_remove_cell_div_root(cell_lin_div_root):
    check_correct_cell_removal(cell_lin_div_root, 17)


def test_remove_cell_unconnected_node(cell_lin_unconnected_node):
    check_correct_cell_removal(cell_lin_unconnected_node, 17)


def test_remove_cell_unconnected_component(cell_lin_unconnected_component):
    check_correct_cell_removal(cell_lin_unconnected_component, 17)
    check_correct_cell_removal(cell_lin_unconnected_component, 18)


def test_remove_cell_unconnected_component_div(cell_lin_unconnected_component_div):
    check_correct_cell_removal(cell_lin_unconnected_component_div, 18)
    check_correct_cell_removal(cell_lin_unconnected_component_div, 19)
    check_correct_cell_removal(cell_lin_unconnected_component_div, 20)
    check_correct_cell_removal(cell_lin_unconnected_component_div, 22)


# _add_link() #################################################################


def test_add_link_normal_lin(cell_lin):
    # Add a valid link.
    cell_lin.add_node(17, frame=6, cell_ID=17)
    cell_lin._add_link(6, 17)
    assert cell_lin.has_edge(6, 17)
    assert cell_lin.nodes[17]["cell_ID"] == 17
    assert cell_lin.nodes[17]["frame"] == 6
    # Add a link that creates a division.
    cell_lin.add_node(18, frame=1, cell_ID=18)
    cell_lin._add_link(1, 18)
    assert cell_lin.has_edge(1, 18)
    assert cell_lin.nodes[18]["cell_ID"] == 18
    assert cell_lin.nodes[18]["frame"] == 1


def test_add_link_existing_edge(cell_lin):
    # Add an existing link.
    with pytest.raises(ValueError):
        cell_lin._add_link(1, 2)


def test_add_link_nonexistent_source(cell_lin):
    # Add a link with a nonexistent source.
    with pytest.raises(ValueError):
        cell_lin._add_link(99, 2)


def test_add_link_nonexistent_target(cell_lin):
    # Add a link with a nonexistent target.
    with pytest.raises(ValueError):
        cell_lin._add_link(1, 99)


def test_add_link_fusion_error(cell_lin):
    # Add a link that creates a fusion event.
    cell_lin.add_edge(3, 12)
    with pytest.raises(FusionError):
        cell_lin._add_link(5, 12)


def test_add_link_time_flow_error(cell_lin):
    # Add a link that violates the flow of time.
    cell_lin.add_node(17, frame=1, cell_ID=17)
    with pytest.raises(TimeFlowError):
        cell_lin._add_link(6, 17)
    cell_lin.add_node(18, frame=0, cell_ID=18)
    with pytest.raises(TimeFlowError):
        cell_lin._add_link(1, 18)


def test_add_link_different_lineages(cell_lin):
    # Add a link between different lineages.
    new_lin = CellLineage(lid=2)
    new_lin.add_node(19, frame=1, cell_ID=19)
    new_lin.add_node(20, frame=2, cell_ID=20)
    new_lin.add_node(21, frame=3, cell_ID=21)
    new_lin.add_edges_from([(19, 20), (20, 21)])
    cell_lin._add_link(1, 19, target_lineage=new_lin)
    assert cell_lin.has_node(19)
    assert cell_lin.nodes[19]["cell_ID"] == 19
    assert cell_lin.nodes[19]["frame"] == 1
    assert cell_lin.has_edge(1, 19)
    assert cell_lin.has_node(20)
    assert cell_lin.has_node(21)
    assert len(new_lin.nodes) == 0


def test_add_link_different_lineages_unconnected_node(cell_lin, cell_lin_unconnected_node):
    # Add a link between a lineage and an unconnected node of another lineage.
    cell_lin._add_link(1, 17, target_lineage=cell_lin_unconnected_node)
    assert cell_lin.has_node(17)
    assert cell_lin.has_edge(1, 17)
    assert cell_lin.nodes[17]["cell_ID"] == 17
    assert cell_lin.nodes[17]["frame"] == 1
    assert not cell_lin_unconnected_node.has_node(17)


def test_add_link_different_lineages_unconnected_component(
    cell_lin, cell_lin_unconnected_component
):
    # Add a link between a lineage and an unconnected component of another lineage.
    cell_lin._add_link(1, 17, target_lineage=cell_lin_unconnected_component)
    assert cell_lin.has_node(17)
    assert cell_lin.has_node(18)
    assert cell_lin.has_edge(1, 17)
    assert cell_lin.has_edge(17, 18)
    assert cell_lin.nodes[17]["cell_ID"] == 17
    assert cell_lin.nodes[17]["frame"] == 1
    assert cell_lin.nodes[18]["cell_ID"] == 18
    assert cell_lin.nodes[18]["frame"] == 2
    assert not cell_lin_unconnected_component.has_node(17)
    assert not cell_lin_unconnected_component.has_node(18)


def test_add_link_conflicting_ID(cell_lin):
    # Add a link between different lineages with a conflicting ID.
    new_lin = CellLineage(lid=2)
    new_lin.add_node(5, frame=1, cell_ID=5)
    IDs_mapping = cell_lin._add_link(1, 5, target_lineage=new_lin)
    assert IDs_mapping == {5: 17}
    # Cell 5 is removed from the target lineage.
    assert not new_lin.has_node(5)
    assert not new_lin.has_node(17)
    # Cell 17 is added with the new edge.
    assert cell_lin.has_node(17)
    assert cell_lin.has_edge(1, 17)
    assert cell_lin.nodes[17]["cell_ID"] == 17
    assert cell_lin.nodes[17]["frame"] == 1
    # Cell 5 is untouched.
    assert cell_lin.has_node(5)
    assert cell_lin.nodes[5]["cell_ID"] == 5
    assert cell_lin.nodes[5]["frame"] == 4


def test_add_link_conflicting_IDs(cell_lin, cell_lin_successive_divs_and_root):
    IDs_mapping = cell_lin._add_link(1, 2, cell_lin_successive_divs_and_root)
    assert IDs_mapping == {
        2: 17,
        3: 18,
        4: 19,
        5: 20,
        6: 21,
        7: 22,
        8: 23,
        9: 24,
        10: 25,
        11: 26,
    }
    # Cells are removed from the target lineage.
    assert len(cell_lin_successive_divs_and_root.nodes) == 0
    # Cells are added with the new edges.
    assert cell_lin.has_edge(1, 17)
    assert cell_lin.nodes[17]["cell_ID"] == 17
    assert cell_lin.nodes[17]["frame"] == 1
    assert cell_lin.has_edge(17, 18)
    assert cell_lin.nodes[18]["cell_ID"] == 18
    assert cell_lin.nodes[18]["frame"] == 2
    # Cells are untouched.
    assert cell_lin.has_node(2)
    assert cell_lin.nodes[2]["cell_ID"] == 2
    assert cell_lin.nodes[2]["frame"] == 1


def test_add_link_same_IDs(cell_lin):
    new_lin = CellLineage(lid=2)
    new_lin.add_node(1, frame=1, cell_ID=1)
    IDs_mapping = cell_lin._add_link(1, 1, new_lin)
    assert IDs_mapping == {1: 17}
    # Cell 1 is removed from the target lineage.
    assert not new_lin.has_node(1)
    assert not new_lin.has_node(17)
    # Cell 17 is added with the new edge.
    assert cell_lin.has_node(17)
    assert cell_lin.has_edge(1, 17)
    assert cell_lin.nodes[17]["cell_ID"] == 17
    assert cell_lin.nodes[17]["frame"] == 1
    # Cell 1 is untouched.
    assert cell_lin.has_node(1)
    assert cell_lin.nodes[1]["cell_ID"] == 1
    assert cell_lin.nodes[1]["frame"] == 0


# _remove_link() ##############################################################


def check_correct_link_removal(cell_lin, source_nid, target_nid):
    link_feats = cell_lin[source_nid][target_nid]
    assert cell_lin._remove_link(source_nid, target_nid) == link_feats
    assert not cell_lin.has_edge(source_nid, target_nid)


def test_remove_link_normal_lin(cell_lin):
    # Remove a valid link with root.
    check_correct_link_removal(cell_lin, 1, 2)
    # Remove a valid link with division.
    check_correct_link_removal(cell_lin, 4, 5)
    # Remove a valid link with leaf.
    check_correct_link_removal(cell_lin, 8, 9)
    # Remove a valid link with intermediate node.
    check_correct_link_removal(cell_lin, 12, 13)


def test_remove_link_nonexistent_source(cell_lin):
    # Remove a link with a nonexistent source.
    with pytest.raises(ValueError):
        cell_lin._remove_link(99, 2)


def test_remove_link_nonexistent_target(cell_lin):
    # Remove a link with a nonexistent target.
    with pytest.raises(ValueError):
        cell_lin._remove_link(1, 99)


def test_remove_link_nonexistent_link(cell_lin):
    # Remove a nonexistent link.
    with pytest.raises(KeyError):
        cell_lin._remove_link(1, 3)


def test_remove_link_empty_lin(empty_cell_lin):
    # Remove a link from an empty lineage.
    with pytest.raises(ValueError):
        empty_cell_lin._remove_link(0, 1)


def test_remove_link_single_node(one_node_cell_lin):
    # Remove a link from a single node lineage.
    with pytest.raises(ValueError):
        one_node_cell_lin._remove_link(1, 2)


def test_remove_link_gap(cell_lin_gap):
    # Remove a valid link in a lineage with gaps.
    check_correct_link_removal(cell_lin_gap, 1, 2)
    check_correct_link_removal(cell_lin_gap, 4, 6)
    check_correct_link_removal(cell_lin_gap, 8, 9)
    check_correct_link_removal(cell_lin_gap, 11, 14)


def test_remove_link_div_root(cell_lin_div_root):
    # Remove a valid link in a lineage with a division root.
    check_correct_link_removal(cell_lin_div_root, 1, 17)


def test_remove_link_unconnected_component(cell_lin_unconnected_component):
    # Remove a valid link in a lineage with an unconnected component.
    check_correct_link_removal(cell_lin_unconnected_component, 17, 18)


def test_remove_link_unconnected_component_div(cell_lin_unconnected_component_div):
    # Remove a valid link in a lineage with an unconnected component and division.
    check_correct_link_removal(cell_lin_unconnected_component_div, 17, 18)
    check_correct_link_removal(cell_lin_unconnected_component_div, 19, 20)
    check_correct_link_removal(cell_lin_unconnected_component_div, 19, 22)


# _split_from_cell() ##########################################################


def test_split_from_cell_division_upstream(cell_lin):
    # Split upstream from a division node.
    new_lin = cell_lin._split_from_cell(4, split="upstream")
    assert sorted(new_lin.nodes()) == [4, 5, 6, 7, 8, 9, 10]
    assert sorted(cell_lin.nodes()) == [1, 2, 3, 11, 12, 13, 14, 15, 16]


def test_split_from_cell_division_downstream(cell_lin):
    # Split downstream from a division node.
    new_lin = cell_lin._split_from_cell(4, split="downstream")
    assert sorted(new_lin.nodes()) == [5, 6, 7, 8, 9, 10]
    assert sorted(cell_lin.nodes()) == [1, 2, 3, 4, 11, 12, 13, 14, 15, 16]


def test_split_from_cell_root_upstream(cell_lin):
    # Split upstream from a root node.
    new_lin = cell_lin._split_from_cell(1, split="upstream")
    assert sorted(new_lin.nodes()) == list(range(1, 17))
    assert sorted(cell_lin.nodes()) == []


def test_split_from_cell_root_downstream(cell_lin):
    # Split downstream from a root node.
    new_lin = cell_lin._split_from_cell(1, split="downstream")
    assert sorted(new_lin.nodes()) == list(range(2, 17))
    assert sorted(cell_lin.nodes()) == [1]


def test_split_from_cell_leaf_upstream(cell_lin):
    # Split upstream from a leaf node.
    new_lin = cell_lin._split_from_cell(9, split="upstream")
    assert sorted(new_lin.nodes()) == [9]
    assert sorted(cell_lin.nodes()) == list(range(1, 9)) + list(range(10, 17))


def test_split_from_cell_leaf_downstream(cell_lin):
    # Split downstream from a leaf node.
    new_lin = cell_lin._split_from_cell(9, split="downstream")
    assert sorted(new_lin.nodes()) == []
    assert sorted(cell_lin.nodes()) == list(range(1, 17))


def test_split_from_cell_middle_upstream(cell_lin):
    # Split upstream from a middle node.
    new_lin = cell_lin._split_from_cell(12, split="upstream")
    assert sorted(new_lin.nodes()) == list(range(12, 17))
    assert sorted(cell_lin.nodes()) == list(range(1, 12))


def test_split_from_cell_middle_downstream(cell_lin):
    # Split downstream from a middle node.
    new_lin = cell_lin._split_from_cell(12, split="downstream")
    assert sorted(new_lin.nodes()) == list(range(13, 17))
    assert sorted(cell_lin.nodes()) == list(range(1, 13))


def test_split_from_cell_upstream_single_node(one_node_cell_lin):
    # Split upstream from a single node.
    new_lin = one_node_cell_lin._split_from_cell(1, split="upstream")
    assert sorted(new_lin.nodes()) == [1]
    assert sorted(one_node_cell_lin.nodes()) == []


def test_split_from_cell_downstream_single_node(one_node_cell_lin):
    # Split downstream from a single node.
    new_lin = one_node_cell_lin._split_from_cell(1, split="downstream")
    assert sorted(new_lin.nodes()) == []
    assert sorted(one_node_cell_lin.nodes()) == [1]


def test_split_from_cell_upstream_gap(cell_lin_gap):
    # Split upstream from a node in a lineage with gaps.
    new_lin = cell_lin_gap._split_from_cell(4, split="upstream")
    assert sorted(new_lin.nodes()) == [4, 6, 8, 9, 10]
    assert sorted(cell_lin_gap.nodes()) == [1, 2, 3, 11, 14, 15, 16]


def test_split_from_cell_downstream_gap(cell_lin_gap):
    # Split downstream from a node in a lineage with gaps.
    new_lin = cell_lin_gap._split_from_cell(4, split="downstream")
    assert sorted(new_lin.nodes()) == [6, 8, 9, 10]
    assert new_lin.in_degree(6) == 0
    assert sorted(cell_lin_gap.nodes()) == [1, 2, 3, 4, 11, 14, 15, 16]


def test_split_from_cell_upstream_div_root(cell_lin_div_root):
    # Split upstream from a node in a lineage with a division root.
    new_lin = cell_lin_div_root._split_from_cell(1, split="upstream")
    assert sorted(new_lin.nodes()) == list(range(1, 18))
    assert sorted(cell_lin_div_root.nodes()) == []


def test_split_from_cell_downstream_div_root(cell_lin_div_root):
    # Split downstream from a node in a lineage with a division root.
    new_lin = cell_lin_div_root._split_from_cell(1, split="downstream")
    assert sorted(new_lin.nodes()) == list(range(2, 18))
    assert sorted(cell_lin_div_root.nodes()) == [1]


def test_split_from_cell_upstream_unconnected_node(cell_lin_unconnected_node):
    # Split upstream from an unconnected node.
    new_lin = cell_lin_unconnected_node._split_from_cell(17, split="upstream")
    assert sorted(new_lin.nodes()) == [17]
    assert sorted(cell_lin_unconnected_node.nodes()) == list(range(1, 17))


def test_split_from_cell_downstream_unconnected_node(cell_lin_unconnected_node):
    # Split downstream from an unconnected node.
    new_lin = cell_lin_unconnected_node._split_from_cell(17, split="downstream")
    assert sorted(new_lin.nodes()) == []
    assert sorted(cell_lin_unconnected_node.nodes()) == list(range(1, 18))


def test_split_from_cell_upstream_unconnected_component(cell_lin_unconnected_component):
    # Split upstream from a node in an unconnected component.
    new_lin = cell_lin_unconnected_component._split_from_cell(17, split="upstream")
    assert sorted(new_lin.nodes()) == [17, 18]
    assert sorted(cell_lin_unconnected_component.nodes()) == list(range(1, 17))


def test_split_from_cell_downstream_unconnected_component(
    cell_lin_unconnected_component,
):
    # Split downstream from a node in an unconnected component.
    new_lin = cell_lin_unconnected_component._split_from_cell(17, split="downstream")
    assert sorted(new_lin.nodes()) == [18]
    assert sorted(cell_lin_unconnected_component.nodes()) == list(range(1, 18))


def test_split_from_cell_invalid_node(cell_lin):
    # Split from an invalid node.
    with pytest.raises(ValueError):
        cell_lin._split_from_cell(99)


def test_split_from_cell_invalid_split(cell_lin):
    # Split with an invalid split parameter.
    with pytest.raises(ValueError):
        cell_lin._split_from_cell(4, split="invalid")


# get_divisions() #############################################################


def test_get_divisions_normal_lin(cell_lin):
    assert sorted(cell_lin.get_divisions()) == [2, 4, 8, 14]
    assert sorted(cell_lin.get_divisions(list(range(1, 17)))) == [2, 4, 8, 14]
    assert sorted(cell_lin.get_divisions([1, 2, 3, 4])) == [2, 4]
    assert sorted(cell_lin.get_divisions([4])) == [4]
    assert sorted(cell_lin.get_divisions([1, 3, 11, 12, 13, 15, 16])) == []


def test_get_divisions_empty_lin(empty_cell_lin):
    assert empty_cell_lin.get_divisions() == []


def test_get_divisions_single_node(one_node_cell_lin):
    assert one_node_cell_lin.get_divisions() == []
    assert one_node_cell_lin.get_divisions([1]) == []


def test_get_divisions_gap(cell_lin_gap):
    assert sorted(cell_lin_gap.get_divisions()) == [2, 4, 8, 14]
    assert sorted(cell_lin_gap.get_divisions([1, 2, 3, 4, 6, 8, 9, 10])) == [2, 4, 8]
    assert sorted(cell_lin_gap.get_divisions([1, 2, 3, 4])) == [2, 4]
    assert sorted(cell_lin_gap.get_divisions([4])) == [4]
    assert sorted(cell_lin_gap.get_divisions([1, 3, 11, 15, 16])) == []


def test_get_divisions_div_root(cell_lin_div_root):
    lin = cell_lin_div_root
    assert sorted(lin.get_divisions()) == [1, 2, 4, 8, 14]
    assert sorted(lin.get_divisions([1, 2, 3, 4, 6, 8, 9, 10])) == [1, 2, 4, 8]
    assert sorted(lin.get_divisions([1])) == [1]
    assert sorted(lin.get_divisions([3, 5, 7, 9])) == []


def test_get_divisions_successive_divs_and_root(cell_lin_successive_divs_and_root):
    lin = cell_lin_successive_divs_and_root
    assert sorted(lin.get_divisions()) == [2, 3, 5, 8]
    assert sorted(lin.get_divisions(list(range(2, 12)))) == [2, 3, 5, 8]
    assert sorted(lin.get_divisions([2, 3, 4, 5, 6, 7])) == [2, 3, 5]
    assert sorted(lin.get_divisions([3])) == [3]
    assert sorted(lin.get_divisions([4, 6, 7, 11])) == []


def test_get_divisions_triple_div(cell_lin_triple_div):
    assert sorted(cell_lin_triple_div.get_divisions()) == [2, 4, 8, 14]
    assert sorted(cell_lin_triple_div.get_divisions([1, 2, 3, 4, 5, 6])) == [2, 4]
    assert sorted(cell_lin_triple_div.get_divisions([4])) == [4]
    assert sorted(cell_lin_triple_div.get_divisions([17, 18])) == []


def test_get_divisions_unconnected_node(cell_lin_unconnected_node):
    lin = cell_lin_unconnected_node
    assert sorted(lin.get_divisions()) == [2, 4, 8, 14]
    assert sorted(lin.get_divisions(list(range(1, 18)))) == [2, 4, 8, 14]
    assert sorted(lin.get_divisions([1, 2, 3, 4, 17])) == [2, 4]
    assert sorted(lin.get_divisions([17])) == []


def test_get_divisions_unconnected_component(cell_lin_unconnected_component):
    lin = cell_lin_unconnected_component
    assert sorted(lin.get_divisions()) == [2, 4, 8, 14]
    assert sorted(lin.get_divisions(list(range(1, 18)))) == [2, 4, 8, 14]
    assert sorted(lin.get_divisions([1, 2, 3, 4, 17, 18])) == [2, 4]
    assert sorted(lin.get_divisions([17])) == []


def test_get_divisions_unconnected_component_div(cell_lin_unconnected_component_div):
    lin = cell_lin_unconnected_component_div
    assert sorted(lin.get_divisions()) == [2, 4, 8, 14, 17, 19]
    assert sorted(lin.get_divisions(list(range(1, 23)))) == [2, 4, 8, 14, 17, 19]
    assert sorted(lin.get_divisions([1, 2, 3, 4, 17, 18, 19, 20])) == [2, 4, 17, 19]
    assert sorted(lin.get_divisions([17])) == [17]
    assert sorted(lin.get_divisions([19])) == [19]
    assert sorted(lin.get_divisions([20, 21, 22])) == []


# get_cell_cycle() ############################################################


def test_get_cell_cycle_normal_lin(cell_lin):
    # From root.
    assert cell_lin.get_cell_cycle(1) == [1, 2]
    # From division.
    assert cell_lin.get_cell_cycle(2) == [1, 2]
    assert cell_lin.get_cell_cycle(4) == [3, 4]
    assert cell_lin.get_cell_cycle(8) == [7, 8]
    assert cell_lin.get_cell_cycle(14) == [11, 12, 13, 14]
    # From leaf.
    assert cell_lin.get_cell_cycle(6) == [5, 6]
    assert cell_lin.get_cell_cycle(9) == [9]
    assert cell_lin.get_cell_cycle(16) == [16]
    # From intermediate node.
    assert cell_lin.get_cell_cycle(3) == [3, 4]
    assert cell_lin.get_cell_cycle(5) == [5, 6]
    assert cell_lin.get_cell_cycle(7) == [7, 8]
    assert cell_lin.get_cell_cycle(11) == [11, 12, 13, 14]
    assert cell_lin.get_cell_cycle(12) == [11, 12, 13, 14]
    assert cell_lin.get_cell_cycle(13) == [11, 12, 13, 14]


def test_get_cell_cycle_single_node(one_node_cell_lin):
    assert one_node_cell_lin.get_cell_cycle(1) == [1]


def test_get_cell_cycle_gap(cell_lin_gap):
    # From root.
    assert cell_lin_gap.get_cell_cycle(1) == [1, 2]
    # From division.
    assert cell_lin_gap.get_cell_cycle(2) == [1, 2]
    assert cell_lin_gap.get_cell_cycle(4) == [3, 4]
    assert cell_lin_gap.get_cell_cycle(8) == [8]
    assert cell_lin_gap.get_cell_cycle(14) == [11, 14]
    # From leaf.
    assert cell_lin_gap.get_cell_cycle(6) == [6]
    assert cell_lin_gap.get_cell_cycle(9) == [9]
    assert cell_lin_gap.get_cell_cycle(16) == [16]
    # From intermediate node.
    assert cell_lin_gap.get_cell_cycle(3) == [3, 4]
    assert cell_lin_gap.get_cell_cycle(11) == [11, 14]


def test_get_cell_cycle_div_root(cell_lin_div_root):
    assert cell_lin_div_root.get_cell_cycle(1) == [1]
    assert cell_lin_div_root.get_cell_cycle(2) == [2]
    assert cell_lin_div_root.get_cell_cycle(17) == [17]


def test_get_cell_cycle_successive_divs_and_root(cell_lin_successive_divs_and_root):
    assert cell_lin_successive_divs_and_root.get_cell_cycle(2) == [2]
    assert cell_lin_successive_divs_and_root.get_cell_cycle(3) == [3]
    assert cell_lin_successive_divs_and_root.get_cell_cycle(4) == [4, 5]
    assert cell_lin_successive_divs_and_root.get_cell_cycle(5) == [4, 5]
    assert cell_lin_successive_divs_and_root.get_cell_cycle(6) == [6]
    assert cell_lin_successive_divs_and_root.get_cell_cycle(8) == [8]
    assert cell_lin_successive_divs_and_root.get_cell_cycle(9) == [9]
    assert cell_lin_successive_divs_and_root.get_cell_cycle(11) == [11]


def test_get_cell_cycle_triple_div(cell_lin_triple_div):
    assert cell_lin_triple_div.get_cell_cycle(1) == [1, 2]
    assert cell_lin_triple_div.get_cell_cycle(4) == [3, 4]
    assert cell_lin_triple_div.get_cell_cycle(5) == [5, 6]
    assert cell_lin_triple_div.get_cell_cycle(8) == [7, 8]
    assert cell_lin_triple_div.get_cell_cycle(17) == [17, 18]
    assert cell_lin_triple_div.get_cell_cycle(18) == [17, 18]


def test_get_cell_cycle_unconnected_node(cell_lin_unconnected_node):
    assert cell_lin_unconnected_node.get_cell_cycle(17) == [17]


def test_get_cell_cycle_unconnected_component(cell_lin_unconnected_component):
    assert cell_lin_unconnected_component.get_cell_cycle(17) == [17, 18]
    assert cell_lin_unconnected_component.get_cell_cycle(18) == [17, 18]


def test_get_cell_cycle_unconnected_component_div(cell_lin_unconnected_component_div):
    assert cell_lin_unconnected_component_div.get_cell_cycle(17) == [17]
    assert cell_lin_unconnected_component_div.get_cell_cycle(18) == [18]
    assert cell_lin_unconnected_component_div.get_cell_cycle(19) == [19]
    assert cell_lin_unconnected_component_div.get_cell_cycle(20) == [20, 21]
    assert cell_lin_unconnected_component_div.get_cell_cycle(21) == [20, 21]
    assert cell_lin_unconnected_component_div.get_cell_cycle(22) == [22]


def test_get_cell_cycle_fusion_error(cell_lin):
    cell_lin.add_edge(3, 12)
    with pytest.raises(FusionError):
        cell_lin.get_cell_cycle(12)


# get_cell_cycles() ###########################################################


def test_get_cell_cycles_normal_lin(cell_lin):
    expected = [
        [1, 2],
        [3, 4],
        [5, 6],
        [7, 8],
        [9],
        [10],
        [11, 12, 13, 14],
        [15],
        [16],
    ]
    assert sorted(cell_lin.get_cell_cycles()) == expected
    # Remove incomplete cycles.
    incomplete = [[1, 2], [5, 6], [9], [10], [15], [16]]
    expected = [cycle for cycle in expected if cycle not in incomplete]
    assert cell_lin.get_cell_cycles(ignore_incomplete_cycles=True) == expected


def test_get_cell_cycles_empty_lin(empty_cell_lin):
    assert empty_cell_lin.get_cell_cycles() == []
    assert empty_cell_lin.get_cell_cycles(ignore_incomplete_cycles=True) == []


def test_get_cell_cycles_single_node(one_node_cell_lin):
    assert one_node_cell_lin.get_cell_cycles() == [[1]]
    assert one_node_cell_lin.get_cell_cycles(ignore_incomplete_cycles=True) == []


def test_get_cell_cycles_gap(cell_lin_gap):
    expected = [
        [1, 2],
        [3, 4],
        [6],
        [8],
        [9],
        [10],
        [11, 14],
        [15],
        [16],
    ]
    assert sorted(cell_lin_gap.get_cell_cycles()) == expected
    # Remove incomplete cycles.
    incomplete = [[1, 2], [6], [9], [10], [15], [16]]
    expected = [cycle for cycle in expected if cycle not in incomplete]
    assert cell_lin_gap.get_cell_cycles(ignore_incomplete_cycles=True) == expected


def test_get_cell_cycles_div_root(cell_lin_div_root):
    expected = [
        [1],
        [2],
        [3, 4],
        [5, 6],
        [7, 8],
        [9],
        [10],
        [11, 12, 13, 14],
        [15],
        [16],
        [17],
    ]
    assert sorted(cell_lin_div_root.get_cell_cycles()) == expected
    # Remove incomplete cycles.
    incomplete = [[1], [5, 6], [9], [10], [15], [16], [17]]
    expected = [cycle for cycle in expected if cycle not in incomplete]
    assert cell_lin_div_root.get_cell_cycles(ignore_incomplete_cycles=True) == expected


def test_get_cell_cycles_successive_divs_and_root(cell_lin_successive_divs_and_root):
    lin = cell_lin_successive_divs_and_root
    expected = [
        [2],
        [3],
        [4, 5],
        [6],
        [7],
        [8],
        [9],
        [10],
        [11],
    ]
    assert sorted(lin.get_cell_cycles()) == expected
    # Remove incomplete cycles.
    incomplete = [[2], [6], [7], [9], [10], [11]]
    expected = [cycle for cycle in expected if cycle not in incomplete]
    assert lin.get_cell_cycles(ignore_incomplete_cycles=True) == expected


def test_get_cell_cycles_triple_div(cell_lin_triple_div):
    lin = cell_lin_triple_div
    expected = [
        [1, 2],
        [3, 4],
        [5, 6],
        [7, 8],
        [9],
        [10],
        [11, 12, 13, 14],
        [15],
        [16],
        [17, 18],
    ]
    assert sorted(lin.get_cell_cycles()) == expected
    # Remove incomplete cycles.
    incomplete = [[1, 2], [5, 6], [9], [10], [15], [16], [17, 18]]
    expected = [cycle for cycle in expected if cycle not in incomplete]
    assert lin.get_cell_cycles(ignore_incomplete_cycles=True) == expected


def test_get_cell_cycles_unconnected_node(cell_lin_unconnected_node):
    lin = cell_lin_unconnected_node
    expected = [
        [1, 2],
        [3, 4],
        [5, 6],
        [7, 8],
        [9],
        [10],
        [11, 12, 13, 14],
        [15],
        [16],
        [17],
    ]
    assert sorted(lin.get_cell_cycles()) == expected
    # Remove incomplete cycles.
    incomplete = [[1, 2], [5, 6], [9], [10], [15], [16], [17]]
    expected = [cycle for cycle in expected if cycle not in incomplete]
    assert len(lin.get_cell_cycles(ignore_incomplete_cycles=True)) == len(expected)
    # assert lin.get_cell_cycles(ignore_incomplete_cycles=True) == expected


def test_get_cell_cycles_unconnected_component(cell_lin_unconnected_component):
    lin = cell_lin_unconnected_component
    expected = [
        [1, 2],
        [3, 4],
        [5, 6],
        [7, 8],
        [9],
        [10],
        [11, 12, 13, 14],
        [15],
        [16],
        [17, 18],
    ]
    assert sorted(lin.get_cell_cycles()) == expected
    # Remove incomplete cycles.
    incomplete = [[1, 2], [5, 6], [9], [10], [15], [16], [17, 18]]
    expected = [cycle for cycle in expected if cycle not in incomplete]
    assert lin.get_cell_cycles(ignore_incomplete_cycles=True) == expected


def test_get_cell_cycles_unconnected_component_div(cell_lin_unconnected_component_div):
    lin = cell_lin_unconnected_component_div
    expected = [
        [1, 2],
        [3, 4],
        [5, 6],
        [7, 8],
        [9],
        [10],
        [11, 12, 13, 14],
        [15],
        [16],
        [17],
        [18],
        [19],
        [20, 21],
        [22],
    ]
    assert sorted(lin.get_cell_cycles()) == expected
    # Remove incomplete cycles.
    incomplete = [[1, 2], [5, 6], [9], [10], [15], [16], [17], [18], [20, 21], [22]]
    expected = [cycle for cycle in expected if cycle not in incomplete]
    assert lin.get_cell_cycles(ignore_incomplete_cycles=True) == expected


def test_get_cell_cycles_fusion_error(cell_lin):
    cell_lin.add_edge(3, 12)
    with pytest.raises(FusionError):
        cell_lin.get_cell_cycles()


# get_sister_cells() ##########################################################


def test_get_sister_cells_normal_lin(cell_lin):
    # Root.
    assert cell_lin.get_sister_cells(1) == []
    # Divisions.
    assert cell_lin.get_sister_cells(2) == []
    assert cell_lin.get_sister_cells(4) == [12]
    assert cell_lin.get_sister_cells(8) == [6]
    assert cell_lin.get_sister_cells(14) == []
    # Just after division.
    assert cell_lin.get_sister_cells(3) == [11]
    assert cell_lin.get_sister_cells(5) == [7]
    assert cell_lin.get_sister_cells(12) == [4]
    assert cell_lin.get_sister_cells(13) == []
    # Leaves.
    assert cell_lin.get_sister_cells(6) == [8]
    assert cell_lin.get_sister_cells(9) == [10]
    assert cell_lin.get_sister_cells(10) == [9]
    assert cell_lin.get_sister_cells(15) == [16]


def test_get_sister_cells_single_node(one_node_cell_lin):
    assert one_node_cell_lin.get_sister_cells(1) == []


def test_get_sister_cells_gap(cell_lin_gap):
    # Root.
    assert cell_lin_gap.get_sister_cells(1) == []
    # Divisions.
    assert cell_lin_gap.get_sister_cells(2) == []
    assert cell_lin_gap.get_sister_cells(4) == []
    assert cell_lin_gap.get_sister_cells(8) == [6]
    assert cell_lin_gap.get_sister_cells(14) == []
    # Just after division.
    assert cell_lin_gap.get_sister_cells(3) == [11]
    # Leaves.
    assert cell_lin_gap.get_sister_cells(6) == [8]
    assert cell_lin_gap.get_sister_cells(9) == [10]
    assert cell_lin_gap.get_sister_cells(10) == [9]
    assert cell_lin_gap.get_sister_cells(15) == [16]


def test_get_sister_cells_div_root(cell_lin_div_root):
    assert cell_lin_div_root.get_sister_cells(1) == []
    assert cell_lin_div_root.get_sister_cells(2) == [17]
    assert cell_lin_div_root.get_sister_cells(17) == [2]


def test_get_sister_cells_successive_divs_and_root(cell_lin_successive_divs_and_root):
    assert cell_lin_successive_divs_and_root.get_sister_cells(2) == []
    assert cell_lin_successive_divs_and_root.get_sister_cells(3) == [11]
    assert cell_lin_successive_divs_and_root.get_sister_cells(4) == [8]
    assert cell_lin_successive_divs_and_root.get_sister_cells(5) == []
    assert cell_lin_successive_divs_and_root.get_sister_cells(6) == [7]
    assert cell_lin_successive_divs_and_root.get_sister_cells(7) == [6]
    assert cell_lin_successive_divs_and_root.get_sister_cells(8) == [4]
    assert cell_lin_successive_divs_and_root.get_sister_cells(9) == [10]
    assert cell_lin_successive_divs_and_root.get_sister_cells(10) == [9]
    assert cell_lin_successive_divs_and_root.get_sister_cells(11) == [3]


def test_get_sister_cells_triple_div(cell_lin_triple_div):
    assert cell_lin_triple_div.get_sister_cells(1) == []
    assert cell_lin_triple_div.get_sister_cells(2) == []
    assert cell_lin_triple_div.get_sister_cells(4) == [12]
    assert cell_lin_triple_div.get_sister_cells(5) == [7, 17]
    assert cell_lin_triple_div.get_sister_cells(6) == [8, 18]
    assert cell_lin_triple_div.get_sister_cells(7) == [5, 17]
    assert cell_lin_triple_div.get_sister_cells(8) == [6, 18]
    assert cell_lin_triple_div.get_sister_cells(13) == []
    assert cell_lin_triple_div.get_sister_cells(14) == []


def test_get_sister_cells_unconnected_node(cell_lin_unconnected_node):
    assert cell_lin_unconnected_node.get_sister_cells(1) == []
    assert cell_lin_unconnected_node.get_sister_cells(17) == []


def test_get_sister_cells_unconnected_component(cell_lin_unconnected_component):
    assert cell_lin_unconnected_component.get_sister_cells(1) == []
    assert cell_lin_unconnected_component.get_sister_cells(2) == []
    assert cell_lin_unconnected_component.get_sister_cells(17) == []
    assert cell_lin_unconnected_component.get_sister_cells(18) == []


def test_get_sister_cells_unconnected_component_div(cell_lin_unconnected_component_div):
    assert cell_lin_unconnected_component_div.get_sister_cells(1) == []
    assert cell_lin_unconnected_component_div.get_sister_cells(2) == []
    assert cell_lin_unconnected_component_div.get_sister_cells(17) == []
    assert cell_lin_unconnected_component_div.get_sister_cells(18) == [19]
    assert cell_lin_unconnected_component_div.get_sister_cells(19) == [18]
    assert cell_lin_unconnected_component_div.get_sister_cells(20) == [22]
    assert cell_lin_unconnected_component_div.get_sister_cells(22) == [20]
    assert cell_lin_unconnected_component_div.get_sister_cells(21) == []


def test_get_sister_cells_fusion_error(cell_lin):
    cell_lin.add_edge(3, 12)
    with pytest.raises(FusionError):
        cell_lin.get_sister_cells(12)


# is_division() ###############################################################


def test_is_division_normal_lin(cell_lin):
    # Root.
    assert not cell_lin.is_division(1)
    # Divisions.
    assert cell_lin.is_division(2)
    assert cell_lin.is_division(4)
    assert cell_lin.is_division(8)
    assert cell_lin.is_division(14)
    # Leaves.
    assert not cell_lin.is_division(6)
    assert not cell_lin.is_division(9)
    assert not cell_lin.is_division(10)
    assert not cell_lin.is_division(15)
    assert not cell_lin.is_division(16)
    # Intermediate nodes.
    assert not cell_lin.is_division(3)
    assert not cell_lin.is_division(5)
    assert not cell_lin.is_division(7)
    assert not cell_lin.is_division(11)
    assert not cell_lin.is_division(12)
    assert not cell_lin.is_division(13)


def test_is_division_single_node(one_node_cell_lin):
    assert not one_node_cell_lin.is_division(1)


def test_is_division_gap(cell_lin_gap):
    # Root.
    assert not cell_lin_gap.is_division(1)
    # Divisions.
    assert cell_lin_gap.is_division(2)
    assert cell_lin_gap.is_division(4)
    assert cell_lin_gap.is_division(8)
    assert cell_lin_gap.is_division(14)
    # Leaves.
    assert not cell_lin_gap.is_division(6)
    assert not cell_lin_gap.is_division(10)
    assert not cell_lin_gap.is_division(16)
    # Intermediate nodes.
    assert not cell_lin_gap.is_division(3)
    assert not cell_lin_gap.is_division(11)


def test_is_division_div_root(cell_lin_div_root):
    # Root.
    assert cell_lin_div_root.is_division(1)
    # Divisions.
    assert cell_lin_div_root.is_division(2)
    assert cell_lin_div_root.is_division(4)
    assert cell_lin_div_root.is_division(8)
    assert cell_lin_div_root.is_division(14)
    # Leaves.
    assert not cell_lin_div_root.is_division(6)
    assert not cell_lin_div_root.is_division(9)
    assert not cell_lin_div_root.is_division(15)
    assert not cell_lin_div_root.is_division(17)
    # Intermediate nodes.
    assert not cell_lin_div_root.is_division(3)
    assert not cell_lin_div_root.is_division(7)


def test_is_division_successive_divs_and_root(cell_lin_successive_divs_and_root):
    # Root.
    assert cell_lin_successive_divs_and_root.is_division(2)
    # Divisions.
    assert cell_lin_successive_divs_and_root.is_division(3)
    assert cell_lin_successive_divs_and_root.is_division(5)
    assert cell_lin_successive_divs_and_root.is_division(8)
    # Leaves.
    assert not cell_lin_successive_divs_and_root.is_division(6)
    assert not cell_lin_successive_divs_and_root.is_division(9)
    assert not cell_lin_successive_divs_and_root.is_division(11)
    # Intermediate nodes.
    assert not cell_lin_successive_divs_and_root.is_division(4)


def test_is_division_unconnected_node(cell_lin_unconnected_node):
    assert not cell_lin_unconnected_node.is_division(17)


def test_is_division_unconnected_component(cell_lin_unconnected_component):
    assert not cell_lin_unconnected_component.is_division(17)
    assert not cell_lin_unconnected_component.is_division(18)


def test_is_division_unconnected_component_div(cell_lin_unconnected_component_div):
    assert cell_lin_unconnected_component_div.is_division(17)
    assert cell_lin_unconnected_component_div.is_division(19)
    assert not cell_lin_unconnected_component_div.is_division(20)
    assert not cell_lin_unconnected_component_div.is_division(21)
    assert not cell_lin_unconnected_component_div.is_division(22)


# CycleLineage __init__() #####################################################


def test_cycle_lineage_normal_lin(cell_lin):
    cycle_lin = CycleLineage(cell_lin)
    assert sorted(list(cycle_lin.nodes())) == [2, 4, 6, 8, 9, 10, 14, 15, 16]
    assert cycle_lin.graph["lineage_ID"] == 1
    assert cycle_lin.nodes[2]["cycle_ID"] == 2
    assert cycle_lin.nodes[2]["cells"] == [1, 2]
    assert cycle_lin.nodes[2]["cycle_length"] == 2
    assert cycle_lin.nodes[2]["level"] == 0
    assert cycle_lin.nodes[9]["cycle_ID"] == 9
    assert cycle_lin.nodes[9]["cells"] == [9]
    assert cycle_lin.nodes[9]["cycle_length"] == 1
    assert cycle_lin.nodes[9]["level"] == 3
    assert cycle_lin.nodes[14]["cycle_ID"] == 14
    assert cycle_lin.nodes[14]["cells"] == [11, 12, 13, 14]
    assert cycle_lin.nodes[14]["cycle_length"] == 4
    assert cycle_lin.nodes[14]["level"] == 1


def test_cycle_lineage_empty_lin(empty_cell_lin):
    cycle_lin = CycleLineage(empty_cell_lin)
    assert len(cycle_lin) == 0
    assert cycle_lin.graph["lineage_ID"] == 1


def test_cycle_lineage_single_node(one_node_cell_lin):
    cycle_lin = CycleLineage(one_node_cell_lin)
    assert len(cycle_lin) == 1
    assert cycle_lin.graph["lineage_ID"] == 1
    assert cycle_lin.nodes[1]["cycle_ID"] == 1
    assert cycle_lin.nodes[1]["cells"] == [1]
    assert cycle_lin.nodes[1]["cycle_length"] == 1
    assert cycle_lin.nodes[1]["level"] == 0


def test_cycle_lineage_gap(cell_lin_gap):
    cycle_lin = CycleLineage(cell_lin_gap)
    assert sorted(list(cycle_lin.nodes())) == [2, 4, 6, 8, 9, 10, 14, 15, 16]
    assert cycle_lin.graph["lineage_ID"] == 1
    assert cycle_lin.nodes[2]["cycle_ID"] == 2
    assert cycle_lin.nodes[2]["cells"] == [1, 2]
    assert cycle_lin.nodes[2]["cycle_length"] == 2
    assert cycle_lin.nodes[2]["level"] == 0
    assert cycle_lin.nodes[9]["cycle_ID"] == 9
    assert cycle_lin.nodes[9]["cells"] == [9]
    assert cycle_lin.nodes[9]["cycle_length"] == 1
    assert cycle_lin.nodes[9]["level"] == 3
    assert cycle_lin.nodes[14]["cycle_ID"] == 14
    assert cycle_lin.nodes[14]["cells"] == [11, 14]
    assert cycle_lin.nodes[14]["cycle_length"] == 2
    assert cycle_lin.nodes[14]["level"] == 1


def test_cycle_lineage_div_root(cell_lin_div_root):
    cycle_lin = CycleLineage(cell_lin_div_root)
    assert sorted(list(cycle_lin.nodes())) == [1, 2, 4, 6, 8, 9, 10, 14, 15, 16, 17]
    assert cycle_lin.graph["lineage_ID"] == 1
    assert cycle_lin.nodes[1]["cycle_ID"] == 1
    assert cycle_lin.nodes[1]["cells"] == [1]
    assert cycle_lin.nodes[1]["cycle_length"] == 1
    assert cycle_lin.nodes[1]["level"] == 0
    assert cycle_lin.nodes[17]["cycle_ID"] == 17
    assert cycle_lin.nodes[17]["cells"] == [17]
    assert cycle_lin.nodes[17]["cycle_length"] == 1
    assert cycle_lin.nodes[17]["level"] == 1


def test_cycle_lineage_successive_divs_and_root(cell_lin_successive_divs_and_root):
    cycle_lin = CycleLineage(cell_lin_successive_divs_and_root)
    assert sorted(list(cycle_lin.nodes())) == [2, 3, 5, 6, 7, 8, 9, 10, 11]
    assert cycle_lin.graph["lineage_ID"] == 2
    assert cycle_lin.nodes[3]["cycle_ID"] == 3
    assert cycle_lin.nodes[3]["cells"] == [3]
    assert cycle_lin.nodes[3]["cycle_length"] == 1
    assert cycle_lin.nodes[3]["level"] == 1
    assert cycle_lin.nodes[5]["cycle_ID"] == 5
    assert cycle_lin.nodes[5]["cells"] == [4, 5]
    assert cycle_lin.nodes[5]["cycle_length"] == 2
    assert cycle_lin.nodes[5]["level"] == 2


def test_cycle_lineage_triple_div(cell_lin_triple_div):
    cycle_lin = CycleLineage(cell_lin_triple_div)
    assert sorted(list(cycle_lin.nodes())) == [2, 4, 6, 8, 9, 10, 14, 15, 16, 18]
    assert cycle_lin.graph["lineage_ID"] == 1
    assert cycle_lin.nodes[4]["cycle_ID"] == 4
    assert cycle_lin.nodes[4]["cells"] == [3, 4]
    assert cycle_lin.nodes[4]["cycle_length"] == 2
    assert cycle_lin.nodes[4]["level"] == 1
    assert cycle_lin.nodes[18]["cycle_ID"] == 18
    assert cycle_lin.nodes[18]["cells"] == [17, 18]
    assert cycle_lin.nodes[18]["cycle_length"] == 2
    assert cycle_lin.nodes[18]["level"] == 2


def test_cycle_lineage_unconnected_node(cell_lin_unconnected_node):
    with pytest.raises(LineageStructureError):
        CycleLineage(cell_lin_unconnected_node)


def test_cycle_lineage_unconnected_component(cell_lin_unconnected_component):
    with pytest.raises(LineageStructureError):
        CycleLineage(cell_lin_unconnected_component)


# get_ancestors() #############################################################


def test_get_ancestors_key_error(cycle_lin):
    with pytest.raises(KeyError):
        cycle_lin.get_ancestors(0)


def test_get_ancestors_cannot_order_cycle(cycle_lin):
    for n in cycle_lin.nodes:
        del cycle_lin.nodes[n]["level"]
    msg = "No 'level' property to order the cell cycles."
    with pytest.warns(UserWarning, match=msg):
        cycle_lin.get_ancestors(5)


# get_edges_within_cycle() ###################################################


def test_get_edges_within_cycle_normal_lin(cell_lin):
    cycle_lin = CycleLineage(cell_lin)
    # From division.
    assert cycle_lin.get_links_within_cycle(2) == [(1, 2)]
    assert cycle_lin.get_links_within_cycle(4) == [(3, 4)]
    assert cycle_lin.get_links_within_cycle(8) == [(7, 8)]
    assert cycle_lin.get_links_within_cycle(14) == [(11, 12), (12, 13), (13, 14)]
    # From leaf.
    assert cycle_lin.get_links_within_cycle(6) == [(5, 6)]
    assert cycle_lin.get_links_within_cycle(9) == []
    assert cycle_lin.get_links_within_cycle(16) == []


def test_get_edges_within_cycle_single_node(one_node_cell_lin):
    cycle_lin = CycleLineage(one_node_cell_lin)
    assert cycle_lin.get_links_within_cycle(1) == []


def test_get_edges_within_cycle_gap(cell_lin_gap):
    cycle_lin = CycleLineage(cell_lin_gap)
    # From division.
    assert cycle_lin.get_links_within_cycle(2) == [(1, 2)]
    assert cycle_lin.get_links_within_cycle(4) == [(3, 4)]
    assert cycle_lin.get_links_within_cycle(8) == []
    assert cycle_lin.get_links_within_cycle(14) == [(11, 14)]
    # From leaf.
    assert cycle_lin.get_links_within_cycle(6) == []
    assert cycle_lin.get_links_within_cycle(9) == []
    assert cycle_lin.get_links_within_cycle(16) == []


def test_get_edges_within_cycle_div_root(cell_lin_div_root):
    cycle_lin = CycleLineage(cell_lin_div_root)
    assert cycle_lin.get_links_within_cycle(1) == []
    assert cycle_lin.get_links_within_cycle(2) == []
    assert cycle_lin.get_links_within_cycle(17) == []


def test_get_edges_within_cycle_successive_divs_and_root(
    cell_lin_successive_divs_and_root,
):
    cycle_lin = CycleLineage(cell_lin_successive_divs_and_root)
    assert cycle_lin.get_links_within_cycle(2) == []
    assert cycle_lin.get_links_within_cycle(3) == []
    assert cycle_lin.get_links_within_cycle(5) == [(4, 5)]
    assert cycle_lin.get_links_within_cycle(6) == []
    assert cycle_lin.get_links_within_cycle(8) == []
    assert cycle_lin.get_links_within_cycle(9) == []
    assert cycle_lin.get_links_within_cycle(11) == []


def test_get_edges_within_cycle_triple_div(cell_lin_triple_div):
    cycle_lin = CycleLineage(cell_lin_triple_div)
    assert cycle_lin.get_links_within_cycle(4) == [(3, 4)]
    assert cycle_lin.get_links_within_cycle(6) == [(5, 6)]
    assert cycle_lin.get_links_within_cycle(8) == [(7, 8)]
    assert cycle_lin.get_links_within_cycle(18) == [(17, 18)]
