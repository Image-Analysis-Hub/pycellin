#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any

from pycellin.classes.data import Data
from pycellin.classes.feature import Feature
from pycellin.classes.feature_calculator import FeatureCalculator

# from pycellin.classes.feature_calculator import FeatureCalculatorFactory


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

        # self._calculators = dict()  # {str: function}
        # Keys are the feature name of the Feature itself? Feature itself would give
        # us info on the type of object to which the feature applies
        # (node, edge, lineage) as well as the return type of the feature
        # (int, float, str...).
        self._calculators = dict()  # {Feature: FeatureCalculator}
        # Since the calculator is just a function, why not store it in the Feature object?
        # self._factory = FeatureCalculatorFactory()

    def register_calculator(self, feature: Feature, calculator: FeatureCalculator):
        self._calculators[Feature] = calculator

    def delete_calculator(self, feature: Feature):
        del self._calculators[Feature]

    def _update_cells(self, data: Data):
        for cell in self._added_cells:
            print(f"Cell {cell.cell_ID} from lineage {cell.lineage_ID}:")
            print(data.cell_data[cell.lineage_ID].nodes[cell.cell_ID])
        # TODO: implement
        # How do I know which features need to be updated?
        # And how to compute custom features?
        # On regarde si dans les features déclarées, il y a des features de pycellin
        # qui n'ont pas été déjà calculées

        # If I do the following, I recompute every feature for every object
        # => not efficient
        # How to do it for a subset of objects? Add optional subset argument to
        # all the calculators?
        for feat, feat_calculator in self._calculators.items():
            feat_calculator.add_to_lineages(feat, data)

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
