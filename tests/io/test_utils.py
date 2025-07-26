#!/usr/bin/env python3

"""Unit test for IO utilities functions."""

import networkx as nx
import pytest

from pycellin.classes import CellLineage
from pycellin.io.utils import _add_lineages_features, _split_graph_into_lineages
from pycellin.utils import is_equal

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
