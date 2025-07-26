#!/usr/bin/env python3

"""Unit test for IO utilities functions."""

import networkx as nx
import pytest

from pycellin.classes import CellLineage
from pycellin.io.utils import (
    _add_lineages_features,
    _split_graph_into_lineages,
    _update_node_feature_key,
    _update_lineage_feature_key,
    _update_lineage_ID_key,
)
from pycellin.utils import is_equal


# _update_node_feature_key ####################################################


def test_update_node_feature_key():
    lineage = CellLineage()
    old_key_values = ["value1", "value2", "value3"]
    lineage.add_node(1, old_key=old_key_values[0])
    lineage.add_node(2, old_key=old_key_values[1])
    lineage.add_node(3, old_key=old_key_values[2])

    _update_node_feature_key(lineage, "old_key", "new_key")

    for i, node in enumerate(lineage.nodes):
        assert "new_key" in lineage.nodes[node]
        assert "old_key" not in lineage.nodes[node]
        assert lineage.nodes[node]["new_key"] == old_key_values[i]


# _update_lineage_feature_key #################################################


def test_update_lineage_feature_key():
    lineage = CellLineage()
    lineage.graph["old_key"] = "old_value"
    _update_lineage_feature_key(lineage, "old_key", "new_key")

    assert "new_key" in lineage.graph
    assert lineage.graph["new_key"] == "old_value"
    assert "old_key" not in lineage.graph


# _update_lineage_feature_key #################################################


def test_update_lineage_ID_key():
    lineage = CellLineage()
    lineage.add_nodes_from([1, 2, 3])
    lineage.graph["TRACK_ID"] = 10
    new_lin_ID = _update_lineage_ID_key(lineage, "TRACK_ID")
    assert new_lin_ID is None
    assert "lineage_ID" in lineage.graph
    assert lineage.graph["lineage_ID"] == 10
    assert "lineage_ID" not in lineage.nodes[1]


def test_update_lineage_ID_key_no_key_multi_node():
    lineage = CellLineage()
    lineage.add_nodes_from([1, 2, 3])
    new_lin_ID = _update_lineage_ID_key(lineage, "TRACK_ID", 0)
    assert new_lin_ID == 0
    assert "lineage_ID" in lineage.graph
    assert lineage.graph["lineage_ID"] == 0


def test_update_lineage_ID_key_no_key_one_node():
    lineage = CellLineage()
    lineage.add_node(1)
    new_lin_ID = _update_lineage_ID_key(lineage, "TRACK_ID")
    assert new_lin_ID == -1
    assert "lineage_ID" in lineage.graph
    assert lineage.graph["lineage_ID"] == -1


def test_update_lineage_ID_key_no_key_no_new_ID():
    lineage = CellLineage()
    lineage.add_nodes_from([1, 2, 3])
    with pytest.raises(
        TypeError,
        match=(
            "Missing available_ID argument for multi-node lineage with no TRACK_ID key."
        ),
    ):
        _update_lineage_ID_key(lineage, "TRACK_ID", None)


# _add_lineages_features ############################################################


def test_add_lineages_features():
    g1_attr = {"name": "blob", "lineage_ID": 0}
    g2_attr = {"name": "blub", "lineage_ID": 1}

    g1_obt = nx.DiGraph()
    g1_obt.add_node(1, lineage_ID=0)
    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, lineage_ID=1)
    _add_lineages_features([g1_obt, g2_obt], [g1_attr, g2_attr])

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


def test_add_lineages_features_different_lin_ID_key():
    g1_attr = {"name": "blob", "TRACK_ID": 0}
    g2_attr = {"name": "blub", "TRACK_ID": 1}

    g1_obt = nx.DiGraph()
    g1_obt.add_node(1, TRACK_ID=0)
    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, TRACK_ID=1)
    _add_lineages_features(
        [g1_obt, g2_obt], [g1_attr, g2_attr], lineage_ID_key="TRACK_ID"
    )

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


def test_add_lineages_features_no_lin_ID_on_all_nodes():
    g1_attr = {"name": "blob", "lineage_ID": 0}
    g2_attr = {"name": "blub", "lineage_ID": 1}

    g1_obt = nx.DiGraph()
    g1_obt.add_node(1)
    g1_obt.add_node(3)
    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, lineage_ID=1)
    _add_lineages_features(
        [g1_obt, g2_obt], [g1_attr, g2_attr], lineage_ID_key="lineage_ID"
    )

    g1_exp = nx.DiGraph()
    g1_exp.add_node(1)
    g1_exp.add_node(3)
    g2_exp = nx.DiGraph()
    g2_exp.graph["name"] = "blub"
    g2_exp.graph["lineage_ID"] = 1
    g2_exp.add_node(2, lineage_ID=1)

    assert is_equal(g1_obt, g1_exp)
    assert is_equal(g2_obt, g2_exp)


def test_add_lineages_features_no_lin_ID_on_one_node():
    g1_attr = {"name": "blob", "lineage_ID": 0}
    g2_attr = {"name": "blub", "lineage_ID": 1}

    g1_obt = nx.DiGraph()
    g1_obt.add_node(1)
    g1_obt.add_node(3)
    g1_obt.add_node(4, lineage_ID=0)

    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, lineage_ID=1)
    _add_lineages_features([g1_obt, g2_obt], [g1_attr, g2_attr])

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


def test_add_lineages_features_different_ID_for_one_track():
    g1_attr = {"name": "blob", "lineage_ID": 0}
    g2_attr = {"name": "blub", "lineage_ID": 1}

    g1_obt = nx.DiGraph()
    g1_obt.add_node(1, lineage_ID=0)
    g1_obt.add_node(3, lineage_ID=2)
    g1_obt.add_node(4, lineage_ID=0)

    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, lineage_ID=1)
    with pytest.raises(ValueError):
        _add_lineages_features([g1_obt, g2_obt], [g1_attr, g2_attr])


def test_add_lineages_features_no_nodes():
    g1_attr = {"name": "blob", "lineage_ID": 0}
    g2_attr = {"name": "blub", "lineage_ID": 1}

    g1_obt = nx.DiGraph()
    g2_obt = nx.DiGraph()
    g2_obt.add_node(2, lineage_ID=1)
    _add_lineages_features([g1_obt, g2_obt], [g1_attr, g2_attr])

    g1_exp = nx.DiGraph()
    g2_exp = nx.DiGraph()
    g2_exp.graph["name"] = "blub"
    g2_exp.graph["lineage_ID"] = 1
    g2_exp.add_node(2, lineage_ID=1)

    assert is_equal(g1_obt, g1_exp)
    assert is_equal(g2_obt, g2_exp)


# _split_graph_into_lineages ##################################################


def test_split_graph_into_lineages():
    g1_attr = {"name": "blob", "lineage_ID": 1}
    g2_attr = {"name": "blub", "lineage_ID": 2}

    g = nx.DiGraph()
    g.add_node(1, lineage_ID=1)
    g.add_node(2, lineage_ID=1)
    g.add_edge(1, 2)
    g.add_node(3, lineage_ID=2)
    g.add_node(4, lineage_ID=2)
    g.add_edge(3, 4)
    obtained = _split_graph_into_lineages(g, [g1_attr, g2_attr])

    g1_exp = CellLineage(g.subgraph([1, 2]))
    g1_exp.graph["name"] = "blob"
    g1_exp.graph["lineage_ID"] = 1
    g2_exp = CellLineage(g.subgraph([3, 4]))
    g2_exp.graph["name"] = "blub"
    g2_exp.graph["lineage_ID"] = 2

    assert len(obtained) == 2
    assert is_equal(obtained[0], g1_exp)
    assert is_equal(obtained[1], g2_exp)


def test_split_graph_into_lineages_different_lin_ID_key():
    g1_attr = {"name": "blob", "TRACK_ID": 1}
    g2_attr = {"name": "blub", "TRACK_ID": 2}

    g = nx.DiGraph()
    g.add_node(1, TRACK_ID=1)
    g.add_node(2, TRACK_ID=1)
    g.add_edge(1, 2)
    g.add_node(3, TRACK_ID=2)
    g.add_node(4, TRACK_ID=2)
    g.add_edge(3, 4)
    obtained = _split_graph_into_lineages(
        g, [g1_attr, g2_attr], lineage_ID_key="TRACK_ID"
    )

    g1_exp = CellLineage(g.subgraph([1, 2]))
    g1_exp.graph["name"] = "blob"
    g1_exp.graph["TRACK_ID"] = 1
    g2_exp = CellLineage(g.subgraph([3, 4]))
    g2_exp.graph["name"] = "blub"
    g2_exp.graph["TRACK_ID"] = 2

    assert len(obtained) == 2
    assert is_equal(obtained[0], g1_exp)
    assert is_equal(obtained[1], g2_exp)


def test_split_graph_into_lineages_no_lin_features():
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


def test_split_graph_into_lineages_different_ID():
    g1_attr = {"name": "blob", "lineage_ID": 1}
    g2_attr = {"name": "blub", "lineage_ID": 2}

    g = nx.DiGraph()
    g.add_node(1, lineage_ID=0)
    g.add_node(2, lineage_ID=1)
    g.add_edge(1, 2)
    g.add_node(3, lineage_ID=2)
    g.add_node(4, lineage_ID=2)
    g.add_edge(3, 4)

    with pytest.raises(ValueError):
        _split_graph_into_lineages(g, [g1_attr, g2_attr])
