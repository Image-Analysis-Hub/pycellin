#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pickle
from typing import Any, Literal

import pandas as pd
import networkx as nx

from pycellin.classes import (
    CellLineage,
    CycleLineage,
    Data,
    Feature,
    FeaturesDeclaration,
)
from pycellin.classes.feature_calculator import FeatureCalculator
from pycellin.classes.updater import ModelUpdater
import pycellin.graph.features.tracking as tracking
import pycellin.graph.features.motion as motion
import pycellin.graph.features.morphology as morpho
import pycellin.graph.features.utils as futils
from pycellin.custom_types import Cell, Link


class Model:
    """ """

    def __init__(
        self,
        metadata: dict[str, Any] | None = None,
        feat_declaration: FeaturesDeclaration = None,
        data: Data = None,
    ) -> None:
        """
        Constructs all the necessary attributes for the Model object.

        Parameters
        ----------
        metadata : dict[str, Any] | None, optional
            Metadata of the model (default is None).
        feat_declaration : FeaturesDeclaration, optional
            The declaration of the features present in the model (default is None).
        data : Data, optional
            The lineages data of the model (default is None).
        """
        self.metadata = metadata
        self.feat_declaration = feat_declaration
        self.data = data

        self._updater = ModelUpdater()

        # Add an optional argument to ask to compute the CycleLineage?
        # Add a description in which people can put whatever they want
        # (string, facultative), or maybe a dict with a few keys (description,
        # author, etc.) that can be defined by the users, or create a function
        # to allow the users to add their own fields?
        # Should name be optional or set to None? If optional and not provided, an
        # error will be raised when trying to access the attribute.
        # Same for provenance, description, etc.

    def __repr__(self) -> str:
        return (
            f"Model(metadata={self.metadata!r}, "
            f"feat_declaration={self.feat_declaration!r}, "
            f"data={self.data!r})"
        )

    def __str__(self) -> str:
        if self.metadata and self.data:
            nb_lin = self.data.number_of_lineages()
            if "name" in self.metadata and "provenance" in self.metadata:
                txt = (
                    f"Model named '{self.metadata['name']}' "
                    f"with {nb_lin} lineage{'s' if nb_lin > 1 else ''}, "
                    f"built from {self.metadata['provenance']}."
                )
            elif "name" in self.metadata:
                txt = (
                    f"Model named '{self.metadata['name']}' "
                    f"with {nb_lin} lineage{'s' if nb_lin > 1 else ''}."
                )
            elif "provenance" in self.metadata:
                txt = (
                    f"Model with {nb_lin} lineage{'s' if nb_lin > 1 else ''}, "
                    f"built from {self.metadata['provenance']}."
                )
            else:
                txt = f"Model with {nb_lin} lineage{'s' if nb_lin > 1 else ''}."
        elif self.data:
            nb_lin = self.data.number_of_lineages()
            txt = f"Model with {nb_lin} lineage{'s' if nb_lin > 1 else ''}."
        elif self.metadata:
            if "name" in self.metadata and "provenance" in self.metadata:
                txt = (
                    f"Model named '{self.metadata['name']}' "
                    f"built from {self.metadata['provenance']}."
                )
            elif "name" in self.metadata:
                txt = f"Model named '{self.metadata['name']}'."
            elif "provenance" in self.metadata:
                txt = f"Model built from {self.metadata['provenance']}."
            else:
                txt = "Empty model."
        else:
            txt = "Empty model."
        return txt

    # TODO: do I need these methods?
    # def get_cell_lineages(self) -> list[CellLineage]:
    #     return self.data.cell_data

    # def get_cycle_lineages(self) -> list[CycleLineage]:
    #     return self.data.cycle_data

    # def get_cell_lineage_from_ID(self, lineage_id: int) -> CellLineage:
    #     return self.data.cell_data[lineage_id]

    # def get_cycle_lineage_from_ID(self, lineage_id: int) -> CycleLineage:
    #     return self.data.cycle_data[lineage_id]

    # def get_lineage_from_name(self, name: str,
    #    lineage_type: Literal["cell", "cycle", "both"] = "both") -> CellLineage:
    #     """
    #     Return the cell lineage with the specified name.

    #     Parameters
    #     ----------
    #     name : str
    #         Name of the cell lineage to return.
    #     lineage_type : Literal["cell", "cycle", "both"], optional
    #         Type of lineage to return (default is "both").

    #     Returns
    #     -------
    #     CellLineage
    #         The cell lineage with the specified name.
    #     """
    #     # FIXME: bad design? In some cases it will return a Lineage
    #     # and in others a dict of Lineages...
    #     pass

    def get_space_unit(self) -> str:
        """
        Return the spatial unit of the model.

        Returns
        -------
        str
            The spatial unit of the model.
        """
        return self.metadata["space_unit"]

    def get_pixel_size(self) -> dict[str, float]:
        """
        Return the pixel size of the model.

        Returns
        -------
        dict[str, float]
            The pixel size of the model.
        """
        return self.metadata["pixel_size"]

    def get_time_unit(self) -> str:
        """
        Return the temporal unit of the model.

        Returns
        -------
        str
            The temporal unit of the model.
        """
        return self.metadata["time_unit"]

    def get_time_step(self) -> float:
        """
        Return the time step of the model.

        Returns
        -------
        int
            The time step of the model.
        """
        return self.metadata["time_step"]

    def get_units_per_features(self) -> dict[str, list[str]]:
        """
        Return a dict of units and the features associated with each unit.

        The method iterates over the node, edge, and lineage features
        of the features declaration object, grouping them by unit.

        Returns
        -------
        dict[str, list[str]]
            A dictionary where the keys are units and the values are lists
            of feature names. For example:
            {'unit1': ['feature1', 'feature2'], 'unit2': ['feature3']}.
        """
        return self.feat_declaration._get_units_per_features()

    def get_features(self) -> dict[str, Feature]:
        """
        Return the features present in the model.

        Returns
        -------
        dict[str, Feature]
            Dictionary of the features present in the model.
        """
        return self.feat_declaration.feats_dict

    def get_cell_lineage_features(
        self,
        include_Lineage_feats: bool = True,
    ) -> dict[str, Feature]:
        """
        Return the cell lineages features present in the model.

        Parameters
        ----------
        include_Lineage_feats : bool, optional
            True to include the Lineage features, False otherwise (default is True).

        Returns
        -------
        dict[str, Feature]
            Dictionary of the cell lineages features present in the model.
        """
        feats = self.feat_declaration._get_feat_dict_from_lin_type("CellLineage")
        if include_Lineage_feats:
            feats.update(self.feat_declaration._get_feat_dict_from_lin_type("Lineage"))
        return feats

    def get_cycle_lineage_features(
        self,
        include_Lineage_feats: bool = True,
    ) -> dict[str, Feature]:
        """
        Return the cycle lineages features present in the model.

        Parameters
        ----------
        include_Lineage_feats : bool, optional
            True to include the Lineage features, False otherwise (default is True).

        Returns
        -------
        dict[str, Feature]
            Dictionary of the cycle lineages features present in the model.
        """
        feats = self.feat_declaration._get_feat_dict_from_lin_type("CycleLineage")
        if include_Lineage_feats:
            feats.update(self.feat_declaration._get_feat_dict_from_lin_type("Lineage"))
        return feats

    def get_node_features(self) -> dict[str, Feature]:
        """
        Return the node features present in the model.

        Returns
        -------
        dict[str, Feature]
            Dictionary of the node features present in the model.
        """
        return self.feat_declaration._get_feat_dict_from_feat_type("node")

    def get_edge_features(self) -> dict[str, Feature]:
        """
        Return the edge features present in the model.

        Returns
        -------
        dict[str, Feature]
            Dictionary of the edge features present in the model.
        """
        return self.feat_declaration._get_feat_dict_from_feat_type("edge")

    def get_lineage_features(self) -> dict[str, Feature]:
        """
        Return the lineage features present in the model.

        Returns
        -------
        dict[str, Feature]
            Dictionary of the lineage features present in the model.
        """
        return self.feat_declaration._get_feat_dict_from_feat_type("lineage")

    def get_cell_lineages(self) -> list[CellLineage]:
        """
        Return the cell lineages present in the model.

        Returns
        -------
        list[CellLineage]
            List of the cell lineages present in the model.
        """
        return list(self.data.cell_data.values())

    def get_cycle_lineages(self) -> list[CycleLineage]:
        """
        Return the cycle lineages present in the model.

        Returns
        -------
        list[CellLineage]
            List of the cycle lineages present in the model.
        """
        return list(self.data.cycle_data.values())

    def get_cell_lineage_from_ID(self, lineage_ID: int) -> CellLineage | None:
        """
        Return the cell lineage with the specified ID.

        Parameters
        ----------
        lineage_ID : int
            ID of the lineage to return.

        Returns
        -------
        CellLineage
            The cell lineage with the specified ID.
        """
        if lineage_ID in self.data.cell_data:
            return self.data.cell_data[lineage_ID]
        else:
            return None

    def get_cycle_lineage_from_ID(self, lineage_ID: int) -> CycleLineage | None:
        """
        Return the cycle lineage with the specified ID.

        Parameters
        ----------
        lineage_ID : int
            ID of the lineage to return.

        Returns
        -------
        CycleLineage
            The cycle lineage with the specified ID.
        """
        if self.data.cycle_data and lineage_ID in self.data.cycle_data:
            return self.data.cycle_data[lineage_ID]
        else:
            return None

    def get_next_available_lineage_ID(self) -> int:
        """
        Return the next available lineage ID.

        Returns
        -------
        int
            The next available lineage ID.
        """
        return max(self.data.cell_data.keys()) + 1

    def has_feature(
        self,
        feature_name: str,
    ) -> bool:
        """
        Check if the model contains the specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature to check.

        Returns
        -------
        bool
            True if the feature is in the model, False otherwise.
        """
        return self.feat_declaration._has_feature(feature_name)

    def prepare_full_data_update(self) -> None:
        """
        Prepare the updater for a full data update.

        All cells, links and lineages in the model data will see
        their feature values recomputed during the next update.
        """
        if self._updater._full_data_update:
            return
        self._updater._full_data_update = True
        self._updater._update_required = True
        for lin_ID, lin in self.data.cell_data.items():
            for noi in lin.nodes:
                self._updater._added_cells.add(Cell(noi, lin_ID))
            for edge in lin.edges:
                self._updater._added_links.add(Link(edge[0], edge[1], lin_ID))
        self._updater._added_lineages = set(self.data.cell_data.keys())

    def is_update_required(self) -> bool:
        """
        Check if the model requires an update.

        The model requires an update if new features have been added to the model,
        or if cells, links or lineages have been added or removed.
        In that case, some features need to be recomputed to account for the changes.

        Returns
        -------
        bool
            True if the model requires an update, False otherwise.
        """
        return self._updater._update_required

    def update(self) -> None:
        """
        Bring the model up to date by recomputing features.
        """
        if not self._updater._update_required:
            print("Model is already up to date.")
            return

        # self.data._freeze_lineage_data()

        # TODO: need to handle all the errors that can be raised
        # by the updater methods to avoid incoherent states.
        # => saving a copy of the model before the update so we can roll back?

        self._updater._update(self.data)

        # self.data._unfreeze_lineage_data()

    def add_lineage(
        self,
        lineage: CellLineage | None = None,
        lineage_ID: int | None = None,
        with_CycleLineage: bool = False,
    ) -> int:
        """
        Add a lineage to the model.

        Parameters
        ----------
        lineage : CellLineage, optional
            Lineage to add (default is None). If None, a new lineage
            will be created.
        lineage_ID : int, optional
            ID of the lineage to add (default is None). If None, a new ID
            will be generated.
        with_CycleLineage : bool, optional
            True to compute the cycle lineage, False otherwise (default is False).

        Returns
        -------
        int
            The ID of the added lineage.
        """
        if lineage is None:
            if lineage_ID is None:
                lineage_ID = self.get_next_available_lineage_ID()
            lineage = CellLineage(lineage_ID=lineage_ID)
        else:
            lineage_ID = lineage.graph["lineage_ID"]
        self.data.cell_data[lineage_ID] = lineage

        if with_CycleLineage:
            cycle_lineage = self.data._compute_cycle_lineage(lineage_ID)
            self.data.cycle_data[lineage_ID] = cycle_lineage

        # Notify that an update of the feature values may be required.
        self._updater._update_required = True
        self._updater._added_lineages.add(lineage_ID)

        return lineage_ID

    def remove_lineage(self, lineage_ID: int) -> CellLineage:
        """
        Remove the specified lineage from the model.

        Parameters
        ----------
        lineage_id : int
            ID of the lineage to remove.

        Returns
        -------
        CellLineage
            The removed lineage.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not
            exist in the model.
        """
        try:
            lineage = self.data.cell_data.pop(lineage_ID)
        except KeyError:
            raise KeyError(f"Lineage with ID {lineage_ID} does not exist.")
        if self.data.cycle_data and lineage_ID in self.data.cycle_data:
            self.data.cycle_data.pop(lineage_ID)

        # Notify that an update of the feature values may be required.
        self._updater._update_required = True
        self._updater._removed_lineages.add(lineage_ID)

        return lineage

    def split_lineage_from_cell(
        self,
        cell_ID: int,
        lineage_ID: int,
        new_lineage_ID: int | None = None,
        split: Literal["upstream", "downstream"] = "upstream",
    ) -> CellLineage:
        """
        From a given cell, split a part of the given lineage into a new lineage.

        By default, the given cell will be the root of the new lineage.

        Parameters
        ----------
        cell_ID : int
            ID of the cell at which to split the lineage.
        lineage_ID : int
            ID of the lineage to split.
        new_lineage_ID : int, optional
            ID of the new lineage (default is None). If None, a new ID
            will be generated.
        split : {"upstream", "downstream"}, optional
            Where to split the lineage relative to the given cell.
            If upstream, the given cell is included in the second lineage.
            If downstream, the given cell is included in the first lineage.
            "upstream" by default.

        Returns
        -------
        CellLineage
            The new lineage.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        """
        # TODO: unclear method... and the case where the cell is a division
        # and split is downstream is not handled correctly (we end up with
        # a lineage with several disconnected components.
        try:
            lineage = self.data.cell_data[lineage_ID]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {lineage_ID} does not exist.") from err

        # Create the new lineage.
        new_lineage = lineage._split_from_cell(cell_ID, split)
        if new_lineage_ID is None:
            new_lineage_ID = self.get_next_available_lineage_ID()
        new_lineage.graph["lineage_ID"] = new_lineage_ID

        # Update the model data.
        self.data.cell_data[new_lineage_ID] = new_lineage
        # The update of the cycle lineages (if needed) will be
        # done by the updater.

        # Notify that an update of the feature values may be required.
        self._updater._update_required = True
        self._updater._added_lineages.add(new_lineage_ID)
        self._updater._modified_lineages.add(lineage_ID)

        return new_lineage

    def add_cell(
        self,
        lineage_ID: int,
        cell_ID: int | None = None,
        frame: int | None = 0,
        feat_values: dict[str, Any] | None = None,
    ) -> int:
        """
        Add a cell to the lineage.

        Parameters
        ----------
        lineage_ID : int
            The ID of the lineage to which the cell belongs.
        cell_ID : int, optional
            The ID of the cell to add (default is None).
        frame : int, optional
            The frame of the cell (default is 0).
        feat_values : dict, optional
            A dictionary containing the features values of the cell to add.

        Returns
        -------
        int
            The ID of the added cell.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        KeyError
            If a feature in the feat_values is not declared.
        """
        try:
            lineage = self.data.cell_data[lineage_ID]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {lineage_ID} does not exist.") from err

        if feat_values is not None:
            for feat in feat_values:
                if not self.feat_declaration._has_feature(feat):
                    raise KeyError(f"The feature {feat} has not been declared.")
        else:
            feat_values = dict()

        cell_ID = lineage._add_cell(cell_ID, frame, **feat_values)

        # Notify that an update of the feature values may be required.
        self._updater._update_required = True
        self._updater._added_cells.add(Cell(cell_ID, lineage_ID))
        self._updater._modified_lineages.add(lineage_ID)

        return cell_ID

    def remove_cell(self, cell_ID: int, lineage_ID: int) -> dict[str, Any]:
        """
        Remove a cell from a lineage.

        Parameters
        ----------
        cell_ID : int
            The ID of the cell to remove.
        lineage_ID : int
            The ID of the lineage to which the cell belongs.

        Returns
        -------
        dict
            Feature values of the removed cell.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        """
        try:
            lineage = self.data.cell_data[lineage_ID]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {lineage_ID} does not exist.") from err

        cell_attrs = lineage._remove_cell(cell_ID)

        # Notify that an update of the feature values may be required.
        self._updater._update_required = True
        self._updater._removed_cells.add(Cell(cell_ID, lineage_ID))
        self._updater._modified_lineages.add(lineage_ID)

        return cell_attrs

    def add_link(
        self,
        source_cell_ID: int,
        source_lineage_ID: int,
        target_cell_ID: int,
        target_lineage_ID: int | None = None,
        feat_values: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a link between two cells.

        Parameters
        ----------
        source_cell_ID : int
            The ID of the source cell.
        source_lineage_ID : int
            The ID of the source lineage.
        target_cell_ID : int
            The ID of the target cell.
        target_lineage_ID : int, optional
            The ID of the target lineage (default is None).
        feat_values : dict, optional
            A dictionary containing the features value of
            the link between the two cells.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        KeyError
            If a feature in the link_attributes is not declared.
        """
        try:
            source_lineage = self.data.cell_data[source_lineage_ID]
        except KeyError as err:
            raise KeyError(
                f"Lineage with ID {source_lineage_ID} does not exist."
            ) from err
        if target_lineage_ID is not None:
            try:
                target_lineage = self.data.cell_data[target_lineage_ID]
            except KeyError as err:
                raise KeyError(
                    f"Lineage with ID {target_lineage_ID} does not exist."
                ) from err
        else:
            target_lineage_ID = source_lineage_ID
            target_lineage = self.data.cell_data[source_lineage_ID]

        if feat_values is not None:
            for feat in feat_values:
                if not self.feat_declaration._has_feature(feat):
                    raise KeyError(f"The feature '{feat}' has not been declared.")
        else:
            feat_values = dict()

        source_lineage._add_link(
            source_cell_ID, target_cell_ID, target_lineage, **feat_values
        )

        # Notify that an update of the feature values may be required.
        self._updater._update_required = True
        self._updater._added_links.add(
            Link(source_cell_ID, target_cell_ID, source_lineage_ID)
        )
        self._updater._modified_lineages.add(source_lineage_ID)

    def remove_link(
        self, source_cell_ID: int, target_cell_ID: int, lineage_ID: int
    ) -> dict[str, Any]:
        """
        Remove a link between two cells.

        Parameters
        ----------
        source_cell_ID : int
            The ID of the source cell.
        target_cell_ID : int
            The ID of the target cell.
        lineage_ID : int
            The ID of the lineage to which the cells belong.

        Returns
        -------
        dict
            Feature values of the removed link.

        Raises
        ------
        KeyError
            If the link between the two cells does not exist.
        """
        try:
            lineage = self.data.cell_data[lineage_ID]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {lineage_ID} does not exist.") from err
        link_attrs = lineage._remove_link(source_cell_ID, target_cell_ID)

        # Notify that an update of the feature values may be required.
        self._updater._update_required = True
        self._updater._removed_links.add(
            Link(source_cell_ID, target_cell_ID, lineage_ID)
        )
        self._updater._modified_lineages.add(lineage_ID)

        return link_attrs

    def get_fusions(self, lineage_IDs: list[int] | None = None) -> list[Cell]:
        """
        Return fusion cells, i.e. cells with more than one parent.

        Parameters
        ----------
        lineage_IDs : list[int], optional
            List of lineage IDs to check for fusions.
            If not specified, all lineages will be checked (default is None).

        Returns
        -------
        list[Cell]
            List of the fusion cells. Each cell is a named tuple:
            (cell_ID, lineage_ID).

        Raises
        ------
        KeyError
            If a lineage with the specified ID does not exist in the model.
        """
        fusions = []
        if lineage_IDs is None:
            lineage_IDs = self.data.cell_data.keys()
        for lin_ID in lineage_IDs:
            try:
                lineage = self.data.cell_data[lin_ID]
            except KeyError as err:
                raise KeyError(f"Lineage with ID {lin_ID} does not exist.") from err
            tmp = lineage.get_fusions()
            if tmp:
                fusions.extend([Cell(cell_ID, lin_ID) for cell_ID in tmp])
        return fusions

    def add_custom_feature(
        self,
        calculator: FeatureCalculator,
    ) -> None:
        """
        Add a custom feature to the model.

        This method adds the feature to the FeaturesDeclaration,
        register the way to compute the feature,
        and notify the updater that all data needs to be updated.
        To actually update the data, the user needs to call the update() method.

        Parameters
        ----------
        calculator : FeatureCalculator
            Calculator to compute the feature.

        Raises
        ------
        ValueError
            If the feature is a cycle lineage feature and cycle lineages
            have not been computed yet.
        """
        if calculator.feature.lin_type == "CycleLineage" and not self.data.cycle_data:
            raise ValueError(
                "Cycle lineages have not been computed yet. "
                "Please compute the cycle lineages first with `model.add_cycle_data()`."
            )
        self.feat_declaration._add_feature(calculator.feature)
        self._updater.register_calculator(calculator)
        self.prepare_full_data_update()

    # TODO: in case of data coming from a loader, there is no calculator associated
    # with the declared features.

    def add_absolute_age(
        self,
        in_time_unit: bool = False,
        rename: str | None = None,
    ) -> None:
        """
        Add the cell absolute age feature to the model.

        The absolute age of a cell is defined as the number of nodes since
        the beginning of the lineage. Absolute age of the root is 0.
        It is given in frames by default, but can be converted
        to the time unit of the model if specified.

        Parameters
        ----------
        in_time_unit : bool, optional
            True to give the absolute age in the time unit of the model,
            False to give it in frames (default is False).
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "absolute_age",
            description="Age of the cell since the beginning of the lineage",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CellLineage",
            data_type="float" if in_time_unit else "int",
            unit=self.metadata["time_step"] if in_time_unit else "frame",
        )
        time_step = self.metadata["time_step"] if in_time_unit else 1
        self.add_custom_feature(tracking.AbsoluteAge(feat, time_step))

    def add_angle(
        self,
        unit: Literal["radian", "degree"] = "radian",
        rename: str | None = None,
    ) -> None:
        """
        Add the angle feature to the model.

        The angle is defined as the angle between the vectors representing
        the displacement of the cell at two consecutive detections.

        Parameters
        ----------
        unit : Literal["radian", "degree"], optional
            Unit of the angle (default is "radian").
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "angle",
            description=(
                "Angle of the cell trajectory between two consecutive detections"
            ),
            provenance="Pycellin",
            feat_type="edge",
            lin_type="CellLineage",
            data_type="float",
            unit=unit,
        )
        self.add_custom_feature(motion.Angle(feat, unit))

    def add_branch_mean_displacement(
        self,
        rename: str | None = None,
    ) -> None:
        """
        Add the branch mean displacement feature to the model.

        The branch mean displacement is defined as the mean displacement of the cell
        during the cell cycle.

        Parameters
        ----------
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "branch_mean_displacement",
            description="Mean displacement of the cell during the cell cycle",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CycleLineage",
            data_type="float",
            unit=self.metadata["space_unit"],
        )
        self.add_custom_feature(motion.BranchMeanDisplacement(feat))

    def add_branch_mean_speed(
        self,
        include_incoming_edge: bool = False,
        rename: str | None = None,
    ) -> None:
        """
        Add the branch mean speed feature to the model.

        The branch mean speed is defined as the mean speed of the cell
        during the cell cycle.

        Parameters
        ----------
        include_incoming_edge : bool, optional
            Whether to include the distance between the first cell and its predecessor.
            Default is False.
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "branch_mean_speed",
            description="Mean speed of the cell during the cell cycle",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CycleLineage",
            data_type="float",
            unit=f"{self.metadata['space_unit']} / {self.metadata['time_unit']}",
        )
        self.add_custom_feature(motion.BranchMeanSpeed(feat, include_incoming_edge))

    def add_branch_total_displacement(
        self,
        rename: str | None = None,
    ) -> None:
        """
        Add the branch displacement feature to the model.

        The branch total displacement is defined as the displacement of the cell during
        the cell cycle.

        Parameters
        ----------
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "branch_total_displacement",
            description="Displacement of the cell during the cell cycle",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CycleLineage",
            data_type="float",
            unit=self.metadata["space_unit"],
        )
        self.add_custom_feature(motion.BranchTotalDisplacement(feat))

    def add_cell_cycle_completeness(
        self,
        rename: str | None = None,
    ) -> None:
        """
        Add the cell cycle completeness feature to the model.

        A cell cycle is defined as complete when it starts by a division
        AND ends by a division. Cell cycles that start at the root
        or end with a leaf are thus incomplete.
        This can be useful when analyzing features like division time. It avoids
        the introduction of a bias since we have no information on what happened
        before the root or after the leaves.

        Parameters
        ----------
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "cell_cycle_completeness",
            description="Completeness of the cell cycle",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CycleLineage",
            data_type="bool",
            unit="none",
        )
        self.add_custom_feature(tracking.CellCycleCompleteness(feat))

    def add_cell_displacement(
        self,
        rename: str | None = None,
    ) -> None:
        """
        Add the displacement feature to the model.

        The displacement is defined as the Euclidean distance between the positions
        of the cell at two consecutive detections.

        Parameters
        ----------
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "cell_displacement",
            description="Displacement of the cell between two consecutive detections",
            provenance="Pycellin",
            feat_type="edge",
            lin_type="CellLineage",
            data_type="float",
            unit=self.metadata["space_unit"],
        )
        self.add_custom_feature(motion.CellDisplacement(feat))

    def add_cell_length(
        self,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
        rename: str | None = None,
    ) -> None:
        feat = Feature(
            name=rename if rename else "cell_length",
            description="Length of the cell",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CellLineage",
            data_type="float",
            unit=self.metadata["space_unit"],
        )
        calc = morpho.CellLength(
            feat,
            self.metadata["pixel_size"]["width"],
            skel_algo=skel_algo,
            tolerance=tolerance,
            method_width=method_width,
            width_ignore_tips=width_ignore_tips,
        )
        self.add_custom_feature(calc)

    def add_cell_speed(
        self,
        in_time_unit: bool = False,
        rename: str | None = None,
    ) -> None:
        """
        Add the speed feature to the model.

        The speed is defined as the displacement of the cell between two consecutive
        detections divided by the time elapsed between these two detections.
        It is given in the spatial unit of the model per time unit by default,
        but can be converted to the spatial unit of the model per frame if specified.

        Parameters
        ----------
        in_time_unit : bool, optional
            True to give the speed in the time unit of the model,
            False to give it in frames (default is False).
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "cell_speed",
            description="Speed of the cell between two consecutive detections",
            provenance="Pycellin",
            feat_type="edge",
            lin_type="CellLineage",
            data_type="float",
            unit=(
                f"{self.metadata['space_unit']}/{self.metadata['time_unit']}"
                if in_time_unit
                else f"{self.metadata['space_unit']}/frame"
            ),
        )
        time_step = self.metadata["time_step"] if in_time_unit else 1
        self.add_custom_feature(motion.CellSpeed(feat, time_step))

    def add_cell_width(
        self,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
        rename: str | None = None,
    ) -> None:
        feat = Feature(
            name=rename if rename else "cell_width",
            description="Width of the cell",
            feat_type="node",
            lin_type="CellLineage",
            data_type="float",
            provenance="Pycellin",
            unit=self.metadata["space_unit"],
        )
        calc = morpho.CellWidth(
            feat,
            self.metadata["pixel_size"]["width"],
            skel_algo=skel_algo,
            tolerance=tolerance,
            method_width=method_width,
            width_ignore_tips=width_ignore_tips,
        )
        self.add_custom_feature(calc)

    def add_division_rate(
        self,
        in_time_unit: bool = False,
        rename: str | None = None,
    ) -> None:
        """
        Add the division rate feature to the model.

        Division rate is defined as the number of divisions per time unit.
        It is the inverse of the division time.
        It is given in divisions per frame by default, but can be converted
        to divisions per time unit of the model if specified.

        Parameters
        ----------
        in_time_unit : bool, optional
            True to give the division rate in the time unit of the model,
            False to give it in frames (default is False).
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "division_rate",
            description="Number of divisions per time unit",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CycleLineage",
            data_type="float",
            unit=f'1/{self.metadata["time_unit"]}' if in_time_unit else "1/frame",
        )
        time_step = self.metadata["time_step"] if in_time_unit else 1
        self.add_custom_feature(tracking.DivisionRate(feat, time_step))

    def add_division_time(
        self,
        in_time_unit: bool = False,
        rename: str | None = None,
    ) -> None:
        """
        Add the division time feature to the model.

        Division time is defined as the time between 2 divisions.
        It is also the length of the cell cycle of the cell of interest.
        It is given in frames by default, but can be converted
        to the time unit of the model if specified.

        Parameters
        ----------
        in_time_unit : bool, optional
            True to give the division time in the time unit of the model,
            False to give it in frames (default is False).
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "division_time",
            description="Time elapsed between the birth of a cell and its division",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CycleLineage",
            data_type="float" if in_time_unit else "int",
            unit=self.metadata["time_step"] if in_time_unit else "frame",
        )
        time_step = self.metadata["time_step"] if in_time_unit else 1
        self.add_custom_feature(tracking.DivisionTime(feat, time_step))

    def add_relative_age(
        self,
        in_time_unit: bool = False,
        rename: str | None = None,
    ) -> None:
        """
        Add the cell relative age feature to the model.

        The relative age of a cell is defined as the number of nodes since
        the start of the cell cycle (i.e. previous division, or beginning
        of the lineage).
        It is given in frames by default, but can be converted
        to the time unit of the model if specified.

        Parameters
        ----------
        in_time_unit : bool, optional
            True to give the relative age in the time unit of the model,
            False to give it in frames (default is False).
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "relative_age",
            description="Age of the cell since the beginning of the current cell cycle",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CellLineage",
            data_type="float" if in_time_unit else "int",
            unit=self.metadata["time_step"] if in_time_unit else "frame",
        )
        time_step = self.metadata["time_step"] if in_time_unit else 1
        self.add_custom_feature(tracking.RelativeAge(feat, time_step))

    def add_straightness(
        self,
        include_incoming_edge: bool = False,
        rename: str | None = None,
    ) -> None:
        """
        Add the straightness feature to the model.

        The straightness is defined as the ratio between the Euclidean distance
        between the first and last positions of the cell and the total length
        of the cell trajectory.
        Straightness is a value between 0 and 1. A straight line has a straightness
        of 1, while a trajectory with many turns has a straightness close to 0.

        Parameters
        ----------
        include_incoming_edge : bool, optional
            Whether to include the distance between the first cell and its predecessor.
            Default is False.
        rename : str, optional
            New name for the feature (default is None).
        """
        feat = Feature(
            name=rename if rename else "straightness",
            description="Straightness of the cell displacement",
            provenance="Pycellin",
            feat_type="node",
            lin_type="CycleLineage",
            data_type="float",
        )
        self.add_custom_feature(motion.Straightness(feat, include_incoming_edge))

    def _get_feature_method(self, feature_name):
        """
        Return the method to compute the feature from its name.

        Parameters
        ----------
        feature_name : str
            Name of the feature.

        Returns
        -------
        callable
            Method to compute the feature.

        Raises
        ------
        AttributeError
            If the method to compute the feature is not found in the Model class.

        Notes
        -----
        The method name must follow the pattern "add_{feature_name}", otherwise
        it won't be recognized.
        """
        method_name = f"add_{feature_name}"
        method = getattr(self, method_name, None)
        if method:
            return method
        else:
            raise AttributeError(f"Method {method_name} not found in Model class.")

    def add_pycellin_feature(self, feature_name: str, **kwargs: bool) -> None:
        """
        Add a single predefined Pycellin feature to the model.

        Parameters
        ----------
        feature_name : str
            Name of the feature to add. Needs to be an available feature.
        kwargs : bool
            Additional keyword arguments to pass to the function
            computing the feature. For example, for absolute_age,
            in_time_unit=True can be used to yield the age
            in the time unit of the model instead of in frames.

        Raises
        ------
        KeyError
            If the feature is not a predefined feature of Pycellin.
        ValueError
            If the feature is a feature of cycle lineages and the cycle lineages
            have not been computed yet.
        """
        cell_lin_feats = list(futils.get_pycellin_cell_lineage_features().keys())
        cycle_lin_feats = list(futils.get_pycellin_cycle_lineage_features().keys())
        if feature_name not in cell_lin_feats + cycle_lin_feats:
            raise KeyError(
                f"Feature {feature_name} is not a predefined feature of Pycellin."
            )
        elif feature_name in cycle_lin_feats and not self.data.cycle_data:
            raise ValueError(
                f"Feature {feature_name} is a feature of cycle lineages, "
                "but the cycle lineages have not been computed yet. "
                "Please compute the cycle lineages first with `model.add_cycle_data()`."
            )
        self._get_feature_method(feature_name)(**kwargs)

    def add_pycellin_features(self, features_info: list[str | dict[str, Any]]) -> None:
        """
        Add the specified predefined Pycellin features to the model.

        Parameters
        ----------
        features_info : list[str | dict[str, Any]]
            List of the features to add. Each feature can be a string
            (the name of the feature) or a dictionary with the name of the
            feature as the key and additional keyword arguments as values.

        Examples
        --------
        With no additional arguments:
        >>> model.add_pycellin_features(["absolute_age", "relative_age"])
        With additional arguments:
        >>> model.add_pycellin_features(
        ...     [
        ...         {"absolute_age": {"in_time_unit": True}},
        ...         {"relative_age": {"in_time_unit": True}},
        ...     ]
        )
        It is possible to mix features with and without additional arguments:
        >>> model.add_pycellin_features(
        ...     [
        ...         {"absolute_age": {"in_time_unit": True}},
        ...         "cell_cycle_completeness",
        ...         {"relative_age": {"in_time_unit": True}},
        ...     ]
        )
        """
        for feat_info in features_info:
            if isinstance(feat_info, str):
                self.add_pycellin_feature(feat_info)
            elif isinstance(feat_info, dict):
                for feature_name, kwargs in feat_info.items():
                    self.add_pycellin_feature(feature_name, **kwargs)

    def recompute_feature(self, feature_name: str) -> None:
        """
        Recompute the values of the specified feature for all lineages.

        Parameters
        ----------
        feature_name : str
            Name of the feature to recompute.

        Raises
        ------
        ValueError
            If the feature does not exist.
        """
        # First need to check if the feature exists.
        if not self.feat_declaration._has_feature(feature_name):
            raise ValueError(f"Feature {feature_name} does not exist.")

        # Then need to update the data.
        # TODO: implement recompute_feature
        pass

    def remove_feature(
        self,
        feature_name: str,
    ) -> None:
        """
        Remove the specified feature from the model.

        This updates the FeaturesDeclaration, remove the feature values
        for all lineages, and notify the updater to unregister the calculator.

        Parameters
        ----------
        feature_name : str
            Name of the feature to remove.

        Raises
        ------
        ValueError
            If the feature does not exist.
        """
        # TODO: stop the user from removing mandatory features? With a force argument
        # set to False to bypass the check?
        # Or create a list of protected features so people can decide to add some of
        # their own features to it?

        # Preliminary checks.
        if not self.feat_declaration._has_feature(feature_name):
            raise ValueError(
                f"There is no feature {feature_name} in the declared features."
            )

        # First we update the FeaturesDeclaration...
        feature_type = self.feat_declaration.feats_dict[feature_name].feat_type
        lineage_type = self.feat_declaration.feats_dict[feature_name].lin_type
        self.feat_declaration.feats_dict.pop(feature_name)

        # ... we remove the feature values...
        if lineage_type == "CellLineage":
            lineage_data = self.data.cell_data
        elif lineage_type == "CycleLineage":
            lineage_data = self.data.cycle_data
        else:
            raise ValueError(
                "Lineage type not recognized. Must be 'CellLineage' or 'CycleLineage'."
            )
        match feature_type:
            case "node":
                for lin in lineage_data.values():
                    for _, data in lin.nodes(data=True):
                        try:
                            del data[feature_name]
                        except KeyError:
                            # No feature doesn't mean there is something wrong,
                            # maybe no update were done.
                            pass
            case "edge":
                for lin in lineage_data.values():
                    for _, _, data in lin.edges(data=True):
                        try:
                            del data[feature_name]
                        except KeyError:
                            # No feature doesn't mean there is something wrong,
                            # maybe no update were done.
                            pass
            case "lineage":
                for lin in lineage_data.values():
                    try:
                        del lin.graph[feature_name]
                    except KeyError:
                        # No feature doesn't mean there is something wrong,
                        # maybe no update were done.
                        pass

        # ... and finally we update the updater.
        try:
            self._updater.delete_calculator(feature_name)
        except KeyError:
            # No calculator doesn't mean there is something wrong,
            # maybe it's just an imported feature.
            pass

    # TODO: add a method to remove several features at the same time?
    # When no argument is provided, remove all features?
    # def remove_features(self, features_info: list[str | dict[str, Any]]) -> None:
    #     pass

    def add_cycle_data(self) -> None:
        """
        Compute and add the cycle lineages of the model.
        """
        self.data._add_cycle_lineages()
        self.feat_declaration._add_cycle_lineage_features()

    def to_cell_dataframe(self, lineages_ID: list[int] | None = None) -> pd.DataFrame:
        """
        Return the cell data of the model as a pandas DataFrame.

        Parameters
        ----------
        lineages_ID : list[int], optional
            List of the lineages ID to export (default is None).
            If None, all lineages are exported.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the cell data.

        Raises
        ------
        ValueError
            If the `lineage_ID`, `frame` or `cell_ID` feature is not found in the model.
        """
        list_df = []
        nb_nodes = 0
        for lin_ID, lineage in self.data.cell_data.items():
            if lineages_ID and lin_ID not in lineages_ID:
                continue
            nb_nodes += len(lineage)
            tmp_df = pd.DataFrame(dict(lineage.nodes(data=True)).values())
            tmp_df["lineage_ID"] = lin_ID
            list_df.append(tmp_df)
        df = pd.concat(list_df, ignore_index=True)
        assert nb_nodes == len(df)

        # Reoder the columns to have Pycellin mandatory features first.
        columns = df.columns.tolist()
        try:
            columns.remove("lineage_ID")
            columns.remove("frame")
            columns.remove("cell_ID")
        except ValueError as err:
            raise err
        columns = ["lineage_ID", "frame", "cell_ID"] + columns
        df = df[columns]
        df.sort_values(
            ["lineage_ID", "frame", "cell_ID"], ignore_index=True, inplace=True
        )

        return df

    def to_link_dataframe(self, lineages_ID: list[int] | None = None) -> pd.DataFrame:
        """
        Return the link data of the model as a pandas DataFrame.

        Parameters
        ----------
        lineages_ID : list[int], optional
            List of the lineages ID to export (default is None).
            If None, all lineages are exported.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the link data.
        """
        list_df = []
        nb_edges = 0
        for lin_ID, lineage in self.data.cell_data.items():
            if lineages_ID and lin_ID not in lineages_ID:
                continue
            nb_edges += len(lineage.edges)
            tmp_df = nx.to_pandas_edgelist(
                lineage, source="source_cell_ID", target="target_cell_ID"
            )
            tmp_df["lineage_ID"] = lin_ID
            list_df.append(tmp_df)
        df = pd.concat(list_df, ignore_index=True)
        assert nb_edges == len(df)

        # Reoder the columns to have Pycellin mandatory features first.
        columns = df.columns.tolist()
        try:
            columns.remove("lineage_ID")
        except ValueError as err:
            raise err
        columns = ["lineage_ID"] + columns
        df = df[columns]
        df.sort_values("lineage_ID", ignore_index=True, inplace=True)

        return df

    def to_lineage_dataframe(
        self, lineages_ID: list[int] | None = None
    ) -> pd.DataFrame:
        """
        Return the lineage data of the model as a pandas DataFrame.

        Parameters
        ----------
        lineages_ID : list[int], optional
            List of the lineages ID to export (default is None).
            If None, all lineages are exported.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the lineage data.

        Raises
        ------
        ValueError
            If the `lineage_ID` is not found in the model.
        """
        list_df = []
        for lin_ID, lineage in self.data.cell_data.items():
            if lineages_ID and lin_ID not in lineages_ID:
                continue
            tmp_df = pd.DataFrame([lineage.graph])
            list_df.append(tmp_df)
        df = pd.concat(list_df, ignore_index=True)

        # Reoder the columns to have Pycellin mandatory features first.
        columns = df.columns.tolist()
        try:
            columns.remove("lineage_ID")
        except ValueError as err:
            raise err
        columns = ["lineage_ID"] + columns
        df = df[columns]
        df.sort_values("lineage_ID", ignore_index=True, inplace=True)

        return df

    def to_cycle_dataframe(self, lineages_ID: list[int] | None = None) -> pd.DataFrame:
        """
        Return the cell cycle data of the model as a pandas DataFrame.

        Parameters
        ----------
        lineages_ID : list[int], optional
            List of the lineages ID to export (default is None).
            If None, all lineages are exported.

        Returns
        -------
        pd.DataFrame
            DataFrame containing the cell cycle data.

        Raises
        ------
        ValueError
            If the cycle lineages have not been computed yet.
        ValueError
            If the `lineage_ID`, `level` or `cycle_ID` feature is not found
            in the model.
        """
        list_df = []
        nb_nodes = 0
        if not self.data.cycle_data:
            raise ValueError(
                "Cycle lineages have not been computed yet. "
                "Please compute the cycle lineages first with `model.add_cycle_data()`."
            )
        for lin_ID, lineage in self.data.cycle_data.items():
            if lineages_ID and lin_ID not in lineages_ID:
                continue
            nb_nodes += len(lineage)
            tmp_df = pd.DataFrame(dict(lineage.nodes(data=True)).values())
            list_df.append(tmp_df)
        df = pd.concat(list_df, ignore_index=True)
        assert nb_nodes == len(df)

        # Reoder the columns to have Pycellin mandatory features first.
        columns = df.columns.tolist()
        try:
            columns.remove("lineage_ID")
            columns.remove("level")
            columns.remove("cycle_ID")
        except ValueError as err:
            raise err
        columns = ["lineage_ID", "level", "cycle_ID"] + columns
        df = df[columns]
        df.sort_values(
            ["lineage_ID", "level", "cycle_ID"], ignore_index=True, inplace=True
        )

        return df

    def save_to_pickle(
        self, path: str, protocol: int = pickle.HIGHEST_PROTOCOL
    ) -> None:
        """
        Save the model to a file by pickling it.

        Parameters
        ----------
        path : str
            Path to save the model.
        protocol : int, optional
            Pickle protocol to use (default is pickle.HIGHEST_PROTOCOL).
        """
        with open(path, "wb") as file:
            pickle.dump(self, file, protocol=protocol)

    @staticmethod
    def load_from_pickle(path: str) -> None:
        """
        Load a model from a pickled Pycellin file.

        Parameters
        ----------
        path : str
            Path to read the model.
        """
        with open(path, "rb") as file:
            return pickle.load(file)

    def export(self, path: str, format: str) -> None:
        """
        Export the model to a file in a specific format (e.g. TrackMate).

        Parameters
        ----------
        path : str
            Path to export the model.
        format : str
            Format of the exported file.
        """
        # TODO: implement
        pass
