#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from itertools import chain
from typing import Optional

from pycellin.classes.lineage import Lineage


class Feature:
    """ """

    def __init__(
        self,
        name: str,
        description: str,
        lineage_type: str,
        provenance: str,
        data_type: str,
        unit: Optional[str] = None,
    ) -> None:
        """
        Constructs all the necessary attributes for the Feature object.

        Parameters
        ----------
        name : str
            The name of the feature.
        description : str
            A description of the feature.
        lineage_type : str
            The type of lineage the feature is associated with (cell, cycle, or both).
        provenance : str
            The provenance of the feature (TrackMate, CTC, Pycellin, custom...).
        data_type : str
            The data type of the feature (int, float, string).
        unit : str, optional
            The unit of the feature (default is None).
        """
        self.name = name
        self.description = description
        self.lineage_type = lineage_type
        self.provenance = provenance
        self.data_type = data_type
        self.unit = unit

    def __repr__(self) -> str:
        """
        Compute a string representation of the Feature object.

        Returns
        -------
        str
            A string representation of the Feature object.
        """
        return (
            f"Feature(name={self.name!r}, description={self.description!r}, "
            f"lineage_type={self.lineage_type!r}, provenance={self.provenance!r}, "
            f"data_type={self.data_type!r}, unit={self.unit!r})"
        )

    def __str__(self) -> str:
        """
        Compute a human-readable string representation of the Feature object.

        Returns
        -------
        str
            A human-readable string representation of the Feature object.
        """
        # TODO: see if and how to simplify the string representation
        return self.__repr__()


class FeaturesDeclaration:
    """
    Spatial and temporal units are not part of the FeaturesDeclaration but of the
    features themselves to allow different units for a same dimension (e.g. time
    in seconds or minutes).
    - dict of node features: {feature_name: Feature}
    - dict of edge features: {feature_name: Feature}
    - dict of lineage features: {feature_name: Feature}
    How to differentiate between cell features and cycle features?
    """

    def __init__(
        self,
        node_features: dict = {},
        edge_features: dict = {},
        lineage_features: dict = {},
    ) -> None:
        self.node_feats = node_features
        self.edge_feats = edge_features
        self.lin_feats = lineage_features

    def __repr__(self) -> str:
        """
        Compute a string representation of the FeaturesDeclaration object.

        Returns
        -------
        str
            A string representation of the FeaturesDeclaration object.
        """
        return (
            f"FeaturesDeclaration(node_features={self.node_feats!r}, "
            f"edge_features={self.edge_feats!r}, "
            f"lineage_features={self.lin_feats!r})"
        )

    def __str__(self) -> str:
        """
        Compute a human-readable string representation of the FeaturesDeclaration object.

        Returns
        -------
        str
            A human-readable string representation of the FeaturesDeclaration object.
        """
        node_features = ", ".join(self.node_feats.keys())
        edge_features = ", ".join(self.edge_feats.keys())
        lineage_features = ", ".join(self.lin_feats.keys())
        return (
            f"Node features: {node_features}\n"
            f"Edge features: {edge_features}\n"
            f"Lineage features: {lineage_features}"
        )

    def has_feature(self, feature_name: str, feature_type: Optional[str]) -> bool:
        """
        Check if the FeaturesDeclaration contains the specified feature.

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
            True if the feature is in the FeaturesDeclaration, False otherwise.
        """
        pass

    def _add_feature(self, feature: Feature, feature_type: str) -> None:
        """
        Add the specified feature to the FeaturesDeclaration.

        Parameters
        ----------
        feature : Feature
            The feature to add.
        feature_type : str
            The type of the feature to add (node, edge, or lineage).
        """
        # TODO: raise an error if the feature already exists
        match feature_type:
            case "node":
                self.node_feats[feature.name] = feature
            case "edge":
                self.edge_feats[feature.name] = feature
            case "lineage":
                self.lin_feats[feature.name] = feature
            case _:
                raise ValueError(f"Invalid feature type: {feature_type}")

    def _add_features(self, features: list[Feature], feature_types: list[str]) -> None:
        """
        Add the specified features to the FeaturesDeclaration.

        Parameters
        ----------
        features : list[Feature]
            The features to add.
        feature_types : list[str]
            The types of the features to add (node, edge, or lineage).
        """
        for feature, feature_type in zip(features, feature_types):
            self._add_feature(feature, feature_type)

    def _remove_feature(self, feature_name: str, feature_type: str) -> None:
        """
        Remove the specified feature from the FeaturesDeclaration.

        Parameters
        ----------
        feature_name : str
            The name of the feature to remove.
        feature_type : str
            The type of the feature to add (node, edge, or lineage).
        """
        match feature_type:
            case "node":
                del self.node_feats[feature_name]
            case "edge":
                del self.edge_feats[feature_name]
            case "lineage":
                del self.lin_feats[feature_name]
            case _:
                raise ValueError(f"Invalid feature type: {feature_type}")

    def _remove_features(
        self, feature_names: list[str], feature_types: list[str]
    ) -> None:
        """
        Remove the specified features from the FeaturesDeclaration.

        Parameters
        ----------
        feature_names : list[str]
            The names of the features to remove.
        feature_types : list[str]
            The types of the features to remove (node, edge, or lineage).
        """
        for feature_name, feature_type in zip(feature_names, feature_types):
            self._remove_feature(feature_name, feature_type)

    # TODO: should this method be at the Model level?
    # Should I add a wrapper at the higher level?
    # => Stephane confirms that it should stay here and that I should add
    # a wrapper in Model.
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
        units = {}
        features_values = [
            self.node_feats.values(),
            self.edge_feats.values(),
            self.lin_feats.values(),
        ]
        for feat in chain.from_iterable(features_values):
            if feat.unit in units:
                units[feat.unit].append(feat.name)
            else:
                units[feat.unit] = [feat.name]
        return units
