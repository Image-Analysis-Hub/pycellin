#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import networkx as nx

from pycellin.classes import Data
from pycellin.classes.feature_calculator import FeatureCalculator
from pycellin.classes.lineage import CellLineage
from pycellin.custom_types import Cell, Link


class ModelUpdater:
    def __init__(self):
        self._update_required = False
        self._full_data_update = False

        # TODO: is a set a good idea? Maybe better to pool the nodes per lineage...
        # In this case I need to be able to modify the content of the collection
        # TODO: what is the use of saving which objects have been removed? Do
        # we have features that need recomputing in that case?
        # => no but in that case we can remove the matching cycle lineage
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
        # in the _calculators dictionary). Even better would be to have a solver.
        # => keep this for later
        # On a related note, currently cell features are computed before cycle features.
        # So if a cell feature depends on a cycle feature, it will not be computed
        # correctly. In that case, the solution is to add the cycle features first,
        # then update, then add the cell features and update again.

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
        calculator: FeatureCalculator,
    ) -> None:
        """
        Register a calculator for a feature.

        Parameters
        ----------
        calculator : FeatureCalculator
            The calculator to use to compute the feature.
        """
        self._calculators[calculator.feature.identifier] = calculator

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

        Warnings
        --------
        This method does not resolve features dependencies. It is the responsibility
        of the user to ensure that features are updated in the correct order, if needed.
        For example, cell lineage features are computed before cycle lineage features,
        so if a cell lineage feature depends on a cycle lineage feature, it will not be
        computed correctly. In that case, the solution is to add the cycle features
        first, then update, then add the cell features and update again.
        """
        # TODO: refactor, this method is too long and does too many things.

        # Remove empty lineages.
        for lin_ID in (self._added_lineages | self._modified_lineages) - self._removed_lineages:
            if len(data.cell_data[lin_ID]) == 0:
                del data.cell_data[lin_ID]
                self._removed_lineages.add(lin_ID)

        # Split lineages with several unconnected components.
        lineages = list(data.cell_data.values())
        for lin in lineages:
            splitted_lins = [
                CellLineage(lin.subgraph(c).copy()) for c in nx.weakly_connected_components(lin)
            ]
            if len(splitted_lins) == 1:
                continue
            # The largest lineage is considered to be the original one
            # and will keep its lineage ID.
            largest_lin = CellLineage()
            for lin in splitted_lins:
                if len(lin) > len(largest_lin):
                    largest_lin = lin
            # We replace it in the data, otherwise the unsplitted lineage
            # will be kept.
            data.cell_data[largest_lin.graph["lineage_ID"]] = largest_lin
            self._modified_lineages.add(largest_lin.graph["lineage_ID"])
            splitted_lins.remove(largest_lin)
            # The other lineages are considered as new lineages.
            for lin in splitted_lins:
                if len(lin) == 1:
                    # ID of a one-node lineage is minus the ID of the node.
                    new_lin_ID = -list(lin.nodes())[0]
                    if new_lin_ID in data.cell_data:
                        # ID is already taken, so we change the ID of the node.
                        new_cell_ID = max(data.cell_data.keys()) + 1
                        cell_feats = lin._remove_cell(-new_lin_ID)
                        frame = cell_feats.pop("frame")
                        assert len(lin) == 0
                        lin._add_cell(new_cell_ID, frame, **cell_feats)
                        self._added_cells.add(new_cell_ID)
                        lin.graph["lineage_ID"] = -new_cell_ID
                        data.cell_data[-new_cell_ID] = lin
                        self._added_lineages.add(-new_cell_ID)
                    else:
                        lin.graph["lineage_ID"] = new_lin_ID
                        data.cell_data[new_lin_ID] = lin
                        self._added_lineages.add(new_lin_ID)
                else:
                    new_lin_ID = max(data.cell_data.keys()) + 1
                    lin.graph["lineage_ID"] = new_lin_ID
                    data.cell_data[new_lin_ID] = lin
                    self._added_lineages.add(new_lin_ID)

        # Update cell lineage features.
        # TODO: Deal with feature dependencies. See comments in __init__.
        if features_to_update is None:
            cell_calculators = [
                calc
                for calc in self._calculators.values()
                if calc.feature.lin_type == "CellLineage"
            ]
        else:
            cell_calculators = [
                self._calculators[feat]
                for feat in features_to_update
                if self._calculators[feat].feature.lin_type == "CellLineage"
            ]
        # Recompute the features as needed.
        for calc in cell_calculators:
            # Depending on the class of the calculator, a different version of
            # the enrich() method is called.
            calc.enrich(
                data,
                nodes_to_enrich=self._added_cells,
                edges_to_enrich=self._added_links,
                lineages_to_enrich=self._added_lineages | self._modified_lineages,
            )

        # In case of modifications in the structure of some cell lineages,
        # we need to recompute the cycle lineages and their features.
        # TODO: optimize so we don't have to recompute EVERYTHING for cycle lineages?
        for lin_ID in (self._modified_lineages | self._added_lineages) - self._removed_lineages:
            if data.cycle_data is not None:
                # To preserve references, but cannot work on frozen lineages...:
                # new_cycle_data = data._compute_cycle_lineage(lin_ID)
                # if lin_ID in data.cycle_data:
                #     data.cycle_data.update({lin_ID: new_cycle_data})
                # else:
                #     data.cycle_data[lin_ID] = new_cycle_data
                data.cycle_data[lin_ID] = data._compute_cycle_lineage(lin_ID)
        # Remove cycle lineages whose cell lineage has been removed.
        for lin_ID in self._removed_lineages:
            if data.cycle_data is not None and lin_ID in data.cycle_data:
                del data.cycle_data[lin_ID]
        # Update cycle lineages with cycle features.
        if data.cycle_data is not None:
            if features_to_update is None:
                cycle_calculators = [
                    calc
                    for calc in self._calculators.values()
                    if calc.feature.lin_type == "CycleLineage"
                ]
            else:
                cycle_calculators = [
                    self._calculators[feat]
                    for feat in features_to_update
                    if self._calculators[feat].feature.lin_type == "CycleLineage"
                ]
            # Since cycle lineages are recreated at each update, every element
            # of the lineages need to be updated with its features.
            cycle_nodes = [
                Cell(cycle_ID, lin_ID)
                for lin_ID in data.cycle_data
                for cycle_ID in data.cycle_data[lin_ID].nodes()
            ]
            cycle_edges = [
                Link(source, target, lin_ID)
                for lin_ID in data.cycle_data
                for source, target in data.cycle_data[lin_ID].edges()
            ]
            for calc in cycle_calculators:
                # Depending on the class of the calculator, a different version of
                # the enrich() method is called.
                calc.enrich(
                    data,
                    nodes_to_enrich=cycle_nodes,
                    edges_to_enrich=cycle_edges,
                    lineages_to_enrich=data.cycle_data.keys(),
                )

        # Update is done, we can clean up.
        self._reinit()
