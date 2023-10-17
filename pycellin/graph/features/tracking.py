#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A collection of diverse tracking features/attributes that can be added to 
lineage graphs.

Vocabulary:
- Feature/Attribute: TrackMate (resp. networkX) uses the word feature (resp. attribute) 
  to refer to spot (resp. node), link (resp. edge) or track (resp. graph) information. 
  Both naming are used here, depending on the context.
- Generation: A generation is a list of nodes between 2 successive divisions. 
  It includes the second division but not the first one.
  For example, in the following graph where node IDs belong to [0, 9]:

        0           we have the following generation:
        |             [0, 1]
        1             [2, 4, 6]
       / \            [3, 5, 7]
      2   3           [8]
      |   |           [9]
      4   5  
      |   |    
      6   7
     / \ 
    8   9

- Complete generation: It is a generation that do not include a root nor a leaf.
  If we take the previous example, the only complete generation is [2, 4, 6].
"""

from typing import Optional

import networkx as nx

from pycellin.graph import lineage as lin
import pycellin.graph.features as feat


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
    feat.add_custom_attr(
        graph,
        "node",
        "GEN_LVL",
        "Generation level",
        "Gen. lvl",
        "NONE",
        "true",
        feat.apply_on_nodes,
        graph,
        "GEN_LVL",
        generation_level,
    )


def generation_completeness(
    graph: nx.DiGraph, node: int, generation: Optional[list[int]] = None
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
    generation : Optional[list[int]], optional
        List of nodes that belong to the generation of the input node. Useful if
        the generation has already been precomputed. If None, the generation will
        first be computed. By default None.

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
    Add the generation completeness feature to the nodes of a graph.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph to process.
    """
    feat.add_custom_attr(
        graph,
        "node",
        "GEN_COMPLETE",
        "Generation completeness",
        "Gen. complete",
        "NONE",
        "true",
        feat.apply_on_nodes,
        graph,
        "GEN_COMPLETE",
        generation_completeness,
        need_TRACK_ID=True,
    )


def division_time(
    graph: nx.DiGraph, node: int, generation: Optional[list[int]] = None
) -> int:
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
    generation : Optional[list[int]], optional
        List of nodes that belong to the generation of the input node. Useful if
        the generation has already been precomputed. If None, the generation will
        first be computed. By default None.

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


def add_division_time(graph: nx.DiGraph) -> None:
    """
    Add the division time feature to the nodes of a graph.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph to process.
    """
    feat.add_custom_attr(
        graph,
        "node",
        "DIV_TIME",
        "Division time",
        "Div. time",
        "TIME",
        "false",
        feat.apply_on_nodes,
        graph,
        "GEN_COMPLETE",
        division_time,
        need_TRACK_ID=True,
    )


def cell_phase(
    graph: nx.DiGraph, node: int, generation: Optional[list[int]] = None
) -> str:
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
    generation : Optional[list[int]], optional
        List of nodes that belong to the generation of the input node. Useful if
        the generation has already been precomputed. If None, the generation will
        first be computed. By default None.

    Returns
    -------
    str
        Phase(s) of the node.
    """

    # TODO: change to concatenated digits tags for TM compatibility
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


def add_cell_phase(graph: nx.DiGraph) -> None:
    """
    Add the cell phase feature to the nodes of a graph.

    Notes
    -----
        TrackMate does not support string features so it is necessary to convert
        cell phase tags to integers. We concatenate digits between 1 and 9 included
        so that when there are several tags per node, no information is lost.
        Examples:
        - '-' -> 0
        - 'first' -> 1
        - 'last' -> 9
        - 'division' -> 2
        - 'birth' -> 3
        - 'first+division' -> 12
        - 'last+birth' -> 93

    Parameters
    ----------
    graph : nx.DiGraph
        Graph to process.
    """

    # TODO: implement
    phase_mapping = {"first": 1, "last": 9, "division": 2, "birth": 3}


def absolute_age(graph: nx.DiGraph, node: int) -> int:
    """
    Compute the absolute age of a given node.

    Absolute age is defined as the number of nodes between the start of the lineage
    (i.e. root of the graph) and the node of interest.
    Absolute age of the root is 0.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph containing the node of interest.
    node : int
        Node ID of the node of interest.

    Returns
    -------
    int
        Absolute age of the node.
    """
    return len(nx.ancestors(graph, node))


def relative_age(
    graph: nx.DiGraph, node: int, generation: Optional[list[int]] = None
) -> int:
    """
    Compute the relative age of a given node.

    Relative age is defined as the number of nodes between the start of the generation
    (i.e. previous division, or root) and the node of interest.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph containing the node of interest.
    node : int
        Node ID of the node of interest.
    generation : Optional[list[int]], optional
        List of nodes that belong to the generation of the input node. Useful if
        the generation has already been precomputed. If None, the generation will
        first be computed. By default None.

    Returns
    -------
    int
        Relative age of the node.
    """
    if generation is not None:
        assert node in generation
    else:
        generation = lin.get_generation(graph, node)
    return generation.index(node)


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
