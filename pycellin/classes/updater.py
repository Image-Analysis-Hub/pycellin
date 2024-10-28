#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any

from pycellin.classes.data import Data
from pycellin.classes.feature import Feature

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
        self._calculators = dict()  # {Feature: function}
        # Since the calculator is just a function, why not store it in the Feature object?
        # self._factory = FeatureCalculatorFactory()

    def register_calculator(self, feature: Feature, calculator: callable):
        self._calculators[Feature] = calculator

    # TODO: need an unregister_calculator method?
    # Should I name these methods add_calculator and remove_calculator?

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

    def feature_calculator(
        self,
        data: Data,
        feature: Feature,
    ):

        feat_name = feature.name
        feat_type = feature.feature_type
        lin_type = feature.lineage_type
        # feature_type is not stored in the Feature object for now,
        # but let's suppose it is.

        # Need to check if lin_type is a valid lineage type...? Same for feat_type?
        # => should be checked when the feature is created
        lineages = data.cell_data if lin_type == "CellLineage" else data.cycle_data

        match feat_type:
            case "node":
                for lin in lineages:
                    for node in lin.nodes:
                        lin.nodes[node][feat_name] = self._calculators[feat_name](
                            node, lin
                        )
            case "edge":
                for lin in lineages:
                    for edge in lin.edges:
                        lin.edges[edge][feat_name] = self._calculators[feat_name](
                            edge, lin
                        )
            case "lineage":
                for lin in lineages:
                    lin[feat_name] = self._calculators[feat_name](lin)
            case _:
                raise ValueError("Invalid feature type.")

    # def global_feature_calculator(self, data: Data, feature: Feature):
    #     pass

    # def _update_edges(self):
    #     pass

    # def _update_cell_lineages(self):
    #     pass

    # def _update_cycle_lineages(self):
    #     pass
