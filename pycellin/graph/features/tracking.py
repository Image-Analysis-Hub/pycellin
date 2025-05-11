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
       / \\            [3, 5, 7]
      2   3           [8]
      |   |           [9]
      4   5
      |   |
      6   7
     / \\
    8   9

- Complete generation: It is a generation that do not include a root nor a leaf.
  If we take the previous example, the only complete generation is [2, 4, 6].
"""

import numpy as np

from pycellin.classes import CellLineage, CycleLineage, Data, Feature
from pycellin.classes.exceptions import FusionError
from pycellin.classes.feature_calculator import NodeGlobalFeatureCalculator

# TODO: should I add the word Calc or Calculator to the class names?
# TODO: add calculator for mandatory cycle lineage features (e.g. cycle length)


class AbsoluteAge(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the absolute age of cells.

    The absolute age of a cell is defined as the time elapsed since
    the beginning of the lineage. Absolute age of the root is 0.
    It is given in frames by default, but can be converted
    to the time unit of the model if specified.
    """

    def __init__(self, feature: Feature, time_step: int | float = 1):
        """
        Parameters
        ----------
        feature : Feature
            Feature object to which the calculator is associated.
        time_step : int | float, optional
            Time step between 2 frames, in time unit. Default is 1.
        """
        super().__init__(feature)
        self.time_step = time_step

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CellLineage, noi: int
    ) -> int | float:
        """
        Compute the absolute age of a given cell.

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
        int | float
            Absolute age of the node.

        Raises
        ------
        KeyError
            If the cell is not in the lineage.
        """
        root = lineage.get_root()
        if noi not in lineage.nodes:
            raise KeyError(f"Cell {noi} not in the lineage.")
        age_in_frame = lineage.nodes[noi]["frame"] - lineage.nodes[root]["frame"]
        return age_in_frame * self.time_step


class RelativeAge(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the relative age of cells.

    The relative age of a cell is defined as the time elapsed since
    the start of the cell cycle (i.e. previous division, or beginning
    of the lineage). Relative age of the first cell of a cell cycle is 0.
    It is given in frames by default, but can be converted
    to the time unit of the model if specified.
    """

    def __init__(self, feature: Feature, time_step: int | float = 1):
        """
        Parameters
        ----------
        feature : Feature
            Feature object to which the calculator is associated.
        time_step : int | float, optional
            Time step between 2 frames, in time unit. Default is 1.
        """
        super().__init__(feature)
        self.time_step = time_step

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CellLineage, noi: int
    ) -> int | float:
        """
        Compute the relative age of a given cell.

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
        int | float
            Relative age of the node.

        Raises
        ------
        KeyError
            If the cell is not in the lineage.
        """
        if noi not in lineage.nodes:
            raise KeyError(f"Cell {noi} not in the lineage.")
        first_cell = lineage.get_cell_cycle(noi)[0]
        age_in_frame = lineage.nodes[noi]["frame"] - lineage.nodes[first_cell]["frame"]
        return age_in_frame * self.time_step


class CycleCompleteness(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the cell cycle completeness.

    A cell cycle is defined as complete when it starts by a division
    AND ends by a division. Cell cycles that start at the root
    or end with a leaf are thus incomplete.
    This can be useful when analyzing features like division time. It avoids
    the introduction of a bias since we have no information on what happened
    before the root or after the leaves.
    """

    def compute(  # type: ignore[override]
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

        Raises
        ------
        KeyError
            If the cell or cycle is not in the lineage.
        """
        if isinstance(lineage, CellLineage):
            if noi not in lineage.nodes:
                raise KeyError(f"Cell {noi} not in the lineage.")
            cell_cycle = lineage.get_cell_cycle(noi)
            if lineage.is_root(cell_cycle[0]) or lineage.is_leaf(cell_cycle[-1]):
                return False
            else:
                return True
        elif isinstance(lineage, CycleLineage):
            if noi not in lineage.nodes:
                raise KeyError(f"Cycle {noi} not in the lineage.")
            if lineage.is_root(noi) or lineage.is_leaf(noi):
                return False
            else:
                return True


def _get_cell_lin_frames(lineage: CellLineage, noi: int) -> tuple[int, int]:
    """
    Get the frames of the divisions defining the cell cycle.

    This function is used by the DivisionTime and DivisionRate calculators.

    Parameters
    ----------
    lineage : CellLineage
        Lineage graph containing the node of interest.
    noi : int
        Node ID (cell_ID) of the cell of interest.

    Returns
    -------
    tuple[int, int]
        Frames of the current and previous division.

    Raises
    ------
    KeyError
        If the cell is not in the lineage.
    FusionError
        If the cell has more than one ancestor.
    """
    if noi not in lineage.nodes:
        raise KeyError(f"Cell {noi} not in the lineage.")
    cells = lineage.get_cell_cycle(noi)
    frame_current_div = lineage.nodes[cells[-1]]["frame"]
    ancestors = list(lineage.predecessors(cells[0]))
    if len(ancestors) > 1:
        raise FusionError(noi, lineage.graph["lineage_ID"])
    elif len(ancestors) == 0:
        frame_prev_div = lineage.nodes[cells[0]]["frame"]
    else:
        frame_prev_div = lineage.nodes[ancestors[0]]["frame"]
    return frame_current_div, frame_prev_div


def _get_cycle_lin_frames(
    data: Data, lineage: CycleLineage, noi: int
) -> tuple[int, int]:
    """
    Get the frames of the divisions defining the cell cycle.

    This function is used by the DivisionTime and DivisionRate calculators.

    Parameters
    ----------
    data : Data
        Data object containing the lineage.
    lineage : CycleLineage
        Lineage graph containing the node of interest.
    noi : int
        Node ID (cell_ID) of the cell of interest.

    Returns
    -------
    tuple[int, int]
        Frames of the current and previous division.

    Raises
    ------
    KeyError
        If the cycle is not in the lineage.
    FusionError
        If the cycle has more than one ancestor.
    """
    if noi not in lineage.nodes:
        raise KeyError(f"Cycle {noi} not in the lineage.")
    cells = lineage.nodes[noi]["cells"]
    cell_lin = data.cell_data[lineage.graph["lineage_ID"]]
    frame_current_div = cell_lin.nodes[cells[-1]]["frame"]
    ancestors = list(lineage.predecessors(noi))
    if len(ancestors) > 1:
        raise FusionError(noi, lineage.graph["lineage_ID"])
    elif len(ancestors) == 0:
        frame_prev_div = cell_lin.nodes[cells[0]]["frame"]
    else:
        prev_cells = lineage.nodes[ancestors[0]]["cells"]
        frame_prev_div = cell_lin.nodes[prev_cells[-1]]["frame"]
    return frame_current_div, frame_prev_div


class DivisionTime(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the division time of cells.

    Division time is defined as the time elapsed between the 2 divisions
    that define the cell cycle. It is given in frames by default, but can
    be converted to the time unit of the model if specified.
    """

    def __init__(self, feature: Feature, time_step: int | float = 1):
        """
        Parameters
        ----------
        feature : Feature
            Feature object to which the calculator is associated.
        time_step : int | float, optional
            Time step between 2 frames, in time unit. Default is 1.
        """
        super().__init__(feature)
        self.time_step = time_step

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CellLineage | CycleLineage, noi: int
    ) -> int | float:
        """
        Compute the division time of a given cell or cell cycle.

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
        int | float
            Division time.

        Raises
        ------
        KeyError
            If the cell or cycle is not in the lineage.
        """
        if isinstance(lineage, CellLineage):
            frame_curr_div, frame_prev_div = _get_cell_lin_frames(lineage, noi)
        elif isinstance(lineage, CycleLineage):
            frame_curr_div, frame_prev_div = _get_cycle_lin_frames(data, lineage, noi)
        else:
            raise TypeError(
                f"Lineage must be of type CellLineage or CycleLineage, "
                f"not {type(lineage)}."
            )

        return (frame_curr_div - frame_prev_div) * self.time_step


class DivisionRate(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the division rate of cells.

    Division rate is defined as the number of divisions per time unit.
    It is the inverse of the division time.
    It is given in divisions per frame by default, but can be converted
    to divisions per time unit of the model if specified.
    """

    def __init__(
        self, feature: Feature, time_step: int | float = 1, use_div_time: bool = False
    ):
        """
        Parameters
        ----------
        feature : Feature
            Feature object to which the calculator is associated.
        time_step : int | float, optional
            Time step between 2 frames, in time unit. Default is 1.
        use_div_time : bool, optional
            If True, use the division time already computed in the lineage.
            If False, compute the division time from the lineage. Default is False.
            The first option is faster but you need to ensure that the division time
            is computed and updated BEFORE division rate. This can be ensured
            by adding to the model the division time feature before the division
            rate feature. Moreover, if `use_div_time` is True, `time_step` will be
            ignored: division rate will use the division time unit (e.g. if division
            time is in frames, division rate will be in divisions per frame).
        """
        super().__init__(feature)
        self.time_step = time_step
        self.use_div_time = use_div_time

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CellLineage | CycleLineage, noi: int
    ) -> int | float:
        """
        Compute the division rate of a given cell or cell cycle.

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
        int | float
            Division rate.

        Raises
        ------
        KeyError
            If the cell or cycle is not in the lineage.
        """
        if self.use_div_time:
            if noi not in lineage.nodes:
                if isinstance(lineage, CellLineage):
                    lin_txt = "Cell"
                elif isinstance(lineage, CycleLineage):
                    lin_txt = "Cycle"
                else:
                    raise TypeError(
                        f"Lineage must be of type CellLineage or CycleLineage, "
                        f"not {type(lineage)}."
                    )
                raise KeyError(f"{lin_txt} {noi} not in the lineage.")
            try:
                div_time = lineage.nodes[noi]["division_time"]
            except KeyError:
                raise KeyError(
                    f"Division time not present for cell {noi} in lineage "
                    f"{lineage.graph['lineage_ID']}."
                )
            if div_time == 0:
                return np.nan
            else:
                return 1 / div_time

        if isinstance(lineage, CellLineage):
            frame_curr_div, frame_prev_div = _get_cell_lin_frames(lineage, noi)
        elif isinstance(lineage, CycleLineage):
            frame_curr_div, frame_prev_div = _get_cycle_lin_frames(data, lineage, noi)
        else:
            raise TypeError(
                f"Lineage must be of type CellLineage or CycleLineage, "
                f"not {type(lineage)}."
            )

        div_time = (frame_curr_div - frame_prev_div) * self.time_step
        if div_time == 0:
            return np.nan
        else:
            return 1 / div_time


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
