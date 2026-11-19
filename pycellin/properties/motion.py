#!/usr/bin/env python3

"""A collection of properties related to cell mobility/motility."""

import math
from itertools import pairwise
from typing import ClassVar, Literal

import numpy as np

from pycellin.classes.data import Data
from pycellin.classes.lineage import CellLineage, CycleLineage
from pycellin.classes.property import Property
from pycellin.classes.property_calculator import (
    EdgeLocalPropCalculator,
    NodeGlobalPropCalculator,
    NodeLocalPropCalculator,
)
from pycellin.exceptions import FusionError
from pycellin.properties.utils import (
    _get_cycle_edge_property_values,
    _get_position,
    _nanmean,
    _nansum,
)


def create_cell_displacement_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    """
    Create the declaration of the ``cell_displacement`` property.

    ``cell_displacement`` is the displacement of the cell between two consecutive
    detections. It is an edge property of cell lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"cell_displacement"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Cell displacement".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Displacement
        of the cell between two consecutive detections".
    unit : str | None, default=None
        Unit of the displacements, e.g. ``"µm"``.

    Returns
    -------
    Property
        Declaration of the ``cell_displacement`` property.
    """
    return Property(
        identifier=custom_identifier or "cell_displacement",
        name=custom_name or "Cell displacement",
        description=custom_description
        or "Displacement of the cell between two consecutive detections",
        provenance="Pycellin",
        prop_type="edge",
        lineage_type="cell",
        dtype="float",
        unit=unit,
    )


class CellDisplacement(EdgeLocalPropCalculator[CellLineage]):
    """
    Calculator to compute the displacement of a cell between two consecutive detections.

    The displacement is defined as the Euclidean distance between the positions
    of the cell at the two consecutive detections.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    coord_props : tuple[str, ...], default=("cell_x", "cell_y", "cell_z")
        Identifiers of the cell lineage node properties holding the coordinates
        of the cells, one per axis. The default is for 3D data.
    """

    def __init__(
        self,
        property: Property,
        coord_props: tuple[str, ...] = ("cell_x", "cell_y", "cell_z"),
    ):
        super().__init__(property)
        self.coord_props = coord_props

    def compute(self, lineage: CellLineage, edge: tuple[int, int]) -> float:
        """
        Compute the displacement of a cell between two consecutive detections.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        edge : tuple[int, int]
            A tuple of cell IDs that defines the edge of interest.

        Returns
        -------
        float
            The cell displacement.

        Raises
        ------
        MissingPropertyError
            If a cell of the edge has no value for one of the coordinates.
        """
        prop_id = self.property.identifier
        pos1 = _get_position(lineage, edge[0], self.coord_props, prop_id)
        pos2 = _get_position(lineage, edge[1], self.coord_props, prop_id)
        return math.dist(pos1, pos2)


def create_cycle_total_displacement_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    """
    Create the declaration of the ``cycle_total_displacement`` property.

    ``cycle_total_displacement`` is the displacement of the cell during the cell
    cycle: the sum of its displacements between consecutive detections. It is a node
    property of cycle lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"cycle_total_displacement"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Cycle total displacement".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Displacement
        of the cell during the cell cycle".
    unit : str | None, default=None
        Unit of the displacements, e.g. ``"µm"``.

    Returns
    -------
    Property
        Declaration of the ``cycle_total_displacement`` property.
    """
    return Property(
        identifier=custom_identifier or "cycle_total_displacement",
        name=custom_name or "Cycle total displacement",
        description=custom_description
        or "Displacement of the cell during the cell cycle",
        provenance="Pycellin",
        prop_type="node",
        lineage_type="cycle",
        dtype="float",
        unit=unit,
    )


class CycleTotalDisplacement(NodeGlobalPropCalculator[CycleLineage]):
    """
    Calculator to compute the total displacement of a cell during a cell cycle.

    The cycle total displacement is defined as the sum of the displacements of the
    cell during the cell cycle. NaN values are ignored. It is NaN when the cell cycle
    has no link with a displacement value, e.g. a cell cycle of a single cell.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    include_incoming_edge : bool, default=False
        Whether to include the incoming edge of the first cell of the cell cycle.
    displacement_prop : str, default="cell_displacement"
        Identifier of the cell lineage edge property holding the
        cell displacements.
    """

    #: Input property: `displacement_prop`, an edge property of cell lineages.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "displacement_prop": ("edge", "cell")
    }

    def __init__(
        self,
        property: Property,
        include_incoming_edge: bool = False,
        displacement_prop: str = "cell_displacement",
    ):
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge
        self.displacement_prop = displacement_prop

    def compute(self, data: Data, lineage: CycleLineage, node_id: int) -> float:
        """
        Compute the total displacement of a cell during the cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        node_id : int
            Node ID (``cycle_id``) of the cell cycle of interest.

        Returns
        -------
        float
            Total displacement of the cell during the cell cycle, or NaN if
            the cell cycle has no link with a displacement value.

        Raises
        ------
        MissingPropertyError
            If a link of the cell cycle has no value for `displacement_prop`.
        FusionError
            If `include_incoming_edge` is True and the first cell of the cell cycle has
            more than one parent.
        """
        disps = _get_cycle_edge_property_values(
            self.displacement_prop, data, lineage, node_id, self.include_incoming_edge
        )
        return _nansum(disps)


def create_cycle_mean_displacement_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    """
    Create the declaration of the ``cycle_mean_displacement`` property.

    ``cycle_mean_displacement`` is the mean displacement of the cell during the cell
    cycle. It is a node property of cycle lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"cycle_mean_displacement"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Cycle mean displacement".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Mean
        displacement of the cell during the cell cycle".
    unit : str | None, default=None
        Unit of the displacements, e.g. ``"µm"``.

    Returns
    -------
    Property
        Declaration of the ``cycle_mean_displacement`` property.
    """
    return Property(
        identifier=custom_identifier or "cycle_mean_displacement",
        name=custom_name or "Cycle mean displacement",
        description=custom_description
        or "Mean displacement of the cell during the cell cycle",
        provenance="Pycellin",
        prop_type="node",
        lineage_type="cycle",
        dtype="float",
        unit=unit,
    )


class CycleMeanDisplacement(NodeGlobalPropCalculator[CycleLineage]):
    """
    Calculator to compute the mean displacement of a cell during a cell cycle.

    The cycle mean displacement is defined as the mean displacement of the cell during
    the cell cycle. NaN values are ignored. It is NaN when the cell cycle has
    no link with a displacement value, e.g. a cell cycle of a single cell.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    include_incoming_edge : bool, default=False
        Whether to include the incoming edge of the first cell of the cell cycle.
    displacement_prop : str, default="cell_displacement"
        Identifier of the cell lineage edge property holding the
        cell displacements.
    """

    #: Input property: `displacement_prop`, an edge property of cell lineages.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "displacement_prop": ("edge", "cell")
    }

    def __init__(
        self,
        property: Property,
        include_incoming_edge: bool = False,
        displacement_prop: str = "cell_displacement",
    ):
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge
        self.displacement_prop = displacement_prop

    def compute(self, data: Data, lineage: CycleLineage, node_id: int) -> float:
        """
        Compute the mean displacement of a cell during the cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        node_id : int
            Node ID (``cycle_id``) of the cell cycle of interest.

        Returns
        -------
        float
            Mean displacement of the cell during the cell cycle, or NaN if
            the cell cycle has no link with a displacement value.

        Raises
        ------
        MissingPropertyError
            If a link of the cell cycle has no value for `displacement_prop`.
        FusionError
            If `include_incoming_edge` is True and the first cell of the cell cycle has
            more than one parent.
        """
        disps = _get_cycle_edge_property_values(
            self.displacement_prop, data, lineage, node_id, self.include_incoming_edge
        )
        return _nanmean(disps)


def create_cell_speed_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    """
    Create the declaration of the ``cell_speed`` property.

    ``cell_speed`` is the speed of the cell between two consecutive detections. It is
    an edge property of cell lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"cell_speed"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Cell speed".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Speed of the
        cell between two consecutive detections".
    unit : str | None, default=None
        Unit of the speeds, e.g. ``"µm/min"``.

    Returns
    -------
    Property
        Declaration of the ``cell_speed`` property.
    """
    return Property(
        identifier=custom_identifier or "cell_speed",
        name=custom_name or "Cell speed",
        description=custom_description
        or "Speed of the cell between two consecutive detections",
        provenance="Pycellin",
        prop_type="edge",
        lineage_type="cell",
        dtype="float",
        unit=unit,
    )


class CellSpeed(EdgeLocalPropCalculator[CellLineage]):
    """
    Calculator to compute the speed of a cell between two consecutive detections.

    The speed is defined as the displacement of the cell divided by the time interval
    between the two consecutive detections. It is computed from the cell positions
    and the time property, not from the cell displacement property.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    time_prop : str
        Identifier of the cell lineage node property holding the time
        of the cells (e.g. ``frame``, ``POSITION_T``).
    coord_props : tuple[str, ...], default=("cell_x", "cell_y", "cell_z")
        Identifiers of the cell lineage node properties holding the coordinates
        of the cells, one per axis. The default is for 3D data.
    """

    #: Input property: `time_prop`, a node property of cell lineages.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {"time_prop": ("node", "cell")}

    def __init__(
        self,
        property: Property,
        time_prop: str,
        coord_props: tuple[str, ...] = ("cell_x", "cell_y", "cell_z"),
    ):
        super().__init__(property)
        self.time_prop = time_prop
        self.coord_props = coord_props

    def compute(self, lineage: CellLineage, edge: tuple[int, int]) -> float:
        """
        Compute the speed of a cell between two consecutive detections.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        edge : tuple[int, int]
            A tuple of cell IDs that defines the edge of interest.

        Returns
        -------
        float
            Cell speed between two consecutive detections.

        Raises
        ------
        KeyError
            If a cell of the edge has no value for `time_prop`.
        MissingPropertyError
            If a cell of the edge has no value for one of the coordinates.
        """
        time1 = lineage.nodes[edge[0]][self.time_prop]
        time2 = lineage.nodes[edge[1]][self.time_prop]
        prop_id = self.property.identifier
        pos1 = _get_position(lineage, edge[0], self.coord_props, prop_id)
        pos2 = _get_position(lineage, edge[1], self.coord_props, prop_id)
        return math.dist(pos1, pos2) / (time2 - time1)


def create_cycle_mean_speed_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    """
    Create the declaration of the ``cycle_mean_speed`` property.

    ``cycle_mean_speed`` is the mean speed of the cell during the cell cycle. It is a
    node property of cycle lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"cycle_mean_speed"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Cycle mean speed".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Mean speed
        of the cell during the cell cycle".
    unit : str | None, default=None
        Unit of the speeds, e.g. ``"µm/min"``.

    Returns
    -------
    Property
        Declaration of the ``cycle_mean_speed`` property.
    """
    return Property(
        identifier=custom_identifier or "cycle_mean_speed",
        name=custom_name or "Cycle mean speed",
        description=custom_description
        or "Mean speed of the cell during the cell cycle",
        provenance="Pycellin",
        prop_type="node",
        lineage_type="cycle",
        dtype="float",
        unit=unit,
    )


class CycleMeanSpeed(NodeGlobalPropCalculator[CycleLineage]):
    """
    Calculator to compute the mean speed of a cell during a cell cycle.

    The cycle mean speed is defined as the mean speed of the cell
    during the cell cycle. NaN values are ignored. It is NaN when the cell cycle
    has no link with a speed value, e.g. a cell cycle of a single cell.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    include_incoming_edge : bool, default=False
        Whether to include the incoming edge of the first cell of the cell cycle.
    speed_prop : str, default="cell_speed"
        Identifier of the cell lineage edge property holding the
        cell speeds.
    """

    #: Input property: `speed_prop`, an edge property of cell lineages.
    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {"speed_prop": ("edge", "cell")}

    def __init__(
        self,
        property: Property,
        include_incoming_edge: bool = False,
        speed_prop: str = "cell_speed",
    ):
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge
        self.speed_prop = speed_prop

    def compute(self, data: Data, lineage: CycleLineage, node_id: int) -> float:
        """
        Compute the mean speed of a cell during the cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        node_id : int
            Node ID (``cycle_id``) of the cell cycle of interest.

        Returns
        -------
        float
            Mean speed of the cell during the cell cycle, or NaN if the cell cycle
            has no link with a speed value.

        Raises
        ------
        MissingPropertyError
            If a link of the cell cycle has no value for `speed_prop`.
        FusionError
            If `include_incoming_edge` is True and the first cell of the cell cycle has
            more than one parent.
        """
        speeds = _get_cycle_edge_property_values(
            self.speed_prop, data, lineage, node_id, self.include_incoming_edge
        )
        return _nanmean(speeds)


def create_straightness_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    """
    Create the declaration of the ``straightness`` property.

    ``straightness`` is the straightness of the cell trajectory during the cell cycle,
    between 0 and 1. It is a node property of cycle lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"straightness"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Straightness".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Straightness
        of the cell trajectory during the cell cycle".

    Returns
    -------
    Property
        Declaration of the ``straightness`` property.
    """
    return Property(
        identifier=custom_identifier or "straightness",
        name=custom_name or "Straightness",
        description=custom_description
        or "Straightness of the cell trajectory during the cell cycle",
        provenance="Pycellin",
        prop_type="node",
        lineage_type="cycle",
        dtype="float",
    )


class Straightness(NodeGlobalPropCalculator[CycleLineage]):
    """
    Calculator to compute the straightness of the cell displacement within a cell cycle.

    The straightness is defined as the ratio of the Euclidean distance between
    the start and end cells of the cell cycle to the total distance traveled.
    Straightness is a value between 0 and 1. A straight line has a straightness of 1,
    while a trajectory with many turns has a straightness close to 0.

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    include_incoming_edge : bool, default=False
        Whether to start the trajectory at the parent of the first cell, i.e. to
        include the link from this parent to the first cell.
    coord_props : tuple[str, ...], default=("cell_x", "cell_y", "cell_z")
        Identifiers of the cell lineage node properties holding the coordinates
        of the cells, one per axis. The default is for 3D data.
    """

    def __init__(
        self,
        property: Property,
        include_incoming_edge: bool = False,
        coord_props: tuple[str, ...] = ("cell_x", "cell_y", "cell_z"),
    ):
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge
        self.coord_props = coord_props

    def compute(self, data: Data, lineage: CycleLineage, node_id: int) -> float:
        """
        Compute the straightness of the cell displacement within a cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        node_id : int
            Node ID (``cycle_id``) of the cell cycle of interest.

        Returns
        -------
        float
            Straightness of the displacement.
            Returns NaN if the total distance traveled is null.

        Raises
        ------
        MissingPropertyError
            If a cell of the cell cycle has no value for one of the coordinates.
        FusionError
            If `include_incoming_edge` is True and the first cell of the cell cycle has
            more than one parent.
        """
        lin_id = lineage.graph["lineage_id"]
        cell_lin = data.cell_lineages[lin_id]
        cells = lineage.nodes[node_id]["cells"]
        prop_id = self.property.identifier
        distances = [
            math.dist(
                _get_position(cell_lin, n1, self.coord_props, prop_id),
                _get_position(cell_lin, n2, self.coord_props, prop_id),
            )
            for (n1, n2) in pairwise(cells)
        ]

        # The trajectory starts at the first cell, or at its parent when the link
        # from the parent is included.
        start_cell = cells[0]
        if self.include_incoming_edge:
            first_cell = cells[0]
            preds = list(cell_lin.predecessors(first_cell))
            if len(preds) == 1:
                dist = math.dist(
                    _get_position(cell_lin, preds[0], self.coord_props, prop_id),
                    _get_position(cell_lin, first_cell, self.coord_props, prop_id),
                )
                distances.append(dist)
                start_cell = preds[0]
            elif len(preds) > 1:
                raise FusionError(first_cell, lin_id)

        if sum(distances) == 0:
            return math.nan

        start_loc = _get_position(cell_lin, start_cell, self.coord_props, prop_id)
        end_loc = _get_position(cell_lin, cells[-1], self.coord_props, prop_id)
        return math.dist(start_loc, end_loc) / sum(distances)


def create_turning_angle_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: Literal["radian", "degree"] = "radian",
) -> Property:
    """
    Create the declaration of the ``turning_angle`` property.

    ``turning_angle`` is the angle of the cell trajectory between two consecutive
    displacements. It is a node property of cell lineages.

    Parameters
    ----------
    custom_identifier : str | None, default=None
        New identifier for the property. If None, the identifier will be
        ``"turning_angle"``.
    custom_name : str | None, default=None
        New name for the property. If None, the name will be "Turning angle".
    custom_description : str | None, default=None
        New description for the property. If None, the description will be "Angle of the
        cell trajectory between two consecutive displacements".
    unit : Literal["radian", "degree"], default="radian"
        Unit of the turning angle.

    Returns
    -------
    Property
        Declaration of the ``turning_angle`` property.
    """
    return Property(
        identifier=custom_identifier or "turning_angle",
        name=custom_name or "Turning angle",
        description=custom_description
        or "Angle of the cell trajectory between two consecutive displacements",
        provenance="Pycellin",
        prop_type="node",
        lineage_type="cell",
        dtype="float",
        unit=unit,
    )


class TurningAngle(NodeLocalPropCalculator[CellLineage]):
    """
    Calculator to compute the angle between two consecutive displacement vectors.

    The angle requires three consecutive detections of the cell. It is computed
    at a given cell detection as the angle between:

    - the displacement vector from its predecessor to itself
    - the displacement vector from itself to its successor

    Parameters
    ----------
    property : Property
        Property object to which the calculator is associated.
    unit : Literal["radian", "degree"], default="radian"
        Unit in which the angle is computed.
    coord_props : tuple[str, ...], default=("cell_x", "cell_y", "cell_z")
        Identifiers of the cell lineage node properties holding the coordinates
        of the cells, one per axis. The default is for 3D data.

    Raises
    ------
    ValueError
        If `unit` is not ``"radian"`` or ``"degree"``.
    """

    def __init__(
        self,
        property: Property,
        unit: Literal["radian", "degree"] = "radian",
        coord_props: tuple[str, ...] = ("cell_x", "cell_y", "cell_z"),
    ):
        super().__init__(property)
        if unit not in ("radian", "degree"):
            raise ValueError(
                f"Unknown unit: {unit}. Valid units are 'radian' and 'degree'."
            )
        self.unit = unit
        self.coord_props = coord_props

    def compute(self, lineage: CellLineage, node_id: int) -> float:
        """
        Compute the angle between two consecutive displacement vectors at a cell.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        node_id : int
            Node ID (``cell_id``) of the cell of interest.

        Returns
        -------
        float
            Angle between the two consecutive displacement vectors.
            Returns NaN if the angle is not defined (first or last node in lineage,
            or dividing cell).

        Raises
        ------
        MissingPropertyError
            If the cell, its predecessor or its successor has no value for one of
            the coordinates.
        FusionError
            If the cell has one successor and more than one predecessor.
        ValueError
            If the unit of the calculator is not ``"radian"`` or ``"degree"``.
        """
        # Find the incoming and outgoing edges of the node of interest.
        predecessors = list(lineage.predecessors(node_id))
        successors = list(lineage.successors(node_id))
        if len(predecessors) == 0 or len(successors) != 1:
            # The angle is not defined for:
            # - the first node of the lineage (no incoming edge)
            # - the last node of the lineage (no outgoing edge)
            # - a dividing node (more than one outgoing edges).
            return math.nan
        elif len(predecessors) > 1:
            raise FusionError(node_id, lineage.graph["lineage_id"])

        # Compute the angle between the incoming and outgoing edges.
        prop_id = self.property.identifier
        in_coords = np.array(
            _get_position(lineage, predecessors[0], self.coord_props, prop_id)
        )
        nid_coords = np.array(
            _get_position(lineage, node_id, self.coord_props, prop_id)
        )
        out_coords = np.array(
            _get_position(lineage, successors[0], self.coord_props, prop_id)
        )
        vector_in = nid_coords - in_coords
        vector_out = out_coords - nid_coords
        # np.cross() needs 3D vectors: 2D ones get a null z.
        vector_in = np.pad(vector_in, (0, 3 - vector_in.size))
        vector_out = np.pad(vector_out, (0, 3 - vector_out.size))
        cross_prod = np.cross(vector_in, vector_out)
        dot_prod = np.dot(vector_in, vector_out)
        angle = math.atan2(np.linalg.norm(cross_prod), dot_prod)
        if self.unit == "radian":
            return angle
        elif self.unit == "degree":
            return math.degrees(angle)
        else:
            raise ValueError(
                f"Unknown unit: {self.unit}. Valid units are 'radian' and 'degree'."
            )
