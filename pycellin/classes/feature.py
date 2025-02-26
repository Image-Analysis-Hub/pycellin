#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from itertools import chain
from typing import Literal

from pycellin.custom_types import FeatureType, LineageType
from pycellin.utils import check_literal_type


class Feature:
    """ """

    def __init__(
        self,
        name: str,
        description: str,
        feat_type: str,
        lin_type: Literal["CellLineage", "CycleLineage"],
        data_type: str,
        provenance: str,
        unit: str | None = None,
    ) -> None:
        """
        Constructs all the necessary attributes for the Feature object.

        Parameters
        ----------
        name : str
            The name of the feature.
        description : str
            A description of the feature.
        feat_type : str
            The type of the feature (node, edge, lineage, or a combination of the 3).
        lin_type : Literal["CellLineage", "CycleLineage"]
            The type of lineage the feature is associated with: cell lineage
            or cell cycle lineage.
        data_type : str
            The data type of the feature (int, float, string).
        provenance : str
            The provenance of the feature (TrackMate, CTC, Pycellin, custom...).
        unit : str, optional
            The unit of the feature (e.g. µm, min, cell).

        Raises
        ------
        ValueError
            If the lineage type is not a valid value.
        """
        # TODO: add a protect argument to prevent the modification of the feature
        # and create the related methods to protect / unprotect the feature, and getters
        self.name = name
        self.description = description
        if not check_literal_type(lin_type, LineageType):
            raise ValueError(
                f"Feature type must be one of {', '.join(LineageType.__args__)}."
            )
        self.feat_type = feat_type
        self.lin_type = lin_type
        self.data_type = data_type
        self.provenance = provenance
        self.unit = unit

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Feature):
            return NotImplemented
        return (
            self.name == other.name
            and self.description == other.description
            and self.feat_type == other.feat_type
            and self.lin_type == other.lin_type
            and self.data_type == other.data_type
            and self.provenance == other.provenance
            and self.unit == other.unit
        )

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
            f"feat_type={self.feat_type!r}, lin_type={self.lin_type!r}, "
            f"provenance={self.provenance!r}, data_type={self.data_type!r}, "
            f"unit={self.unit!r})"
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
    The FeaturesDeclaration class is used to store the features that are
    associated with the nodes, edges, and lineages of a cell lineage graph.

    Attributes
    ----------
    feats_dict : dict[str, Feature]
        A dictionary of features where the keys are the feature names and
        the values are the Feature objects.

    Notes
    -----
    Spatial and temporal units are not part of the FeaturesDeclaration but of the
    features themselves to allow different units for a same dimension (e.g. time
    in seconds or minutes).
    """

    def __init__(
        self,
        feats_dict: dict[str, Feature] | None = None,
    ) -> None:
        self.feats_dict = feats_dict if feats_dict else {}

    def __eq__(self, other):
        if not isinstance(other, FeaturesDeclaration):
            return False
        return self.feats_dict == other.feats_dict

    def __repr__(self) -> str:
        """
        Compute a string representation of the FeaturesDeclaration object.

        Returns
        -------
        str
            A string representation of the FeaturesDeclaration object.
        """
        return f"FeaturesDeclaration(feats_dict={self.feats_dict!r}"

    def __str__(self) -> str:
        """
        Compute a human-readable str representation of the FeaturesDeclaration object.

        Returns
        -------
        str
            A human-readable string representation of the FeaturesDeclaration object.
        """
        node_feats = ", ".join(self.get_node_feats().keys())
        edge_feats = ", ".join(self.get_edge_feats().keys())
        lin_feats = ", ".join(self.get_lin_feats().keys())
        return (
            f"Node features: {node_feats}\n"
            f"Edge features: {edge_feats}\n"
            f"Lineage features: {lin_feats}"
        )

    def _has_feature(
        self,
        feature_name: str,
    ) -> bool:
        """
        Check if the FeaturesDeclaration contains the specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature to check.

        Returns
        -------
        bool
            True if the feature has been declared, False otherwise.

        Raises
        ------
        ValueError
            If the feature type is invalid.
        """
        if feature_name in self.feats_dict:
            return True
        else:
            return False

    def _get_feat_dict_from_feat_type(
        self, feat_type: Literal["node", "edge", "lineage"]
    ) -> dict:
        """
        Return the dictionary of features corresponding to the specified type.

        Parameters
        ----------
        feat_type : Literal["node", "edge", "lineage"]
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
        if not check_literal_type(feat_type, FeatureType):
            raise ValueError(
                f"Feature type must be one of {', '.join(FeatureType.__args__)}."
            )
        feats_dict = {
            k: v for k, v in self.feats_dict.items() if feat_type in v.feat_type
        }
        return feats_dict

    def _add_feature(self, feature: Feature) -> None:
        """
        Add the specified feature to the FeaturesDeclaration.

        Parameters
        ----------
        feature : Feature
            The feature to add.

        Raises
        ------
        ValueError
            If the feature type is invalid.
        ValueError
            If a feature with the same name already exists.
        """
        if feature.name in self.feats_dict:
            # TODO: a warning would be more appropriate here so it doesn't
            # block execution.
            raise ValueError(
                f"A Feature called {feature.name} already exists in "
                f"the declared features."
            )
        self.feats_dict[feature.name] = feature

    def _add_features(
        self,
        features: list[Feature],
    ) -> None:
        """
        Add the specified features to the FeaturesDeclaration.

        Parameters
        ----------
        features : list[Feature]
            The features to add.
        """
        for feature in features:
            self._add_feature(feature)

    def _add_cycle_lineage_features(self) -> None:
        """
        Add the basic features of cell cycle lineages.
        """
        common_fields = {
            "feat_type": "cycle",
            "lineage_type": "CycleLineage",
            "data_type": "int",
            "provenance": "Pycellin",
        }

        # Node features.
        # TODO: should add these features to features.utils
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
            description=(
                "Node IDs of the cells in the cell cycle, in chronological order."
            ),
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
        self._add_features([feat_ID, feat_cells, feat_length, feat_level])

        # We don't need to add the lineage_ID feature to the lineage features
        # since it is already present in the cell lineage features.
        # TODO: Lineage should be a valid choice of lin_type.

    def _remove_feature(
        self, feature_name: str, feature_type: Literal["node", "edge", "lineage"]
    ) -> None:
        """
        Remove the specified feature from the FeaturesDeclaration.

        Parameters
        ----------
        feature_name : str
            The name of the feature to remove.
        feature_type : Literal["node", "edge", "lineage"]
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
        self,
        feature_names: list[str],
        feature_types: list[Literal["node", "edge", "lineage"]],
    ) -> None:
        """
        Remove the specified features from the FeaturesDeclaration.

        Parameters
        ----------
        feature_names : list[str]
            The names of the features to remove.
        feature_types : list[Literal["node", "edge", "lineage"]]
            The types of the features to remove (node, edge, or lineage).
        """
        for feature_name, feature_type in zip(feature_names, feature_types):
            self._remove_feature(feature_name, feature_type)

    def _rename_feature(
        self,
        feature_name: str,
        new_name: str,
        feature_type: Literal["node", "edge", "lineage"],
    ) -> None:
        """
        Rename a specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature to rename.
        new_name : str
            The new name for the feature.
        feature_type : Literal["node", "edge", "lineage"]
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
        self,
        feature_name: str,
        new_description: str,
        feature_type: Literal["node", "edge", "lineage"],
    ) -> None:
        """
        Modify the description of a specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature whose description is to be modified.
        new_description : str
            The new description for the feature.
        feature_type : Literal["node", "edge", "lineage"]
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

    def _get_units_per_features(self) -> dict[str, list[str]]:
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
