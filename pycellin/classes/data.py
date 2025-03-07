#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from typing import Literal
import warnings

import networkx as nx

from pycellin.classes.lineage import Lineage, CellLineage, CycleLineage


class Data:
    """
    Class to store and manipulate cell lineages and cell cycle lineages.
    """

    def __init__(
        self, data: dict[str, CellLineage], add_cycle_data: bool = False
    ) -> None:
        self.cell_data = data
        if add_cycle_data:
            self._compute_cycle_lineages()
        else:
            self.cycle_data = None

    def __repr__(self) -> str:
        return f"Data(cell_data={self.cell_data!r}, cycle_data={self.cycle_data!r})"

    def __str__(self) -> str:
        if self.cycle_data:
            txt = f" and {self.number_of_lineages()} cycle lineages"
        else:
            txt = ""
        return f"Data object with {self.number_of_lineages()} cell lineages{txt}."

    def _add_cycle_lineages(self, lineage_IDs: list[int] | None = None) -> None:
        """
        Add the cell cycle lineages from the cell lineages.

        Parameters
        ----------
        lineage_IDs : list[int], optional
            The IDs of the lineages to compute the cycle lineages for,
            by default None i.e. all lineages.
        """
        if lineage_IDs is None:
            lineage_IDs = list(self.cell_data.keys())
        self.cycle_data = {
            lin_id: self._compute_cycle_lineage(lin_id) for lin_id in lineage_IDs
        }

    def _compute_cycle_lineage(self, lineage_ID: int) -> CycleLineage:
        """
        Compute and return the cycle lineage corresponding to a given cell lineage.

        Parameters
        ----------
        lineage_ID : int
            The ID of the cell lineage.

        Returns
        -------
        CycleLineage
            The cycle lineage corresponding to the cell lineage.
        """
        return CycleLineage(self.cell_data[lineage_ID])

    def _freeze_lineage_data(self):
        """
        Freeze all cell lineages.

        When a cell lineage is frozen, its structure cannot be modified:
        nodes and edges cannot be added or removed. However, graph, node and edge
        attributes can still be modified.
        """
        for lineage in self.cell_data.values():
            if not nx.is_frozen(lineage):
                nx.freeze(lineage)

    def _unfreeze_lineage_data(self):
        """
        Unfreeze all cell lineages.
        """
        for lineage in self.cell_data.values():
            Lineage.unfreeze(lineage)

    def number_of_lineages(self) -> int:
        """
        Return the number of lineages in the data.

        Returns
        -------
        int
            The number of cell lineages in the data.

        Raises
        ------
        Warning
            If the number of cell lineages and cycle lineages do not match.
        """
        if self.cycle_data:
            if len(self.cell_data) != len(self.cycle_data):
                msg = (
                    f"Number of cell lineages ({len(self.cell_data)}) "
                    f"and cycle lineages ({len(self.cycle_data)}) do not match. "
                    "An update of the model is required. "
                )
                warnings.warn(msg)
        return len(self.cell_data)

    def get_closest_cell(
        self,
        noi: int,
        lineage: CellLineage,
        radius: float = 0,
        time_window: int = 0,
        time_window_type: Literal["before", "after", "symetric"] = "symetric",
        lineages_to_search: list[CellLineage] = None,
        reference: Literal["center", "border"] = "center",
    ) -> tuple[CellLineage, int]:
        """
        Find the closest cell to a given cell of a lineage.

        Parameters
        ----------
        noi : int
            Node of interest, the one for which to find the closest cell.
        lineage : CellLineage
            The lineage the node belongs to.
        radius : float, optional
            The maximum distance to consider, by default 0.
            If 0, the whole space is considered.
        time_window : int, optional
            The time window to consider, by default 0 i.e. only the current frame.
        time_window_type : Literal["before", "after", "symetric"], optional
            The type of time window to consider, by default "symetric".
        lineages_to_search : list[CellLineage], optional
            The lineages to search in, by default None i.e. all lineages.
        reference : Literal["center", "border"], optional
            The reference point to consider for the distance, by default "center".

        Returns
        -------
        tuple[int, CellLineage]
            The node ID of the closest cell and the lineage it belongs to.
        """
        distances = self.get_closest_cells(
            noi=noi,
            lineage=lineage,
            radius=radius,
            time_window=time_window,
            time_window_type=time_window_type,
            lineages_to_search=lineages_to_search,
            reference=reference,
        )
        return distances[0]

    def get_closest_cells(
        self,
        noi: int,
        lineage: CellLineage,
        radius: float = 0,
        time_window: int = 0,
        time_window_type: Literal["before", "after", "symetric"] = "symetric",
        lineages_to_search: list[CellLineage] = None,
        reference: Literal["center", "border"] = "center",
    ) -> list[tuple[int, CellLineage]]:
        """
        Find the closest cells to a given cell of a lineage.

        Parameters
        ----------
        noi : int
            Node of interest, the one for which to find the closest cell.
        lineage : CellLineage
            The lineage the node belongs to.
        radius : float, optional
            The maximum distance to consider, by default 0.
            If 0, the whole space is considered.
        time_window : int, optional
            The time window to consider, by default 0 i.e. only the current frame.
        time_window_type : Literal["before", "after", "symetric"], optional
            The type of time window to consider, by default "symetric".
        lineages_to_search : list[CellLineage], optional
            The lineages to search in, by default None i.e. all lineages.
        reference : Literal["center", "border"], optional
            The reference point to consider for the distance, by default "center".

        Returns
        -------
        tuple[int, CellLineage]
            The node ID of the closest cells and the lineages it belongs to,
            sorted by increasing distance.
        """
        # TODO: implement the reference parameter

        # Identification of the frames to search in.
        center_frame = lineage.nodes[noi]["frame"]
        if time_window == 0:
            frames_to_search = [center_frame]
        else:
            if time_window_type == "symetric":
                frames_to_search = list(
                    range(center_frame - time_window, center_frame + time_window + 1)
                )
            elif time_window_type == "before":
                frames_to_search = list(
                    range(center_frame - time_window, center_frame + 1)
                )
            elif time_window_type == "after":
                frames_to_search = list(
                    range(center_frame, center_frame + time_window + 1)
                )
            else:
                raise ValueError(
                    f"Unknown time window type: '{time_window_type}'."
                    " Should be 'before', 'after' or 'symetric'."
                )
            frames_to_search.sort()

        # Identification of nodes that are good candidates,
        # i.e. nodes that are in the time window
        # and in the lineages to search in.
        if not lineages_to_search:
            lineages_to_search = list(self.cell_data.values())
        candidate_cells = {}
        for lin in lineages_to_search:
            nodes = [
                node
                for node, frame in lin.nodes(data="frame")
                if frame in frames_to_search
            ]
            if nodes:
                candidate_cells[lin] = nodes
        # Need to remove the node itself from the candidates.
        candidate_cells[lineage].remove(noi)

        # Identification of the closest cell.
        distances = []
        for lin, nodes in candidate_cells.items():
            for node in nodes:
                distance = math.dist(
                    lineage.nodes[noi]["location"], lin.nodes[node]["location"]
                )
                if radius == 0 or distance <= radius:
                    distances.append((node, lin, distance))
        distances.sort(key=lambda x: x[2])
        return [(node, lin) for node, lin, _ in distances]

    # def get_neighbouring_cells(
    #     lineage: CellLineage,
    #     node: int,
    #     radius: float,
    #     time_window: int | tuple[int, int],
    # ) -> list[tuple[CellLineage, int]]:
    #     """ """
    #     # TODO: implement get_neighbouring_cells()
    #     # Parameter to define sort order? By default closest to farthest
    #     # Need to implement get_distance() between 2 nodes, not necessarily
    #     # from the same lineage...
    #     # To identify a node, need to have lineage_ID and cell_ID
    #     pass
