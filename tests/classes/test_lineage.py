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
    lineage.add_node(1, timepoint=0)
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
        lineage.nodes[n]["timepoint"] = nx.shortest_path_length(lineage, 1, n)
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
    new_lin.add_node(17, timepoint=1)
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
        lineage.nodes[n]["timepoint"] = nx.shortest_path_length(lineage, 2, n) + 1
        lineage.nodes[n]["cell_ID"] = n
    lineage.graph["lineage_ID"] = 2
    return lineage


@pytest.fixture
def cell_lin_triple_div(cell_lin):
    # Triple division.
    new_lin = cell_lin.copy()
    new_lin.add_node(17, timepoint=4)
    new_lin.add_node(18, timepoint=5)
    new_lin.add_edges_from([(4, 17), (17, 18)])
    return new_lin


@pytest.fixture
def cell_lin_unconnected_node(cell_lin):
    new_lin = cell_lin.copy()
    new_lin.add_node(17, timepoint=1, cell_ID=17)
    new_lin.graph["lineage_ID"] = 2
    return new_lin


@pytest.fixture
def cell_lin_unconnected_component(cell_lin):
    new_lin = cell_lin.copy()
    new_lin.add_node(17, timepoint=1, cell_ID=17)
    new_lin.add_node(18, timepoint=2, cell_ID=18)
    new_lin.add_edge(17, 18)
    new_lin.graph["lineage_ID"] = 2
    return new_lin


@pytest.fixture
def cell_lin_unconnected_component_div(cell_lin_unconnected_component):
    """Lineage with an unconnected component containing multiple divisions."""
    new_lin = cell_lin_unconnected_component.copy()
    new_lin.add_node(19, timepoint=2)
    new_lin.add_node(20, timepoint=3)
    new_lin.add_node(21, timepoint=4)
    new_lin.add_node(22, timepoint=3)
    new_lin.add_edges_from([(17, 19), (19, 20), (20, 21), (19, 22)])
    return new_lin


# CycleLineage fixtures #######################################################


@pytest.fixture
def empty_cycle_lin():
    return CycleLineage(time_prop="timepoint", time_step=1)


@pytest.fixture
def one_node_cycle_lin():
    lineage = CycleLineage(time_prop="timepoint", time_step=1)
    lineage.add_node(1, level=0)
    return lineage


@pytest.fixture
def cycle_lin():
    # Nothing special, just a lineage.
    lineage = CycleLineage(time_prop="timepoint", time_step=1)
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


# Test classes ###############################################################

# Base Lineage functionality


class TestLineageRemoveProp:
    """Test cases for Lineage._remove_prop method."""

    def test_node_property_removal(self, cell_lin):
        """Test removing property from all nodes."""
        cell_lin._remove_prop("timepoint", "node")
        for node in cell_lin.nodes:
            assert "timepoint" not in cell_lin.nodes[node]

    def test_edge_property_removal(self, cell_lin):
        """Test removing property from all edges."""
        cell_lin._remove_prop("name", "edge")
        for edge in cell_lin.edges:
            assert "name" not in cell_lin.edges[edge]

    def test_lineage_property_removal(self, cell_lin):
        """Test removing property from lineage graph."""
        cell_lin._remove_prop("lineage_ID", "lineage")
        assert "lineage_ID" not in cell_lin.graph

    def test_unknown_property_removal(self, cell_lin):
        """Test that removing non-existent property does not raise error."""
        cell_lin._remove_prop("unknown_property", "node")
        cell_lin._remove_prop("unknown_property", "edge")
        cell_lin._remove_prop("unknown_property", "lineage")

    def test_missing_property_removal(self, cell_lin):
        """Test removing property not present in some elements does not raise error."""
        cell_lin.add_edge(16, 17)
        cell_lin._remove_prop("timepoint", "node")
        cell_lin._remove_prop("name", "edge")

    def test_invalid_type_raises_error(self, cell_lin):
        """Test that invalid prop_type raises ValueError."""
        with pytest.raises(
            ValueError,
            match="Invalid prop_type. Must be one of 'node', 'edge', or 'lineage'.",
        ):
            cell_lin._remove_prop("custom_property", "invalid_type")


class TestLineageGetRoot:
    """Test cases for Lineage.get_root method."""

    def test_normal_lineage(self, cell_lin):
        """Test get_root on normal lineage."""
        assert cell_lin.get_root() == 1
        assert cell_lin.get_root(ignore_lone_nodes=True) == 1

    def test_empty_lineage(self, empty_cell_lin):
        """Test get_root on empty lineage."""
        assert empty_cell_lin.get_root() == []
        assert empty_cell_lin.get_root(ignore_lone_nodes=True) == []

    def test_single_node(self, one_node_cell_lin):
        """Test get_root on single node lineage."""
        assert one_node_cell_lin.get_root() == 1
        assert one_node_cell_lin.get_root(ignore_lone_nodes=True) == []

    def test_lineage_with_gap(self, cell_lin_gap):
        """Test get_root on lineage with gaps."""
        assert cell_lin_gap.get_root() == 1
        assert cell_lin_gap.get_root(ignore_lone_nodes=True) == 1

    def test_division_root(self, cell_lin_div_root):
        """Test get_root on lineage with division at root."""
        assert cell_lin_div_root.get_root() == 1
        assert cell_lin_div_root.get_root(ignore_lone_nodes=True) == 1

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test get_root on lineage with unconnected node."""
        assert cell_lin_unconnected_node.get_root() == [1, 17]
        assert cell_lin_unconnected_node.get_root(ignore_lone_nodes=True) == 1

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test get_root on lineage with unconnected component."""
        assert cell_lin_unconnected_component.get_root() == [1, 17]
        assert cell_lin_unconnected_component.get_root(ignore_lone_nodes=True) == [
            1,
            17,
        ]


class TestLineageGetLeaves:
    """Test cases for Lineage.get_leaves method."""

    def test_normal_lineage(self, cell_lin):
        """Test get_leaves on normal lineage."""
        assert cell_lin.get_leaves() == [6, 9, 10, 15, 16]
        assert cell_lin.get_leaves(ignore_lone_nodes=True) == [6, 9, 10, 15, 16]

    def test_empty_lineage(self, empty_cell_lin):
        """Test get_leaves on empty lineage."""
        assert empty_cell_lin.get_leaves() == []
        assert empty_cell_lin.get_leaves(ignore_lone_nodes=True) == []

    def test_single_node(self, one_node_cell_lin):
        """Test get_leaves on single node lineage."""
        assert one_node_cell_lin.get_leaves() == [1]
        assert one_node_cell_lin.get_leaves(ignore_lone_nodes=True) == []

    def test_lineage_with_gap(self, cell_lin_gap):
        """Test get_leaves on lineage with gaps."""
        assert cell_lin_gap.get_leaves() == [6, 9, 10, 15, 16]

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test get_leaves on lineage with unconnected node."""
        res = cell_lin_unconnected_node.get_leaves()
        assert res == [6, 9, 10, 15, 16, 17]
        res = cell_lin_unconnected_node.get_leaves(ignore_lone_nodes=True)
        assert res == [6, 9, 10, 15, 16]

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test get_leaves on lineage with unconnected component."""
        res = cell_lin_unconnected_component.get_leaves()
        assert res == [6, 9, 10, 15, 16, 18]
        res = cell_lin_unconnected_component.get_leaves(ignore_lone_nodes=True)
        assert res == [6, 9, 10, 15, 16, 18]


class TestLineageGetAncestors:
    """Test cases for CellLineage.get_ancestors and CycleLineage.get_ancestors methods."""

    def test_normal_cell_lineage(self, cell_lin):
        """Test get_ancestors on normal CellLineage."""
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

    def test_normal_cycle_lineage(self, cycle_lin):
        """Test get_ancestors on normal CycleLineage."""
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

    def test_single_node(self, one_node_cell_lin, one_node_cycle_lin):
        """Test get_ancestors on single node lineages."""
        # CellLineage
        assert one_node_cell_lin.get_ancestors(1) == []
        assert one_node_cell_lin.get_ancestors(1, sorted=False) == []
        # CycleLineage
        assert one_node_cycle_lin.get_ancestors(1) == []
        assert one_node_cycle_lin.get_ancestors(1, sorted=False) == []

    def test_lineage_with_gap(self, cell_lin_gap):
        """Test get_ancestors on lineage with gaps."""
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

    def test_division_root(self, cell_lin_div_root):
        """Test get_ancestors on lineage with division at root."""
        assert cell_lin_div_root.get_ancestors(1) == []
        assert sorted(cell_lin_div_root.get_ancestors(1, sorted=False)) == []
        assert cell_lin_div_root.get_ancestors(2) == [1]
        assert sorted(cell_lin_div_root.get_ancestors(2, sorted=False)) == [1]
        assert cell_lin_div_root.get_ancestors(17) == [1]
        assert sorted(cell_lin_div_root.get_ancestors(17, sorted=False)) == [1]

    def test_successive_divisions_and_root(self, cell_lin_successive_divs_and_root):
        """Test get_ancestors on lineage with successive divisions."""
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

    def test_triple_division(self, cell_lin_triple_div, cycle_lin_triple_div):
        """Test get_ancestors on lineage with triple division."""
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

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test get_ancestors on lineage with unconnected node."""
        assert cell_lin_unconnected_node.get_ancestors(17) == []
        assert cell_lin_unconnected_node.get_ancestors(17, sorted=False) == []

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test get_ancestors on lineage with unconnected component."""
        assert cell_lin_unconnected_component.get_ancestors(17) == []
        assert cell_lin_unconnected_component.get_ancestors(17, sorted=False) == []
        assert cell_lin_unconnected_component.get_ancestors(18) == [17]
        assert cell_lin_unconnected_component.get_ancestors(18, sorted=False) == [17]

    def test_node_id_error(self, cell_lin, cycle_lin):
        """Test get_ancestors raises KeyError for non-existent node."""
        with pytest.raises(KeyError):
            cell_lin.get_ancestors(0)
        with pytest.raises(KeyError):
            cycle_lin.get_ancestors(0)

    def test_cannot_order_warning(self, cell_lin):
        """Test get_ancestors issues warning when nodes cannot be ordered."""
        for n in cell_lin.nodes:
            del cell_lin.nodes[n]["timepoint"]
        with pytest.warns(
            UserWarning, match="No 'timepoint' property to order the cells."
        ):
            cell_lin.get_ancestors(16)


class TestLineageGetDescendants:
    """Test cases for CellLineage.get_descendants and CycleLineage.get_descendants methods."""

    def test_normal_cell_lineage(self, cell_lin):
        """Test get_descendants on normal CellLineage."""
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

    def test_normal_cycle_lineage(self, cycle_lin):
        """Test get_descendants on normal CycleLineage."""
        # Root.
        assert sorted(cycle_lin.get_descendants(1)) == [2, 3, 4, 5]
        # Leaves.
        assert cycle_lin.get_descendants(3) == []
        assert cycle_lin.get_descendants(5) == []
        # Other.
        assert cycle_lin.get_descendants(2) == [4, 5]

    def test_single_node(self, one_node_cell_lin, one_node_cycle_lin):
        """Test get_descendants on single node lineages."""
        # CellLineage
        assert one_node_cell_lin.get_descendants(1) == []
        # CycleLineage
        assert one_node_cycle_lin.get_descendants(1) == []

    def test_lineage_with_gap(self, cell_lin_gap):
        """Test get_descendants on lineage with gaps."""
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

    def test_division_root(self, cell_lin_div_root):
        """Test get_descendants on lineage with division at root."""
        assert sorted(cell_lin_div_root.get_descendants(1)) == list(range(2, 18))

    def test_successive_divisions_and_root(self, cell_lin_successive_divs_and_root):
        """Test get_descendants on lineage with successive divisions."""
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

    def test_triple_division(self, cell_lin_triple_div, cycle_lin_triple_div):
        """Test get_descendants on lineage with triple division."""
        # CellLineage
        lin = cell_lin_triple_div
        assert sorted(lin.get_descendants(4)) == list(range(5, 11)) + [17, 18]
        assert lin.get_descendants(17) == [18]
        assert lin.get_descendants(18) == []
        # CycleLineage
        assert sorted(cycle_lin_triple_div.get_descendants(2)) == [4, 5, 6]
        assert cycle_lin_triple_div.get_descendants(6) == []

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test get_descendants on lineage with unconnected node."""
        assert cell_lin_unconnected_node.get_descendants(17) == []

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test get_descendants on lineage with unconnected component."""
        assert cell_lin_unconnected_component.get_descendants(17) == [18]
        assert cell_lin_unconnected_component.get_descendants(18) == []


class TestLineageIsRoot:
    """Test cases for CellLineage.is_root and CycleLineage.is_root methods."""

    def test_normal_lineage(self, cell_lin, cycle_lin):
        """Test is_root on normal lineages."""
        # CellLineage
        assert cell_lin.is_root(1)
        assert not cell_lin.is_root(2)
        assert not cell_lin.is_root(6)
        # CycleLineage
        assert cycle_lin.is_root(1)
        assert not cycle_lin.is_root(2)
        assert not cycle_lin.is_root(4)

    def test_single_node(self, one_node_cell_lin, one_node_cycle_lin):
        """Test is_root on single node lineages."""
        # CellLineage
        assert one_node_cell_lin.is_root(1)
        # CycleLineage
        assert one_node_cycle_lin.is_root(1)

    def test_lineage_with_gap(self, cell_lin_gap):
        """Test is_root on lineage with gaps."""
        assert cell_lin_gap.is_root(1)
        assert not cell_lin_gap.is_root(2)
        assert not cell_lin_gap.is_root(6)

    def test_division_root(self, cell_lin_div_root):
        """Test is_root on lineage with division at root."""
        assert cell_lin_div_root.is_root(1)
        assert not cell_lin_div_root.is_root(2)
        assert not cell_lin_div_root.is_root(17)

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test is_root on lineage with unconnected node."""
        assert cell_lin_unconnected_node.is_root(17)

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test is_root on lineage with unconnected component."""
        assert cell_lin_unconnected_component.is_root(17)
        assert not cell_lin_unconnected_component.is_root(18)


class TestLineageIsLeaf:
    """Test cases for CellLineage.is_leaf and CycleLineage.is_leaf methods."""

    def test_normal_lineage(self, cell_lin, cycle_lin):
        """Test is_leaf on normal lineages."""
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

    def test_single_node(self, one_node_cell_lin, one_node_cycle_lin):
        """Test is_leaf on single node lineages."""
        # CellLineage
        assert one_node_cell_lin.is_leaf(1)
        # CycleLineage
        assert one_node_cycle_lin.is_leaf(1)

    def test_lineage_with_gap(self, cell_lin_gap):
        """Test is_leaf on lineage with gaps."""
        assert not cell_lin_gap.is_leaf(1)
        assert not cell_lin_gap.is_leaf(4)
        assert cell_lin_gap.is_leaf(6)
        assert cell_lin_gap.is_leaf(9)
        assert cell_lin_gap.is_leaf(15)

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test is_leaf on lineage with unconnected node."""
        assert cell_lin_unconnected_node.is_leaf(17)

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test is_leaf on lineage with unconnected component."""
        assert not cell_lin_unconnected_component.is_leaf(17)
        assert cell_lin_unconnected_component.is_leaf(18)


class TestLineageGetFusions:
    """Test cases for CellLineage.get_fusions method."""

    def test_normal_lineage(self, cell_lin):
        """Test get_fusions on normal lineage."""
        # No fusions.
        assert cell_lin.get_fusions() == []
        # Fusion.
        cell_lin.add_edge(3, 12)
        assert cell_lin.get_fusions() == [12]
        # Multiple fusions.
        cell_lin.add_edge(5, 8)
        cell_lin.add_edge(4, 14)
        assert sorted(cell_lin.get_fusions()) == [8, 12, 14]

    def test_empty_lineage(self, empty_cell_lin):
        """Test get_fusions on empty lineage."""
        # No fusions.
        assert empty_cell_lin.get_fusions() == []

    def test_single_node(self, one_node_cell_lin):
        """Test get_fusions on single node lineage."""
        # No fusions.
        assert one_node_cell_lin.get_fusions() == []

    def test_lineage_with_gap(self, cell_lin_gap):
        """Test get_fusions on lineage with gaps."""
        # No fusions.
        assert cell_lin_gap.get_fusions() == []
        # Fusion.
        cell_lin_gap.add_edge(3, 14)
        assert cell_lin_gap.get_fusions() == [14]
        # Multiple fusions.
        cell_lin_gap.add_edge(8, 15)
        assert sorted(cell_lin_gap.get_fusions()) == [14, 15]

    def test_division_root(self, cell_lin_div_root):
        """Test get_fusions on lineage with division at root."""
        # No fusions.
        assert cell_lin_div_root.get_fusions() == []
        # Fusion.
        cell_lin_div_root.add_edge(17, 11)
        assert cell_lin_div_root.get_fusions() == [11]

    def test_successive_divisions_and_root(self, cell_lin_successive_divs_and_root):
        """Test get_fusions on lineage with successive divisions."""
        # No fusions.
        assert cell_lin_successive_divs_and_root.get_fusions() == []
        # Fusion.
        cell_lin_successive_divs_and_root.add_edge(4, 9)
        assert cell_lin_successive_divs_and_root.get_fusions() == [9]

    def test_triple_fusion(self, cell_lin_triple_div):
        """Test get_fusions on lineage with triple division."""
        # No fusions.
        assert cell_lin_triple_div.get_fusions() == []
        # Fusion.
        cell_lin_triple_div.add_edges_from([(6, 9), (18, 9)])
        assert cell_lin_triple_div.get_fusions() == [9]

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test get_fusions on lineage with unconnected node."""
        # No fusions.
        assert cell_lin_unconnected_node.get_fusions() == []
        # Multiple fusions.
        cell_lin_unconnected_node.add_edge(5, 8)
        cell_lin_unconnected_node.add_edge(4, 14)
        assert sorted(cell_lin_unconnected_node.get_fusions()) == [8, 14]

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test get_fusions on lineage with unconnected component."""
        # No fusions.
        assert cell_lin_unconnected_component.get_fusions() == []
        # Fusion.
        cell_lin_unconnected_component.add_edges_from([(17, 19), (18, 20), (19, 20)])
        assert cell_lin_unconnected_component.get_fusions() == [20]


# CellLineage-specific basic operations


class TestCellLineageGetNextAvailableNodeID:
    """Test cases for CellLineage._get_next_available_node_ID method."""

    def test_normal_lineage(self, cell_lin):
        """Test _get_next_available_node_ID on normal lineage."""
        assert cell_lin._get_next_available_node_ID() == 17

    def test_empty_lineage(self, empty_cell_lin):
        """Test _get_next_available_node_ID on empty lineage."""
        assert empty_cell_lin._get_next_available_node_ID() == 0

    def test_single_node(self, one_node_cell_lin):
        """Test _get_next_available_node_ID on single node lineage."""
        assert one_node_cell_lin._get_next_available_node_ID() == 2

    def test_lineage_with_gap(self, cell_lin_gap):
        """Test _get_next_available_node_ID on lineage with gaps."""
        assert cell_lin_gap._get_next_available_node_ID() == 17

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test _get_next_available_node_ID on lineage with unconnected node."""
        assert cell_lin_unconnected_node._get_next_available_node_ID() == 18

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test _get_next_available_node_ID on lineage with unconnected component."""
        assert cell_lin_unconnected_component._get_next_available_node_ID() == 19


class TestCellLineageAddCell:
    """Test cases for CellLineage._add_cell method."""

    def test_no_arguments(self, cell_lin):
        """Test _add_cell with no arguments."""
        next_id = cell_lin._get_next_available_node_ID()
        assert cell_lin._add_cell() == next_id
        assert cell_lin.nodes[next_id]["cell_ID"] == next_id
        assert cell_lin.nodes[next_id]["timepoint"] == 0

    def test_with_id(self, cell_lin):
        """Test _add_cell with specific ID."""
        assert cell_lin._add_cell(nid=20) == 20
        assert cell_lin.nodes[20]["cell_ID"] == 20
        assert cell_lin.nodes[20]["timepoint"] == 0

    def test_with_timepoint(self, cell_lin):
        """Test _add_cell with specific timepoint."""
        next_id = cell_lin._get_next_available_node_ID()
        assert (
            cell_lin._add_cell(time_prop_name="timepoint", time_prop_value=5) == next_id
        )
        assert cell_lin.nodes[next_id]["cell_ID"] == next_id
        assert cell_lin.nodes[next_id]["timepoint"] == 5

    def test_with_properties(self, cell_lin):
        """Test _add_cell with additional properties."""
        cell_id = 20
        assert cell_lin._add_cell(20, color="red", size=10) == cell_id
        assert cell_lin.nodes[cell_id]["cell_ID"] == cell_id
        assert cell_lin.nodes[cell_id]["timepoint"] == 0
        assert cell_lin.nodes[cell_id]["color"] == "red"
        assert cell_lin.nodes[cell_id]["size"] == 10

    def test_existing_id_raises_error(self, cell_lin):
        """Test _add_cell raises ValueError for existing ID."""
        with pytest.raises(ValueError):
            cell_lin._add_cell(1)
        cell_lin.graph["lineage_ID"] = 1
        with pytest.raises(ValueError):
            cell_lin._add_cell(1)

    def test_empty_lineage(self, empty_cell_lin):
        """Test _add_cell on empty lineage."""
        assert empty_cell_lin._add_cell() == 0
        assert empty_cell_lin.nodes[0]["cell_ID"] == 0
        assert empty_cell_lin.nodes[0]["timepoint"] == 0

    def test_single_node(self, one_node_cell_lin):
        """Test _add_cell on single node lineage."""
        assert one_node_cell_lin._add_cell() == 2
        assert one_node_cell_lin.nodes[2]["cell_ID"] == 2
        assert one_node_cell_lin.nodes[2]["timepoint"] == 0


class TestCellLineageRemoveCell:
    """Test cases for CellLineage._remove_cell method."""

    @staticmethod
    def check_correct_cell_removal(cell_lin, node_id):
        """Helper function to check correct cell removal."""
        cell_props = cell_lin.nodes[node_id]
        assert cell_lin._remove_cell(node_id) == cell_props
        assert node_id not in cell_lin.nodes
        assert not any(node_id in edge for edge in cell_lin.edges)

    def test_normal_lineage(self, cell_lin):
        """Test _remove_cell on normal lineage."""
        # Root.
        self.check_correct_cell_removal(cell_lin, 1)
        # Division.
        self.check_correct_cell_removal(cell_lin, 4)
        # Just after division.
        self.check_correct_cell_removal(cell_lin, 11)
        # Leaves.
        self.check_correct_cell_removal(cell_lin, 10)
        self.check_correct_cell_removal(cell_lin, 16)
        # Intermediate node.
        self.check_correct_cell_removal(cell_lin, 12)

    def test_empty_lineage_raises_error(self, empty_cell_lin):
        """Test _remove_cell raises KeyError on empty lineage."""
        with pytest.raises(KeyError):
            empty_cell_lin._remove_cell(0)

    def test_single_node(self, one_node_cell_lin):
        """Test _remove_cell on single node lineage."""
        self.check_correct_cell_removal(one_node_cell_lin, 1)

    def test_lineage_with_gap(self, cell_lin_gap):
        """Test _remove_cell on lineage with gaps."""
        # Root.
        self.check_correct_cell_removal(cell_lin_gap, 1)
        # Division.
        self.check_correct_cell_removal(cell_lin_gap, 4)
        self.check_correct_cell_removal(cell_lin_gap, 8)
        self.check_correct_cell_removal(cell_lin_gap, 14)
        # Just after division.
        self.check_correct_cell_removal(cell_lin_gap, 11)
        # Leaves.
        self.check_correct_cell_removal(cell_lin_gap, 6)
        self.check_correct_cell_removal(cell_lin_gap, 15)

    def test_division_root(self, cell_lin_div_root):
        """Test _remove_cell on lineage with division at root."""
        self.check_correct_cell_removal(cell_lin_div_root, 17)

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test _remove_cell on lineage with unconnected node."""
        self.check_correct_cell_removal(cell_lin_unconnected_node, 17)

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test _remove_cell on lineage with unconnected component."""
        self.check_correct_cell_removal(cell_lin_unconnected_component, 17)
        self.check_correct_cell_removal(cell_lin_unconnected_component, 18)

    def test_unconnected_component_div(self, cell_lin_unconnected_component_div):
        """Test _remove_cell on lineage with unconnected component division."""
        self.check_correct_cell_removal(cell_lin_unconnected_component_div, 18)
        self.check_correct_cell_removal(cell_lin_unconnected_component_div, 19)
        self.check_correct_cell_removal(cell_lin_unconnected_component_div, 20)
        self.check_correct_cell_removal(cell_lin_unconnected_component_div, 22)


class TestCellLineageAddLink:
    """Test cases for CellLineage._add_link method."""

    def test_normal_lineage(self, cell_lin):
        """Test _add_link on normal lineage."""
        # Add a valid link.
        cell_lin.add_node(17, timepoint=6, cell_ID=17)
        cell_lin._add_link(6, 17)
        assert cell_lin.has_edge(6, 17)
        assert cell_lin.nodes[17]["cell_ID"] == 17
        assert cell_lin.nodes[17]["timepoint"] == 6
        # Add a link that creates a division.
        cell_lin.add_node(18, timepoint=1, cell_ID=18)
        cell_lin._add_link(1, 18)
        assert cell_lin.has_edge(1, 18)
        assert cell_lin.nodes[18]["cell_ID"] == 18
        assert cell_lin.nodes[18]["timepoint"] == 1

    def test_existing_edge_raises_error(self, cell_lin):
        """Test _add_link raises ValueError for existing edge."""
        with pytest.raises(ValueError):
            cell_lin._add_link(1, 2)

    def test_nonexistent_source_raises_error(self, cell_lin):
        """Test _add_link raises ValueError for nonexistent source."""
        with pytest.raises(ValueError):
            cell_lin._add_link(99, 2)

    def test_nonexistent_target_raises_error(self, cell_lin):
        """Test _add_link raises ValueError for nonexistent target."""
        with pytest.raises(ValueError):
            cell_lin._add_link(1, 99)

    def test_fusion_error(self, cell_lin):
        """Test _add_link raises FusionError for fusion event."""
        cell_lin.add_edge(3, 12)
        with pytest.raises(FusionError):
            cell_lin._add_link(5, 12)

    def test_time_flow_error(self, cell_lin):
        """Test _add_link raises TimeFlowError for time flow violations."""
        cell_lin.add_node(17, timepoint=1, cell_ID=17)
        with pytest.raises(TimeFlowError):
            cell_lin._add_link(6, 17)
        cell_lin.add_node(18, timepoint=0, cell_ID=18)
        with pytest.raises(TimeFlowError):
            cell_lin._add_link(1, 18)

    def test_different_lineages(self, cell_lin):
        """Test _add_link between different lineages."""
        new_lin = CellLineage(lid=2)
        new_lin.add_node(19, timepoint=1, cell_ID=19)
        new_lin.add_node(20, timepoint=2, cell_ID=20)
        new_lin.add_node(21, timepoint=3, cell_ID=21)
        new_lin.add_edges_from([(19, 20), (20, 21)])
        cell_lin._add_link(1, 19, target_lineage=new_lin)
        assert cell_lin.has_node(19)
        assert cell_lin.nodes[19]["cell_ID"] == 19
        assert cell_lin.nodes[19]["timepoint"] == 1
        assert cell_lin.has_edge(1, 19)
        assert cell_lin.has_node(20)
        assert cell_lin.has_node(21)
        assert len(new_lin.nodes) == 0

    def test_different_lineages_unconnected_node(
        self, cell_lin, cell_lin_unconnected_node
    ):
        """Test _add_link between a lineage and an unconnected node of another lineage."""
        cell_lin._add_link(1, 17, target_lineage=cell_lin_unconnected_node)
        assert cell_lin.has_node(17)
        assert cell_lin.has_edge(1, 17)
        assert cell_lin.nodes[17]["cell_ID"] == 17
        assert cell_lin.nodes[17]["timepoint"] == 1
        assert not cell_lin_unconnected_node.has_node(17)

    def test_different_lineages_unconnected_component(
        self, cell_lin, cell_lin_unconnected_component
    ):
        """Test _add_link between a lineage and an unconnected component of another lineage."""
        cell_lin._add_link(1, 17, target_lineage=cell_lin_unconnected_component)
        assert cell_lin.has_node(17)
        assert cell_lin.has_node(18)
        assert cell_lin.has_edge(1, 17)
        assert cell_lin.has_edge(17, 18)
        assert cell_lin.nodes[17]["cell_ID"] == 17
        assert cell_lin.nodes[17]["timepoint"] == 1
        assert cell_lin.nodes[18]["cell_ID"] == 18
        assert cell_lin.nodes[18]["timepoint"] == 2
        assert not cell_lin_unconnected_component.has_node(17)
        assert not cell_lin_unconnected_component.has_node(18)

    def test_conflicting_ID(self, cell_lin):
        """Test _add_link between different lineages with a conflicting ID."""
        new_lin = CellLineage(lid=2)
        new_lin.add_node(5, timepoint=1, cell_ID=5)
        IDs_mapping = cell_lin._add_link(1, 5, target_lineage=new_lin)
        assert IDs_mapping == {5: 17}
        # Cell 5 is removed from the target lineage.
        assert not new_lin.has_node(5)
        assert not new_lin.has_node(17)
        # Cell 17 is added with the new edge.
        assert cell_lin.has_node(17)
        assert cell_lin.has_edge(1, 17)
        assert cell_lin.nodes[17]["cell_ID"] == 17
        assert cell_lin.nodes[17]["timepoint"] == 1
        # Cell 5 is untouched.
        assert cell_lin.has_node(5)
        assert cell_lin.nodes[5]["cell_ID"] == 5
        assert cell_lin.nodes[5]["timepoint"] == 4

    def test_conflicting_IDs(self, cell_lin, cell_lin_successive_divs_and_root):
        """Test _add_link between different lineages with multiple conflicting IDs."""
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
        assert cell_lin.nodes[17]["timepoint"] == 1
        assert cell_lin.has_edge(17, 18)
        assert cell_lin.nodes[18]["cell_ID"] == 18
        assert cell_lin.nodes[18]["timepoint"] == 2
        # Cells are untouched.
        assert cell_lin.has_node(2)
        assert cell_lin.nodes[2]["cell_ID"] == 2
        assert cell_lin.nodes[2]["timepoint"] == 1

    def test_same_IDs(self, cell_lin):
        """Test _add_link between different lineages with the same single ID."""
        new_lin = CellLineage(lid=2)
        new_lin.add_node(1, timepoint=1, cell_ID=1)
        IDs_mapping = cell_lin._add_link(1, 1, new_lin)
        assert IDs_mapping == {1: 17}
        # Cell 1 is removed from the target lineage.
        assert not new_lin.has_node(1)
        assert not new_lin.has_node(17)
        # Cell 17 is added with the new edge.
        assert cell_lin.has_node(17)
        assert cell_lin.has_edge(1, 17)
        assert cell_lin.nodes[17]["cell_ID"] == 17
        assert cell_lin.nodes[17]["timepoint"] == 1
        # Cell 1 is untouched.
        assert cell_lin.has_node(1)
        assert cell_lin.nodes[1]["cell_ID"] == 1
        assert cell_lin.nodes[1]["timepoint"] == 0


class TestCellLineageRemoveLink:
    """Test cases for CellLineage.remove_link method."""

    @staticmethod
    def check_correct_link_removal(cell_lin, source_nid, target_nid):
        """Helper function to check correct link removal."""
        link_props = cell_lin[source_nid][target_nid]
        assert cell_lin._remove_link(source_nid, target_nid) == link_props
        assert not cell_lin.has_edge(source_nid, target_nid)

    def test_normal_lin(self, cell_lin):
        """Test remove_link on normal lineage."""
        # Remove a valid link with root.
        self.check_correct_link_removal(cell_lin, 1, 2)
        # Remove a valid link with division.
        self.check_correct_link_removal(cell_lin, 4, 5)
        # Remove a valid link with leaf.
        self.check_correct_link_removal(cell_lin, 8, 9)
        # Remove a valid link with intermediate node.
        self.check_correct_link_removal(cell_lin, 12, 13)

    def test_nonexistent_source(self, cell_lin):
        """Test remove_link with a nonexistent source."""
        with pytest.raises(ValueError):
            cell_lin._remove_link(99, 2)

    def test_nonexistent_target(self, cell_lin):
        """Test remove_link with a nonexistent target."""
        with pytest.raises(ValueError):
            cell_lin._remove_link(1, 99)

    def test_nonexistent_link(self, cell_lin):
        """Test remove_link on a nonexistent link."""
        with pytest.raises(KeyError):
            cell_lin._remove_link(1, 3)

    def test_empty_lin(self, empty_cell_lin):
        """Test remove_link raises ValueError for empty lineage."""
        with pytest.raises(ValueError):
            empty_cell_lin._remove_link(0, 1)

    def test_single_node(self, one_node_cell_lin):
        """Test remove_link raises ValueError for single node lineage."""
        with pytest.raises(ValueError):
            one_node_cell_lin._remove_link(1, 2)

    def test_gap(self, cell_lin_gap):
        """Test remove_link on a valid link in a lineage with gaps."""
        self.check_correct_link_removal(cell_lin_gap, 1, 2)
        self.check_correct_link_removal(cell_lin_gap, 4, 6)
        self.check_correct_link_removal(cell_lin_gap, 8, 9)
        self.check_correct_link_removal(cell_lin_gap, 11, 14)

    def test_div_root(self, cell_lin_div_root):
        """Test remove_link on a valid link in a lineage with a division root."""
        self.check_correct_link_removal(cell_lin_div_root, 1, 17)

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test remove_link on a valid link in a lineage with an unconnected component."""
        self.check_correct_link_removal(cell_lin_unconnected_component, 17, 18)

    def test_unconnected_component_div(self, cell_lin_unconnected_component_div):
        """Test remove_link on a valid link in a lineage with an unconnected component and division root."""
        self.check_correct_link_removal(cell_lin_unconnected_component_div, 17, 18)
        self.check_correct_link_removal(cell_lin_unconnected_component_div, 19, 20)
        self.check_correct_link_removal(cell_lin_unconnected_component_div, 19, 22)


# CellLineage advanced operations


class TestCellLineageSplitFromCell:
    """Test cases for CellLineage.split_from_cell method."""

    def test_division_upstream(self, cell_lin):
        """Test split upstream from a division node."""
        new_lin = cell_lin._split_from_cell(4, split="upstream")
        assert sorted(new_lin.nodes()) == [4, 5, 6, 7, 8, 9, 10]
        assert sorted(cell_lin.nodes()) == [1, 2, 3, 11, 12, 13, 14, 15, 16]

    def test_division_downstream(self, cell_lin):
        """Test split downstream from a division node."""
        new_lin = cell_lin._split_from_cell(4, split="downstream")
        assert sorted(new_lin.nodes()) == [5, 6, 7, 8, 9, 10]
        assert sorted(cell_lin.nodes()) == [1, 2, 3, 4, 11, 12, 13, 14, 15, 16]

    def test_root_upstream(self, cell_lin):
        """Test split upstream from a root node."""
        new_lin = cell_lin._split_from_cell(1, split="upstream")
        assert sorted(new_lin.nodes()) == list(range(1, 17))
        assert sorted(cell_lin.nodes()) == []

    def test_root_downstream(self, cell_lin):
        """Test split downstream from a root node."""
        new_lin = cell_lin._split_from_cell(1, split="downstream")
        assert sorted(new_lin.nodes()) == list(range(2, 17))
        assert sorted(cell_lin.nodes()) == [1]

    def test_leaf_upstream(self, cell_lin):
        """Test split upstream from a leaf node."""
        new_lin = cell_lin._split_from_cell(9, split="upstream")
        assert sorted(new_lin.nodes()) == [9]
        assert sorted(cell_lin.nodes()) == list(range(1, 9)) + list(range(10, 17))

    def test_leaf_downstream(self, cell_lin):
        """Test split downstream from a leaf node."""
        new_lin = cell_lin._split_from_cell(9, split="downstream")
        assert sorted(new_lin.nodes()) == []
        assert sorted(cell_lin.nodes()) == list(range(1, 17))

    def test_middle_upstream(self, cell_lin):
        """Test split upstream from a middle node."""
        new_lin = cell_lin._split_from_cell(12, split="upstream")
        assert sorted(new_lin.nodes()) == list(range(12, 17))
        assert sorted(cell_lin.nodes()) == list(range(1, 12))

    def test_middle_downstream(self, cell_lin):
        """Test split downstream from a middle node."""
        new_lin = cell_lin._split_from_cell(12, split="downstream")
        assert sorted(new_lin.nodes()) == list(range(13, 17))
        assert sorted(cell_lin.nodes()) == list(range(1, 13))

    def test_upstream_single_node(self, one_node_cell_lin):
        """Test split upstream from a single node."""
        new_lin = one_node_cell_lin._split_from_cell(1, split="upstream")
        assert sorted(new_lin.nodes()) == [1]
        assert sorted(one_node_cell_lin.nodes()) == []

    def test_downstream_single_node(self, one_node_cell_lin):
        """Test split downstream from a single node."""
        new_lin = one_node_cell_lin._split_from_cell(1, split="downstream")
        assert sorted(new_lin.nodes()) == []
        assert sorted(one_node_cell_lin.nodes()) == [1]

    def test_upstream_gap(self, cell_lin_gap):
        """Test split upstream from a node in a lineage with gaps."""
        new_lin = cell_lin_gap._split_from_cell(4, split="upstream")
        assert sorted(new_lin.nodes()) == [4, 6, 8, 9, 10]
        assert sorted(cell_lin_gap.nodes()) == [1, 2, 3, 11, 14, 15, 16]

    def test_downstream_gap(self, cell_lin_gap):
        """Test split downstream from a node in a lineage with gaps."""
        new_lin = cell_lin_gap._split_from_cell(4, split="downstream")
        assert sorted(new_lin.nodes()) == [6, 8, 9, 10]
        assert new_lin.in_degree(6) == 0
        assert sorted(cell_lin_gap.nodes()) == [1, 2, 3, 4, 11, 14, 15, 16]

    def test_upstream_div_root(self, cell_lin_div_root):
        """Test split upstream from a node in a lineage with a division root."""
        new_lin = cell_lin_div_root._split_from_cell(1, split="upstream")
        assert sorted(new_lin.nodes()) == list(range(1, 18))
        assert sorted(cell_lin_div_root.nodes()) == []

    def test_downstream_div_root(self, cell_lin_div_root):
        """Test split downstream from a node in a lineage with a division root."""
        new_lin = cell_lin_div_root._split_from_cell(1, split="downstream")
        assert sorted(new_lin.nodes()) == list(range(2, 18))
        assert sorted(cell_lin_div_root.nodes()) == [1]

    def test_upstream_unconnected_node(self, cell_lin_unconnected_node):
        """Test split upstream from an unconnected node."""
        new_lin = cell_lin_unconnected_node._split_from_cell(17, split="upstream")
        assert sorted(new_lin.nodes()) == [17]
        assert sorted(cell_lin_unconnected_node.nodes()) == list(range(1, 17))

    def test_downstream_unconnected_node(self, cell_lin_unconnected_node):
        """Test split downstream from an unconnected node."""
        new_lin = cell_lin_unconnected_node._split_from_cell(17, split="downstream")
        assert sorted(new_lin.nodes()) == []
        assert sorted(cell_lin_unconnected_node.nodes()) == list(range(1, 18))

    def test_upstream_unconnected_component(self, cell_lin_unconnected_component):
        """Test split upstream from a node in an unconnected component."""
        new_lin = cell_lin_unconnected_component._split_from_cell(17, split="upstream")
        assert sorted(new_lin.nodes()) == [17, 18]
        assert sorted(cell_lin_unconnected_component.nodes()) == list(range(1, 17))

    def test_downstream_unconnected_component(self, cell_lin_unconnected_component):
        """Test split downstream from a node in an unconnected component."""
        new_lin = cell_lin_unconnected_component._split_from_cell(
            17, split="downstream"
        )
        assert sorted(new_lin.nodes()) == [18]
        assert sorted(cell_lin_unconnected_component.nodes()) == list(range(1, 18))

    def test_invalid_node(self, cell_lin):
        """Test _split_from_cell raises ValueError on an invalid node."""
        with pytest.raises(ValueError):
            cell_lin._split_from_cell(99)

    def test_invalid_split(self, cell_lin):
        """Test _split_from_cell raises ValueError on an invalid split."""
        with pytest.raises(ValueError):
            cell_lin._split_from_cell(4, split="invalid")


class TestCellLineageGetDivisions:
    """Test cases for CellLineage.get_divisions method."""

    def test_normal_lineage(self, cell_lin):
        """Test get_divisions on normal lineage."""
        expected = [2, 4, 8, 14]
        assert sorted(cell_lin.get_divisions()) == sorted(expected)

    def test_empty_lineage(self, empty_cell_lin):
        """Test get_divisions on empty lineage."""
        assert empty_cell_lin.get_divisions() == []

    def test_single_node(self, one_node_cell_lin):
        """Test get_divisions on single node lineage."""
        assert one_node_cell_lin.get_divisions() == []

    def test_gap(self, cell_lin_gap):
        """Test get_divisions on lineage with gaps."""
        assert sorted(cell_lin_gap.get_divisions()) == [2, 4, 8, 14]
        assert sorted(cell_lin_gap.get_divisions([1, 2, 3, 4, 6, 8, 9, 10])) == [
            2,
            4,
            8,
        ]
        assert sorted(cell_lin_gap.get_divisions([1, 2, 3, 4])) == [2, 4]
        assert sorted(cell_lin_gap.get_divisions([4])) == [4]
        assert sorted(cell_lin_gap.get_divisions([1, 3, 11, 15, 16])) == []

    def test_div_root(self, cell_lin_div_root):
        """Test get_divisions on lineage with division root."""
        lin = cell_lin_div_root
        assert sorted(lin.get_divisions()) == [1, 2, 4, 8, 14]
        assert sorted(lin.get_divisions([1, 2, 3, 4, 6, 8, 9, 10])) == [1, 2, 4, 8]
        assert sorted(lin.get_divisions([1])) == [1]
        assert sorted(lin.get_divisions([3, 5, 7, 9])) == []

    def test_successive_divs_and_root(self, cell_lin_successive_divs_and_root):
        """Test get_divisions on lineage with successive divisions and division root."""
        lin = cell_lin_successive_divs_and_root
        assert sorted(lin.get_divisions()) == [2, 3, 5, 8]
        assert sorted(lin.get_divisions(list(range(2, 12)))) == [2, 3, 5, 8]
        assert sorted(lin.get_divisions([2, 3, 4, 5, 6, 7])) == [2, 3, 5]
        assert sorted(lin.get_divisions([3])) == [3]
        assert sorted(lin.get_divisions([4, 6, 7, 11])) == []

    def test_triple_div(self, cell_lin_triple_div):
        """Test get_divisions on lineage with triple division."""
        assert sorted(cell_lin_triple_div.get_divisions()) == [2, 4, 8, 14]
        assert sorted(cell_lin_triple_div.get_divisions([1, 2, 3, 4, 5, 6])) == [2, 4]
        assert sorted(cell_lin_triple_div.get_divisions([4])) == [4]
        assert sorted(cell_lin_triple_div.get_divisions([17, 18])) == []

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test get_divisions on unconnected node lineage."""
        lin = cell_lin_unconnected_node
        assert sorted(lin.get_divisions()) == [2, 4, 8, 14]
        assert sorted(lin.get_divisions(list(range(1, 18)))) == [2, 4, 8, 14]
        assert sorted(lin.get_divisions([1, 2, 3, 4, 17])) == [2, 4]
        assert sorted(lin.get_divisions([17])) == []

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test get_divisions on unconnected component lineage."""
        lin = cell_lin_unconnected_component
        assert sorted(lin.get_divisions()) == [2, 4, 8, 14]
        assert sorted(lin.get_divisions(list(range(1, 18)))) == [2, 4, 8, 14]
        assert sorted(lin.get_divisions([1, 2, 3, 4, 17, 18])) == [2, 4]
        assert sorted(lin.get_divisions([17])) == []

    def test_unconnected_component_div(self, cell_lin_unconnected_component_div):
        """Test get_divisions on unconnected component with multiple divisions."""
        lin = cell_lin_unconnected_component_div
        assert sorted(lin.get_divisions()) == [2, 4, 8, 14, 17, 19]
        assert sorted(lin.get_divisions(list(range(1, 23)))) == [2, 4, 8, 14, 17, 19]
        assert sorted(lin.get_divisions([1, 2, 3, 4, 17, 18, 19, 20])) == [2, 4, 17, 19]
        assert sorted(lin.get_divisions([17])) == [17]
        assert sorted(lin.get_divisions([19])) == [19]
        assert sorted(lin.get_divisions([20, 21, 22])) == []


# CellLineage cell cycle operations


class TestCellLineageGetCellCycle:
    """Test cases for CellLineage.get_cell_cycle method."""

    def test_normal_lin(self, cell_lin):
        """Test get_cell_cycle on normal lineage."""
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

    def test_single_node(self, one_node_cell_lin):
        """Test get_cell_cycle on single node lineage."""
        assert one_node_cell_lin.get_cell_cycle(1) == [1]

    def test_gap(self, cell_lin_gap):
        """Test get_cell_cycle on lineage with gaps."""
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

    def test_div_root(self, cell_lin_div_root):
        """Test get_cell_cycle on division root."""
        assert cell_lin_div_root.get_cell_cycle(1) == [1]
        assert cell_lin_div_root.get_cell_cycle(2) == [2]
        assert cell_lin_div_root.get_cell_cycle(17) == [17]

    def test_successive_divs_and_root(self, cell_lin_successive_divs_and_root):
        """Test get_cell_cycle on lineage with successive divisions and division root."""
        assert cell_lin_successive_divs_and_root.get_cell_cycle(2) == [2]
        assert cell_lin_successive_divs_and_root.get_cell_cycle(3) == [3]
        assert cell_lin_successive_divs_and_root.get_cell_cycle(4) == [4, 5]
        assert cell_lin_successive_divs_and_root.get_cell_cycle(5) == [4, 5]
        assert cell_lin_successive_divs_and_root.get_cell_cycle(6) == [6]
        assert cell_lin_successive_divs_and_root.get_cell_cycle(8) == [8]
        assert cell_lin_successive_divs_and_root.get_cell_cycle(9) == [9]
        assert cell_lin_successive_divs_and_root.get_cell_cycle(11) == [11]

    def test_triple_div(self, cell_lin_triple_div):
        """Test get_cell_cycle on lineage with triple division."""
        assert cell_lin_triple_div.get_cell_cycle(1) == [1, 2]
        assert cell_lin_triple_div.get_cell_cycle(4) == [3, 4]
        assert cell_lin_triple_div.get_cell_cycle(5) == [5, 6]
        assert cell_lin_triple_div.get_cell_cycle(8) == [7, 8]
        assert cell_lin_triple_div.get_cell_cycle(17) == [17, 18]
        assert cell_lin_triple_div.get_cell_cycle(18) == [17, 18]

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test get_cell_cycle on lineage with unconnected node."""
        assert cell_lin_unconnected_node.get_cell_cycle(17) == [17]

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test get_cell_cycle on lineage with unconnected component."""
        assert cell_lin_unconnected_component.get_cell_cycle(17) == [17, 18]
        assert cell_lin_unconnected_component.get_cell_cycle(18) == [17, 18]

    def test_unconnected_component_div(self, cell_lin_unconnected_component_div):
        """Test get_cell_cycle on lineage with unconnected component with divisions."""
        assert cell_lin_unconnected_component_div.get_cell_cycle(17) == [17]
        assert cell_lin_unconnected_component_div.get_cell_cycle(18) == [18]
        assert cell_lin_unconnected_component_div.get_cell_cycle(19) == [19]
        assert cell_lin_unconnected_component_div.get_cell_cycle(20) == [20, 21]
        assert cell_lin_unconnected_component_div.get_cell_cycle(21) == [20, 21]
        assert cell_lin_unconnected_component_div.get_cell_cycle(22) == [22]

    def test_fusion_error(self, cell_lin):
        """Test get_cell_cycle raises FusionError for fusion event."""
        cell_lin.add_edge(3, 12)
        with pytest.raises(FusionError):
            cell_lin.get_cell_cycle(12)


class TestCellLineageGetCellCycles:
    """Test cases for CellLineage.get_cell_cycles method."""

    def test_normal_lin(self, cell_lin):
        """Test get_cell_cycles on normal lineage."""
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

    def test_empty_lin(self, empty_cell_lin):
        """Test get_cell_cycles on empty lineage."""
        assert empty_cell_lin.get_cell_cycles() == []
        assert empty_cell_lin.get_cell_cycles(ignore_incomplete_cycles=True) == []

    def test_single_node(self, one_node_cell_lin):
        """Test get_cell_cycles on single node lineage."""
        assert one_node_cell_lin.get_cell_cycles() == [[1]]
        assert one_node_cell_lin.get_cell_cycles(ignore_incomplete_cycles=True) == []

    def test_gap(self, cell_lin_gap):
        """Test get_cell_cycles on lineage with gaps."""
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

    def test_div_root(self, cell_lin_div_root):
        """Test get_cell_cycles on lineage with division root."""
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
        assert (
            cell_lin_div_root.get_cell_cycles(ignore_incomplete_cycles=True) == expected
        )

    def test_successive_divs_and_root(self, cell_lin_successive_divs_and_root):
        """Test get_cell_cycles on lineage with successive divisions and division root."""
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

    def test_triple_div(self, cell_lin_triple_div):
        """Test get_cell_cycles on lineage with triple division."""
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

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test get_cell_cycles on lineage with unconnected node."""
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

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test get_cell_cycles on lineage with unconnected component."""
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

    def test_unconnected_component_div(self, cell_lin_unconnected_component_div):
        """Test get_cell_cycles on lineage with unconnected component with divisions."""
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

    def test_fusion_error(self, cell_lin):
        """Test get_cell_cycles raises FusionError for fusion event."""
        cell_lin.add_edge(3, 12)
        with pytest.raises(FusionError):
            cell_lin.get_cell_cycles()


class TestCellLineageGetSisterCells:
    """Test cases for CellLineage.get_sister_cells method."""

    def test_normal_lin(self, cell_lin):
        """Test get_sister_cells on normal lineage."""
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

    def test_single_node(self, one_node_cell_lin):
        """Test get_sister_cells on single node lineage."""
        assert one_node_cell_lin.get_sister_cells(1) == []

    def test_gap(self, cell_lin_gap):
        """Test get_sister_cells on lineage with gaps."""
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

    def test_div_root(self, cell_lin_div_root):
        """Test get_sister_cells on division root."""
        assert cell_lin_div_root.get_sister_cells(1) == []
        assert cell_lin_div_root.get_sister_cells(2) == [17]
        assert cell_lin_div_root.get_sister_cells(17) == [2]

    def test_successive_divs_and_root(self, cell_lin_successive_divs_and_root):
        """Test get_sister_cells on lineage with successive divisions and division root."""
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

    def test_triple_div(self, cell_lin_triple_div):
        """Test get_sister_cells on lineage with triple division."""
        assert cell_lin_triple_div.get_sister_cells(1) == []
        assert cell_lin_triple_div.get_sister_cells(2) == []
        assert cell_lin_triple_div.get_sister_cells(4) == [12]
        assert cell_lin_triple_div.get_sister_cells(5) == [7, 17]
        assert cell_lin_triple_div.get_sister_cells(6) == [8, 18]
        assert cell_lin_triple_div.get_sister_cells(7) == [5, 17]
        assert cell_lin_triple_div.get_sister_cells(8) == [6, 18]
        assert cell_lin_triple_div.get_sister_cells(13) == []
        assert cell_lin_triple_div.get_sister_cells(14) == []

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test get_sister_cells on unconnected node."""
        assert cell_lin_unconnected_node.get_sister_cells(1) == []
        assert cell_lin_unconnected_node.get_sister_cells(17) == []

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test get_sister_cells on unconnected component."""
        assert cell_lin_unconnected_component.get_sister_cells(1) == []
        assert cell_lin_unconnected_component.get_sister_cells(2) == []
        assert cell_lin_unconnected_component.get_sister_cells(17) == []
        assert cell_lin_unconnected_component.get_sister_cells(18) == []

    def test_unconnected_component_div(self, cell_lin_unconnected_component_div):
        """Test get_sister_cells on unconnected component with divisions."""
        assert cell_lin_unconnected_component_div.get_sister_cells(1) == []
        assert cell_lin_unconnected_component_div.get_sister_cells(2) == []
        assert cell_lin_unconnected_component_div.get_sister_cells(17) == []
        assert cell_lin_unconnected_component_div.get_sister_cells(18) == [19]
        assert cell_lin_unconnected_component_div.get_sister_cells(19) == [18]
        assert cell_lin_unconnected_component_div.get_sister_cells(20) == [22]
        assert cell_lin_unconnected_component_div.get_sister_cells(22) == [20]
        assert cell_lin_unconnected_component_div.get_sister_cells(21) == []

    def test_fusion_error(self, cell_lin):
        """Test get_sister_cells raises FusionError for fusion event."""
        cell_lin.add_edge(3, 12)
        with pytest.raises(FusionError):
            cell_lin.get_sister_cells(12)


class TestCellLineageIsDivision:
    """Test cases for CellLineage.is_division method."""

    def test_normal_lineage(self, cell_lin):
        """Test is_division on normal lineage."""
        # Root.
        assert not cell_lin.is_division(1)
        # Divisions.
        assert cell_lin.is_division(2)
        assert cell_lin.is_division(4)
        assert cell_lin.is_division(8)
        assert cell_lin.is_division(14)
        # Just after division.
        assert not cell_lin.is_division(3)
        assert not cell_lin.is_division(5)
        assert not cell_lin.is_division(7)
        assert not cell_lin.is_division(11)
        # Leaves.
        assert not cell_lin.is_division(6)
        assert not cell_lin.is_division(9)
        assert not cell_lin.is_division(10)
        assert not cell_lin.is_division(15)
        assert not cell_lin.is_division(16)

    def test_single_node(self, one_node_cell_lin):
        """Test is_division on single node lineage."""
        assert not one_node_cell_lin.is_division(1)

    def test_gap(self, cell_lin_gap):
        """Test is_division on lineage with gaps."""
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

    def test_div_root(self, cell_lin_div_root):
        """Test is_division on lineage with division root."""
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

    def test_successive_divs_and_root(self, cell_lin_successive_divs_and_root):
        """Test is_division on lineage with successive divisions and division root."""
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

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test is_division on lineage with unconnected node."""
        assert not cell_lin_unconnected_node.is_division(17)

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test is_division on lineage with unconnected component."""
        assert not cell_lin_unconnected_component.is_division(17)
        assert not cell_lin_unconnected_component.is_division(18)

    def test_unconnected_component_div(self, cell_lin_unconnected_component_div):
        """Test is_division on lineage with unconnected component with divisions."""
        assert cell_lin_unconnected_component_div.is_division(17)
        assert cell_lin_unconnected_component_div.is_division(19)
        assert not cell_lin_unconnected_component_div.is_division(20)
        assert not cell_lin_unconnected_component_div.is_division(21)
        assert not cell_lin_unconnected_component_div.is_division(22)


# CycleLineage operations


class TestCycleLineageInit:
    """Test cases for CycleLineage.__init__ method."""

    def test_normal_lin(self, cell_lin):
        """Test CycleLineage creation on normal lineage."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=cell_lin
        )
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

    def test_empty_lin(self, empty_cell_lin):
        """Test CycleLineage creation on empty lineage."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=empty_cell_lin
        )
        assert len(cycle_lin) == 0
        assert cycle_lin.graph["lineage_ID"] == 1

    def test_single_node(self, one_node_cell_lin):
        """Test CycleLineage creation on single node lineage."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=one_node_cell_lin
        )
        assert len(cycle_lin) == 1
        assert cycle_lin.graph["lineage_ID"] == 1
        assert cycle_lin.nodes[1]["cycle_ID"] == 1
        assert cycle_lin.nodes[1]["cells"] == [1]
        assert cycle_lin.nodes[1]["cycle_length"] == 1
        assert cycle_lin.nodes[1]["level"] == 0

    def test_gap(self, cell_lin_gap):
        """Test CycleLineage creation on lineage with gaps."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=cell_lin_gap
        )
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

    def test_div_root(self, cell_lin_div_root):
        """Test CycleLineage creation on lineage with division root."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=cell_lin_div_root
        )
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

    def test_successive_divs_and_root(self, cell_lin_successive_divs_and_root):
        """Test CycleLineage creation on lineage with successive divisions and division root."""
        cycle_lin = CycleLineage(
            time_prop="timepoint",
            time_step=1,
            cell_lineage=cell_lin_successive_divs_and_root,
        )
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

    def test_triple_div(self, cell_lin_triple_div):
        """Test CycleLineage creation on lineage with triple division."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=cell_lin_triple_div
        )
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

    def test_unconnected_node(self, cell_lin_unconnected_node):
        """Test CycleLineage creation on lineage with unconnected node."""
        with pytest.raises(LineageStructureError):
            CycleLineage(
                time_prop="timepoint",
                time_step=1,
                cell_lineage=cell_lin_unconnected_node,
            )

    def test_unconnected_component(self, cell_lin_unconnected_component):
        """Test CycleLineage creation on lineage with unconnected component."""
        with pytest.raises(LineageStructureError):
            CycleLineage(
                time_prop="timepoint",
                time_step=1,
                cell_lineage=cell_lin_unconnected_component,
            )


class TestCycleLineageGetAncestors:
    """Test cases for CycleLineage.get_ancestors method."""

    def test_key_error(self, cycle_lin):
        """Test get_ancestors raises KeyError for non-existing cycle_ID."""
        with pytest.raises(KeyError):
            cycle_lin.get_ancestors(0)

    def test_cannot_order_cycle(self, cycle_lin):
        """Test get_ancestors raises UserWarning if 'level' property is missing."""
        for n in cycle_lin.nodes:
            del cycle_lin.nodes[n]["level"]
        msg = "No 'level' property to order the cell cycles."
        with pytest.warns(UserWarning, match=msg):
            cycle_lin.get_ancestors(5)


class TestCycleLineageGetEdgesWithinCycle:
    """Test cases for CycleLineage.get_edges_within_cycle method."""

    def test_normal_lin(self, cell_lin):
        """Test get_edges_within_cycle on normal lineage."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=cell_lin
        )
        # From division.
        assert cycle_lin.get_links_within_cycle(2) == [(1, 2)]
        assert cycle_lin.get_links_within_cycle(4) == [(3, 4)]
        assert cycle_lin.get_links_within_cycle(8) == [(7, 8)]
        assert cycle_lin.get_links_within_cycle(14) == [(11, 12), (12, 13), (13, 14)]
        # From leaf.
        assert cycle_lin.get_links_within_cycle(6) == [(5, 6)]
        assert cycle_lin.get_links_within_cycle(9) == []
        assert cycle_lin.get_links_within_cycle(16) == []

    def test_single_node(self, one_node_cell_lin):
        """Test get_edges_within_cycle on single node lineage."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=one_node_cell_lin
        )
        assert cycle_lin.get_links_within_cycle(1) == []

    def test_gap(self, cell_lin_gap):
        """Test get_edges_within_cycle on lineage with gaps."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=cell_lin_gap
        )
        # From division.
        assert cycle_lin.get_links_within_cycle(2) == [(1, 2)]
        assert cycle_lin.get_links_within_cycle(4) == [(3, 4)]
        assert cycle_lin.get_links_within_cycle(8) == []
        assert cycle_lin.get_links_within_cycle(14) == [(11, 14)]
        # From leaf.
        assert cycle_lin.get_links_within_cycle(6) == []
        assert cycle_lin.get_links_within_cycle(9) == []
        assert cycle_lin.get_links_within_cycle(16) == []

    def test_div_root(self, cell_lin_div_root):
        """Test get_edges_within_cycle on lineage with division root."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=cell_lin_div_root
        )
        assert cycle_lin.get_links_within_cycle(1) == []
        assert cycle_lin.get_links_within_cycle(2) == []
        assert cycle_lin.get_links_within_cycle(17) == []

    def test_successive_divs_and_root(
        self,
        cell_lin_successive_divs_and_root,
    ):
        """Test get_edges_within_cycle on lineage with successive divisions and division root."""
        cycle_lin = CycleLineage(
            time_prop="timepoint",
            time_step=1,
            cell_lineage=cell_lin_successive_divs_and_root,
        )
        assert cycle_lin.get_links_within_cycle(2) == []
        assert cycle_lin.get_links_within_cycle(3) == []
        assert cycle_lin.get_links_within_cycle(5) == [(4, 5)]
        assert cycle_lin.get_links_within_cycle(6) == []
        assert cycle_lin.get_links_within_cycle(8) == []
        assert cycle_lin.get_links_within_cycle(9) == []
        assert cycle_lin.get_links_within_cycle(11) == []

    def test_triple_div(self, cell_lin_triple_div):
        """Test get_edges_within_cycle on lineage with triple division."""
        cycle_lin = CycleLineage(
            time_prop="timepoint", time_step=1, cell_lineage=cell_lin_triple_div
        )
        assert cycle_lin.get_links_within_cycle(4) == [(3, 4)]
        assert cycle_lin.get_links_within_cycle(6) == [(5, 6)]
        assert cycle_lin.get_links_within_cycle(8) == [(7, 8)]
        assert cycle_lin.get_links_within_cycle(18) == [(17, 18)]
