#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pickle
from typing import Any, Callable, Literal

from pycellin.classes.data import Data
from pycellin.classes.feature import Feature, FeaturesDeclaration
from pycellin.classes.lineage import CellLineage, CycleLineage
import pycellin.graph.features as pgf


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

        # This in the metadata now.
        # self.date = datetime.now()
        # self.pycellin_version = get_distribution("pycellin").version
        # self.name = name
        # self.provenance = provenance
        # self.space_unit
        # self.time_unit
        # self.time_step
        # TODO: I think these fields should be made mandatory

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

    def get_pycellin_cell_lineage_features(self) -> dict[str, str]:
        """
        Return the Pycellin features that can be computed on cell lineages.

        Returns
        -------
        dict[str, str]
            Dictionary of features of the cell lineages,
            with features name as keys and features description as values.
        """
        cell_lineage_feats = {
            "absolute_age": "Age of the cell since the beginning of the lineage",
            "relative_age": (
                "Age of the cell since the beginning of the current cell cycle"
            ),
        }
        return cell_lineage_feats

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

    def get_pycellin_cycle_lineage_features(self) -> dict[str, str]:
        """
        Return the Pycellin features that can be computed on cycle lineages.

        Returns
        -------
        dict[str, str]
            Dictionary of features of the cycle lineages,
            with features name as keys and features description as values.
        """
        cycle_lineage_feats = {
            "cell_cycle_completeness": (
                "Completeness of the cell cycle, "
                "i.e. does it start and end with a division"
            ),
            "division_time": (
                "Time elapsed between the birth of a cell and its division"
            ),
            "division_rate": "Number of divisions per time unit",
        }
        return cycle_lineage_feats

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

    def add_lineage(self, lineage: CellLineage, with_CycleLineage: bool = True) -> None:
        """
        Add a lineage to the model.

        Parameters
        ----------
        lineage : CellLineage
            Lineage to add.
        with_CycleLineage : bool, optional
            True to compute the cycle lineage, False otherwise (default is True).

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
        return lineage

    def add_custom_feature(
        self,
        feat: Feature,
        feat_type: Literal["node", "edge", "lineage"],
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Add a custom feature to the model.

        Parameters
        ----------
        feat: Feature
            Feature to add.
        feat_type : Literal["node", "edge", "lineage"]
            Type of feature to add.
        func : Callable
            Function to compute the feature.
        args : Any
            Arguments to pass to the function.
        kwargs : Any
            Keyword arguments to pass to the function.
        """
        self.feat_declaration._add_feature(feat, feat_type)
        func(*args, **kwargs)

    def add_width_and_length(
        self,
        skel_algo: str = "zhang",
        tolerance: float = 0.5,
        method_width: str = "mean",
        width_ignore_tips: bool = False,
    ) -> None:
        """
        Compute and add the width and length features to the cells of the model.
        """
        # Updating the features declaration.
        feat_width = Feature(
            "width",
            "Width of the cell",
            "CellLineage",
            "Pycellin",
            "float",
            self.metadata["space_unit"],
        )
        feat_length = Feature(
            "length",
            "Length of the cell",
            "CellLineage",
            "Pycellin",
            "float",
            self.metadata["space_unit"],
        )
        self.feat_declaration._add_features([feat_width, feat_length], ["node"] * 2)

        # Computing the features values.
        assert (
            self.metadata["pixel_size"]["width"]
            == self.metadata["pixel_size"]["height"]
        ), "Pixel size should be the same for width and height."
        for lin in self.data.cell_data.values():
            for node in lin.nodes:
                width, length = pgf.get_width_and_length(
                    node,
                    lin,
                    self.metadata["pixel_size"]["width"],
                    skel_algo=skel_algo,
                    tolerance=tolerance,
                    method_width=method_width,
                    width_ignore_tips=width_ignore_tips,
                )
                lin.nodes[node]["width"] = width
                lin.nodes[node]["length"] = length

    def add_absolute_age(self, in_time_unit: bool = False) -> None:
        """
        Compute and add the absolute age feature to the cells of the model.

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
            self.metadata["time_unit"] if in_time_unit else "frame",
        )
        self.add_custom_feature(
            feat,
            "node",
            pgf.tracking._add_absolute_age,
            self.data.cell_data.values(),
            self.metadata["time_step"] if in_time_unit else 1,
        )

    def add_relative_age(self, in_time_unit: bool = False) -> None:
        """
        Compute and add the relative age feature to the cells of the model.

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
            self.metadata["time_unit"] if in_time_unit else "frame",
        )
        self.add_custom_feature(
            feat,
            "node",
            pgf.tracking._add_relative_age,
            self.data.cell_data.values(),
            self.metadata["time_step"] if in_time_unit else 1,
        )

    def add_cell_cycle_completeness(self) -> None:
        """
        Compute and add the cell cycle completeness feature to the cell cycles of the model.

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
            "node",
            pgf.tracking._add_cell_cycle_completeness,
            self.data.cycle_data.values(),
        )

    def add_division_time(self, in_time_unit: bool = False) -> None:
        """
        Compute and add the division time feature to the cell cycles of the model.

        The division time of a cell cycle is defined as the difference
        between the absolute ages of the two daughter cells.
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
            self.metadata["time_unit"] if in_time_unit else "frame",
        )
        self.add_custom_feature(
            feat,
            "node",
            pgf.tracking._add_division_time,
            self.data.cycle_data.values(),
            self.metadata["time_step"] if in_time_unit else 1,
        )

    def add_division_rate(self, in_time_unit: bool = False) -> None:
        """
        Compute and add the division rate feature to the cell cycles of the model.

        Division rate is defined as the number of divisions per time unit.
        It is the inverse of the division time.
        It is given in frames by default, but can be converted
        to the time unit of the model if specified.

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
            self.metadata["time_unit"] if in_time_unit else "frame",
        )
        self.add_custom_feature(
            feat,
            "node",
            pgf.tracking._add_division_rate,
            self.data.cycle_data.values(),
            self.metadata["time_step"] if in_time_unit else 1,
        )

    def add_pycellin_feature(self, feature_name: str, **kwargs: bool) -> None:
        """
        Add the specified predefined Pycellin feature to the model.

        This updates the FeaturesDeclaration and compute the feature values
        for all lineages.

        Parameters
        ----------
        feature_name : str
            Name of the feature to add. Need to be an available feature.
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
            feature_name in self.get_pycellin_cycle_lineage_features()
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

    def add_pycellin_features(self, feature_names: list[str], **kwargs: bool) -> None:
        """
        Add the specified predefined Pycellin features to the model.

        This updates the FeaturesDeclaration and compute the feature values
        for all lineages.

        Parameters
        ----------
        feature_names : list[str]
            Names of the features to add. Need to be available features.
        kwargs : bool
            Additional keyword arguments to pass to the function
            computing the feature. For example, for absolute_age,
            in_time_unit=True can be used to yield the age
            in the time unit of the model instead of in frames.
        """
        for feature_name in feature_names:
            self.add_pycellin_feature(feature_name, **kwargs)

    def recompute_feature(self, feature_name: str) -> None:
        """
        Recompute the values of the specified feature for all lineages.

        Parameters
        ----------
        feature_name : str
            Name of the feature to recompute.
        """
        # First need to check if the feature exists.
        if not self.feat_declaration.has_feature(feature_name):
            raise ValueError(f"Feature {feature_name} does not exist.")

        # Then need to update the data.
        pass

    def remove_feature(self, feature_name: str) -> None:
        """
        Remove the specified feature from the model.

        This updates the FeaturesDeclaration and remove the feature values
        for all lineages.

        Parameters
        ----------
        feature_name : str
            Name of the feature to remove.
        """
        # First need to check if the feature exists.
        if not self.feat_declaration.has_feature(feature_name):
            raise ValueError(f"Feature {feature_name} does not exist.")

        # Then need to update the FeaturesDeclaration and the data.
        # TODO

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
        pass
