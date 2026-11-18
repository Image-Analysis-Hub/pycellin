#!/usr/bin/env python3

"""The `Data` class: the cell lineages of a model and their cycle lineages."""

import copy
import math
import warnings
from typing import Any, Literal

import networkx as nx

from pycellin.classes.lineage import CellLineage, CycleLineage


class Data:
    """
    Class to store and manipulate cell lineages and cell cycle lineages.

    Parameters
    ----------
    cell_lineages : dict[int, CellLineage]
        The cell lineages to store, by lineage ID.

    Attributes
    ----------
    cell_lineages : dict[int, CellLineage]
        The cell lineages stored, by lineage ID.
    cycle_lineages : dict[int, CycleLineage] | None
        The cycle lineages stored, by lineage ID, if any.
    """

    def __init__(self, cell_lineages: dict[int, CellLineage]) -> None:
        self.cell_lineages = cell_lineages
        self.cycle_lineages: dict[int, CycleLineage] | None = None

    def __deepcopy__(self, memo: dict[int, Any]) -> "Data":
        """
        Create a deep copy of the `Data` object.

        Parameters
        ----------
        memo : dict[int, Any]
            A dictionary used by the copy module to track already copied objects
            to handle circular references.

        Returns
        -------
        Data
            A deep copy of the `Data` object with all cell lineages and
            cycle lineages (if present) independently copied.
        """
        # Cell lineages.
        cell_lineages_copy = {
            lid: copy.deepcopy(lineage, memo)
            for lid, lineage in self.cell_lineages.items()
        }

        # Cycle lineages.
        cycle_lineages_copy = None
        if self.cycle_lineages is not None:
            cycle_lineages_copy = {
                lid: copy.deepcopy(cycle_lineage, memo)
                for lid, cycle_lineage in self.cycle_lineages.items()
            }

        new_data = Data(cell_lineages_copy)
        new_data.cycle_lineages = cycle_lineages_copy

        return new_data

    def __repr__(self) -> str:
        """
        Return the representation of the data, with its cell and cycle lineages.

        Returns
        -------
        str
            The representation of the data.
        """
        return (
            f"Data(cell_lineages={self.cell_lineages!r}, "
            f"cycle_lineages={self.cycle_lineages!r})"
        )

    def __str__(self) -> str:
        """
        Return a short description of the data.

        Returns
        -------
        str
            The number of cell lineages, and of cycle lineages if any.
        """
        txt = f"Data object with {len(self.cell_lineages)} cell lineages"
        if self.cycle_lineages:
            txt += f" and {len(self.cycle_lineages)} cycle lineages"
        return txt + "."

    def _add_cycle_lineages(
        self, time_prop: str, lids: list[int] | None = None
    ) -> None:
        """
        Add the cell cycle lineages from the cell lineages.

        Without `lids`, the cycle lineages of all the cell lineages are computed and
        replace the stored ones. With `lids`, only the cycle lineages of these
        lineages are computed, and the others are kept.

        Parameters
        ----------
        time_prop : str
            The name of the time property to use for computation
            of cycle lineage properties.
        lids : list[int] | None, default=None
            The IDs of the lineages for which to compute cycle lineages.
            If None, all lineages.

        Raises
        ------
        KeyError
            If a lineage of `lids` is not in the data, or if a cell has no
            `time_prop` value.
        LineageStructureError
            If a cell lineage has several roots or cell fusions. It is a
            `~pycellin.exceptions.FusionError` for cell fusions.
        """
        if lids is None:
            self.cycle_lineages = {
                lin_id: self._compute_cycle_lineage(time_prop, lin_id)
                for lin_id in self.cell_lineages
            }
        else:
            new_cycle_lineages = {
                lin_id: self._compute_cycle_lineage(time_prop, lin_id)
                for lin_id in lids
            }
            self.cycle_lineages = {**(self.cycle_lineages or {}), **new_cycle_lineages}

    def _compute_cycle_lineage(self, time_prop: str, lid: int) -> CycleLineage:
        """
        Compute and return the cycle lineage corresponding to a given cell lineage.

        Parameters
        ----------
        time_prop : str
            The name of the time property to use for cycle lineage computation.
        lid : int
            The ID of the cell lineage for which to compute the cycle lineage.

        Returns
        -------
        CycleLineage
            The cycle lineage corresponding to the cell lineage.

        Raises
        ------
        KeyError
            If there is no cell lineage with the ID `lid`, or if a cell has no
            `time_prop` value.
        LineageStructureError
            If the cell lineage has several roots or cell fusions. It is a
            `~pycellin.exceptions.FusionError` for cell fusions.
        """
        return CycleLineage(time_prop, self.cell_lineages[lid])

    def _freeze_lineage_data(self):
        """
        Freeze all cell lineages.

        When a cell lineage is frozen, its structure cannot be modified:
        nodes and edges cannot be added or removed. However, graph, node and edge
        attributes can still be modified.
        """
        for lineage in self.cell_lineages.values():
            if not nx.is_frozen(lineage):
                nx.freeze(lineage)

    # def _unfreeze_lineage_data(self):
    #     """
    #     Unfreeze all cell lineages.
    #     """
    #     for lineage in self.cell_lineages.values():
    #         Lineage.unfreeze(lineage)

    def copy(self, deep: bool = True) -> "Data":
        """
        Create a copy of the `Data` instance.

        Parameters
        ----------
        deep : bool, default=True
            If True, creates a deep copy. If False, creates a shallow copy.

        Returns
        -------
        Data
            A copy of the `Data` instance. If `deep` is True, all cell lineages and
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

        Warns
        -----
        UserWarning
            If the number of cell lineages and cycle lineages do not match.
        """
        if self.cycle_lineages and len(self.cell_lineages) != len(self.cycle_lineages):
            msg = (
                f"Number of cell lineages ({len(self.cell_lineages)}) "
                f"and cycle lineages ({len(self.cycle_lineages)}) do not match. "
                "An update of the model is required. "
            )
            warnings.warn(msg)
        return len(self.cell_lineages)

    def _get_next_available_lineage_id(self, positive: bool) -> int:
        """
        Return the next available lineage ID, either positive or negative.

        Parameters
        ----------
        positive : bool
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
        This way, lineage IDs of previously deleted lineages are not reused,
        unless they were above the maximum (or below the minimum) of the remaining
        lineage IDs. This avoids potential confusion or errors in lineage handling.

        The returned lineage ID cannot be 0 in case the user wants to reserve
        it for special purposes.
        """
        new_lin_id: int
        if len(self.cell_lineages) == 0:
            new_lin_id = 1 if positive else -1
        else:
            if positive:
                new_lin_id = max(self.cell_lineages.keys()) + 1
                new_lin_id = max(new_lin_id, 1)
            else:
                new_lin_id = min(self.cell_lineages.keys()) - 1
                new_lin_id = min(new_lin_id, -1)
        return new_lin_id

    def get_closest_cell(
        self,
        cell_id: int,
        lineage: CellLineage,
        radius: float = 0,
        time_window: int = 0,
        time_window_type: Literal["before", "after", "symmetric"] = "symmetric",
        lineages_to_search: list[CellLineage] | None = None,
        reference: Literal["center", "border"] = "center",
    ) -> tuple[int, CellLineage] | None:
        """
        Find the closest cell to a given cell of a lineage.

        The distances are measured between the positions of the cells: ``cell_x`` and
        ``cell_y``, and ``cell_z`` when the given cell has one.

        Parameters
        ----------
        cell_id : int
            ID of the cell for which to find the closest cell.
        lineage : CellLineage
            The lineage the cell belongs to.
        radius : float, default=0
            The maximum distance to consider.
            If 0, the whole space is considered.
        time_window : int, default=0
            The time window to consider, in values of the ``timepoint`` property. If
            0, only the cells with the same ``timepoint`` value as the given cell are
            considered.
        time_window_type : Literal["before", "after", "symmetric"], default="symmetric"
            The type of time window to consider: before the time of the given cell,
            after it, or on both sides.
        lineages_to_search : list[CellLineage] | None, default=None
            The lineages to search in. If None, all lineages.
        reference : Literal["center", "border"], default="center"
            The reference point to consider for the distance. Only ``"center"``, the
            position of the cells, is implemented.

        Returns
        -------
        tuple[int, CellLineage] | None
            The ID of the closest cell and the lineage it belongs to, or None if no
            other cell is within the radius and the time window.

        Raises
        ------
        KeyError
            If `cell_id` is not a cell of `lineage`, or if it has no ``timepoint``
            value.
            If the given cell or a cell in the time window lacks one of the
            coordinates.
        ValueError
            If `time_window_type` or `reference` is not one of the values above.
        NotImplementedError
            If `reference` is ``"border"``.
        """
        distances = self.get_closest_cells(
            cell_id=cell_id,
            lineage=lineage,
            radius=radius,
            time_window=time_window,
            time_window_type=time_window_type,
            lineages_to_search=lineages_to_search,
            reference=reference,
        )
        return distances[0] if distances else None

    def get_closest_cells(
        self,
        cell_id: int,
        lineage: CellLineage,
        radius: float = 0,
        time_prop: str = "timepoint",
        time_window: int = 0,
        time_window_type: Literal["before", "after", "symmetric"] = "symmetric",
        lineages_to_search: list[CellLineage] | None = None,
        reference: Literal["center", "border"] = "center",
    ) -> list[tuple[int, CellLineage]]:
        """
        Find the closest cells to a given cell of a lineage.

        The distances are measured between the positions of the cells: ``cell_x`` and
        ``cell_y``, and ``cell_z`` when the given cell has one.

        Parameters
        ----------
        cell_id : int
            ID of the cell for which to find the closest cells.
        lineage : CellLineage
            The lineage the cell belongs to.
        radius : float, default=0
            The maximum distance to consider.
            If 0, the whole space is considered.
        time_prop : str, default="timepoint"
            The name of the time property.
        time_window : int, default=0
            The time window to consider, in values of `time_prop`. If 0, only the
            cells with the same `time_prop` value as the given cell are considered.
        time_window_type : Literal["before", "after", "symmetric"], default="symmetric"
            The type of time window to consider: before the time of the given cell,
            after it, or on both sides.
        lineages_to_search : list[CellLineage] | None, default=None
            The lineages to search in. If None, all lineages.
        reference : Literal["center", "border"], default="center"
            The reference point to consider for the distance. Only ``"center"``, the
            position of the cells, is implemented.

        Returns
        -------
        list[tuple[int, CellLineage]]
            The ID of each cell found and the lineage it belongs to, sorted by
            increasing distance. The given cell is not included.

        Raises
        ------
        KeyError
            If `cell_id` is not a cell of `lineage`, or if it has no `time_prop`
            value.
            If the given cell or a cell in the time window lacks one of the
            coordinates.
        ValueError
            If `time_window_type` or `reference` is not one of the values above.
        NotImplementedError
            If `reference` is ``"border"``.
        """
        # TODO: implement the "border" reference, e.g. from the cell contours.
        if reference == "border":
            raise NotImplementedError(
                "The distance between cell borders is not implemented yet: use "
                "reference='center'."
            )
        if reference != "center":
            raise ValueError(
                f"Unknown reference: '{reference}'. Should be 'center' or 'border'."
            )
        if time_window_type not in ("before", "after", "symmetric"):
            raise ValueError(
                f"Unknown time window type: '{time_window_type}'."
                " Should be 'before', 'after' or 'symmetric'."
            )

        # Position of the cell, in 3D when the cell has a z coordinate.
        cell = lineage.nodes[cell_id]
        coord_props = ["cell_x", "cell_y"]
        if "cell_z" in cell:
            coord_props.append("cell_z")
        position = [cell[prop] for prop in coord_props]

        # Time interval to search in.
        time = cell[time_prop]
        start = time if time_window_type == "after" else time - time_window
        end = time if time_window_type == "before" else time + time_window

        if lineages_to_search is None:
            lineages_to_search = list(self.cell_lineages.values())
        distances = []
        for lin in lineages_to_search:
            for node, node_time in lin.nodes(data=time_prop):
                if node_time is None or not start <= node_time <= end:
                    continue
                if lin is lineage and node == cell_id:
                    continue
                other_position = [lin.nodes[node][prop] for prop in coord_props]
                distance = math.dist(position, other_position)
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
    #     # To identify a node, need to have lineage_id and cell_id
    #     pass
