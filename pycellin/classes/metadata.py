#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional


class Metadata:
    """
    Spatial and temporal units are not part of the metadata but of the features to
    allow different units for a same dimension (e.g. time in seconds or minutes).
    - dict of node features: {feature_name: Feature}
    - dict of edge features: {feature_name: Feature}
    - dict of lineage features: {feature_name: Feature}
    """

    def __init__(
        self,
        node_features: dict = None,
        edge_features: dict = None,
        lineage_features: dict = None,
    ) -> None:
        self.node_feats = node_features
        self.edge_feats = edge_features
        self.lin_feats = lineage_features

    def has_feature(self, feature_name: str, feature_type: Optional[str]) -> bool:
        """
        Check if the metadata contains the specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature to check.
        feature_type : str, optional
            The type of the feature to check (node, edge, or lineage). If not specified,
            the method will check all types.

        Returns
        -------
        bool
            True if the feature is in the metadata, False otherwise.
        """
        pass

    def _add_feature(self, feature_name: str) -> None:
        """
        Add the specified feature to the metadata.

        Parameters
        ----------
        feature_name : str
            The name of the feature to add.
        """
        pass

    def _remove_feature(self, feature_name: str) -> None:
        """
        Remove the specified feature from the metadata.

        Parameters
        ----------
        feature_name : str
            The name of the feature to remove.
        """
        pass


class Feature:
    """
    - name
    - description
    - data type (int, float, string)
    - unit (for TM compatibility, dimension will be infered from the unit. Ask JY for java code when needed)
    - provenance? (TM, CTC, pycellin, custom)
    """

    def __init__(self) -> None:
        pass
