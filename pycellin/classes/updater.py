#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Any

from pycellin.classes import Data
from pycellin.classes import Feature
from pycellin.classes.feature_calculator import FeatureCalculator


class ModelUpdater:

    def __init__(self):

        self._update_required = False
        self._full_data_update = False

        # TODO: is a set a good idea? Maybe better to pool the nodes per lineage...
        # In this case I need to be able to modify the content of the collection
        self._added_cells = set()  # set of Cell()
        self._removed_cells = set()
        self._added_links = set()  # set of Link()
        self._removed_links = set()
        self._added_lineages = set()  # set of lineage_ID
        self._removed_lineages = set()
        self._modified_lineages = set()

        self._calculators = dict()  # {feat_name: FeatureCalculator}

        # TODO: add something to store the order in which features are computed?
        # Or maybe add an argument to update() to specify the order? We need to be able
        # to specify the order only for features that have dependencies. So it might be
        # easier to put this as an argument to the update() method, and have a default
        # order for the other features that is the order of registration (order of keys
        # in the _calculators dictionary).

    def register_calculator(
        self,
        feature: Feature,
        calculator: FeatureCalculator,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self._calculators[feature.name] = calculator(feature, *args, **kwargs)

    def delete_calculator(self, feature_name: str) -> None:
        if feature_name in self._calculators:
            del self._calculators[feature_name]
        else:
            raise KeyError(f"Feature {feature_name} has no registered calculator.")

    def _update(self, data: Data, features_to_update: list[str] | None = None) -> None:
        """
        Update the feature values of the data.

        Parameters
        ----------
        data : Data
            The data to update.
        features_to_update : list of str, optional
            List of features to update. If None, all features are updated.
        """
        # TODO: For now we ignore cycle lineages.
        # TODO: Deal with feature dependencies.

        if features_to_update is None:
            calculators = self._calculators.values()
        else:
            calculators = [self._calculators[feat] for feat in features_to_update]

        for calc in calculators:
            if calc.is_for_local_feature():
                # Local features: we recompute them for added / modified objects only.
                feature_type = calc.get_feature_type()
                match feature_type:
                    case "node":
                        for cell_ID, lin_ID in self._added_cells:
                            lineage = data.cell_data[lin_ID]
                            calc.add_to_one(lineage, cell_ID)
                    case "edge":
                        for link in self._added_links:
                            lineage = data.cell_data[link.lineage_ID]
                            link_node_IDs = (link.source_cell_ID, link.target_cell_ID)
                            calc.add_to_one(lineage, link_node_IDs)
                    case "lineage":
                        for lin_ID in self._added_lineages | self._modified_lineages:
                            lineage = data.cell_data[lin_ID]
                            calc.add_to_one(lineage)
                    case _:
                        raise ValueError(
                            f"Unknown feature type in calculator: {feature_type}"
                        )
            else:
                # Global features: we recompute them for all objects.
                calc.add_to_all(data)

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
