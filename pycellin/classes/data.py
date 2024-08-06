#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math

from typing import Literal

from pycellin.classes.lineage import CellLineage, CycleLineage


class Data:
    """
    Do I really need this one?
      => do I have something that is applicable for both core and branch data?
    Or maybe I need only the Data class and no subclasses.
    """

    def __init__(
        self, data: dict[str, CellLineage], add_cycle_data: bool = False
    ) -> None:
        self.cell_data = data
        if add_cycle_data:
            self._compute_cycle_lineages()
        else:
            self.cycle_data = None

    def _compute_cycle_lineages(self):
        self.cycle_data = {
            lin_id: CycleLineage(lin) for lin_id, lin in self.cell_data.items()
        }

    def number_of_lineages(self) -> int:
        if self.cycle_data:
            assert len(self.cell_data) == len(self.cycle_data), (
                f"Impossible state:"
                f"number of cell lineages ({len(self.cell_data)}) "
                f"and cycle lineages ({len(self.cycle_data)}) do not match."
            )
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
    ) -> tuple[CellLineage, int] | None:
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
        tuple[CellLineage, int] | None
            The node ID of the closest cell and the lineage it belongs to.
        """
        # TODO:
        # - Implement the radius parameter.
        # - Implement the reference parameter.
        # - Do I also return the distance itself?
        # - Return a tuple or a dict?
        # - Use a tuple for (noi, lin)? In which order?

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
        print(frames_to_search)

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
        print(candidate_cells)

        # Identification of the closest cell.
        cells_distance = []
        for lin, nodes in candidate_cells.items():
            for node in nodes:
                distance = math.dist(
                    lineage.nodes[noi]["location"], lin.nodes[node]["location"]
                )
                cells_distance.append((lin, node, distance))
        print(cells_distance)
        cells_distance.sort(key=lambda x: x[2])
        closest = cells_distance[0]

        return closest[0], closest[1]

    def get_closest_cells(
        node: int,
        lineage: CellLineage,
        radius: float = 0,
        time_window: int = 0,
        lineages_to_search: list[CellLineage] = None,
        reference: Literal["center", "border"] = "center",
    ) -> list[tuple[CellLineage, int]] | None:
        """
        Find the closest cells to a given cell of a lineage.

        Parameters
        ----------
        node : int
            The node for which to find the closest cell.
        lineage : CellLineage
            The lineage the node belongs to.
        radius : float, optional
            The maximum distance to consider, by default 0.
            If 0, the whole space is considered.
        time_window : int, optional
            The time window to consider, by default 0 i.e. only the current frame.
        lineages_to_search : list[CellLineage], optional
            The lineages to search in, by default None i.e. all lineages.
        reference : Literal["center", "border"], optional
            The reference point to consider for the distance, by default "center".

        Returns
        -------
        list[tuple[CellLineage, int]] | None
            The node IDs of the closest cells and the lineages they belong to.
        """
        # TODO: implement
        pass

    # def get_neighbouring_cells(
    #     lineage: CellLineage,
    #     node: int,
    #     radius: float,
    #     time_window: int | tuple[int, int],
    # ) -> list[tuple[CellLineage, int]]:
    #     """ """
    #     # TODO: implement
    #     # Parameter to define sort order? By default closest to farthest
    #     # Need to implement get_distance() between 2 nodes, not necessarily
    #     # from the same lineage...
    #     # To identify a node, need to have lineage_ID and cell_ID
    #     pass
