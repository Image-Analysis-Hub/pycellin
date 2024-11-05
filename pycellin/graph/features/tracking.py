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
from pycellin.classes import Data
from pycellin.classes.feature_calculator import NodeGlobalFeatureCalculator

# TODO: should I add the word Calc or Calculator to the class names?


class AbsoluteAgeInFrames(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the absolute age of cells.

    The absolute age of a cell is defined as the time elapsed since
    the beginning of the lineage. Absolute age of the root is 0.
    Here, it is given in frames.
    """

    def compute(self, data: Data, lineage: CellLineage, noi: int) -> int:
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
    """
    Calculator to compute the absolute age of cells, in time units.

    The absolute age of a cell is defined as the time elapsed since
    the beginning of the lineage. Absolute age of the root is 0.
    Here, it is given in time units.
    """

    def __init__(self, feature: Feature, time_step: float):
        super().__init__(feature)
        self.time_step = time_step

    def compute(self, data: Data, lineage: CellLineage, noi: int) -> float:
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
        float
            Absolute age of the node, in time units.
        """
        return len(nx.ancestors(lineage, noi)) * self.time_step


class RelativeAgeInFrames(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the relative age of cells, in frames.

    The relative age of a cell is defined as the time elapsed since
    the start of the cell cycle (i.e. previous division, or beginning
    of the lineage).
    Here, it is given in frames.
    """

    def compute(self, data: Data, lineage: CellLineage, noi: int) -> int:
        """
        Compute the relative age of a given node, in frames.

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
            Relative age of the node, in frames.
        """
        cell_cycle = lineage.get_cell_cycle(noi)
        return cell_cycle.index(noi)


class RelativeAgeInTime(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the relative age of cells, in time units.

    The relative age of a cell is defined as the time elapsed since
    the start of the cell cycle (i.e. previous division, or beginning
    of the lineage).
    Here, it is given in time units.
    """

    def __init__(self, feature: Feature, time_step: float):
        super().__init__(feature)
        self.time_step = time_step

    def compute(self, data: Data, lineage: CellLineage, noi: int) -> float:
        """
        Compute the relative age of a given node, in time units.

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
        float
            Relative age of the node, in time units.
        """
        cell_cycle = lineage.get_cell_cycle(noi)
        return cell_cycle.index(noi) * self.time_step


class CellCycleCompleteness(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the cell cycle completeness.

    A cell cycle is defined as complete when it starts by a division
    AND ends by a division. Cell cycles that start at the root
    or end with a leaf are thus incomplete.
    This can be useful when analyzing features like division time. It avoids
    the introduction of a bias since we have no information on what happened
    before the root or after the leaves.
    """

    def compute(
        self, data: Data, lineage: CellLineage | CycleLineage, noi: int
    ) -> bool:
        """
        Compute the cell cycle completeness of a given cell or cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage | CycleLineage
            Lineage graph containing the node (cell or cell cycle) of interest.
        noi : int
            Node ID of the node (cell or cell cycle) of interest.

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


class DivisionTimeInFrames(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the division time of cells, in frames.

    Division time is defined as the time between 2 divisions.
    It is also the length of the cell cycle of the cell of interest.
    Here, it is given in frames.
    """

    def compute(self, data: Data, lineage: CellLineage | CycleLineage, noi: int) -> int:
        """
        Compute the division time of a given cell or cell cycle, in frames.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage | CycleLineage
            Lineage graph containing the node (cell or cell cycle) of interest.
        noi : int
            Node ID of the node (cell or cell cycle) of interest.

        Returns
        -------
        int
            Division time, in frames.
        """
        if isinstance(lineage, CellLineage):
            cell_cycle = lineage.get_cell_cycle(noi)
            return len(cell_cycle)
        elif isinstance(lineage, CycleLineage):
            return lineage.nodes[noi]["cycle_length"]


class DivisionTimeInTime(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the division time of cells, in time units.

    Division time is defined as the time between 2 divisions.
    It is also the length of the cell cycle of the cell of interest.
    Here, it is given in time units.
    """

    def __init__(self, feature: Feature, time_step: float):
        super().__init__(feature)
        self.time_step = time_step

    def compute(
        self, data: Data, lineage: CellLineage | CycleLineage, noi: int
    ) -> float:
        """
        Compute the division time of a given cell or cell cycle, in time units.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage | CycleLineage
            Lineage graph containing the node (cell or cell cycle) of interest.
        noi : int
            Node ID of the node (cell or cell cycle) of interest.

        Returns
        -------
        float
            Division time, in time units.
        """
        if isinstance(lineage, CellLineage):
            cell_cycle = lineage.get_cell_cycle(noi)
            return len(cell_cycle) * self.time_step
        elif isinstance(lineage, CycleLineage):
            return lineage.nodes[noi]["cycle_length"] * self.time_step


class DivisionRateInFrames(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the division rate of cells, in frames.

    Division rate is defined as the number of divisions per time unit.
    It is the inverse of the division time.
    Here, it is given in frames.
    """

    def compute(
        self, data: Data, lineage: CellLineage | CycleLineage, noi: int
    ) -> float:
        """
        Compute the division rate of a given cell or cell cycle, in frames.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage | CycleLineage
            Lineage graph containing the node (cell or cell cycle) of interest.
        noi : int
            Node ID of the node (cell or cell cycle) of interest.

        Returns
        -------
        float
            Division rate, in frames.
        """
        if isinstance(lineage, CellLineage):
            cell_cycle = lineage.get_cell_cycle(noi)
            return 1 / len(cell_cycle)
        elif isinstance(lineage, CycleLineage):
            return 1 / lineage.nodes[noi]["cycle_length"]


class DivisionRateInTime(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the division rate of cells, in time units.

    Division rate is defined as the number of divisions per time unit.
    It is the inverse of the division time.
    Here, it is given in time units.
    """

    def __init__(self, feature: Feature, time_step: float):
        super().__init__(feature)
        self.time_step = time_step

    def compute(
        self, data: Data, lineage: CellLineage | CycleLineage, noi: int
    ) -> float:
        """
        Compute the division rate of a given cell or cell cycle, in time units.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage | CycleLineage
            Lineage graph containing the node (cell or cell cycle) of interest.
        noi : int
            Node ID of the node (cell or cell cycle) of interest.

        Returns
        -------
        float
            Division rate, in time units.
        """
        if isinstance(lineage, CellLineage):
            cell_cycle = lineage.get_cell_cycle(noi)
            return 1 / (len(cell_cycle) * self.time_step)
        elif isinstance(lineage, CycleLineage):
            return 1 / (lineage.nodes[noi]["cycle_length"] * self.time_step)


# class CellPhase(NodeGlobalFeatureCalculator):

#     def compute(self, data: Data, lineage: CellLineage, noi: int) -> str:
#         """
#         Compute the phase(s) of the cell of interest.

#         Phases can be:
#         - 'division' -> when the out degree of the node is higher than its in degree
#         - 'birth' -> when the previous node is a division
#         - 'first' -> graph root i.e. beginning of lineage
#         - 'last' -> graph leaf i.e end of lineage
#         - '-' -> when the node is not in one of the above phases.

#         Notice that a node can be in different phases simultaneously, e.g. 'first'
#         and 'division'. In that case, a '+' sign is used as separator between phases,
#         e.g. 'first+division'.

#         Parameters
#         ----------
#         data : Data
#             Data object containing the lineage.
#         lineage : CellLineage
#             Lineage graph containing the cell of interest.
#         noi : int
#             Node ID (cell_ID) of the cell of interest.

#         Returns
#         -------
#         str
#             Phase(s) of the node.
#         """

#         def append_tag(tag, new_tag):
#             if not tag:
#                 tag = new_tag
#             else:
#                 tag += f"+{new_tag}"
#             return tag

#         tag = ""
#         # Straightforward cases.
#         if lineage.is_root(noi):
#             tag = append_tag(tag, "first")
#         if lineage.is_leaf(noi):
#             tag = append_tag(tag, "last")
#         if lineage.is_division(noi):
#             tag = append_tag(tag, "division")
#         # Checking for cell birth.
#         cc = lineage.get_cell_cycle(noi)
#         if noi == cc[0]:
#             tag = append_tag(tag, "birth")

#         if not tag:
#             return "-"
#         else:
#             return tag
