#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
        # TODO: Keys are the feature name or the Feature itself? Feature itself
        # would give us info on the type of object to which the feature applies
        # (node, edge, lineage) as well as the return type of the feature
        # (int, float, str...).
        self._local_calculators = dict()  # {Feature: FeatureCalculator}
        self._global_calculators = dict()  # {Feature: FeatureCalculator}
        # TODO: is it useful to divide into local and global calculators?
        # TODO: Since the calculator is just a function, why not store it
        # in the Feature object? => I feel it's wrong to do that
        # self._factory = FeatureCalculatorFactory()

    def register_calculator(
        self, feature: Feature, calculator: FeatureCalculator
    ) -> None:
        # TODO: is it the correct place to instantiate the calculator?
        # Should I register the class or an instance...?
        if calculator.LOCAL_FEATURE:
            self._local_calculators[feature] = calculator()
        else:
            self._global_calculators[feature] = calculator()

    def delete_calculator(self, feature: Feature) -> None:
        if feature in self._local_calculators:
            del self._local_calculators[feature]
        elif feature in self._global_calculators:
            del self._global_calculators[feature]
        else:
            raise KeyError(f"Feature {feature} has no registered calculator.")

    def _update(self, data: Data) -> None:

        # TODO: For now we ignore cycle lineages.
        # TODO: What if we have interdependencies between features?
        # Maybe we need something to define the order in which features are computed?
        # Something saved in the ModelUpdater object? An argumentto the
        # update method?
        # => not implementing this for now to keep things "simple",
        # but I definitely need to address this later.
        # In any case, we need to recompute local features BEFORE global ones.

        # Local features: we recompute them for added / modified objects only.
        for cell_ID, lin_ID in self._added_cells:
            for feat, calc in self._local_calculators.items():
                lineage = data.cell_data[lin_ID]
                calc.add_to_one(feat.name, lineage, cell_ID)

        for link in self._added_links:
            for feat, calc in self._local_calculators.items():
                lineage = data.cell_data[link.lineage_ID]
                link_node_IDs = (link.source_cell_ID, link.target_cell_ID)
                calc.add_to_one(feat.name, lineage, link_node_IDs)

        for lin_ID in self._added_lineages | self._modified_lineages:
            for feat, calc in self._local_calculators.items():
                lineage = data.cell_data[lin_ID]
                calc.add_to_one(feat.name, lineage)

        # Global features: we recompute them for all objects.
        for feat, calc in self._global_calculators.items():
            # print(calc)
            # print(calc.add_to_all)
            calc.add_to_all(feat, data)

        # Update is done, we can clean up.
        self._update_required = False
        self._added_cells.clear()
        self._removed_cells.clear()
        self._added_links.clear()
        self._removed_links.clear()
        self._added_lineages.clear()
        self._removed_lineages.clear()
        self._modified_lineages.clear()

        # TODO: maybe separate in 3 different methods?
