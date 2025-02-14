#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A collection of features related to cell mobility/motility.
"""

from itertools import pairwise
import math
import numpy as np
from typing import Literal

from pycellin.classes import Data, CellLineage, CycleLineage, Feature
from pycellin.classes.exceptions import FusionError
from pycellin.classes.feature_calculator import (
    EdgeLocalFeatureCalculator,
    NodeGlobalFeatureCalculator,
)


class CellDisplacement(EdgeLocalFeatureCalculator):
    """
    Calculator to compute the displacement of a cell between two consecutive detections.

    The displacement is defined as the Euclidean distance between the positions
    of the cell at the two consecutive detections.
    """

    def compute(self, lineage: CellLineage, edge: tuple[int, int]) -> float:
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
        pos1 = lineage.nodes[edge[0]]["location"]
        pos2 = lineage.nodes[edge[1]]["location"]
        return math.dist(pos1, pos2)


class BranchTotalDisplacement(NodeGlobalFeatureCalculator):

    def __init__(self, feature: Feature, include_incoming_edge: bool = False):
        super().__init__(feature)
        self.include_incoming_edge = include_incoming_edge

    def compute(self, data: Data, lineage: CycleLineage, noi: int) -> float:
        lin_ID = lineage.graph["cycle_lineage_ID"]
        cell_lin = data.cell_data[lin_ID]
        disps = [
            cell_lin.edges[edge]["cell_displacement"]
            for edge in lineage.yield_edges_within_cycle(noi)
        ]

        if self.include_incoming_edge:
            first_cell = lineage.nodes[noi]["cells"][0]
            predecessors = list(cell_lin.predecessors(first_cell))
            if len(predecessors) == 1:
                edge = (predecessors[0], first_cell)
                disps.append(cell_lin.edges[edge]["cell_displacement"])
            elif len(predecessors) > 1:
                raise FusionError(first_cell, lin_ID)
        return sum(disps)


class CellSpeed(EdgeLocalFeatureCalculator):
    """
    Calculator to compute the speed of a cell between two consecutive detections.

    The speed is defined as the displacement of the cell divided by the time interval
    between the two consecutive detections.
    """

    def __init__(self, feature: Feature, time_step: int | float = 1):
        """
        Parameters
        ----------
        feature : Feature
            Feature object to which the calculator is associated.
        time_step : int or float, optional
            Time step between 2 frames, in time unit. Default is 1.
        """
        super().__init__(feature)
        self.time_step = time_step

    def compute(self, lineage: CellLineage, edge: tuple[int, int]) -> float:
        time1 = lineage.nodes[edge[0]]["frame"] * self.time_step
        time2 = lineage.nodes[edge[1]]["frame"] * self.time_step
        if "cell_displacement" in lineage.edges[edge]:
            return lineage.edges[edge]["cell_displacement"] / (time2 - time1)
        else:
            pos1 = lineage.nodes[edge[0]]["location"]
            pos2 = lineage.nodes[edge[1]]["location"]
            return math.dist(pos1, pos2) / (time2 - time1)


class BranchSpeed(NodeGlobalFeatureCalculator):

    def __init__(self, feature: Feature, include_incoming_edge: bool = False):
        super().__init__(feature)
        self.include_incoming_edge = include_incoming_edge

    def compute(self, data: Data, lineage: CycleLineage, noi: int) -> float:
        lin_ID = lineage.graph["cycle_lineage_ID"]
        cell_lin = data.cell_data[lin_ID]
        speeds = [
            cell_lin.edges[edge]["cell_speed"]
            for edge in lineage.yield_edges_within_cycle(noi)
        ]
        if self.include_incoming_edge:
            first_cell = lineage.nodes[noi]["cells"][0]
            predecessors = list(cell_lin.predecessors(first_cell))
            if len(predecessors) == 1:
                edge = (predecessors[0], first_cell)
                speeds.append(cell_lin.edges[edge]["cell_speed"])
            elif len(predecessors) > 1:
                raise FusionError(first_cell, lin_ID)
        return np.mean(speeds)


class Straightness(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the straightness of the cell displacement within a cell cycle.

    The straightness is defined as the ratio of the Euclidean distance between
    the start and end cells of the cell cycle to the total distance traveled.
    Straightness is a value between 0 and 1. A straight line has a straightness of 1,
    while a trajectory with many turns has a straightness close to 0.
    """

    def __init__(self, feature: Feature, include_incoming_edge: bool = False):
        """
        Parameters
        ----------
        feature : Feature
            Feature object to which the calculator is associated.
        include_incoming_edge : bool, optional
            Whether to include the distance between the first cell and its predecessor.
            Default is False.
        """
        super().__init__(feature)
        self.include_incoming_edge = include_incoming_edge

    def compute(self, data: Data, cycle_lin: CycleLineage, noi: int) -> float:
        """
        Compute the straightness of the cell displacement within a cell cycle.

        Parameters
        ----------
        data : Data
            Data object containing the lineage.
        lineage : CycleLineage
            Lineage graph containing the node of interest.
        node : int
            Node ID (cycle_ID) of the cell of interest.

        Returns
        -------
        float
            Straightness of the displacement.
        """
        lin_ID = cycle_lin.graph["cycle_lineage_ID"]
        cell_lin = data.cell_data[lin_ID]
        cells = cycle_lin.nodes[noi]["cells"]
        distances = [
            math.dist(cell_lin.nodes[n1]["location"], cell_lin.nodes[n2]["location"])
            for (n1, n2) in pairwise(cells)
        ]
        if self.include_incoming_edge:
            first_cell = cells[0]
            predecessors = list(cell_lin.predecessors(first_cell))
            if len(predecessors) == 1:
                dist = math.dist(
                    cell_lin.nodes[predecessors[0]]["location"],
                    cell_lin.nodes[first_cell]["location"],
                )
                distances.append(dist)
            elif len(predecessors) > 1:
                raise FusionError(first_cell, lin_ID)
        first_cell_loc = cell_lin.nodes[cells[0]]["location"]
        last_cell_loc = cell_lin.nodes[cells[-1]]["location"]
        return math.dist(first_cell_loc, last_cell_loc) / sum(distances)


class Angle(NodeGlobalFeatureCalculator):
    """
    Calculator to compute the angle between two consecutive detections of a cell.

    The angle is defined as the angle between the vectors representing the displacement
    of the cell at two consecutive detections.
    """

    def __init__(self, feature: Feature, unit: Literal["radian", "degree"] = "radian"):
        """
        Parameters
        ----------
        feature : Feature
            Feature object to which the calculator is associated.
        unit : {'radian', 'degree'}, optional
            Unit in which the angle is computed. Default is 'radian'.
        """
        super().__init__(feature)
        self.unit = unit

    def compute(self, data: Data, lineage: CellLineage, noi: int) -> float:
        """
        Compute the angle between two consecutive detections of a cell.

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
            Angle between the two consecutive displacements.
        """

        # Find the incoming and outgoing edges of the node of interest.
        predecessors = list(lineage.predecessors(noi))
        successors = list(lineage.successors(noi))
        if len(predecessors) == 0 or len(successors) != 1:
            # The angle is not defined for:
            # - the first node of the lineage (no incoming edge)
            # - the last node of the lineage (no outgoing edge)
            # - a dividing node (more than one outgoing edges).
            return math.nan
        elif len(predecessors) > 1:
            raise FusionError(noi, lineage.graph["lineage_ID"])

        # Compute the angle between the incoming and outgoing edges.
        in_coords = lineage.nodes[predecessors[0]]["location"]
        noi_coords = lineage.nodes[noi]["location"]
        out_coords = lineage.nodes[successors[0]]["location"]
        vector_in = np.array(noi_coords) - np.array(in_coords)
        vector_out = np.array(out_coords) - np.array(noi_coords)
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
