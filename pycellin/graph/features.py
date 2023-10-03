#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A collection of diverse features/attributes that can be added to lineage graphs.
"""

from typing import Any, Callable

import networkx as nx
import numpy as np

from pycellin.graph import lineage as lin


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
    _summary_

    Parameters
    ----------
    graph : nx.DiGraph
        _description_
    attr_type : str
        _description_
    attr : str
        _description_
    name : str
        _description_
    shortname : str
        _description_
    dimension : str
        _description_
    isint : str
        _description_
    func : Callable
        _description_
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

    # Adding feature declaration.
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
        Graph to process.
    node : int
        Node ID.

    Returns
    -------
    int
        Generation level of the node.
    """
    divisions = [n for n in nx.ancestors(graph, node) if graph.out_degree(n) > 1]
    return len(divisions)


def add_generation_level(graph: nx.DiGraph) -> None:
    """
    _summary_

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


# TODO: the argument generation is of union type: bool U list


def generation_completeness(
    graph: nx.DiGraph, node: int, generation: bool = False
) -> bool:
    """
    Compute the generation completeness of a given node.

    A generation is defined as complete when it starts by a division
    AND ends by a division. Generations that start at the root or end with a leaf
    are thus incomplete.
    This can be useful when analyzing features like division time. It avoids
    the introduction of a bias since we have no information on what happened before
    the root or after the leaves.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph to process.
    node : int
        Node ID.
    generation : bool, optional
        _description_, by default False

    Returns
    -------
    bool
        Generation completeness of the node.
    """
    if generation:
        assert node in generation
    else:
        generation = lin.get_generation(graph, node)
    if lin.is_root(graph, generation[0]) or lin.is_leaf(graph, generation[-1]):
        return False
    else:
        return True


def add_generation_completeness(graph: nx.DiGraph) -> None:
    """
    _summary_

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


def division_time(graph: nx.DiGraph, node: int, generation: bool = False) -> int:
    if generation:
        assert node in generation
    else:
        generation = lin.get_generation(graph, node)
    return len(generation)


def cell_phase(graph: nx.DiGraph, node: int, generation: bool = False) -> str:
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


def relative_age(graph: nx.DiGraph, node: int, generation: bool = False) -> int:
    if generation:
        assert node in generation
    else:
        generation = lin.get_generation(graph, node)
    return generation.index(node) + 1


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

    def test_map(graph, node):
        return f"{node*2}pm"

    apply_on_nodes(G, "time", test_map)

    print(G.nodes)
    print(G.nodes[1])
    print(G.nodes[4])
