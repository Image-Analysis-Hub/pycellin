#!/usr/bin/env python3

"""Unit test for IO utilities functions."""

import networkx as nx
import pytest

from pycellin.classes import CellLineage
from pycellin.io.utils import (
    _add_lineage_props,
    _split_graph_into_lineages,
    _update_lineage_prop_key,
    _update_lineages_IDs_key,
    _update_node_prop_key,
)
from pycellin.utils import is_equal


# Fixtures ####################################################################


@pytest.fixture
def lineage_with_old_key():
    """Lineage with nodes that all have old_key property."""
    lineage = CellLineage()
    lineage.add_node(1, old_key="value1")
    lineage.add_node(2, old_key="value2")
    lineage.add_node(3, old_key="value3")
    return lineage


@pytest.fixture
def lineage_with_mixed_keys():
    """Lineage with some nodes having old_key and some without."""
    lineage = CellLineage()
    lineage.add_node(1, old_key="value1")
    lineage.add_node(2)  # No old_key
    lineage.add_node(3, old_key="value3")
    return lineage


@pytest.fixture
def lineage_attrs():
    """Common lineage attribute dictionaries for testing."""
    return [
        {"name": "blob", "lineage_ID": 0},
        {"name": "blub", "lineage_ID": 1},
    ]


@pytest.fixture
def lineage_attrs_with_track_id():
    """Lineage attribute dictionaries using TRACK_ID."""
    return [
        {"name": "blob", "TRACK_ID": 0},
        {"name": "blub", "TRACK_ID": 1},
    ]


# Test classes ###############################################################


class TestUpdateNodePropKey:
    """Test cases for _update_node_prop_key function."""

    def test_update_node_prop_key(self, lineage_with_old_key):
        """Test basic update of node property key."""
        old_key_values = ["value1", "value2", "value3"]
        _update_node_prop_key(lineage_with_old_key, "old_key", "new_key")

        for i, node in enumerate(lineage_with_old_key.nodes):
            assert "new_key" in lineage_with_old_key.nodes[node]
            assert "old_key" not in lineage_with_old_key.nodes[node]
            assert lineage_with_old_key.nodes[node]["new_key"] == old_key_values[i]

    def test_missing_old_key_skip(self, lineage_with_mixed_keys):
        """Test that nodes without old_key are skipped when enforce_old_key_existence=False."""
        _update_node_prop_key(lineage_with_mixed_keys, "old_key", "new_key")

        assert lineage_with_mixed_keys.nodes[1]["new_key"] == "value1"
        assert "old_key" not in lineage_with_mixed_keys.nodes[1]
        assert "new_key" not in lineage_with_mixed_keys.nodes[2]
        assert "old_key" not in lineage_with_mixed_keys.nodes[2]
        assert lineage_with_mixed_keys.nodes[3]["new_key"] == "value3"
        assert "old_key" not in lineage_with_mixed_keys.nodes[3]

    def test_enforce_old_key_existence(self, lineage_with_mixed_keys):
        """Test that missing old_key raises error when enforce_old_key_existence=True."""
        err_msg = "Node 2 does not have the required key 'old_key'"
        with pytest.raises(ValueError, match=err_msg):
            _update_node_prop_key(
                lineage_with_mixed_keys,
                "old_key",
                "new_key",
                enforce_old_key_existence=True,
            )

    def test_set_default_if_missing(self, lineage_with_mixed_keys):
        """Test setting default value when old_key is missing and set_default_if_missing=True."""
        _update_node_prop_key(
            lineage_with_mixed_keys,
            "old_key",
            "new_key",
            set_default_if_missing=True,
            default_value="default",
        )

        assert lineage_with_mixed_keys.nodes[1]["new_key"] == "value1"
        assert "old_key" not in lineage_with_mixed_keys.nodes[1]
        assert lineage_with_mixed_keys.nodes[2]["new_key"] == "default"
        assert "old_key" not in lineage_with_mixed_keys.nodes[2]
        assert lineage_with_mixed_keys.nodes[3]["new_key"] == "value3"
        assert "old_key" not in lineage_with_mixed_keys.nodes[3]

    def test_set_default_none(self, lineage_with_mixed_keys):
        """Test setting None as default value when old_key is missing."""
        _update_node_prop_key(
            lineage_with_mixed_keys, "old_key", "new_key", set_default_if_missing=True
        )

        assert lineage_with_mixed_keys.nodes[1]["new_key"] == "value1"
        assert lineage_with_mixed_keys.nodes[2]["new_key"] is None

    def test_empty_lineage(self):
        """Test function with empty lineage (no nodes)."""
        lineage = CellLineage()
        # Should not raise an error and do nothing
        _update_node_prop_key(lineage, "old_key", "new_key")
        assert len(lineage.nodes) == 0

    def test_same_key_name(self):
        """Test updating a key to itself (should work without issues)."""
        lineage = CellLineage()
        lineage.add_node(1, test_key="value1")
        lineage.add_node(2, test_key="value2")

        _update_node_prop_key(lineage, "test_key", "test_key")

        assert lineage.nodes[1]["test_key"] == "value1"
        assert lineage.nodes[2]["test_key"] == "value2"


class TestUpdateLineagePropKey:
    """Test cases for _update_lineage_prop_key function."""

    def test_update_lineage_prop_key(self):
        """Test updating a lineage property key."""
        lineage = CellLineage()
        lineage.graph["old_key"] = "old_value"
        _update_lineage_prop_key(lineage, "old_key", "new_key")

        assert "new_key" in lineage.graph
        assert lineage.graph["new_key"] == "old_value"
        assert "old_key" not in lineage.graph


class TestUpdateLineagesIDsKey:
    """Test cases for _update_lineages_IDs_key function."""

    def test_update_lineages_IDs_key(self):
        """Test updating lineage IDs key."""
        lin1 = CellLineage()
        lin1.add_nodes_from([1, 2, 3])
        lin1.graph["TRACK_ID"] = 10
        lin2 = CellLineage()
        lin2.add_nodes_from([4, 5])
        lin2.graph["TRACK_ID"] = 20

        _update_lineages_IDs_key([lin1, lin2], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == 10
        assert lin2.graph["lineage_ID"] == 20
        assert "TRACK_ID" not in lin1.graph
        assert "TRACK_ID" not in lin2.graph

    def test_no_key_multi_node(self):
        """Test updating lineage IDs key when no TRACK_ID key is present in a multi-node lineage."""
        lin1 = CellLineage()
        lin1.add_nodes_from([1, 2, 3])
        lin2 = CellLineage()
        lin2.add_nodes_from([4, 5])
        lin2.graph["TRACK_ID"] = 20

        _update_lineages_IDs_key([lin1, lin2], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == 21
        assert lin2.graph["lineage_ID"] == 20
        assert "TRACK_ID" not in lin1.graph
        assert "TRACK_ID" not in lin2.graph

    def test_no_key_one_node(self):
        """Test updating lineage IDs key when no TRACK_ID key is present in a one-node lineage."""
        lin1 = CellLineage()
        lin1.add_node(1)
        lin2 = CellLineage()
        lin2.add_nodes_from([4, 5])
        lin2.graph["TRACK_ID"] = 20
        _update_lineages_IDs_key([lin1, lin2], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == -1
        assert lin2.graph["lineage_ID"] == 20

    def test_all_lineages_no_key(self):
        """Test updating lineage IDs key when no lineages have the key."""
        lin1 = CellLineage()
        lin1.add_nodes_from([1, 2, 3])
        lin2 = CellLineage()
        lin2.add_nodes_from([4, 5])
        lin3 = CellLineage()
        lin3.add_node(6)

        _update_lineages_IDs_key([lin1, lin2, lin3], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == 0
        assert lin2.graph["lineage_ID"] == 1
        assert lin3.graph["lineage_ID"] == -6
        assert "TRACK_ID" not in lin1.graph
        assert "TRACK_ID" not in lin2.graph
        assert "TRACK_ID" not in lin3.graph

    def test_empty_list(self):
        """Test updating lineage IDs key with empty lineages list."""
        _update_lineages_IDs_key([], "TRACK_ID")

    def test_mixed_scenarios(self):
        """Test with mix of single-node, multi-node, and lineages with existing keys."""
        lin1 = CellLineage()  # single node, no key
        lin1.add_node(1)
        lin2 = CellLineage()  # multi-node, no key
        lin2.add_nodes_from([2, 3])
        lin3 = CellLineage()  # has key
        lin3.add_node(4)
        lin3.graph["TRACK_ID"] = 10
        lin4 = CellLineage()  # single node, no key
        lin4.add_node(5)

        _update_lineages_IDs_key([lin1, lin2, lin3, lin4], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == -1
        assert lin2.graph["lineage_ID"] == 11
        assert lin3.graph["lineage_ID"] == 10
        assert lin4.graph["lineage_ID"] == -5

    def test_preserves_other_graph_attributes(self):
        """Test that other graph attributes are preserved."""
        lin1 = CellLineage()
        lin1.add_node(1)
        lin1.graph["TRACK_ID"] = 10
        lin1.graph["other_attr"] = "value"

        _update_lineages_IDs_key([lin1], "TRACK_ID")
        assert lin1.graph["lineage_ID"] == 10
        assert lin1.graph["other_attr"] == "value"
        assert "TRACK_ID" not in lin1.graph


class TestAddLineagesProps:
    """Test cases for _add_lineage_props function."""

    def test_add_lineages_props(self, lineage_attrs):
        """Test adding lineage properties to graphs."""
        g1_attr, g2_attr = lineage_attrs

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1, lineage_ID=0)
        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr])

        g1_exp = nx.DiGraph()
        g1_exp.graph["name"] = "blob"
        g1_exp.graph["lineage_ID"] = 0
        g1_exp.add_node(1, lineage_ID=0)
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["lineage_ID"] = 1
        g2_exp.add_node(2, lineage_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)

    def test_different_lin_ID_key(self, lineage_attrs_with_track_id):
        """Test adding lineage properties with different lineage ID key."""
        g1_attr, g2_attr = lineage_attrs_with_track_id

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1, TRACK_ID=0)
        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, TRACK_ID=1)
        _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr], lineage_ID_key="TRACK_ID")

        g1_exp = nx.DiGraph()
        g1_exp.graph["name"] = "blob"
        g1_exp.graph["TRACK_ID"] = 0
        g1_exp.add_node(1, TRACK_ID=0)
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["TRACK_ID"] = 1
        g2_exp.add_node(2, TRACK_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)

    def test_no_lin_ID_on_all_nodes(self, lineage_attrs):
        """Test adding lineage properties when no nodes have lineage ID."""
        g1_attr, g2_attr = lineage_attrs

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1)
        g1_obt.add_node(3)
        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr], lineage_ID_key="lineage_ID")

        g1_exp = nx.DiGraph()
        g1_exp.add_node(1)
        g1_exp.add_node(3)
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["lineage_ID"] = 1
        g2_exp.add_node(2, lineage_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)

    def test_no_lin_ID_on_one_node(self, lineage_attrs):
        """Test adding lineage properties when some nodes lack lineage ID."""
        g1_attr, g2_attr = lineage_attrs

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1)
        g1_obt.add_node(3)
        g1_obt.add_node(4, lineage_ID=0)

        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr])

        g1_exp = nx.DiGraph()
        g1_exp.graph["name"] = "blob"
        g1_exp.graph["lineage_ID"] = 0
        g1_exp.add_node(1)
        g1_exp.add_node(3)
        g1_exp.add_node(4, lineage_ID=0)
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["lineage_ID"] = 1
        g2_exp.add_node(2, lineage_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)

    def test_different_ID_for_one_track(self, lineage_attrs):
        """Test that different lineage IDs within one graph raises error."""
        g1_attr, g2_attr = lineage_attrs

        g1_obt = nx.DiGraph()
        g1_obt.add_node(1, lineage_ID=0)
        g1_obt.add_node(3, lineage_ID=2)
        g1_obt.add_node(4, lineage_ID=0)

        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        with pytest.raises(ValueError):
            _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr])

    def test_no_nodes(self, lineage_attrs):
        """Test adding lineage properties to graph with no nodes."""
        g1_attr, g2_attr = lineage_attrs

        g1_obt = nx.DiGraph()
        g2_obt = nx.DiGraph()
        g2_obt.add_node(2, lineage_ID=1)
        _add_lineage_props([g1_obt, g2_obt], [g1_attr, g2_attr])

        g1_exp = nx.DiGraph()
        g2_exp = nx.DiGraph()
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["lineage_ID"] = 1
        g2_exp.add_node(2, lineage_ID=1)

        assert is_equal(g1_obt, g1_exp)
        assert is_equal(g2_obt, g2_exp)


class TestSplitGraphIntoLineages:
    """Test cases for _split_graph_into_lineages function."""

    def test_split_graph_into_lineages(self, lineage_attrs):
        """Test splitting graph into lineages."""
        g1_attr, g2_attr = lineage_attrs

        g = nx.DiGraph()
        g.add_node(1, lineage_ID=0)
        g.add_node(2, lineage_ID=0)
        g.add_edge(1, 2)
        g.add_node(3, lineage_ID=1)
        g.add_node(4, lineage_ID=1)
        g.add_edge(3, 4)
        obtained = _split_graph_into_lineages(g, [g1_attr, g2_attr])

        g1_exp = CellLineage(g.subgraph([1, 2]))
        g1_exp.graph["name"] = "blob"
        g1_exp.graph["lineage_ID"] = 0
        g2_exp = CellLineage(g.subgraph([3, 4]))
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["lineage_ID"] = 1

        assert len(obtained) == 2
        assert is_equal(obtained[0], g1_exp)
        assert is_equal(obtained[1], g2_exp)

    def test_different_lin_ID_key(self, lineage_attrs_with_track_id):
        """Test splitting graph with different lineage ID key."""
        g1_attr, g2_attr = lineage_attrs_with_track_id

        g = nx.DiGraph()
        g.add_node(1, TRACK_ID=0)
        g.add_node(2, TRACK_ID=0)
        g.add_edge(1, 2)
        g.add_node(3, TRACK_ID=1)
        g.add_node(4, TRACK_ID=1)
        g.add_edge(3, 4)
        obtained = _split_graph_into_lineages(g, [g1_attr, g2_attr], lineage_ID_key="TRACK_ID")

        g1_exp = CellLineage(g.subgraph([1, 2]))
        g1_exp.graph["name"] = "blob"
        g1_exp.graph["TRACK_ID"] = 0
        g2_exp = CellLineage(g.subgraph([3, 4]))
        g2_exp.graph["name"] = "blub"
        g2_exp.graph["TRACK_ID"] = 1

        assert len(obtained) == 2
        assert is_equal(obtained[0], g1_exp)
        assert is_equal(obtained[1], g2_exp)

    def test_no_lin_props(self):
        """Test splitting graph with no lineage properties."""
        g = nx.DiGraph()
        g.add_edges_from([(1, 2), (3, 4)])

        obtained = _split_graph_into_lineages(g)

        g1_exp = CellLineage(g.subgraph([1, 2]))
        g1_exp.graph["lineage_ID"] = 0
        g2_exp = CellLineage(g.subgraph([3, 4]))
        g2_exp.graph["lineage_ID"] = 1

        assert len(obtained) == 2
        assert is_equal(obtained[0], g1_exp)
        assert is_equal(obtained[1], g2_exp)

    def test_different_ID(self, lineage_attrs):
        """Test that different lineage IDs in connected nodes raises error."""
        g1_attr, g2_attr = lineage_attrs

        g = nx.DiGraph()
        g.add_node(1, lineage_ID=2)
        g.add_node(2, lineage_ID=0)
        g.add_edge(1, 2)
        g.add_node(3, lineage_ID=1)
        g.add_node(4, lineage_ID=1)
        g.add_edge(3, 4)

        with pytest.raises(ValueError):
            _split_graph_into_lineages(g, [g1_attr, g2_attr])
