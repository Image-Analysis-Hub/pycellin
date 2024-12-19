#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from collections import namedtuple
import pickle
from typing import Any, Literal

from pycellin.classes import Data
from pycellin.classes import Feature, FeaturesDeclaration
from pycellin.classes.feature_calculator import FeatureCalculator
from pycellin.classes import CellLineage
from pycellin.classes.updater import ModelUpdater
import pycellin.graph.features.tracking as tracking
import pycellin.graph.features.morphology as morpho
import pycellin.graph.features.utils as futils

# TODO: should I force the user to use the Cell and Link named tuples?
# Would impact the signature of a lot of methods, but would make these
# signatures more structured and consistent (looking at you, add_cell()).

Cell = namedtuple("Cell", ["cell_ID", "lineage_ID"])
Link = namedtuple(
    "Link",
    ["source_cell_ID", "target_cell_ID", "lineage_ID"],
)


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
        # FIXME: pretty sure creating an empty model will create issues
        self.metadata = metadata
        self.feat_declaration = feat_declaration
        self.data = data

        self._updater = ModelUpdater()
        # self._updater = ModelUpdater(self)

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
            if "Name" in self.metadata and "Provenance" in self.metadata:
                txt = (
                    f"Model named '{self.metadata['Name']}' "
                    f"with {self.data.number_of_lineages()} lineages, "
                    f"built from {self.metadata['Provenance']}."
                )
            elif "Name" in self.metadata:
                txt = (
                    f"Model named '{self.metadata['Name']}' "
                    f"with {self.data.number_of_lineages()} lineages."
                )
            elif "Provenance" in self.metadata:
                txt = (
                    f"Model with {self.data.number_of_lineages()} lineages, "
                    f"built from {self.metadata['Provenance']}."
                )
            else:
                txt = f"Model with {self.data.number_of_lineages()} lineages."
        elif self.data:
            txt = f"Model with {self.data.number_of_lineages()} lineages."
        elif self.metadata:
            if "Name" in self.metadata and "Provenance" in self.metadata:
                txt = (
                    f"Model named '{self.metadata['Name']}' "
                    f"built from {self.metadata['Provenance']}."
                )
            elif "Name" in self.metadata:
                txt = f"Model named '{self.metadata['Name']}'."
            elif "Provenance" in self.metadata:
                txt = f"Model built from {self.metadata['Provenance']}."
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

    # def get_lineage_from_name(self, name: str, lineage_type: Literal["cell", "cycle", "both"] = "both") -> CellLineage:
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

    def get_cell_lineage_features(self):
        """
        Return the cell lineages features present in the model.

        Returns
        -------
        list[str]
            List of the names of the cell lineages features present in the model.
        """
        cell_lineage_feats = []
        for feat_dict in [
            self.feat_declaration.node_feats,
            self.feat_declaration.edge_feats,
            self.feat_declaration.lin_feats,
        ]:
            cell_lineage_feats.extend(
                [
                    feat.name
                    for feat in feat_dict.values()
                    if feat.lineage_type == "CellLineage"
                ]
            )
        return cell_lineage_feats

    def get_cycle_lineage_features(self):
        """
        Return the cycle lineages features present in the model.

        Returns
        -------
        list[str]
            List of the names of the cycle lineages features present in the model.
        """
        cycle_lineage_feats = []
        for feat_dict in [
            self.feat_declaration.node_feats,
            self.feat_declaration.edge_feats,
            self.feat_declaration.lin_feats,
        ]:
            cycle_lineage_feats.extend(
                [
                    feat.name
                    for feat in feat_dict.values()
                    if feat.lineage_type == "CycleLineage"
                ]
            )
        return cycle_lineage_feats

    def get_next_available_lineage_ID(self) -> int:
        """
        Return the next available lineage ID.

        Returns
        -------
        int
            The next available lineage ID.
        """
        return max(self.data.cell_data.keys()) + 1

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
        self, lineage: CellLineage, with_CycleLineage: bool = False
    ) -> None:
        """
        Add a lineage to the model.

        Parameters
        ----------
        lineage : CellLineage
            Lineage to add.
        with_CycleLineage : bool, optional
            True to compute the cycle lineage, False otherwise (default is False).

        Raises
        ------
        KeyError
            If the lineage does not have a lineage_ID.
        """
        try:
            lin_ID = lineage.graph["lineage_ID"]
        except KeyError:
            raise KeyError("Lineage does not have a lineage_ID.")
        self.data.cell_data["lineage_ID"] = lineage

        if with_CycleLineage:
            cycle_lineage = self.data._compute_cycle_lineage(lin_ID)
            self.data.cycle_data["cycle_lineage_ID"] = cycle_lineage

        # Notify that an update of the feature values may be required.
        self._updater._update_required = True
        self._updater._added_lineages.add(lin_ID)

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
        # TODO: should I instead list all the removed cells and links?

        return new_lineage

    def add_cell(
        self,
        lineage_ID: int,
        cell_ID: int | None = None,
        cell_attributes: dict[str, Any] | None = None,
    ) -> int:
        """
        Add a cell to the lineage.

        Parameters
        ----------
        lineage_ID : int
            The ID of the lineage to which the cell belongs.
        cell_ID : int, optional
            The ID of the cell to add (default is None).
        cell_attributes : dict, optional
            A dictionary containing the features value of the cell to add.

        Returns
        -------
        int
            The ID of the added cell.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        KeyError
            If a feature in the cell_attributes is not declared.
        """
        try:
            lineage = self.data.cell_data[lineage_ID]
        except KeyError as err:
            raise KeyError(f"Lineage with ID {lineage_ID} does not exist.") from err

        if cell_attributes is not None:
            for feat in cell_attributes:
                if feat not in self.feat_declaration.node_feats:
                    raise KeyError(f"The feature {feat} has not been declared.")
        else:
            cell_attributes = dict()

        cell_ID = lineage._add_cell(cell_ID, **cell_attributes)

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

    def link_cells(
        self,
        source_cell_ID: int,
        source_lineage_ID: int,
        target_cell_ID: int,
        target_lineage_ID: int | None = None,
        link_attributes: dict[str, Any] | None = None,
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
        link_attributes : dict, optional
            A dictionary containing the features value of
            the link between the two cells.

        Raises
        ------
        KeyError
            If the lineage with the specified ID does not exist in the model.
        KeyError
            If a feature in the link_attributes is not declared.
        """
        # TODO: is the name add_link() better?
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

        if link_attributes is not None:
            for feat in link_attributes:
                if feat not in self.feat_declaration.edge_feats:
                    raise KeyError(f"The feature '{feat}' has not been declared.")
        else:
            link_attributes = dict()

        source_lineage._add_link(
            source_cell_ID, target_cell_ID, target_lineage, **link_attributes
        )

        # Notify that an update of the feature values may be required.
        self._updater._update_required = True
        self._updater._added_links.add(
            Link(source_cell_ID, target_cell_ID, source_lineage_ID)
        )
        self._updater._modified_lineages.add(source_lineage_ID)

    def unlink_cells(
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

    def check_for_fusions(self) -> list[Cell]:
        """
        Check if the cell lineages have fusion events and return the fusion cells.

        A fusion event is defined as a cell with more than one parent.

        Returns
        -------
        list[Cell]
            List of the fusion cells. Each cell is a named tuple:
            (cell_ID, lineage_ID).
        """
        fusions = []
        for lineage in self.data.cell_data.values():
            tmp = lineage.check_for_fusions()
            if tmp:
                lineage_ID = lineage.graph["lineage_ID"]
                fusions.extend([Cell(cell_ID, lineage_ID) for cell_ID in tmp])
        return fusions

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

    def add_custom_feature(
        self,
        feat: Feature,
        calculator: FeatureCalculator,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Add a custom feature to the model.

        This method adds the feature to the FeaturesDeclaration,
        register the way to compute the feature,
        and notify the updater that all data needs to be updated.
        To actually update the data, the user needs to call the update() method.

        Parameters
        ----------
        feat: Feature
            Feature to add.
        calculator : FeatureCalculator
            Calculator to compute the feature.

        Raises
        ------
        ValueError
            If the feature is a cycle lineage feature and cycle lineages
            have not been computed yet.
        """
        if feat.lineage_type == "CycleLineage" and not self.data.cycle_data:
            raise ValueError(
                "Cycle lineages have not been computed yet. "
                "Please compute the cycle lineages first with `model.add_cycle_data()`."
            )
        self.feat_declaration._add_feature(feat, calculator.get_feature_type())
        self._updater.register_calculator(feat, calculator, *args, **kwargs)
        self.prepare_full_data_update()

    # TODO: in case of data coming from a loader, there is no calculator associated
    # with the declared features.

    def add_cell_width(
        self,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
    ) -> None:
        feat = Feature(
            "cell_width",
            "Width of the cell",
            "CellLineage",
            "Pycellin",
            "float",
            self.metadata["space_unit"],
        )
        self.add_custom_feature(
            feat,
            morpho.CellWidth,
            self.metadata["pixel_size"]["width"],
            skel_algo=skel_algo,
            tolerance=tolerance,
            method_width=method_width,
            width_ignore_tips=width_ignore_tips,
        )

    def add_cell_length(
        self,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
    ) -> None:
        feat = Feature(
            "cell_length",
            "Length of the cell",
            "CellLineage",
            "Pycellin",
            "float",
            self.metadata["space_unit"],
        )
        self.add_custom_feature(
            feat,
            morpho.CellLength,
            self.metadata["pixel_size"]["width"],
            skel_algo=skel_algo,
            tolerance=tolerance,
            method_width=method_width,
            width_ignore_tips=width_ignore_tips,
        )

    def add_absolute_age(self, in_time_unit: bool = False) -> None:
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
        """
        feat = Feature(
            "absolute_age",
            "Age of the cell since the beginning of the lineage",
            "CellLineage",
            "Pycellin",
            "float" if in_time_unit else "int",
            self.metadata["time_step"] if in_time_unit else "frame",
        )
        time_step = self.metadata["time_step"] if in_time_unit else 1
        self.add_custom_feature(feat, tracking.AbsoluteAge, time_step)

    def add_relative_age(self, in_time_unit: bool = False) -> None:
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
        """
        feat = Feature(
            "relative_age",
            "Age of the cell since the beginning of the current cell cycle",
            "CellLineage",
            "Pycellin",
            "float" if in_time_unit else "int",
            self.metadata["time_step"] if in_time_unit else "frame",
        )
        time_step = self.metadata["time_step"] if in_time_unit else 1
        self.add_custom_feature(feat, tracking.RelativeAge, time_step)

    def add_cell_cycle_completeness(self) -> None:
        """
        Add the cell cycle completeness feature to the model.

        A cell cycle is defined as complete when it starts by a division
        AND ends by a division. Cell cycles that start at the root
        or end with a leaf are thus incomplete.
        This can be useful when analyzing features like division time. It avoids
        the introduction of a bias since we have no information on what happened
        before the root or after the leaves.
        """
        feat = Feature(
            "cell_cycle_completeness",
            "Completeness of the cell cycle",
            "CycleLineage",
            "Pycellin",
            "bool",
            "none",
        )
        self.add_custom_feature(
            feat,
            tracking.CellCycleCompleteness,
        )

    def add_division_time(self, in_time_unit: bool = False) -> None:
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
        """
        feat = Feature(
            "division_time",
            "Time elapsed between the birth of a cell and its division",
            "CycleLineage",
            "Pycellin",
            "float" if in_time_unit else "int",
            self.metadata["time_step"] if in_time_unit else "frame",
        )
        time_step = self.metadata["time_step"] if in_time_unit else 1
        self.add_custom_feature(feat, tracking.DivisionTime, time_step)

    def add_division_rate(self, in_time_unit: bool = False) -> None:
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
        """
        feat = Feature(
            "division_rate",
            "Number of divisions per time unit",
            "CycleLineage",
            "Pycellin",
            "float",
            f'1/{self.metadata["time_unit"]}' if in_time_unit else "1/frame",
        )
        time_step = self.metadata["time_step"] if in_time_unit else 1
        self.add_custom_feature(feat, tracking.DivisionRate, time_step)

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
        """
        if (
            feature_name in futils.get_pycellin_cycle_lineage_features()
            and not self.data.cycle_data
        ):
            raise ValueError(
                f"Feature {feature_name} is a feature of cycle lineages, "
                "but the cycle lineages have not been computed yet. "
                "Please compute the cycle lineages first with `model.add_cycle_data()`."
            )
        feat_dict = {
            "absolute_age": self.add_absolute_age,
            "relative_age": self.add_relative_age,
            "cell_width": self.add_cell_width,
            "cell_length": self.add_cell_length,
            "cell_cycle_completeness": self.add_cell_cycle_completeness,
            "division_time": self.add_division_time,
            "division_rate": self.add_division_rate,
        }
        try:
            feat_dict[feature_name](**kwargs)
        except KeyError:
            available_features = ", ".join(feat_dict.keys())
            raise KeyError(
                f"Feature {feature_name} is not a predefined feature of Pycellin. "
                f"Available Pycellin features are: {available_features}."
            )

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
        if not self.feat_declaration.has_feature(feature_name):
            raise ValueError(f"Feature {feature_name} does not exist.")

        # Then need to update the data.
        # TODO: implement
        pass

    def remove_feature(
        self,
        feature_name: str,
        feature_type: Literal["node", "edge", "lineage"],
    ) -> None:
        """
        Remove the specified feature from the model.

        This updates the FeaturesDeclaration, remove the feature values
        for all lineages, and notify the updater to unregister the calculator.

        Parameters
        ----------
        feature_name : str
            Name of the feature to remove.
        feature_type : str, optional
            The type of the feature to check (node, edge, or lineage).

        Raises
        ------
        ValueError
            If the feature does not exist.
        """
        # First we check if the feature exists.
        if not self.feat_declaration.has_feature(feature_name, feature_type):
            raise ValueError(
                f"There is no feature {feature_name} in {feature_type} features."
            )

        # Then we update the FeaturesDeclaration...
        feat_dict = self.feat_declaration._get_feat_dict_from_feat_type(feature_type)
        lineage_type = feat_dict[feature_name].lineage_type
        feat_dict.pop(feature_name)

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
    def read_from_pickle(path: str) -> None:
        """
        Read a model from a pickled Pycellin file.

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
