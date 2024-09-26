#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pycellin.classes.data import Data
from pycellin.classes.feature import FeaturesDeclaration


class ModelUpdater:

    def __init__(self):

        self._update_required = False

        # TODO: is a set a good idea? Maybe better to pool the nodes per lineage...
        # In this case I need to be able to modify the content of the collection
        self._added_cells = set()  # set of Cell()
        self._removed_cells = set()
        self._added_links = set()
        self._removed_links = set()

    def _update_cells(self, feat_declaration: FeaturesDeclaration, data: Data):
        for cell in self._added_cells:
            print(f"Cell {cell.cell_ID} from lineage {cell.lineage_ID}:")
            print(data.cell_data[cell.lineage_ID].nodes[cell.cell_ID])
            # How do I know which features need to be updated?
            # And how to compute custom features?

    # def _update_edges(self):
    #     pass

    # def _update_cell_lineages(self):
    #     pass

    # def _update_cycle_lineages(self):
    #     pass
