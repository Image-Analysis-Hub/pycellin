#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class Metadata:
    """
    - dict of features: {feature_name: Feature}
    """

    def __init__(self):
        self.features = {}

    def __init__(self, features: dict):
        self.features = features

    def has_feature(self, feature_name: str):
        """
        Check if the metadata contains the specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature to check.

        Returns
        -------
        bool
            True if the feature is in the metadata, False otherwise.
        """
        pass

    def _add_feature(self, feature_name: str):
        """
        Add the specified feature to the metadata.

        Parameters
        ----------
        feature_name : str
            The name of the feature to add.
        """
        pass

    def _remove_feature(self, feature_name: str):
        """
        Remove the specified feature from the metadata.

        Parameters
        ----------
        feature_name : str
            The name of the feature to remove.
        """
        pass


# Do I need to make this a class?
# If I don't I will have a dict of dicts.
class Feature:
    """
    - name
    - data type (int, float, string)
    - type (node, edge, lineage)
    - unit?
    - provenance? (TM, CTC, pycellin, custom)
    """

    pass
