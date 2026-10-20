#!/usr/bin/env python3

"""
A collection of properties related to cell mobility/motility.
"""

import math
from itertools import pairwise
from typing import ClassVar, Literal

import numpy as np

from pycellin.classes.data import Data
from pycellin.classes.exceptions import FusionError
from pycellin.classes.lineage import CellLineage, CycleLineage
from pycellin.classes.property import Property
from pycellin.classes.property_calculator import (
    EdgeLocalPropCalculator,
    NodeGlobalPropCalculator,
    NodeLocalPropCalculator,
)
from pycellin.properties.utils import (
    _get_cycle_edge_property_values,
    _nanmean,
    _nansum,
)

# Cell coordinates of 3D data. 2D data has no "cell_z".
_CELL_COORD_PROPS = ("cell_x", "cell_y", "cell_z")


def _get_position(
    lineage: CellLineage, cell_id: int, coord_props: tuple[str, ...]
) -> list[float]:
    """
    Return the position of a cell.

    Parameters
    ----------
    lineage : CellLineage
        Lineage graph containing the cell.
    cell_id : int
        ID of the cell.
    coord_props : tuple[str, ...]
        Identifiers of the node properties holding the coordinates of the cells,
        one per axis.

    Returns
    -------
    list[float]
        The coordinates of the cell, in the order of `coord_props`.
    """
    return [lineage.nodes[cell_id][prop] for prop in coord_props]


def create_cell_displacement_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cell_displacement",
        name=custom_name or "Cell displacement",
        description=custom_description
        or "Displacement of the cell between two consecutive detections",
        provenance="pycellin",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


class CellDisplacement(EdgeLocalPropCalculator):
    """
    Calculator to compute the displacement of a cell between two consecutive detections.

    The displacement is defined as the Euclidean distance between the positions
    of the cell at the two consecutive detections.
    """

    def __init__(
        self, property: Property, coord_props: tuple[str, ...] = _CELL_COORD_PROPS
    ):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        coord_props : tuple[str, ...], optional
            Identifiers of the cell lineage node properties holding the coordinates
            of the cells, one per axis. Default is ("cell_x", "cell_y", "cell_z"),
            for 3D data.
        """
        super().__init__(property)
        self.coord_props = coord_props

    def compute(  # type: ignore[override]
        self, lineage: CellLineage, edge: tuple[int, int]
    ) -> float:
        """
        Compute the displacement of a cell between two consecutive detections.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        edge : tuple of int
            A tuple of cell_id that defines the edge of interest.

        Returns
        -------
        float
            The cell displacement.
        """
        pos1 = _get_position(lineage, edge[0], self.coord_props)
        pos2 = _get_position(lineage, edge[1], self.coord_props)
        return math.dist(pos1, pos2)


def create_cycle_total_displacement_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cycle_total_displacement",
        name=custom_name or "Cycle total displacement",
        description=custom_description
        or "Displacement of the cell during the cell cycle",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=unit,
    )


class CycleTotalDisplacement(NodeGlobalPropCalculator):
    """
    Calculator to compute the total displacement of a cell during a cell cycle.

    The cycle total displacement is defined as the displacement of the cell during
    the cell cycle. NaN values are ignored. It is NaN when the cell cycle has
    no link with a displacement value, e.g. a cell cycle of a single cell.
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "displacement_prop": ("edge", "CellLineage")
    }

    def __init__(
        self,
        property: Property,
        include_incoming_edge: bool = False,
        displacement_prop: str = "cell_displacement",
    ):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        include_incoming_edge : bool, optional
            Whether to include the incoming edge of the first cell of the cell cycle.
            Default is False.
        displacement_prop : str, optional
            Identifier of the cell lineage edge property holding the
            cell displacements.
            Default is "cell_displacement".
        """
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge
        self.displacement_prop = displacement_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CycleLineage, nid: int
    ) -> float:
        """
        Compute the total displacement of a cell during the cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cycle_id) of the cell cycle of interest.

        Returns
        -------
        float
            Total displacement of the cell during the cell cycle, or NaN if
            the cell cycle has no link with a displacement value.
        """
        disps = _get_cycle_edge_property_values(
            self.displacement_prop, data, lineage, nid, self.include_incoming_edge
        )
        return _nansum(disps)


def create_cycle_mean_displacement_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cycle_mean_displacement",
        name=custom_name or "Cycle mean displacement",
        description=custom_description
        or "Mean displacement of the cell during the cell cycle",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=unit,
    )


class CycleMeanDisplacement(NodeGlobalPropCalculator):
    """
    Calculator to compute the mean displacement of a cell during a cell cycle.

    The cycle mean displacement is defined as the mean displacement of the cell during
    the cell cycle. NaN values are ignored. It is NaN when the cell cycle has
    no link with a displacement value, e.g. a cell cycle of a single cell.
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "displacement_prop": ("edge", "CellLineage")
    }

    def __init__(
        self,
        property: Property,
        include_incoming_edge: bool = False,
        displacement_prop: str = "cell_displacement",
    ):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        include_incoming_edge : bool, optional
            Whether to include the incoming edge of the first cell of the cell cycle.
            Default is False.
        displacement_prop : str, optional
            Identifier of the cell lineage edge property holding the
            cell displacements.
            Default is "cell_displacement".
        """
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge
        self.displacement_prop = displacement_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CycleLineage, nid: int
    ) -> float:
        """
        Compute the mean displacement of a cell during the cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cycle_id) of the cell cycle of interest.

        Returns
        -------
        float
            Mean displacement of the cell during the cell cycle, or NaN if
            the cell cycle has no link with a displacement value.
        """
        disps = _get_cycle_edge_property_values(
            self.displacement_prop, data, lineage, nid, self.include_incoming_edge
        )
        return _nanmean(disps)


def create_cell_speed_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cell_speed",
        name=custom_name or "Cell speed",
        description=custom_description
        or "Speed of the cell between two consecutive detections",
        provenance="pycellin",
        prop_type="edge",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


class CellSpeed(EdgeLocalPropCalculator):
    """
    Calculator to compute the speed of a cell between two consecutive detections.

    The speed is defined as the displacement of the cell divided by the time interval
    between the two consecutive detections. It is computed from the cell positions
    and the time property, not from the cell displacement property.
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "time_prop": ("node", "CellLineage")
    }

    def __init__(
        self,
        property: Property,
        time_prop: str,
        coord_props: tuple[str, ...] = _CELL_COORD_PROPS,
    ):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        time_prop : str
            Identifier of the cell lineage node property holding the time
            of the cells (e.g. "frame", "POSITION_T").
        coord_props : tuple[str, ...], optional
            Identifiers of the cell lineage node properties holding the coordinates
            of the cells, one per axis. Default is ("cell_x", "cell_y", "cell_z"),
            for 3D data.
        """
        super().__init__(property)
        self.time_prop = time_prop
        self.coord_props = coord_props

    def compute(  # type: ignore[override]
        self, lineage: CellLineage, edge: tuple[int, int]
    ) -> float:
        """
        Compute the speed of a cell between two consecutive detections.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        edge : tuple of int
            A tuple of cell_id that defines the edge of interest.

        Returns
        -------
        float
            Cell speed between two consecutive detections.
        """
        time1 = lineage.nodes[edge[0]][self.time_prop]
        time2 = lineage.nodes[edge[1]][self.time_prop]
        pos1 = _get_position(lineage, edge[0], self.coord_props)
        pos2 = _get_position(lineage, edge[1], self.coord_props)
        return math.dist(pos1, pos2) / (time2 - time1)


def create_cycle_mean_speed_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "cycle_mean_speed",
        name=custom_name or "Cycle mean speed",
        description=custom_description or "Mean speed of the cell during the cell cycle",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
        unit=unit,
    )


class CycleMeanSpeed(NodeGlobalPropCalculator):
    """
    Calculator to compute the mean speed of a cell during a cell cycle.

    The cycle mean speed is defined as the mean speed of the cell
    during the cell cycle. NaN values are ignored. It is NaN when the cell cycle
    has no link with a speed value, e.g. a cell cycle of a single cell.
    """

    INPUT_PROPS: ClassVar[dict[str, tuple[str, str]]] = {
        "speed_prop": ("edge", "CellLineage")
    }

    def __init__(
        self,
        property: Property,
        include_incoming_edge: bool = False,
        speed_prop: str = "cell_speed",
    ):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        include_incoming_edge : bool, optional
            Whether to include the incoming edge of the first cell of the cell cycle.
            Default is False.
        speed_prop : str, optional
            Identifier of the cell lineage edge property holding the
            cell speeds.
            Default is "cell_speed".
        """
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge
        self.speed_prop = speed_prop

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CycleLineage, nid: int
    ) -> float:
        """
        Compute the mean speed of a cell during the cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cycle_id) of the cell cycle of interest.

        Returns
        -------
        float
            Mean speed of the cell during the cell cycle, or NaN if the cell cycle
            has no link with a speed value.
        """
        speeds = _get_cycle_edge_property_values(
            self.speed_prop, data, lineage, nid, self.include_incoming_edge
        )
        return _nanmean(speeds)


def create_straightness_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
) -> Property:
    return Property(
        identifier=custom_identifier or "straightness",
        name=custom_name or "Straightness",
        description=custom_description
        or "Straightness of the cell trajectory during the cell cycle",
        provenance="pycellin",
        prop_type="node",
        lin_type="CycleLineage",
        dtype="float",
    )


class Straightness(NodeGlobalPropCalculator):
    """
    Calculator to compute the straightness of the cell displacement within a cell cycle.

    The straightness is defined as the ratio of the Euclidean distance between
    the start and end cells of the cell cycle to the total distance traveled.
    Straightness is a value between 0 and 1. A straight line has a straightness of 1,
    while a trajectory with many turns has a straightness close to 0.
    """

    def __init__(
        self,
        property: Property,
        include_incoming_edge: bool = False,
        coord_props: tuple[str, ...] = _CELL_COORD_PROPS,
    ):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        include_incoming_edge : bool, optional
            Whether to include the distance between the first cell and its predecessor.
            Default is False.
        coord_props : tuple[str, ...], optional
            Identifiers of the cell lineage node properties holding the coordinates
            of the cells, one per axis. Default is ("cell_x", "cell_y", "cell_z"),
            for 3D data.
        """
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge
        self.coord_props = coord_props

    def compute(  # type: ignore[override]
        self, data: Data, cycle_lin: CycleLineage, nid: int
    ) -> float:
        """
        Compute the straightness of the cell displacement within a cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        node : int
            Node ID (cycle_id) of the cell cycle of interest.

        Returns
        -------
        float
            Straightness of the displacement.
            Returns NaN if the total distance traveled is null.
        """
        lin_id = cycle_lin.graph["lineage_id"]
        cell_lin = data.cell_data[lin_id]
        cells = cycle_lin.nodes[nid]["cells"]
        distances = [
            math.dist(
                _get_position(cell_lin, n1, self.coord_props),
                _get_position(cell_lin, n2, self.coord_props),
            )
            for (n1, n2) in pairwise(cells)
        ]

        if self.include_incoming_edge:
            first_cell = cells[0]
            preds = list(cell_lin.predecessors(first_cell))
            if len(preds) == 1:
                dist = math.dist(
                    _get_position(cell_lin, preds[0], self.coord_props),
                    _get_position(cell_lin, first_cell, self.coord_props),
                )
                distances.append(dist)
            elif len(preds) > 1:
                raise FusionError(first_cell, lin_id)

        if sum(distances) == 0:
            return math.nan

        first_cell_loc = _get_position(cell_lin, cells[0], self.coord_props)
        last_cell_loc = _get_position(cell_lin, cells[-1], self.coord_props)
        return math.dist(first_cell_loc, last_cell_loc) / sum(distances)


def create_turning_angle_property(
    custom_identifier: str | None = None,
    custom_name: str | None = None,
    custom_description: str | None = None,
    unit: Literal["radian", "degree"] = "radian",
) -> Property:
    return Property(
        identifier=custom_identifier or "turning_angle",
        name=custom_name or "Turning angle",
        description=custom_description
        or "Angle of the cell trajectory between two consecutive displacements",
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )


class TurningAngle(NodeLocalPropCalculator):
    """
    Calculator to compute the angle between two consecutive displacement vectors of a cell.

    The angle requires three consecutive detections of the cell. It is computed
    at a given cell detection as the angle between:
        - the displacement vector from its predecessor to itself
        - the displacement vector from itself to its successor
    """

    def __init__(
        self,
        property: Property,
        unit: Literal["radian", "degree"] = "radian",
        coord_props: tuple[str, ...] = _CELL_COORD_PROPS,
    ):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        unit : {'radian', 'degree'}, optional
            Unit in which the angle is computed. Default is 'radian'.
        coord_props : tuple[str, ...], optional
            Identifiers of the cell lineage node properties holding the coordinates
            of the cells, one per axis. Default is ("cell_x", "cell_y", "cell_z"),
            for 3D data.
        """
        super().__init__(property)
        self.unit = unit
        self.coord_props = coord_props

    def compute(  # type: ignore[override]
        self, lineage: CellLineage, nid: int
    ) -> float:
        """
        Compute the angle between two consecutive displacement vectors at a cell detection.

        Parameters
        ----------
        lineage : CellLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cell_id) of the cell of interest.

        Returns
        -------
        float
            Angle between the two consecutive displacement vectors.
            Returns NaN if the angle is not defined (first or last node in lineage,
            or dividing cell).
        """
        # Find the incoming and outgoing edges of the node of interest.
        predecessors = list(lineage.predecessors(nid))
        successors = list(lineage.successors(nid))
        if len(predecessors) == 0 or len(successors) != 1:
            # The angle is not defined for:
            # - the first node of the lineage (no incoming edge)
            # - the last node of the lineage (no outgoing edge)
            # - a dividing node (more than one outgoing edges).
            return math.nan
        elif len(predecessors) > 1:
            raise FusionError(nid, lineage.graph["lineage_id"])

        # Compute the angle between the incoming and outgoing edges.
        in_coords = np.array(_get_position(lineage, predecessors[0], self.coord_props))
        nid_coords = np.array(_get_position(lineage, nid, self.coord_props))
        out_coords = np.array(_get_position(lineage, successors[0], self.coord_props))
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
