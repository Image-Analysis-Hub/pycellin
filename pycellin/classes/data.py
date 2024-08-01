#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


# class CoreData(Data):
#     """
#     dict of cell lineage: {lineage_id: CellLineage}
#     """

#     pass


# class BranchData(Data):
#     """
#     dict of cycle lineage: {lineage_id: CycleLineage}
#     """

#     pass
