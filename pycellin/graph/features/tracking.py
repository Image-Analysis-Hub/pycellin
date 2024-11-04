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

import networkx as nx

from pycellin.classes import CellLineage, CycleLineage
from pycellin.classes import Feature
from pycellin.classes.feature_calculator import (
    NodeGlobalFeatureCalculator,
    NodeLocalFeatureCalculator,
)


class AbsoluteAgeInFrames(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the absolute age of cells.

    The absolute age of a cell is defined as the number of nodes since
    the beginning of the lineage. Absolute age of the root is 0.
    It is given in frames.
    """

    def compute(self, data, lineage, noi):
        """
        Compute the absolute age of a given node, in frames.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage
            Lineage graph containing the node of interest.
        noi : int
            Node ID (cell_ID) of the cell of interest.

        Returns
        -------
        int
            Absolute age of the node, in frames.
        """
        return len(nx.ancestors(lineage, noi))


class AbsoluteAgeInTime(NodeGlobalFeatureCalculator):

    def __init__(self, feature: Feature, time_step: float):
        super().__init__(feature)
        self.time_step = time_step

    def compute(self, data, lineage, noi):
        """
        Compute the absolute age of a given node, in time units.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage
            Lineage graph containing the node of interest.
        noi : int
            Node ID (cell_ID) of the cell of interest.

        Returns
        -------
        int
            Absolute age of the node, in time units.
        """
        return len(nx.ancestors(lineage, noi)) * self.time_step


def get_absolute_age(
    noi: int, lineage: CellLineage, time_step: float = 1
) -> int | float:
    """
    Compute the absolute age of a given node.

    The absolute age of a cell is defined as the number of nodes since
    the beginning of the lineage. Absolute age of the root is 0.
    It is given in frames by default, but can be converted
    to the time unit of the model if specified.

    Parameters
    ----------
    noi : int
        Node ID (cell_ID) of the cell of interest.
    lineage : CellLineage
        Lineage graph containing the node of interest.
    time_step : float, optional
        Time step between 2 frames, by default 1.

    Returns
    -------
    int | float
        Absolute age of the node.
    """
    return len(nx.ancestors(lineage, noi)) * time_step


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
            lin.nodes[node]["absolute_age"] = get_absolute_age(node, lin, time_step)


def get_relative_age(
    noi: int,
    lineage: CellLineage,
    time_step: float = 1,
    cell_cycle: list[int] | None = None,
) -> int | float:
    """
    Compute the relative age of a given node.

    The relative age of a cell is defined as the number of nodes since
    the start of the cell cycle (i.e. previous division, or beginning
    of the lineage).
    It is given in frames by default, but can be converted
    to the time unit of the model if specified.

    Parameters
    ----------
    noi : int
        Node ID (cell_ID) of the cell of interest.
    lineage : CellLineage
        Lineage graph containing the node of interest.
    time_step : float, optional
        Time step between 2 frames, by default 1.
    cell_cycle : list[int] | None, optional
        List of nodes that belong to the cell cycle of the input node.
        Useful if the cell cycle has already been precomputed.
        If None, the cell cycle will first be computed. By default None.

    Returns
    -------
    int | float
        Relative age of the node.
    """
    if cell_cycle is not None:
        assert noi in cell_cycle
    else:
        cell_cycle = lineage.get_cell_cycle(noi)
    return cell_cycle.index(noi) * time_step


def _add_relative_age(lineages: list[CellLineage], time_step: float = 1) -> None:
    """
    Compute and add the relative age feature to all the nodes of a list of lineages.

    Parameters
    ----------
    lineages : list[CellLineage]
        Lineage graphs to update with the relative age feature.
    time_step : float, optional
        Time step between 2 frames, by default 1.
    """
    for lin in lineages:
        for node in lin.nodes:
            lin.nodes[node]["relative_age"] = get_relative_age(node, lin, time_step)


def get_cell_cycle_completeness(noi: int, lineage: CellLineage | CycleLineage) -> bool:
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
    noi : int
        Node ID (cell_ID) of the cell of interest.
    lineage: CellLineage | CycleLineage
        Lineage graph containing the node of interest.

    Returns
    -------
    bool
        True if the cell cycle is complete, False otherwise.
    """
    if isinstance(lineage, CellLineage):
        cell_cycle = lineage.get_cell_cycle(noi)
        if lineage.is_root(cell_cycle[0]) or lineage.is_leaf(cell_cycle[-1]):
            return False
        else:
            return True
    elif isinstance(lineage, CycleLineage):
        if lineage.is_root(noi) or lineage.is_leaf(noi):
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
                node, lin
            )


def get_division_time(
    noi: int, lineage: CellLineage | CycleLineage, time_step: float = 1
) -> int | float:
    """
    Compute the division time of a given node, expressed in frames.

    Division time is defined as the number of frames between 2 divisions.
    It is also the length of the cell cycle of the node of interest.
    It is given in frames by default, but can be converted
    to the time unit of the model if specified.

    Parameters
    ----------
    noi : int
        Node ID (cell_ID) of the cell of interest.
    lineage : CellLineage | CycleLineage
        Lineage graph containing the node of interest.
    time_step : float, optional
        Time step between 2 frames, by default 1.

    Returns
    -------
    int | float
        Division time of the node, expressed in frames.
    """
    if isinstance(lineage, CellLineage):
        cell_cycle = lineage.get_cell_cycle(noi)
        return len(cell_cycle) * time_step
    elif isinstance(lineage, CycleLineage):
        return lineage.nodes[noi]["cycle_length"] * time_step


def _add_division_time(lineages: list[CycleLineage], time_step: float = 1) -> None:
    """
    Compute and add the division time feature to all the nodes of a list of lineages.

    Parameters
    ----------
    lineages : list[CellLineage]
        Lineage graphs to update with the relative age feature.
    time_step : float, optional
        Time step between 2 frames, by default 1.
    """
    for lin in lineages:
        for node in lin.nodes:
            lin.nodes[node]["division_time"] = get_division_time(node, lin, time_step)


def get_division_rate(
    noi: int, lineage: CellLineage | CycleLineage, time_step: float = 1
) -> float:
    """
    Compute the division rate of a given node.

    Division rate is defined as the number of divisions per time unit.
    It is the inverse of the division time.
    It is given in frames by default, but can be converted
    to the time unit of the model if specified.

    Parameters
    ----------
    noi : int
        Node ID (cell_ID) of the cell of interest.
    lineage : CellLineage | CycleLineage
        Lineage graph containing the node of interest.
    time_step : float, optional
        Time step between 2 frames, by default 1.

    Returns
    -------
    float
        Division rate of the node.
    """
    return 1 / get_division_time(noi, lineage, time_step)


def _add_division_rate(lineages: list[CycleLineage], time_step: float = 1) -> None:
    """
    Compute and add the division rate feature to all the nodes of a list of lineages.

    Parameters
    ----------
    lineages : list[CellLineage]
        Lineage graphs to update with the division rate feature.
    time_step : float, optional
        Time step between 2 frames, by default 1.
    """
    for lin in lineages:
        for node in lin.nodes:
            lin.nodes[node]["division_rate"] = 1 / get_division_time(
                node, lin, time_step
            )


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
