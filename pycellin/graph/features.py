#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A collection of diverse features/attributes that can be added to lineage graphs.

Vocabulary:
- TrackMate (resp. networkX) uses the word feature (resp. attribute) to refer to 
spot (resp. node), link (resp. edge) or track (resp. graph) information. Both naming 
are used her, depending on the context.
- A generation is a list of nodes between 2 successive divisions.
"""

from typing import Any, Callable, Optional

import networkx as nx
import numpy as np

from pycellin.graph import lineage as lin


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


def generation_level(graph: nx.DiGraph, node: int) -> int:
    """
    Compute the generation level of a given node.

    Generation level is defined by how ancient the generation is,
    i.e. how many divisions there was upstream.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph containing the node of interest.
    node : int
        Node ID of the node of interest.

    Returns
    -------
    int
        Generation level of the node.
    """
    divisions = [n for n in nx.ancestors(graph, node) if graph.out_degree(n) > 1]
    return len(divisions)


def add_generation_level(graph: nx.DiGraph) -> None:
    """
    Add the generation level feature to the nodes of a graph.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph to process.
    """
    add_custom_attr(
        graph,
        "node",
        "GEN_LVL",
        "Generation level",
        "Gen. lvl",
        "NONE",
        "true",
        apply_on_nodes,
        graph,
        "GEN_LVL",
        generation_level,
    )


def generation_completeness(
    graph: nx.DiGraph, node: int, generation: Optional[list[int]]
) -> bool:
    """
    Compute the generation completeness of a given node.

    A generation is defined as complete when it starts by a division
    AND ends by a division. Generations that start at the root or end with a leaf
    are thus incomplete.nodes,
        graph,
        "GEN_COMPLETE",
        generation_completen
    This can be useful when analyzing features like division time. It avoids
    the introduction of a bias since we have no information on what happened before
    the root or after the leaves.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph containing the node of interest.
    node : int
        Node ID of the node of interest.
    generation : Optional[list[int]]
        List of nodes that belong to the generation of the input node. Useful if
        the generation has already been precomputed. If None, the generation will
        first be computed.

    Returns
    -------
    bool
        True if the generation is complete, False otherwise.
    """

    if generation is not None:
        assert node in generation
    else:
        generation = lin.get_generation(graph, node)
    if lin.is_root(graph, generation[0]) or lin.is_leaf(graph, generation[-1]):
        return False
    else:
        return True


def add_generation_completeness(graph: nx.DiGraph) -> None:
    """
    Add the generation_completeness feature to the nodes of a graph.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph to process.
    """
    add_custom_attr(
        graph,
        "node",
        "GEN_COMPLETE",
        "Generation completeness",
        "Gen. complete",
        "NONE",
        "true",
        apply_on_nodes,
        graph,
        "GEN_COMPLETE",
        generation_completeness,
        need_TRACK_ID=True,
    )


def division_time(graph: nx.DiGraph, node: int, generation: Optional[list[int]]) -> int:
    """
    Compute the division time of a given node, expressed in nodes.

    Division time is defined as the number of nodes between the 2 divisions surrounding
    the node of interest. It is the length of the generation of the node of interest.
    This means that all the nodes of a generation will have the same division time.
    It also means that when studying division time, it is important to only take one
    node per generation into account (usually first or last node of the generation).
    Otherwise a bias will be introduced since longer generations will be more
    represented.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph containing the node of interest.
    node : int
        Node ID of the node of interest.
    generation : Optional[list[int]]
        List of nodes that belong to the generation of the input node. Useful if
        the generation has already been precomputed. If None, the generation will
        first be computed.

    Returns
    -------
    int
        Division time of the node, expressed in nodes.
    """
    if generation is not None:
        assert node in generation
    else:
        generation = lin.get_generation(graph, node)
    return len(generation)


def cell_phase(graph: nx.DiGraph, node: int, generation: Optional[list[int]]) -> str:
    """
    Compute the phase(s)/stage(s) in which the node of interest is currently in.

    Phases can be:
    - 'division' -> when the out degree of the node is higher than its in degree
    - 'birth' -> when the previous node is a division
    - 'first' -> graph root i.e. beginning of lineage
    - 'last' -> graph leaf i.e end of lineage
    - '-' -> when the node is not in one of the above phases.

    Notice that a node can be in different phases simultaneously, e.g. 'first'
    and 'division'. In that case, a '+' sign is used as separator between phases,
    e.g. 'first+division'.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph containing the node of interest.
    node : int
        Node ID of the node of interest.
    generation : Optional[list[int]]
        List of nodes that belong to the generation of the input node. Useful if
        the generation has already been precomputed. If None, the generation will
        first be computed.

    Returns
    -------
    str
        Phase(s) of the node.
    """

    def append_tag(tag, new_tag):
        if not tag:
            tag = new_tag
        else:
            tag += f"+{new_tag}"
        return tag

    tag = ""
    # Straightforward cases.
    if lin.is_root(graph, node):
        tag = append_tag(tag, "first")
    if lin.is_leaf(graph, node):
        tag = append_tag(tag, "last")
    if lin.is_division(graph, node):
        tag = append_tag(tag, "division")
    # Checking for cell birth.
    if generation:
        assert node in generation
    else:
        generation = lin.get_generation(graph, node)
    if node == generation[0]:
        tag = append_tag(tag, "birth")

    if not tag:
        return "-"
    else:
        return tag


def absolute_age(graph: nx.DiGraph, node: int) -> int:
    return len(nx.ancestors(graph, node)) + 1


def relative_age(graph: nx.DiGraph, node: int, generation: Optional[list[int]]) -> int:
    if generation is not None:
        assert node in generation
    else:
        generation = lin.get_generation(graph, node)
    return generation.index(node) + 1


def generation_ID(graph: nx.DiGraph, node: int) -> Optional[str]:
    """
    Compute the generation ID of a given node.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph containing the node of interest.
    node : int
        Node ID of the node of interest.

    Returns
    -------
    Optional[str]
        Generation ID of the given node.
    """
    try:
        track_ID = graph.nodes[node]["TRACK_ID"]
    except KeyError as err:
        print(err, f"Has a tracking been done on node {node}?")
    else:
        gen_end_node = lin.get_generation(graph, node)[-1]
        gen_ID = f"{track_ID}_{gen_end_node}"
        return gen_ID


def area_increment(graph: nx.DiGraph, node: int) -> float:
    # Area of node at t minus area at t-1.
    predecessors = list(graph.predecessors(node))
    if len(predecessors) == 0:
        return np.NaN
    else:
        err_mes = (
            f'Node {node} in track {graph.graph["name"]} has multiple predecessors.'
        )
        assert len(predecessors) == 1, err_mes
        # print(predecessors)
        return graph.nodes[node]["AREA"] - graph.nodes[predecessors[0]]["AREA"]


if __name__ == "__main__":
    G = nx.Graph()
    G.add_node(1, color="blue")
    G.add_node(2, color="blue")
    G.add_node(3, color="blue")
    G.add_node(4, color="blue")
    print(G)

    def add_attr(graph, node):
        graph.nodes[node]["time"] = f"{node*2}pm"

    def add_new_node(graph, new_node):
        G.add_node(new_node, color="blue")

    for n in G:
        add_attr(G, n)

    add_new_node(G, 5)

    print(G.nodes)
    print(G.nodes[1])
    print(G.nodes[4])
    print(G.nodes[5])
