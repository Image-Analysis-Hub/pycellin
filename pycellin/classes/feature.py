#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from itertools import chain
from typing import Literal, Optional


class Feature:
    """ """

    def __init__(
        self,
        name: str,
        description: str,
        lineage_type: Literal["CellLineage", "CycleLineage"],
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
            The type of lineage the feature is associated with: cell lineage
            or cell cycle lineage.
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

    def _rename(self, new_name: str) -> None:
        """
        Rename the feature.

        Parameters
        ----------
        new_name : str
            The new name of the feature.
        """
        self.name = new_name

    def _modify_description(self, new_description: str) -> None:
        """
        Modify the description of the feature.

        Parameters
        ----------
        new_description : str
            The new description of the feature.
        """
        self.description = new_description


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

    def _get_feat_dict_from_feat_type(self, feature_type: str) -> dict:
        """
        Return the dictionary of features corresponding to the specified type.

        Parameters
        ----------
        feature_type : str
            The type of the features to return (node, edge, or lineage).

        Returns
        -------
        dict
            The dictionary of features corresponding to the specified type.

        Raises
        ------
        ValueError
            If the feature type is invalid.
        """
        # TODO: use literals instead of strings for feature types
        match feature_type:
            case "node":
                return self.node_feats
            case "edge":
                return self.edge_feats
            case "lineage":
                return self.lin_feats
            case _:
                raise ValueError(f"Invalid feature type: {feature_type}")

    def _add_feature(self, feature: Feature, feature_type: str) -> None:
        """
        Add the specified feature to the FeaturesDeclaration.

        Parameters
        ----------
        feature : Feature
            The feature to add.
        feature_type : str
            The type of the feature to add (node, edge, or lineage).

        Raises
        ------
        ValueError
            If the feature type is invalid.
        ValueError
            If a feature with the same name already exists in the specified type.
        """
        try:
            dict_feats = self._get_feat_dict_from_feat_type(feature_type)
        except ValueError as e:
            raise ValueError(e)

        if feature.name in dict_feats:
            raise ValueError(
                f"A Feature called {feature.name} already exists in "
                f"{feature_type} features."
            )

        dict_feats[feature.name] = feature

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

    def _add_cycle_lineage_features(self) -> None:
        """
        Add the basic features of cell cycle lineages.
        """
        common_fields = {
            "lineage_type": "CycleLineage",
            "provenance": "Pycellin",
            "data_type": "int",
        }

        # Node features.
        feat_ID = Feature(
            name="cycle_ID",
            description=(
                "Node ID of the cell cycle, "
                "i.e. node ID of the last cell in the cell cycle."
            ),
            **common_fields,
        )
        feat_cells = Feature(
            name="cells",
            description="Node ID of the cells in the cell cycle.",
            **common_fields,
        )
        feat_length = Feature(
            name="cycle_length",
            description="Number of cells in the cell cycle.",
            **common_fields,
        )
        feat_level = Feature(
            name="level",
            description=(
                "Level of the cell cycle in the lineage, "
                "i.e. number of cell cycles upstream of the current one."
            ),
            **common_fields,
        )
        self._add_features([feat_ID, feat_cells, feat_length, feat_level], ["node"] * 4)

        # Lineage features.
        feat_ID = Feature(
            name="cycle_lineage_ID",
            description=(
                "ID of the cell cycle lineage, "
                "which is the same ID as its associated cell lineage."
            ),
            **common_fields,
        )
        self._add_feature(feat_ID, "lineage")

    def _remove_feature(self, feature_name: str, feature_type: str) -> None:
        """
        Remove the specified feature from the FeaturesDeclaration.

        Parameters
        ----------
        feature_name : str
            The name of the feature to remove.
        feature_type : str
            The type of the feature to add (node, edge, or lineage).

        Raises
        ------
        ValueError
            If the feature type is invalid.
        KeyError
            If the feature does not exist within the specified type.
        """
        try:
            dict_feats = self._get_feat_dict_from_feat_type(feature_type)
        except ValueError as e:
            raise ValueError(e)

        if feature_name not in dict_feats:
            raise KeyError(
                f"Feature {feature_name} does not exist in {feature_type} features."
            )

        del dict_feats[feature_name]

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

    def _rename_feature(
        self, feature_name: str, new_name: str, feature_type: str
    ) -> None:
        """
        Rename a specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature to rename.
        new_name : str
            The new name for the feature.
        feature_type : str
            The type of the feature to rename. Valid values are "node",
            "edge", or "lineage".

        Raises
        ------
        ValueError
            If the feature type is invalid.
        KeyError
            If the feature does not exist within the specified type.
        """
        # TODO: make the feature type optional, but raise an error
        # if several features with the same name exist.
        # + do the same for the other relevant method
        try:
            dict_feats = self._get_feat_dict_from_feat_type(feature_type)
        except ValueError as e:
            raise ValueError(e)

        if feature_name not in dict_feats:
            raise KeyError(
                f"Feature {feature_name} does not exist in {feature_type} features."
            )

        dict_feats[new_name] = dict_feats.pop(feature_name)
        dict_feats[new_name]._rename(new_name)

    def _modify_feature_description(
        self, feature_name: str, new_description: str, feature_type: str
    ) -> None:
        """
        Modify the description of a specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature whose description is to be modified.
        new_description : str
            The new description for the feature.
        feature_type : str
            The type of the feature to be modified. Valid values are "node",
            "edge", or "lineage".

        Raises
        ------
        ValueError
            If the feature type is invalid.
        KeyError
            If the feature does not exist within the specified type.
        """
        try:
            dict_feats = self._get_feat_dict_from_feat_type(feature_type)
        except ValueError as e:
            raise ValueError(e)

        if feature_name not in dict_feats:
            raise KeyError(
                f"Feature {feature_name} does not exist in {feature_type} features."
            )

        dict_feats[feature_name]._modify_description(new_description)

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
