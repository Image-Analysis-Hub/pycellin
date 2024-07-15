#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pickle
from typing import Any, Literal

from pycellin.classes.data import CoreData
from pycellin.classes.feature import FeaturesDeclaration
from pycellin.classes.lineage import CellLineage, CycleLineage


class Model:
    """ """

    def __init__(
        self,
        metadata: dict[str, Any] = None,
        feat_declaration: FeaturesDeclaration = None,
        coredata: CoreData = None,
    ) -> None:
        """
        Constructs all the necessary attributes for the Model object.

        Parameters
        ----------
        metadata : dict[str, Any], optional
            Metadata of the model (default is None).
        feat_declaration : FeaturesDeclaration, optional
            The declaration of the features present in the model (default is None).
        coredata : CoreData, optional
            The lineages data of the model (default is None).
        """
        self.metadata = metadata
        self.feat_declaration = feat_declaration
        self.coredata = coredata
        # self.date = datetime.now()
        # self.pycellin_version = get_distribution("pycellin").version
        # self.name = name
        # self.provenance = provenance

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
            f"coredata={self.coredata!r})"
        )

    def __str__(self) -> str:
        if "Name" in self.metadata and "Provenance" in self.metadata:
            txt = (
                f"Model named '{self.metadata['Name']}' "
                f"with {self.coredata.number_of_lineages()} lineages, "
                f"built from {self.metadata['Provenance']}."
            )
        elif "Name" in self.metadata:
            txt = (
                f"Model named '{self.metadata['Name']}' "
                f"with {self.coredata.number_of_lineages()} lineages."
            )
        elif "Provenance" in self.metadata:
            txt = (
                f"Model with {self.coredata.number_of_lineages()} lineages, "
                f"built from {self.metadata['Provenance']}."
            )
        else:
            txt = f"Model with {self.coredata.number_of_lineages()} lineages."
        return txt

    # TODO: do I need these methods?
    # def get_cell_lineages(self) -> list[CellLineage]:
    #     return self.coredata.data

    # def get_cycle_lineages(self) -> list[CycleLineage]:
    #     return self.cycledata.data

    # def get_cell_lineage_from_ID(self, lineage_id: int) -> CellLineage:
    #     return self.coredata.data[lineage_id]

    # def get_cycle_lineage_from_ID(self, lineage_id: int) -> CycleLineage:
    #     return self.cycledata.data[lineage_id]

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

    def add_feature(self, feature_name: str) -> None:
        """
        Add the specified feature to the model.

        This updates the FeaturesDeclaration and compute the feature values for all lineages.

        Parameters
        ----------
        feature_name : str
            Name of the feature to add. Need to be an available feature.
        """
        # Need to update the FeaturesDeclaration and the data
        # The name of the feature defines if its a node or an edge feature
        # (or a graph one?), and a cell or a cycle feature.
        pass

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

    def remove_feature(self, feature_name: str) -> None:
        """
        Remove the specified feature from the model.

        This updates the FeaturesDeclaration and remove the feature values for all lineages.

        Parameters
        ----------
        feature_name : str
            Name of the feature to remove.
        """
        # First need to check if the feature exists.
        if not self.feat_declaration.has_feature(feature_name):
            raise ValueError(f"Feature {feature_name} does not exist.")

        # Then need to update the FeaturesDeclaration and the data.

    # Should I have methods to process several features at once?
    # Yes if I need it at some point.

    def compute_CycleLineage(self) -> None:
        """
        Compute the CycleLineage from the CellLineage.
        """
        pass

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
