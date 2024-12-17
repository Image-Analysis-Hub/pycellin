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
        # TODO: what is the use of saving which objects have been removed? Do
        # we have features that need recomputing in that case?
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

    def _reinit(self) -> None:
        """
        Reset the state of the updater.
        """
        self._update_required = False
        self._full_data_update = False
        self._added_cells.clear()
        self._removed_cells.clear()
        self._added_links.clear()
        self._removed_links.clear()
        self._added_lineages.clear()
        self._removed_lineages.clear()
        self._modified_lineages.clear()

    def _print_state(self) -> None:
        """
        Print the state of the updater.
        """
        print("Update required:", self._update_required)
        print("Full data update:", self._full_data_update)
        print("Added cells:", self._added_cells)
        print("Removed cells:", self._removed_cells)
        print("Added links:", self._added_links)
        print("Removed links:", self._removed_links)
        print("Added lineages:", self._added_lineages)
        print("Removed lineages:", self._removed_lineages)
        print("Modified lineages:", self._modified_lineages)

    def register_calculator(
        self,
        feature: Feature,
        calculator: FeatureCalculator,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Register a calculator for a feature.

        Parameters
        ----------
        feature : Feature
            The feature of interest.
        calculator : FeatureCalculator
            The calculator to use to compute the feature.
        args : tuple
            Positional arguments to pass to the calculator.
        kwargs : dict
            Keyword arguments to pass to the calculator.
        """
        self._calculators[feature.name] = calculator(feature, *args, **kwargs)
        # TODO: isn't it better to pass an instance of the calculator instead of a class?
        # I feel like maybe it is easier / more intuitive for the user...?
        # Discuss with Marie.

    def delete_calculator(self, feature_name: str) -> None:
        """
        Delete the calculator for a feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature for which to delete the calculator.

        Raises
        ------
        KeyError
            If the feature has no registered calculator.
        """
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
        # TODO: Deal with feature dependencies.

        if features_to_update is None:
            calculators = self._calculators.values()
        else:
            calculators = [self._calculators[feat] for feat in features_to_update]

        # In case of modifications in the structure of some cell lineages,
        # we need to recompute the cycle lineages and their features.
        # TODO: optimize so we don't have to recompute EVERYTHING for cycle lineages.
        for lin_ID in self._modified_lineages:
            data.cycle_data[lin_ID] = data._compute_cycle_lineage(lin_ID)

        # TODO: avoid having to do a case depending on data to update
        # I can try:
        # - passing the data to update to the feature calculator
        # - create an intermediary class, maybe called ModelUpdate
        # mu = ModelUpdate(self._added_cells, self._added_links, ...)
        for calc in calculators:
            if calc.is_for_local_feature():
                # calc.calc(mu)
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
        self._reinit()
