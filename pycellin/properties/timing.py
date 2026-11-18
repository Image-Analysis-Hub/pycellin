#!/usr/bin/env python3

r"""
A collection of time-related properties/attributes that can be added to lineage graphs.

Vocabulary:

- Property/Attribute: TrackMate (resp. NetworkX) uses the word property (resp.
  attribute) to refer to spot (resp. node), link (resp. edge) or track (resp. graph)
  information.
  Both are used here, depending on the context.
- Cell cycle: A cell cycle is a list of nodes between 2 successive divisions.
  It includes the second division but not the first one.
  For example, in the following graph where node IDs belong to [0, 9]::

        0           we have the following cell cycles:
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

- Complete cell cycle: It is a cell cycle that includes neither a root nor a leaf.
  If we take the previous example, the only complete cell cycle is [2, 4, 6].
"""

from typing import ClassVar

import numpy as np

from pycellin.classes.data import Data
from pycellin.classes.lineage import CellLineage, CycleLineage
from pycellin.classes.property import Property
from pycellin.classes.property_calculator import (
    NodeGlobalPropCalculator,
    NodeLocalPropCalculator,
)
from pycellin.exceptions import FusionError

# TODO: should I add the word Calc or Calculator to the class names?
# TODO: add calculator for mandatory cycle lineage properties (e.g. cycle_num_cells)


def create_absolute_age_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    dtype: str = "float",
    unit: str | None = None,
) -> Property:
    """
    Create the declaration of the ``absolute_age`` property.

    ``absolute_age`` is the age of the cell since the start of the lineage. It is a
    node property of cell lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"absolute_age"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Absolute age".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Age of the
        cell since the start of the lineage".
    dtype : str, default="float"
        Data type of the ages, usually the one of the time property they are computed
        from.
    unit : str | None, default=None
        Unit of the ages, usually the one of the time property they are computed from.

    Returns
    -------
    Property
        Declaration of the ``absolute_age`` property.
    """
    return Property(
        identifier=custom_identifier or "absolute_age",
        name=custom_name or "Absolute age",
        description=custom_description
        or "Age of the cell since the start of the lineage",
        provenance="pycellin",
        prop_type="node",
        lineage_type="cell",
        dtype=dtype,
        unit=unit,
    )


class AbsoluteAge(NodeLocalPropCalculator):
    """
    Calculator to compute the absolute age of cells.

    The absolute age of a cell is defined as the time elapsed since
    the beginning of the lineage. Absolute age of the root is 0.
    It is computed in the same unit as the time property given as input
    (e.g. ``frame``, ``time``, etc.).

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    time_prop : str
        Identifier of the cell lineage node property holding the time
        of the cells (e.g. ``frame``, ``POSITION_T``).
    """

    #: Input property: `time_prop`, a node property of cell lineages.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {"time_prop": ("node", "cell")}

    def __init__(self, property: Property, time_prop: str):
        super().__init__(property)
        self.time_prop = time_prop

    def compute(  # type: ignore[override]
        self, lineage: CellLineage, node_id: int
    ) -> int | float:
        """
        Compute the absolute age of a given cell.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        node_id : int
            Node ID (``cell_id``) of the cell of interest.

        Returns
        -------
        int | float
            Absolute age of the node.

        Raises
        ------
        KeyError
            If the cell is not in the lineage.
        LineageStructureError
            If the lineage doesn't have exactly one root, e.g. because of a cell fusion.
        """
        if node_id not in lineage.nodes:
            raise KeyError(f"Cell {node_id} not in the lineage.")
        root = lineage.get_root()
        age = (
            lineage.nodes[node_id][self.time_prop] - lineage.nodes[root][self.time_prop]
        )
        return age


def create_relative_age_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    dtype: str = "float",
    unit: str | None = None,
) -> Property:
    """
    Create the declaration of the ``relative_age`` property.

    ``relative_age`` is the age of the cell since the start of its cell cycle. It is
    a node property of cell lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"relative_age"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Relative age".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Age of the
        cell since the start of the current cell cycle".
    dtype : str, default="float"
        Data type of the ages, usually the one of the time property they are computed
        from.
    unit : str | None, default=None
        Unit of the ages, usually the one of the time property they are computed from.

    Returns
    -------
    Property
        Declaration of the ``relative_age`` property.
    """
    return Property(
        identifier=custom_identifier or "relative_age",
        name=custom_name or "Relative age",
        description=custom_description
        or "Age of the cell since the start of the current cell cycle",
        provenance="pycellin",
        prop_type="node",
        lineage_type="cell",
        dtype=dtype,
        unit=unit,
    )


class RelativeAge(NodeLocalPropCalculator):
    """
    Calculator to compute the relative age of cells.

    The relative age of a cell is defined as the time elapsed since
    the start of the cell cycle (i.e. previous division, or beginning
    of the lineage). Relative age of the first cell of a cell cycle is 0.
    It is computed in the same unit as the time property given as input
    (e.g. ``frame``, ``time``, etc.).

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    time_prop : str
        Identifier of the cell lineage node property holding the time
        of the cells (e.g. ``frame``, ``POSITION_T``).
    """

    #: Input property: `time_prop`, a node property of cell lineages.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {"time_prop": ("node", "cell")}

    def __init__(self, property: Property, time_prop: str):
        super().__init__(property)
        self.time_prop = time_prop

    def compute(  # type: ignore[override]
        self, lineage: CellLineage, node_id: int
    ) -> int | float:
        """
        Compute the relative age of a given cell.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        node_id : int
            Node ID (``cell_id``) of the cell of interest.

        Returns
        -------
        int | float
            Relative age of the node.

        Raises
        ------
        KeyError
            If the cell is not in the lineage.
        FusionError
            If the cell or an earlier cell of its cell cycle has more than one parent.
        """
        if node_id not in lineage.nodes:
            raise KeyError(f"Cell {node_id} not in the lineage.")
        first_cell = lineage.get_cell_cycle(node_id)[0]
        age = (
            lineage.nodes[node_id][self.time_prop]
            - lineage.nodes[first_cell][self.time_prop]
        )
        return age


def create_normalized_age_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    """
    Create the declaration of the ``normalized_age`` property.

    ``normalized_age`` is the relative age of the cell divided by the duration of its
    cell cycle: 0 for the first cell of the cycle, 1 for the last one. It is a node
    property of cell lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"normalized_age"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Normalized age".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Relative age
        of the cell divided by the duration of its cell cycle: 0 for the first cell of
        the cycle, 1 for the last one".

    Returns
    -------
    Property
        Declaration of the ``normalized_age`` property.
    """
    return Property(
        identifier=custom_identifier or "normalized_age",
        name=custom_name or "Normalized age",
        description=custom_description
        or "Relative age of the cell divided by the duration of its cell cycle: "
        "0 for the first cell of the cycle, 1 for the last one",
        provenance="pycellin",
        prop_type="node",
        lineage_type="cell",
        dtype="float",
    )


class NormalizedAge(NodeLocalPropCalculator):
    """
    Calculator to compute the normalized age of cells.

    The normalized age of a cell is its relative age divided by the duration of
    its cell cycle, both computed from the time property given as input. It is 0
    for the first cell of a cell cycle and 1 for the last one. Incomplete cell
    cycles, which start at the root or end with a leaf, are normalized over their
    observed part, unless `ignore_incomplete_cycles` is True: their cells then get
    NaN. The normalized age is also NaN for the cells of a cell cycle that lasts
    no time, such as a cell cycle of a single cell.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    time_prop : str
        Identifier of the cell lineage node property holding the time
        of the cells (e.g. ``frame``, ``POSITION_T``).
    ignore_incomplete_cycles : bool, default=False
        True to give NaN to the cells of incomplete cell cycles, False to
        normalize them over their observed part.
    """

    #: Input property: `time_prop`, a node property of cell lineages.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {"time_prop": ("node", "cell")}

    def __init__(
        self,
        property: Property,
        time_prop: str,
        ignore_incomplete_cycles: bool = False,
    ):
        super().__init__(property)
        self.time_prop = time_prop
        self.ignore_incomplete_cycles = ignore_incomplete_cycles

    def compute(  # type: ignore[override]
        self, lineage: CellLineage, node_id: int
    ) -> float:
        """
        Compute the normalized age of a given cell.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        node_id : int
            Node ID (``cell_id``) of the cell of interest.

        Returns
        -------
        float
            Normalized age of the cell, or NaN if its cell cycle lasts no time
            or is an ignored incomplete cell cycle.

        Raises
        ------
        KeyError
            If the cell is not in the lineage.
        FusionError
            If the cell or an earlier cell of its cell cycle has more than one parent.
        """
        if node_id not in lineage.nodes:
            raise KeyError(f"Cell {node_id} not in the lineage.")
        cells = lineage.get_cell_cycle(node_id)
        if self.ignore_incomplete_cycles and (
            lineage.is_root(cells[0]) or lineage.is_leaf(cells[-1])
        ):
            return np.nan
        start_time = lineage.nodes[cells[0]][self.time_prop]
        duration = lineage.nodes[cells[-1]][self.time_prop] - start_time
        if duration == 0:
            return np.nan
        return (lineage.nodes[node_id][self.time_prop] - start_time) / duration


def _get_cell_lin_timepoints(
    lineage: CellLineage, nid: int, time_prop: str
) -> tuple[int | float, int | float]:
    """
    Get the time values of the divisions defining the cell cycle of a cell.

    This function is used by the `InterdivisionTime` and `DivisionRate` calculators.

    Parameters
    ----------
    lineage : CellLineage
        Lineage graph containing the node of interest.
    nid : int
        Node ID (``cell_id``) of the cell of interest.
    time_prop : str
        The identifier of the time property (e.g. ``frame``, ``time``, etc.) to use
        for calculation.

    Returns
    -------
    tuple[int | float, int | float]
        Time values of the current and previous division: of the last cell of the
        cell cycle, and of the parent of its first cell, or of the first cell itself
        if it is the root.

    Raises
    ------
    KeyError
        If the cell is not in the lineage.
    FusionError
        If the cell or an earlier cell of its cell cycle has more than one parent.
    """
    if nid not in lineage.nodes:
        raise KeyError(f"Cell {nid} not in the lineage.")
    cells = lineage.get_cell_cycle(nid)
    frame_current_div = lineage.nodes[cells[-1]][time_prop]
    ancestors = list(lineage.predecessors(cells[0]))
    if len(ancestors) > 1:
        raise FusionError(nid, lineage.graph["lineage_id"])
    elif len(ancestors) == 0:
        frame_prev_div = lineage.nodes[cells[0]][time_prop]
    else:
        frame_prev_div = lineage.nodes[ancestors[0]][time_prop]
    return frame_current_div, frame_prev_div


def _get_cycle_lin_timepoints(
    data: Data, lineage: CycleLineage, nid: int, time_prop: str
) -> tuple[int | float, int | float]:
    """
    Get the time values of the divisions defining a cell cycle.

    This function is used by the `InterdivisionTime` and `DivisionRate` calculators.

    Parameters
    ----------
    data : Data
        Data object containing the lineage.
    lineage : CycleLineage
        Lineage graph containing the node of interest.
    nid : int
        Node ID (``cycle_id``) of the cell cycle of interest.
    time_prop : str
        The identifier of the time property (e.g. ``frame``, ``time``, etc.) to use
        for calculation.

    Returns
    -------
    tuple[int | float, int | float]
        Time values of the current and previous division: of the last cell of the
        cell cycle, and of the last cell of the previous cell cycle, or of the first
        cell of the cell cycle if it is the root.

    Raises
    ------
    KeyError
        If the cycle is not in the lineage.
    FusionError
        If the cycle has more than one parent.
    """
    if nid not in lineage.nodes:
        raise KeyError(f"Cycle {nid} not in the lineage.")
    cells = lineage.nodes[nid]["cells"]
    cell_lin = data.cell_lineages[lineage.graph["lineage_id"]]
    frame_current_div = cell_lin.nodes[cells[-1]][time_prop]
    ancestors = list(lineage.predecessors(nid))
    if len(ancestors) > 1:
        raise FusionError(nid, lineage.graph["lineage_id"])
    elif len(ancestors) == 0:
        frame_prev_div = cell_lin.nodes[cells[0]][time_prop]
    else:
        prev_cells = lineage.nodes[ancestors[0]]["cells"]
        frame_prev_div = cell_lin.nodes[prev_cells[-1]][time_prop]
    return frame_current_div, frame_prev_div


def create_interdivision_time_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    dtype: str = "float",
    unit: str | None = None,
) -> Property:
    """
    Create the declaration of the ``interdivision_time`` property.

    ``interdivision_time`` is the time elapsed between two successive divisions. It is
    a node property of cycle lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"interdivision_time"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Interdivision time".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Time elapsed
        between two successive divisions".
    dtype : str, default="float"
        Data type of the interdivision times, usually the one of the time property they
        are computed from.
    unit : str | None, default=None
        Unit of the interdivision times, usually the one of the time property they are
        computed from.

    Returns
    -------
    Property
        Declaration of the ``interdivision_time`` property.
    """
    return Property(
        identifier=custom_identifier or "interdivision_time",
        name=custom_name or "Interdivision time",
        description=custom_description
        or "Time elapsed between two successive divisions",
        provenance="pycellin",
        prop_type="node",
        lineage_type="cycle",
        dtype=dtype,
        unit=unit,
    )


class InterdivisionTime(NodeGlobalPropCalculator):
    """
    Calculator to compute the interdivision time of cells.

    Interdivision time is defined as the time elapsed between the 2 divisions
    that define the cell cycle.
    It is computed in the same unit as the time property given as input
    (e.g. ``frame``, ``time``, etc.).

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    time_prop : str
        Identifier of the cell lineage node property holding the time
        of the cells (e.g. ``frame``, ``POSITION_T``).
    """

    #: Input property: `time_prop`, a node property of cell lineages.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {"time_prop": ("node", "cell")}

    def __init__(self, property: Property, time_prop: str):
        super().__init__(property)
        self.time_prop = time_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CellLineage | CycleLineage, node_id: int
    ) -> int | float:
        """
        Compute the interdivision time of a given cell or cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage | CycleLineage
            Lineage graph containing the node (cell or cell cycle) of interest.
        node_id : int
            Node ID of the node (cell or cell cycle) of interest.

        Returns
        -------
        int | float
            Interdivision time.

        Raises
        ------
        KeyError
            If the cell or cycle is not in the lineage.
        FusionError
            If the cell or cell cycle, or an earlier cell of its cell cycle, has more
            than one parent.
        TypeError
            If `lineage` is neither a `~pycellin.CellLineage` nor a
            `~pycellin.CycleLineage`.
        """
        if isinstance(lineage, CellLineage):
            timepoint_curr_div, timepoint_prev_div = _get_cell_lin_timepoints(
                lineage, node_id, self.time_prop
            )
        elif isinstance(lineage, CycleLineage):
            timepoint_curr_div, timepoint_prev_div = _get_cycle_lin_timepoints(
                data, lineage, node_id, self.time_prop
            )
        else:
            raise TypeError(
                "Lineage must be of type CellLineage or CycleLineage, not "
                f"{type(lineage)}."
            )

        return timepoint_curr_div - timepoint_prev_div


def create_division_rate_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    """
    Create the declaration of the ``division_rate`` property.

    ``division_rate`` is the number of divisions per time unit. It is a node property
    of cycle lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"division_rate"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Division rate".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Number of
        divisions per time unit".
    unit : str | None, default=None
        Unit of the division rates, e.g. ``"1/min"``.

    Returns
    -------
    Property
        Declaration of the ``division_rate`` property.
    """
    return Property(
        identifier=custom_identifier or "division_rate",
        name=custom_name or "Division rate",
        description=custom_description or "Number of divisions per time unit",
        provenance="pycellin",
        prop_type="node",
        lineage_type="cycle",
        dtype="float",
        unit=unit,
    )


class DivisionRate(NodeGlobalPropCalculator):
    """
    Calculator to compute the division rate of cells.

    Division rate is defined as the number of divisions per time unit.
    It is the inverse of the interdivision time.
    It is computed in the inverse of the unit of the time property given as input
    (e.g. ``frame``, ``time``, etc.).

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    time_prop : str
        Identifier of the cell lineage node property holding the time
        of the cells (e.g. ``frame``, ``POSITION_T``).
    """

    #: Input property: `time_prop`, a node property of cell lineages.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {"time_prop": ("node", "cell")}

    def __init__(self, property: Property, time_prop: str):
        super().__init__(property)
        self.time_prop = time_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CellLineage | CycleLineage, node_id: int
    ) -> int | float:
        """
        Compute the division rate of a given cell or cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage | CycleLineage
            Lineage graph containing the node (cell or cell cycle) of interest.
        node_id : int
            Node ID of the node (cell or cell cycle) of interest.

        Returns
        -------
        int | float
            Division rate, or NaN if the interdivision time is 0.

        Raises
        ------
        KeyError
            If the cell or cycle is not in the lineage.
        FusionError
            If the cell or cell cycle, or an earlier cell of its cell cycle, has more
            than one parent.
        TypeError
            If `lineage` is neither a `~pycellin.CellLineage` nor a
            `~pycellin.CycleLineage`.
        """
        if isinstance(lineage, CellLineage):
            timepoint_curr_div, timepoint_prev_div = _get_cell_lin_timepoints(
                lineage, node_id, self.time_prop
            )
        elif isinstance(lineage, CycleLineage):
            timepoint_curr_div, timepoint_prev_div = _get_cycle_lin_timepoints(
                data, lineage, node_id, self.time_prop
            )
        else:
            raise TypeError(
                "Lineage must be of type CellLineage or CycleLineage, not "
                f"{type(lineage)}."
            )

        div_time = timepoint_curr_div - timepoint_prev_div
        if div_time == 0:
            return np.nan
        else:
            return 1 / div_time


# class CellPhase(NodeGlobalPropCalculator):

#     def compute(self, data: Data, lineage: CellLineage, nid: int) -> str:
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
#         nid : int
#             Node ID (cell_id) of the cell of interest.

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
#         if lineage.is_root(nid):
#             tag = append_tag(tag, "first")
#         if lineage.is_leaf(nid):
#             tag = append_tag(tag, "last")
#         if lineage.is_division(nid):
#             tag = append_tag(tag, "division")
#         # Checking for cell birth.
#         cc = lineage.get_cell_cycle(nid)
#         if nid == cc[0]:
#             tag = append_tag(tag, "birth")

#         if not tag:
#             return "-"
#         else:
#             return tag
