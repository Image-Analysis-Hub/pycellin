#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import itertools
from pathlib import Path
from pkg_resources import get_distribution
from typing import Optional

from pycellin.classes.metadata import Metadata
from pycellin.classes.data import CoreData


class Model:
    """ """

    def __init__(
        self,
        metadata: Metadata,
        coredata: CoreData,
        name: str = None,  # Should I make it optional? name: Optionale[str] = None
        provenance: str = None,
    ):
        """
        Constructs all the necessary attributes for the Model object.

        Parameters
        ----------
        metadata : Metadata
            The metadata associated with the model.
        coredata : CoreData
            The lineages data of the model.
        name : str, optional
            The name of the model (default is None).
        provenance : str, optional
            The provenance of the model (default is None).
        """
        self.date = datetime.now()
        self.pycellin_version = get_distribution("pycellin").version
        self.metadata = metadata
        self.coredata = coredata
        self.name = name
        self.provenance = provenance

        # Add an optional argument to ask to compute the CycleLineage?
        # Add a description in which people can put whatever they want
        # (string, facultative), or maybe a dict with a few keys (description,
        # author, etc.) that can be defined by the users, or create a function
        # to allow the users to add their own fields?

    def add_feature(self, feature_name: str):
        """
        Add the specified feature to the model.

        This updates the metadata and compute the feature values for all lineages.

        Parameters
        ----------
        feature_name : str
            Name of the feature to add. Need to be an available feature.
        """
        # Need to update the metadata and the data
        # The name of the feature defines if its a node or an edge feature
        # (or a graph one?), and a cell or a cycle feature.
        pass

    def recompute_feature(self, feature_name: str):
        """
        Recompute the values of the specified feature for all lineages.

        Parameters
        ----------
        feature_name : str
            Name of the feature to recompute.
        """
        # First need to check if the feature exists.
        if not self.metadata.has_feature(feature_name):
            raise ValueError(f"Feature {feature_name} does not exist.")

        # Then need to update the data.

    def remove_feature(self, feature_name: str):
        """
        Remove the specified feature from the model.

        This updates the metadata and remove the feature values for all lineages.

        Parameters
        ----------
        feature_name : str
            Name of the feature to remove.
        """
        # First need to check if the feature exists.
        if not self.metadata.has_feature(feature_name):
            raise ValueError(f"Feature {feature_name} does not exist.")

        # Then need to update the metadata and the data.

    # Should I have methods to process several features at once?
    # Yes if I need it at some point.

    def compute_CycleLineage(self):
        """
        Compute the CycleLineage from the CellLineage.
        """
        pass

    def export(self, path: str, format: str):
        """Export to another format, e.g. TrackMate."""
        pass
