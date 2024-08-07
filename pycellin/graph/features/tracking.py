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

from typing import Literal, Optional

import networkx as nx

from pycellin.classes.lineage import CellLineage, CycleLineage, Lineage

# from pycellin.graph import lineage as lin
# import pycellin.graph.features as feat


def get_absolute_age(lineage: CellLineage, node: int, time_step: float = 1) -> int:
    """
    Compute the absolute age of a given node.

    The absolute age of a cell is defined as the number of nodes since
    the beginning of the lineage. Absolute age of the root is 0.
    Is is given in frames by default, but can be converted
    to the time unit of the model if specified.

    Parameters
    ----------
    lineage : CellLineage
        Lineage graph containing the node of interest.
    node : int
        Node ID (cell_ID) of the node of interest.
    time_step : float, optional
        Time step between 2 frames, by default 1.

    Returns
    -------
    int
        Absolute age of the node.
    """
    return len(nx.ancestors(lineage, node)) * time_step


def _add_absolute_age(lineages: list[CellLineage], time_step: float = 1) -> None:
    """
    Compute and add the absolute age feature to all the nodes of a list of lineages.

    Parameters
    ----------
    lineages : list[CellLineage]
        Lineage graphs to update with the absolute age feature.
    time_step : float, optional
        Time step between 2 frames, by default 1.
    """
    for lin in lineages:
        for node in lin.nodes:
            lin.nodes[node]["absolute_age"] = get_absolute_age(lin, node, time_step)


def get_relative_age(
    lineage: CellLineage, node: int, cell_cycle: Optional[list[int]] = None
) -> int:
    """
    Compute the relative age of a given node.

    The relative age of a cell is defined as the number of nodes since
    the start of the cell cycle (i.e. previous division, or beginning
    of the lineage).

    Parameters
    ----------
    lineage : CellLineage
        Lineage graph containing the node of interest.
    node : int
        Node ID (cell_ID) of the node of interest.
    cell_cycle : Optional[list[int]], optional
        List of nodes that belong to the cell cycle of the input node.
        Useful if the cell cycle has already been precomputed.
        If None, the cell cycle will first be computed. By default None.

    Returns
    -------
    int
        Relative age of the node.
    """
    if cell_cycle is not None:
        assert node in cell_cycle
    else:
        cell_cycle = lineage.get_cell_cycle(node)
    return cell_cycle.index(node)


def _add_relative_age(lineages: list[CellLineage]) -> None:
    """
    Compute and add the relative age feature to all the nodes of a list of lineages.

    Parameters
    ----------
    lineages : list[CellLineage]
        Lineage graphs to update with the relative age feature.
    """
    for lin in lineages:
        for node in lin.nodes:
            lin.nodes[node]["relative_age"] = get_relative_age(lin, node)


# ON CELL CYCLE GRAPH
# def generation_level(graph: nx.DiGraph, node: int) -> int:
#     """
#     Compute the generation level of a given node.

#     Generation level is defined by how ancient the generation is,
#     i.e. how many divisions there was upstream.

#     Parameters
#     ----------
#     graph : nx.DiGraph
#         Graph containing the node of interest.
#     node : int
#         Node ID of the node of interest.

#     Returns
#     -------
#     int
#         Generation level of the node.
#     """
#     divisions = [n for n in nx.ancestors(graph, node) if graph.out_degree(n) > 1]
#     return len(divisions)

# ON CELL CYCLE GRAPH
# def add_generation_level(graph: nx.DiGraph) -> None:
#     """
#     Add the generation level feature to the nodes of a graph.

#     Parameters
#     ----------
#     graph : nx.DiGraph
#         Graph to process.
#     """
#     feat.add_custom_attr(
#         graph,
#         "node",
#         "GEN_LVL",
#         "Generation level",
#         "Gen. lvl",
#         "NONE",
#         "true",
#         feat.apply_on_nodes,
#         graph,
#         "GEN_LVL",
#         generation_level,
#     )


def get_cell_cycle_completeness(lineage: CellLineage | CycleLineage, node: int) -> bool:
    """
    Compute the cell cycle completeness of a given node.

    A cell cycle is defined as complete when it starts by a division
    AND ends by a division. Cell cycles that start at the root
    or end with a leaf are thus incomplete.
    This can be useful when analyzing features like division time. It avoids
    the introduction of a bias since we have no information on what happened
    before the root or after the leaves.

    Parameters
    ----------
    lineage: CellLineage | CycleLineage
        Lineage graph containing the node of interest.
    node : int
        Node ID of the node of interest.

    Returns
    -------
    bool
        True if the cell cycle is complete, False otherwise.
    """
    if isinstance(lineage, CellLineage):
        cell_cycle = lineage.get_cell_cycle(node)
        if lineage.is_root(cell_cycle[0]) or lineage.is_leaf(cell_cycle[-1]):
            return False
        else:
            return True
    elif isinstance(lineage, CycleLineage):
        if lineage.is_root(node) or lineage.is_leaf(node):
            return False
        else:
            return True


def _add_cell_cycle_completeness(lineages: list[CycleLineage]) -> None:
    """
    Add the cell cycle completeness feature to the nodes of a cycle lineage.

    Parameters
    ----------
    lineages: list[CycleLineage]
        Cell cycle lineages to update with the cell cycle completeness feature.
    """
    for lin in lineages:
        for node in lin.nodes:
            lin.nodes[node]["cell_cycle_completeness"] = get_cell_cycle_completeness(
                lin, node
            )


def get_division_time(lineage: CellLineage | CycleLineage, node: int) -> int:
    """
    Compute the division time of a given node, expressed in frames.

    Division time is defined as the number of frames between 2 divisions.
    It is also the length of the cell cycle of the node of interest.

    Parameters
    ----------
    lineage : CellLineage | CycleLineage
        Lineage graph containing the node of interest.
    node : int
        Node ID of the node of interest.

    Returns
    -------
    int
        Division time of the node, expressed in frames.
    """
    if isinstance(lineage, CellLineage):
        cell_cycle = lineage.get_cell_cycle(node)
        return len(cell_cycle)
    elif isinstance(lineage, CycleLineage):
        # It's the same as the cell cycle length / duration...
        return lineage.nodes[node]["duration"]


def _add_division_time(lineages: list[CycleLineage]) -> None:
    """
    Compute and add the division time feature to all the nodes of a list of lineages.

    Parameters
    ----------
    lineages : list[CellLineage]
        Lineage graphs to update with the relative age feature.
    """
    for lin in lineages:
        for node in lin.nodes:
            lin.nodes[node]["division_time"] = get_division_time(lin, node)


# ON CELL CYCLE GRAPH
# def generation_ID(graph: nx.DiGraph, node: int) -> Optional[str]:
#     """
#     Compute the generation ID of a given node.

#     It is defined as {track_ID}_{generation_last_node} to ensure uniqueness.

#     Parameters
#     ----------
#     graph : nx.DiGraph
#         Graph containing the node of interest.
#     node : int
#         Node ID of the node of interest.

#     Returns
#     -------
#     Optional[str]
#         Generation ID of the given node.
#     """
#     try:
#         track_ID = graph.nodes[node]["TRACK_ID"]
#     except KeyError as err:
#         print(err, f"Has a tracking been done on node {node}?")
#     else:
#         gen_end_node = lin.get_generation(graph, node)[-1]
#         gen_ID = f"{track_ID}_{gen_end_node}"
#         return gen_ID

# ON CELL CYCLE GRAPH
# def add_generation_ID(graph: nx.DiGraph) -> None:
#     """
#     Add the generation ID feature to the nodes of a graph.

#     Notes
#     -----
#     This feature is currently not compatible with TrackMate and thus will not
#     carry over the XML file. TrackMate do not support string features.

#     Parameters
#     ----------
#     graph : nx.DiGraph
#         Graph to process.
#     """
#     feat.add_custom_attr(
#         graph,
#         "node",
#         "GEN_ID",
#         "Generation ID",
#         "Gen. ID",
#         "NONE",
#         "false",
#         feat.apply_on_nodes,
#         graph,
#         "GEN_ID",
#         generation_ID,
#     )

# def cell_phase(
#     graph: nx.DiGraph, node: int, generation: Optional[list[int]] = None
# ) -> str:
#     """
#     Compute the phase(s)/stage(s) in which the node of interest is currently in.

#     Phases can be:
#     - 'division' -> when the out degree of the node is higher than its in degree
#     - 'birth' -> when the previous node is a division
#     - 'first' -> graph root i.e. beginning of lineage
#     - 'last' -> graph leaf i.e end of lineage
#     - '-' -> when the node is not in one of the above phases.

#     Notice that a node can be in different phases simultaneously, e.g. 'first'
#     and 'division'. In that case, a '+' sign is used as separator between phases,
#     e.g. 'first+division'.

#     Parameters
#     ----------
#     graph : nx.DiGraph
#         Graph containing the node of interest.
#     node : int
#         Node ID of the node of interest.
#     generation : Optional[list[int]], optional
#         List of nodes that belong to the generation of the input node. Useful if
#         the generation has already been precomputed. If None, the generation will
#         first be computed. By default None.

#     Returns
#     -------
#     str
#         Phase(s) of the node.
#     """

#     def append_tag(tag, new_tag):
#         if not tag:
#             tag = new_tag
#         else:
#             tag += f"+{new_tag}"
#         return tag

#     tag = ""
#     # Straightforward cases.
#     if lin.is_root(graph, node):
#         tag = append_tag(tag, "first")
#     if lin.is_leaf(graph, node):
#         tag = append_tag(tag, "last")
#     if lin.is_division(graph, node):
#         tag = append_tag(tag, "division")
#     # Checking for cell birth.
#     if generation:
#         assert node in generation
#     else:
#         generation = lin.get_generation(graph, node)
#     if node == generation[0]:
#         tag = append_tag(tag, "birth")

#     if not tag:
#         return "-"
#     else:
#         return tag


# def add_cell_phase(graph: nx.DiGraph) -> None:
#     """
#     Add the cell phase feature to the nodes of a graph.

#     Notes
#     -----
#     This feature is currently not compatible with TrackMate and thus will not
#     carry over the XML file. TrackMate do not support string features.

#     Parameters
#     ----------
#     graph : nx.DiGraph
#         Graph to process.
#     """
#     feat.add_custom_attr(
#         graph,
#         "node",
#         "CELL_PHASE",
#         "Cell cycle phase",
#         "Phase",
#         "NONE",
#         "false",
#         feat.apply_on_nodes,
#         graph,
#         "CELL_PHASE",
#         cell_phase,
#     )
