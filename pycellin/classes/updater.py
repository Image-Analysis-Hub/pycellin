#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any

from pycellin.classes.data import Data


class ModelUpdater:

    def __init__(self):

        self._update_required = False

        # TODO: is a set a good idea? Maybe better to pool the nodes per lineage...
        # In this case I need to be able to modify the content of the collection
        self._added_cells = set()  # set of Cell()
        self._removed_cells = set()
        self._added_links = set()  # set of Link()
        self._removed_links = set()
        self._added_lineages = set()  # set of lineage_ID
        self._removed_lineages = set()
        self._modified_lineages = set()

    def _update_cells(self, dict_feat: dict[str, Any], data: Data):
        for cell in self._added_cells:
            print(f"Cell {cell.cell_ID} from lineage {cell.lineage_ID}:")
            print(data.cell_data[cell.lineage_ID].nodes[cell.cell_ID])
            # TODO: implement
            # How do I know which features need to be updated?
            # And how to compute custom features?
            # On regarde si dans les features déclarées, il y a des features de pycellin
            # qui n'ont pas été déjà calculées

        # Update is done.
        self._update_required = False

    # TODO: need to check somewhere that no fusion were created when
    # modifying the graphs
    # => maybe better in Model?
    # Implement a higher level function in Model but need to check for fusion
    # every time an edge is added
    # TODO: also need to check if there are lone nodes in the graph, or a graph with
    # several connected components, or a graph with no nodes.

    # def _update_edges(self):
    #     pass

    # def _update_cell_lineages(self):
    #     pass

    # def _update_cycle_lineages(self):
    #     pass
