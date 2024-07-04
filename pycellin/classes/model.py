#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import itertools
from pathlib import Path
from pkg_resources import get_distribution

# from pycellin.classes.metadata import Metadata


class Model:
    """What do I need here on top of data and metadata?
    - an ID (string or number), can be the name of the file when it is built from a TM file
    - a provenance field? (mandatory) TM, CTC...
    - a date? (mandatory) can be useful for traceability
    - the version of Pycellin that was used to build the model? (mandatory) can be useful for traceability
    - a description in which people can put whatever they want (string, facultative),
      or maybe a dict with a few keys (description, author, etc.) that can be defined
      by the users, or create a function to allow the users to add their own fields?
    - and I'm probably forgetting something...

    """

    id_iter = itertools.count()

    def __init__(self):
        self.id = next(Model.id_iter)
        self.provenance = "Python"
        self.date = datetime.now()
        self.pycellin_version = get_distribution("pycellin").version

        self.metadata = None
        self.coredatas = None

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

    def export(self, path: str, format: str):
        """Export to another format, e.g. TrackMate."""
        pass
