#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any, Callable

import networkx as nx


def get_node_attributes_names(graph: nx.DiGraph) -> list[str]:
    """Return a list of the attributes used for nodes.

    Args:
        graph (nx.DiGraph): Graph on which to work.

    Returns:
        list[str]: Names of the attributes used for nodes.
    """
    # node_attributes = set([k for n in graph.nodes for k in graph.nodes[n].keys()])
    node_attributes = list()
    for node in graph.nodes:
        # By construction, each and every node has the same set of attributes,
        # only their values change. So we get the first node, whichever it is,
        # and get its attributes. There's no need to do it for every node.
        node_attributes = list(graph.nodes[node].keys())
        break
    return node_attributes


def apply_on_nodes(
    graph: nx.DiGraph, feature: str, fun: Callable, need_TRACK_ID: bool = False
) -> None:
    """
    Apply a function in order to add a new feature on all nodes of a graph.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph to process.
    feature : str
        Name of the feature to add.
    fun : Callable
        Function to apply on all nodes.
    need_TRACK_ID : bool, optional
        True if the new feature needs tracking data to be computed, False otherwise.
        By default False.
    """
    for n in graph:
        if not need_TRACK_ID or (need_TRACK_ID and "TRACK_ID" in graph.nodes[n]):
            graph.nodes[n][feature] = fun(graph, n)


def add_custom_attr(
    graph: nx.DiGraph,
    attr_type: str,
    attr: str,
    name: str,
    shortname: str,
    dimension: str,
    isint: str,
    func: Callable,
    *args: Any,
    **kwargs: Any,
) -> None:
    """
    Add a custom feature to a graph while ensuring TrackMate compatibility.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph to process.
    attr_type : str
        Type of feature to add: node, edge or track.
    attr : str
        Attribute name used by networkx to access its data. This is also the
        name of the matching feature inTrackMate.
    name : str
        Full name for the TrackMate attribute.
    shortname : str
        Abridged name for the TrackMate attribute.
    dimension : str
        Dimension of the TrackMate attribute.
    isint : str
        'true' if the TrackMate attribute is meant to be a an int, 'false' otherwise.
    func : Callable
        Function that will compute the feature values.
    """
    err_message = "Wrong type attribute. Only 'node', 'edge' and 'track' are valid."
    attr_type = attr_type.lower()
    assert attr_type in ["node", "edge", "track"], err_message

    if attr_type == "node":
        tag = "SpotFeatures"
    elif attr_type == "edge":
        tag = "EdgeFeatures"
    else:
        tag = "TrackFeatures"

    # Adding feature declaration for TrackMate compatibility.
    graph.graph["Model"][tag][attr] = {
        "feature": attr,
        "name": name,
        "shortname": shortname,
        "dimension": dimension,
        "isint": isint,
    }

    # Computing new feature values.
    func(*args, **kwargs)
