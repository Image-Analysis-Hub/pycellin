#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A collection of properties related to cell mobility/motility.
"""

from itertools import pairwise
import math
import numpy as np
from typing import Any, Literal

from pycellin.classes import Data, CellLineage, CycleLineage, Property
from pycellin.classes.exceptions import FusionError
from pycellin.classes.property_calculator import (
    EdgeLocalPropCalculator,
    NodeGlobalPropCalculator,
)


def _get_branch_edge_property_values(
    prop_name: str,
    data: Data,
    lineage: CycleLineage,
    nid: int,
    include_incoming_edge: bool,
) -> list[Any]:
    """
    Get the values of a given property for all edges within a cell cycle.

    Parameters
    ----------
    prop_name : str
        Name of the property to retrieve.
    data : Data
        Data object containing the lineage.
    lineage : CycleLineage
        Lineage graph containing the node of interest.
    nid : int
        Node ID (cycle_ID) of the cell of interest.
    include_incoming_edge : bool
        Whether to include the incoming edge of the first cell of the cell cycle.

    Returns
    -------
    list of Any
        List of values of the property for all edges within the cell cycle.

    Raises
    ------
    KeyError
        If the property does not exist in the cell lineage.
    """
    lin_ID = lineage.graph["lineage_ID"]
    cell_lin = data.cell_data[lin_ID]
    try:
        values = [cell_lin.edges[edge][prop_name] for edge in lineage.yield_links_within_cycle(nid)]
    except KeyError:
        raise KeyError(f"Property '{prop_name}' does not exist in the cell lineage '{lin_ID}'.")

    if include_incoming_edge:
        first_cell = lineage.nodes[nid]["cells"][0]
        predecessors = list(cell_lin.predecessors(first_cell))
        if len(predecessors) == 1:
            edge = (predecessors[0], first_cell)
            values.append(cell_lin.edges[edge][prop_name])
        elif len(predecessors) > 1:
            raise FusionError(first_cell, lin_ID)

    return values


class CellDisplacement(EdgeLocalPropCalculator):
    """
    Calculator to compute the displacement of a cell between two consecutive detections.

    The displacement is defined as the Euclidean distance between the positions
    of the cell at the two consecutive detections.
    """

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
            A tuple of cell_ID that defines the edge of interest.

        Returns
        -------
        float
            The cell displacement.
        """
        pos1 = []
        pos2 = []
        for axis in ["x", "y", "z"]:
            pos1.append(lineage.nodes[edge[0]][f"cell_{axis}"])
            pos2.append(lineage.nodes[edge[1]][f"cell_{axis}"])
            # pos1 = lineage.nodes[edge[0]][f"link_{axis}"]
            # pos2 = lineage.nodes[edge[1]][f"link_{axis}"]
        #     if i == 0:
        #         displacement = (pos1 - pos2) ** 2
        #     else:
        #         displacement += (pos1 - pos2) ** 2
        # pos1 = lineage.nodes[edge[0]]["cell_location"]
        # pos2 = lineage.nodes[edge[1]]["cell_location"]
        return math.dist(pos1, pos2)


class BranchTotalDisplacement(NodeGlobalPropCalculator):
    """
    Calculator to compute the total displacement of a cell during a cell cycle.

    The branch total displacement is defined as the displacement of the cell during
    the cell cycle.
    """

    def __init__(self, property: Property, include_incoming_edge: bool = False):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        include_incoming_edge : bool, optional
            Whether to include the incoming edge of the first cell of the cell cycle.
            Default is False.
        """
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge

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
            Node ID (cycle_ID) of the cell cycle of interest.

        Returns
        -------
        float
            Total displacement of the cell during the cell cycle.
        """
        disps = _get_branch_edge_property_values(
            "cell_displacement", data, lineage, nid, self.include_incoming_edge
        )
        return np.nansum(disps)


class BranchMeanDisplacement(NodeGlobalPropCalculator):
    """
    Calculator to compute the mean displacement of a cell during a cell cycle.

    The branch mean displacement is defined as the mean displacement of the cell during
    the cell cycle.
    """

    def __init__(self, property: Property, include_incoming_edge: bool = False):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        include_incoming_edge : bool, optional
            Whether to include the incoming edge of the first cell of the cell cycle.
            Default is False.
        """
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge

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
            Node ID (cycle_ID) of the cell cycle of interest.

        Returns
        -------
        float
            Mean displacement of the cell during the cell cycle.
        """
        disps = _get_branch_edge_property_values(
            "cell_displacement", data, lineage, nid, self.include_incoming_edge
        )
        return np.nanmean(disps).item()


class CellSpeed(EdgeLocalPropCalculator):
    """
    Calculator to compute the speed of a cell between two consecutive detections.

    The speed is defined as the displacement of the cell divided by the time interval
    between the two consecutive detections.
    """

    def __init__(self, property: Property, time_step: int | float = 1):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        time_step : int or float, optional
            Time step between 2 frames, in time unit. Default is 1.
        """
        super().__init__(property)
        self.time_step = time_step

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
            A tuple of cell_ID that defines the edge of interest.

        Returns
        -------
        float
            Cell speed between two consecutive detections.
        """
        time1 = lineage.nodes[edge[0]]["frame"] * self.time_step
        time2 = lineage.nodes[edge[1]]["frame"] * self.time_step
        if "cell_displacement" in lineage.edges[edge]:
            return lineage.edges[edge]["cell_displacement"] / (time2 - time1)
        else:
            pos1 = []
            pos2 = []
            for axis in ["x", "y", "z"]:
                pos1.append(lineage.nodes[edge[0]][f"cell_{axis}"])
                pos2.append(lineage.nodes[edge[1]][f"cell_{axis}"])
            # pos1 = lineage.nodes[edge[0]]["location"]
            # pos2 = lineage.nodes[edge[1]]["location"]
            return math.dist(pos1, pos2) / (time2 - time1)


class BranchMeanSpeed(NodeGlobalPropCalculator):
    """
    Calculator to compute the mean speed of a cell during a cell cycle.

    The branch mean speed is defined as the mean speed of the cell
    during the cell cycle.
    """

    def __init__(self, property: Property, include_incoming_edge: bool = False):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        include_incoming_edge : bool, optional
            Whether to include the incoming edge of the first cell of the cell cycle.
            Default is False.
        """
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge

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
            Node ID (cycle_ID) of the cell cycle of interest.

        Returns
        -------
        float
            Mean speed of the cell during the cell cycle.
        """
        speeds = _get_branch_edge_property_values(
            "cell_speed", data, lineage, nid, self.include_incoming_edge
        )
        return np.nanmean(speeds).item()


class Straightness(NodeGlobalPropCalculator):
    """
    Calculator to compute the straightness of the cell displacement within a cell cycle.

    The straightness is defined as the ratio of the Euclidean distance between
    the start and end cells of the cell cycle to the total distance traveled.
    Straightness is a value between 0 and 1. A straight line has a straightness of 1,
    while a trajectory with many turns has a straightness close to 0.
    """

    def __init__(self, property: Property, include_incoming_edge: bool = False):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        include_incoming_edge : bool, optional
            Whether to include the distance between the first cell and its predecessor.
            Default is False.
        """
        super().__init__(property)
        self.include_incoming_edge = include_incoming_edge

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
            Node ID (cycle_ID) of the cell cycle of interest.

        Returns
        -------
        float
            Straightness of the displacement.
        """
        lin_ID = cycle_lin.graph["lineage_ID"]
        cell_lin = data.cell_data[lin_ID]
        cells = cycle_lin.nodes[nid]["cells"]
        distances = [
            math.dist(
                (
                    cell_lin.nodes[n1]["cell_x"],
                    cell_lin.nodes[n1]["cell_y"],
                    cell_lin.nodes[n1]["cell_z"],
                ),
                (
                    cell_lin.nodes[n2]["cell_x"],
                    cell_lin.nodes[n2]["cell_y"],
                    cell_lin.nodes[n2]["cell_z"],
                ),
            )
            for (n1, n2) in pairwise(cells)
        ]
        if self.include_incoming_edge:
            first_cell = cells[0]
            preds = list(cell_lin.predecessors(first_cell))
            if len(preds) == 1:
                dist = math.dist(
                    (
                        cell_lin.nodes[preds[0]]["cell_x"],
                        cell_lin.nodes[preds[0]]["cell_y"],
                        cell_lin.nodes[preds[0]]["cell_z"],
                    ),
                    (
                        cell_lin.nodes[first_cell]["cell_x"],
                        cell_lin.nodes[first_cell]["cell_y"],
                        cell_lin.nodes[first_cell]["cell_z"],
                    ),
                )
                distances.append(dist)
            elif len(preds) > 1:
                raise FusionError(first_cell, lin_ID)
        first_cell_loc = (
            cell_lin.nodes[cells[0]]["cell_x"],
            cell_lin.nodes[cells[0]]["cell_y"],
            cell_lin.nodes[cells[0]]["cell_z"],
        )
        last_cell_loc = (
            cell_lin.nodes[cells[-1]]["cell_x"],
            cell_lin.nodes[cells[-1]]["cell_y"],
            cell_lin.nodes[cells[-1]]["cell_z"],
        )
        return math.dist(first_cell_loc, last_cell_loc) / sum(distances)


class Angle(NodeGlobalPropCalculator):
    """
    Calculator to compute the angle between two consecutive detections of a cell.

    The angle is defined as the angle between the vectors representing the displacement
    of the cell at two consecutive detections.
    """

    def __init__(self, property: Property, unit: Literal["radian", "degree"] = "radian"):
        """
        Parameters
        ----------
        property : Property
            Property object to which the calculator is associated.
        unit : {'radian', 'degree'}, optional
            Unit in which the angle is computed. Default is 'radian'.
        """
        super().__init__(property)
        self.unit = unit

    def compute(  # type: ignore[override]
        self, data: Data, lineage: CellLineage, nid: int
    ) -> float:
        """
        Compute the angle between two consecutive detections of a cell.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CellLineage
            Lineage graph containing the node of interest.
        nid : int
            Node ID (cell_ID) of the cell of interest.

        Returns
        -------
        float
            Angle between the two consecutive displacements.
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
            raise FusionError(nid, lineage.graph["lineage_ID"])

        # Compute the angle between the incoming and outgoing edges.
        in_coords = (
            lineage.nodes[predecessors[0]]["cell_x"],
            lineage.nodes[predecessors[0]]["cell_y"],
            lineage.nodes[predecessors[0]]["cell_z"],
        )
        nid_coords = (
            lineage.nodes[nid]["cell_x"],
            lineage.nodes[nid]["cell_y"],
            lineage.nodes[nid]["cell_z"],
        )
        out_coords = (
            lineage.nodes[successors[0]]["cell_x"],
            lineage.nodes[successors[0]]["cell_y"],
            lineage.nodes[successors[0]]["cell_z"],
        )
        vector_in = np.array(nid_coords) - np.array(in_coords)
        vector_out = np.array(out_coords) - np.array(nid_coords)
        cross_prod = np.cross(vector_in, vector_out)
        dot_prod = np.dot(vector_in, vector_out)
        angle = math.atan2(np.linalg.norm(cross_prod), dot_prod)
        if self.unit == "radian":
            return angle
        elif self.unit == "degree":
            return math.degrees(angle)
        else:
            raise ValueError(f"Unknown unit: {self.unit}. Valid units are 'radian' and 'degree'.")
