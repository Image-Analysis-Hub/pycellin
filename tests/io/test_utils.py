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
    _update_lineages_IDs_key,
)
from pycellin.utils import is_equal


# _update_node_feature_key ####################################################


# def _update_node_feature_key(
#     lineage: CellLineage,
#     old_key: str,
#     new_key: str,
#     enforce_old_key_existence: bool = False,
#     set_default_if_missing: bool = False,
#     default_value: Any | None = None,
# ) -> None:
#     """
#     Update the key of a feature in all the nodes of a lineage.

#     Parameters
#     ----------
#     lineage : CellLineage
#         The lineage to update.
#     old_key : str
#         The old key of the feature.
#     new_key : str
#         The new key of the feature.
#     enforce_old_key_existence : bool, optional
#         If True, raises an error when the old key does not exist in a node.
#         If False, the function will skip nodes that do not have the old key.
#         Defaults to False.
#     set_default_if_missing : bool, optional
#         If True, set the new key to `default_value` when the old key does not exist.
#         If False, the new key will not be set when the old key does not exist.
#         Defaults to False.
#     default_value : Any | None, optional
#         The default value to set if the old key does not exist
#         and set_default_if_missing is True. Defaults to None.
#     """
#     for node in lineage.nodes:
#         if old_key in lineage.nodes[node]:
#             lineage.nodes[node][new_key] = lineage.nodes[node].pop(old_key)
#         else:
#             if enforce_old_key_existence:
#                 raise ValueError(
#                     f"Node {node} does not have the required key '{old_key}'."
#                 )
#             if set_default_if_missing:
#                 lineage.nodes[node][new_key] = default_value


def test_update_node_feature_key():
    """Test updating a node feature key."""
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


def test_update_node_feature_key_missing_old_key_skip():
    """Test that nodes without old_key are skipped when enforce_old_key_existence=False."""
    lineage = CellLineage()
    lineage.add_node(1, old_key="value1")
    lineage.add_node(2)  # No old_key
    lineage.add_node(3, old_key="value3")

    _update_node_feature_key(lineage, "old_key", "new_key")

    assert lineage.nodes[1]["new_key"] == "value1"
    assert "old_key" not in lineage.nodes[1]
    assert "new_key" not in lineage.nodes[2]
    assert "old_key" not in lineage.nodes[2]
    assert lineage.nodes[3]["new_key"] == "value3"
    assert "old_key" not in lineage.nodes[3]


def test_update_node_feature_key_enforce_old_key_existence():
    """Test that missing old_key raises error when enforce_old_key_existence=True."""
    lineage = CellLineage()
    lineage.add_node(1, old_key="value1")
    lineage.add_node(2)  # No old_key

    with pytest.raises(
        ValueError, match="Node 2 does not have the required key 'old_key'"
    ):
        _update_node_feature_key(
            lineage, "old_key", "new_key", enforce_old_key_existence=True
        )


def test_update_node_feature_key_set_default_if_missing():
    """Test setting default value when old_key is missing and set_default_if_missing=True."""
    lineage = CellLineage()
    lineage.add_node(1, old_key="value1")
    lineage.add_node(2)  # No old_key
    lineage.add_node(3, old_key="value3")

    _update_node_feature_key(
        lineage,
        "old_key",
        "new_key",
        set_default_if_missing=True,
        default_value="default",
    )

    assert lineage.nodes[1]["new_key"] == "value1"
    assert "old_key" not in lineage.nodes[1]
    assert lineage.nodes[2]["new_key"] == "default"
    assert "old_key" not in lineage.nodes[2]
    assert lineage.nodes[3]["new_key"] == "value3"
    assert "old_key" not in lineage.nodes[3]


def test_update_node_feature_key_set_default_none():
    """Test setting None as default value when old_key is missing."""
    lineage = CellLineage()
    lineage.add_node(1, old_key="value1")
    lineage.add_node(2)  # No old_key

    _update_node_feature_key(lineage, "old_key", "new_key", set_default_if_missing=True)

    assert lineage.nodes[1]["new_key"] == "value1"
    assert lineage.nodes[2]["new_key"] is None


def test_update_node_feature_key_empty_lineage():
    """Test function with empty lineage (no nodes)."""
    lineage = CellLineage()
    # Should not raise an error and do nothing
    _update_node_feature_key(lineage, "old_key", "new_key")
    assert len(lineage.nodes) == 0


def test_update_node_feature_key_same_key_name():
    """Test updating a key to itself (should work without issues)."""
    lineage = CellLineage()
    lineage.add_node(1, test_key="value1")
    lineage.add_node(2, test_key="value2")

    _update_node_feature_key(lineage, "test_key", "test_key")

    assert lineage.nodes[1]["test_key"] == "value1"
    assert lineage.nodes[2]["test_key"] == "value2"


# _update_lineage_feature_key #################################################


def test_update_lineage_feature_key():
    lineage = CellLineage()
    lineage.graph["old_key"] = "old_value"
    _update_lineage_feature_key(lineage, "old_key", "new_key")

    assert "new_key" in lineage.graph
    assert lineage.graph["new_key"] == "old_value"
    assert "old_key" not in lineage.graph


# _update_lineages_IDs_key #################################################


def test_update_lineages_IDs_key():
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


def test_update_lineages_IDs_key_no_key_multi_node():
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


def test_update_lineages_IDs_key_no_key_one_node():
    """Test updating lineage IDs key when no TRACK_ID key is present in a one-node lineage."""
    lin1 = CellLineage()
    lin1.add_node(1)
    lin2 = CellLineage()
    lin2.add_nodes_from([4, 5])
    lin2.graph["TRACK_ID"] = 20
    _update_lineages_IDs_key([lin1, lin2], "TRACK_ID")
    assert lin1.graph["lineage_ID"] == -1
    assert lin2.graph["lineage_ID"] == 20


def test_update_lineages_IDs_key_all_lineages_no_key():
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


def test_update_lineages_IDs_key_empty_list():
    """Test updating lineage IDs key with empty lineages list."""
    _update_lineages_IDs_key([], "TRACK_ID")


def test_update_lineages_IDs_key_mixed_scenarios():
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


def test_update_lineages_IDs_key_preserves_other_graph_attributes():
    """Test that other graph attributes are preserved."""
    lin1 = CellLineage()
    lin1.add_node(1)
    lin1.graph["TRACK_ID"] = 10
    lin1.graph["other_attr"] = "value"

    _update_lineages_IDs_key([lin1], "TRACK_ID")
    assert lin1.graph["lineage_ID"] == 10
    assert lin1.graph["other_attr"] == "value"
    assert "TRACK_ID" not in lin1.graph


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
