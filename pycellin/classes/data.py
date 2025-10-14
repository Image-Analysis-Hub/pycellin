#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import copy
import math
import warnings
from typing import Literal

import networkx as nx

from pycellin.classes.lineage import CellLineage, CycleLineage


class Data:
    """
    Class to store and manipulate cell lineages and cell cycle lineages.

    Attributes
    ----------
    cell_data : dict[int, CellLineage]
        The cell lineages stored.
    cycle_data : dict[int, CycleLineage] | None
        The cycle lineages stored, if any.
    """

    def __init__(self, cell_data: dict[int, CellLineage], add_cycle_data: bool = False) -> None:
        """
        Initialize a Data object.

        Parameters
        ----------
        cell_data : dict[int, CellLineage]
            The cell lineages to store.
        add_cycle_data : bool, optional
            Whether to compute and store the cycle lineages, by default False.
        """
        self.cell_data = cell_data
        if add_cycle_data:
            self._add_cycle_lineages()
        else:
            self.cycle_data = None  # type: dict[int, CycleLineage] | None

    def __deepcopy__(self, memo) -> "Data":
        """
        Create a deep copy of the Data object.

        Parameters
        ----------
        memo : dict
            A dictionary used by the copy module to track already copied objects
            to handle circular references.

        Returns
        -------
        Data
            A deep copy of the Data object with all cell lineages and
            cycle lineages (if present) independently copied.
        """
        # Cell_data
        cell_data_copy = {
            lid: copy.deepcopy(lineage, memo) for lid, lineage in self.cell_data.items()
        }

        # Cycle_data
        cycle_data_copy = None
        if self.cycle_data is not None:
            cycle_data_copy = {
                lid: copy.deepcopy(cycle_lineage, memo)
                for lid, cycle_lineage in self.cycle_data.items()
            }

        new_data = Data(cell_data_copy, add_cycle_data=False)
        new_data.cycle_data = cycle_data_copy

        return new_data

    def __repr__(self) -> str:
        return f"Data(cell_data={self.cell_data!r}, cycle_data={self.cycle_data!r})"

    def __str__(self) -> str:
        if self.cycle_data:
            txt = f" and {self.number_of_lineages()} cycle lineages"
        else:
            txt = ""
        return f"Data object with {self.number_of_lineages()} cell lineages{txt}."

    def _add_cycle_lineages(
        self, time_prop: str, time_step: int | float, lids: list[int] | None = None
    ) -> None:
        """
        Add the cell cycle lineages from the cell lineages.

        Parameters
        ----------
        time_prop : str
            The name of the time property to use for cycle lineage computation.
        time_step : int | float
            The time step between two consecutive time points.
        lids : list[int], optional
            The IDs of the lineages for which to compute cycle lineages,
            by default None i.e. all lineages.
        """
        if lids is None:
            lids = list(self.cell_data.keys())
        self.cycle_data = {
            lin_id: self._compute_cycle_lineage(time_prop, time_step, lin_id) for lin_id in lids
        }

    def _compute_cycle_lineage(self, time_prop: str, time_step: float, lid: int) -> CycleLineage:
        """
        Compute and return the cycle lineage corresponding to a given cell lineage.

        Parameters
        ----------
        time_prop : str
            The name of the time property to use for cycle lineage computation.
        time_step : float
            The time step between two consecutive time points.
        lid : int
            The ID of the cell lineage for which to compute the cycle lineage.

        Returns
        -------
        CycleLineage
            The cycle lineage corresponding to the cell lineage.
        """
        return CycleLineage(time_prop, time_step, self.cell_data[lid])

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

    # def _unfreeze_lineage_data(self):
    #     """
    #     Unfreeze all cell lineages.
    #     """
    #     for lineage in self.cell_data.values():
    #         Lineage.unfreeze(lineage)

    def copy(self, deep: bool = True) -> "Data":
        """
        Create a copy of the Data instance.

        Parameters
        ----------
        deep : bool, optional
            If True (default), creates a deep copy. If False, creates a shallow copy.

        Returns
        -------
        Data
            A copy of the Data instance. If deep=True, all cell lineages and
            cycle lineages (if present) are copied independently.
        """
        if deep:
            return copy.deepcopy(self)
        else:
            return copy.copy(self)

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

    def _get_next_available_lineage_ID(self, positive: bool) -> int:
        """
        Return the next available lineage ID, either positive or negative.

        Parameters
        ----------
        positive : bool, optional
            True to return a positive lineage ID,
            False to return a negative lineage ID.

        Returns
        -------
        int
            The next available lineage ID.

        Notes
        -----
        Next available lineage IDs are determined by finding the maximum
        (for positive IDs) or minimum (for negative IDs) existing lineage ID
        in the model and incrementing or decrementing it by one, respectively.
        This way, lineage IDs of previously deleted lineages are not reused.
        This avoids potential confusion or errors in lineage handling.

        Positive lineage IDs should be used for lineages with more than one cell.
        Negative lineage IDs should be used for lineages with a single cell,
        and are equal to the negative of the cell ID.
        """
        new_lin_id: int
        if len(self.cell_data) == 0:
            new_lin_id = 1 if positive else -1
        else:
            if positive:
                new_lin_id = max(self.cell_data.keys()) + 1
                if new_lin_id < 1:
                    new_lin_id = 1
            else:
                new_lin_id = min(self.cell_data.keys()) - 1
                if new_lin_id > -1:
                    new_lin_id = -1
        return new_lin_id

    def get_closest_cell(
        self,
        nid: int,
        lineage: CellLineage,
        radius: float = 0,
        time_window: int = 0,
        time_window_type: Literal["before", "after", "symmetric"] = "symmetric",
        lineages_to_search: list[CellLineage] | None = None,
        reference: Literal["center", "border"] = "center",
    ) -> tuple[int, CellLineage]:
        """
        Find the closest cell to a given cell of a lineage.

        Parameters
        ----------
        nid : int
            ID of the node for which to find the closest cell.
        lineage : CellLineage
            The lineage the node belongs to.
        radius : float, optional
            The maximum distance to consider, by default 0.
            If 0, the whole space is considered.
        time_window : int, optional
            The time window to consider, by default 0 i.e. only the current frame.
        time_window_type : Literal["before", "after", "symmetric"], optional
            The type of time window to consider, by default "symmetric".
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
            nid=nid,
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
        nid: int,
        lineage: CellLineage,
        radius: float = 0,
        time_property: str = "frame",
        time_window: int = 0,
        time_window_type: Literal["before", "after", "symmetric"] = "symmetric",
        lineages_to_search: list[CellLineage] | None = None,
        reference: Literal["center", "border"] = "center",
    ) -> list[tuple[int, CellLineage]]:
        """
        Find the closest cells to a given cell of a lineage.

        Parameters
        ----------
        nid : int
            ID of the node for which to find the closest cell.
        lineage : CellLineage
            The lineage the node belongs to.
        radius : float, optional
            The maximum distance to consider, by default 0.
            If 0, the whole space is considered.
        time_property: str = "frame"
            The name of the time property to use, by default "frame".
        time_window : int, optional
            The time window to consider, by default 0 i.e. only the current frame.
        time_window_type : Literal["before", "after", "symmetric"], optional
            The type of time window to consider, by default "symmetric".
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

        # Identification of the time interval to search in.
        center_timepoint = lineage.nodes[nid][time_property]
        if time_window == 0:
            timepoints_to_search = [center_timepoint]
        else:
            if time_window_type == "symmetric":
                timepoints_to_search = list(
                    range(center_timepoint - time_window, center_timepoint + time_window + 1)
                )
            elif time_window_type == "before":
                timepoints_to_search = list(
                    range(center_timepoint - time_window, center_timepoint + 1)
                )
            elif time_window_type == "after":
                timepoints_to_search = list(
                    range(center_timepoint, center_timepoint + time_window + 1)
                )
            else:
                raise ValueError(
                    f"Unknown time window type: '{time_window_type}'."
                    " Should be 'before', 'after' or 'symmetric'."
                )
            timepoints_to_search.sort()

        # Identification of nodes that are good candidates,
        # i.e. nodes that are in the time window
        # and in the lineages to search in.
        if not lineages_to_search:
            lineages_to_search = list(self.cell_data.values())
        candidate_cells = {}
        for lin in lineages_to_search:
            nodes = [
                node
                for node, timepoint in lin.nodes(data=time_property)
                if timepoint in timepoints_to_search
            ]
            if nodes:
                candidate_cells[lin] = nodes
        # Need to remove the node itself from the candidates.
        candidate_cells[lineage].remove(nid)

        # Identification of the closest cell.
        distances = []
        for lin, nodes in candidate_cells.items():
            for node in nodes:
                distance = math.dist(lineage.nodes[nid]["location"], lin.nodes[node]["location"])
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
