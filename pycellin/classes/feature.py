#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import warnings

from pycellin.custom_types import FeatureType, LineageType
from pycellin.utils import check_literal_type


class Feature:
    """ """

    def __init__(
        self,
        name: str,
        description: str,
        provenance: str,
        feat_type: str,
        lin_type: LineageType,
        data_type: str,
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
        lin_type : LineageType
            The type of lineage the feature is associated with: cell lineage,
            cell cycle lineage or both.
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
        self.provenance = provenance
        self.feat_type = feat_type
        self.lin_type = lin_type
        self.data_type = data_type
        self.unit = unit

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Feature):
            return NotImplemented
        return (
            self.name == other.name
            and self.description == other.description
            and self.provenance == other.provenance
            and self.feat_type == other.feat_type
            and self.lin_type == other.lin_type
            and self.data_type == other.data_type
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
            f"provenance={self.provenance!r}, feat_type={self.feat_type!r}, "
            f"lin_type={self.lin_type!r}, data_type={self.data_type!r}, "
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
        string = (
            f"Feature '{self.name}'\n"
            f"  Description: {self.description}\n"
            f"  Provenance: {self.provenance}\n"
            f"  Type: {self.feat_type}\n"
            f"  Lineage type: {self.lin_type}\n"
            f"  Data type: {self.data_type}\n"
            f"  Unit: {self.unit}"
        )
        return string

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

    def is_equal(self, other: Feature, ignore_feat_type: bool = False) -> bool:
        """
        Check if the feature is equal to another feature.

        Parameters
        ----------
        other : Feature
            The other feature to compare with.
        ignore_feat_type : bool, optional
            Whether to ignore the feature type when comparing the features.

        Returns
        -------
        bool
            True if the features are equal, False otherwise.
        """
        if ignore_feat_type:
            return (
                self.name == other.name
                and self.description == other.description
                and self.provenance == other.provenance
                and self.lin_type == other.lin_type
                and self.data_type == other.data_type
                and self.unit == other.unit
            )
        else:
            return self == other


def frame_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="frame",
        description="Frame number of the cell ",
        provenance=provenance,
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
        unit="frame",
    )
    return feat


def cell_ID_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="cell_ID",
        description="Unique identifier of the cell",
        provenance=provenance,
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
    )
    return feat


def lineage_ID_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="lineage_ID",
        description="Unique identifier of the lineage",
        provenance=provenance,
        feat_type="lineage",
        lin_type="Lineage",
        data_type="int",
    )
    return feat


def cell_coord_Feature(unit: str, axis: str, provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name=f"cell_{axis}",
        description=f"{axis.upper()} coordinate of the cell",
        provenance=provenance,
        feat_type="node",
        lin_type="CellLineage",
        data_type="float",
        unit=unit,
    )
    return feat


def link_coord_Feature(unit: str, axis: str, provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name=f"link_{axis}",
        description=(
            f"{axis.upper()} coordinate of the link, "
            f"i.e. mean coordinate of its two cells"
        ),
        provenance=provenance,
        feat_type="edge",
        lin_type="CellLineage",
        data_type="float",
        unit=unit,
    )
    return feat


def lineage_coord_Feature(
    unit: str, axis: str, provenance: str = "Pycellin"
) -> Feature:
    feat = Feature(
        name=f"lineage_{axis}",
        description=(
            f"{axis.upper()} coordinate of the lineage, "
            f"i.e. mean coordinate of its cells"
        ),
        provenance=provenance,
        feat_type="lineage",
        lin_type="CellLineage",
        data_type="float",
        unit=unit,
    )
    return feat


def cycle_ID_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="cycle_ID",
        description=(
            "Unique identifier of the cell cycle, "
            "i.e. cell_ID of the last cell in the cell cycle"
        ),
        provenance=provenance,
        feat_type="node",
        lin_type="CycleLineage",
        data_type="int",
    )
    return feat


def cells_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="cells",
        description="cell_IDs of the cells in the cell cycle, in chronological order",
        provenance=provenance,
        feat_type="node",
        lin_type="CycleLineage",
        data_type="int",
    )
    return feat


def cycle_length_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="cycle_length",
        description="Number of cells in the cell cycle",
        provenance=provenance,
        feat_type="node",
        lin_type="CycleLineage",
        data_type="int",
    )
    return feat


# TODO: define_cycle_duration_Feature


def level_Feature(provenance: str = "Pycellin") -> Feature:
    feat = Feature(
        name="level",
        description=(
            "Level of the cell cycle in the lineage, "
            "i.e. number of cell cycles upstream of the current one"
        ),
        provenance=provenance,
        feat_type="node",
        lin_type="CycleLineage",
        data_type="int",
    )
    return feat


class FeaturesDeclaration:
    """
    The FeaturesDeclaration class is used to store the features that are
    associated with the nodes, edges, and lineages of cell lineage graphs.

    Attributes
    ----------
    feats_dict : dict[str, Feature]
        A dictionary of features where the keys are the feature names and
        the values are the Feature objects.
    protected_feats : list[str]
        A list of feature names that are protected from being modified or removed.

    Notes
    -----
    Spatial and temporal units are not part of the FeaturesDeclaration but of the
    features themselves to allow different units for a same dimension (e.g. time
    in seconds or minutes).
    """

    def __init__(
        self,
        feats_dict: dict[str, Feature] | None = None,
        protected_feats: list[str] | None = None,
    ) -> None:
        self.feats_dict = feats_dict if feats_dict else {}
        self._protected_feats = protected_feats if protected_feats else []
        for feat in self._protected_feats:
            if feat not in self.feats_dict:
                msg = (
                    f"Protected feature '{feat}' does not exist in the declared "
                    "features. Removing it from the list of protected features."
                )
                warnings.warn(msg)
                self._protected_feats.remove(feat)

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
        node_feats = ", ".join(self._get_feat_dict_from_feat_type("node").keys())
        edge_feats = ", ".join(self._get_feat_dict_from_feat_type("edge").keys())
        lin_feats = ", ".join(self._get_feat_dict_from_feat_type("lineage").keys())
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
        """
        if feature_name in self.feats_dict:
            return True
        else:
            return False

    def _get_feat_dict_from_feat_type(self, feat_type: FeatureType) -> dict:
        """
        Return the dictionary of features corresponding to the specified type.

        Parameters
        ----------
        feat_type : FeatureType
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
        feats = {k: v for k, v in self.feats_dict.items() if feat_type == v.feat_type}
        return feats

    def _get_feat_dict_from_lin_type(self, lin_type: LineageType) -> dict:
        """
        Return the dictionary of features corresponding to the specified lineage type.

        Parameters
        ----------
        lin_type : LineageType
            The type of the lineage features to return (CellLineage,
            CycleLineage or Lineage).

        Returns
        -------
        dict
            The dictionary of features corresponding to the specified lineage type.

        Raises
        ------
        ValueError
            If the lineage type is invalid.
        """
        if not check_literal_type(lin_type, LineageType):
            raise ValueError(
                f"Lineage type must be one of {', '.join(LineageType.__args__)}."
            )
        feats = {k: v for k, v in self.feats_dict.items() if lin_type == v.lin_type}
        return feats

    def _get_protected_features(self) -> list[str]:
        """
        Return the list of protected features.

        Returns
        -------
        list[str]
            The list of protected features.
        """
        return self._protected_feats

    def _add_feature(self, feature: Feature) -> None:
        """
        Add the specified feature to the FeaturesDeclaration.

        Parameters
        ----------
        feature : Feature
            The feature to add.

        Raises
        ------
        UserWarning
            If an identical feature has already been declared.
        UserWarning
            If an identical feature has already been declared
            but with a different type.
        UserWarning
            If a feature with the same name has already been declared
            but with a different definition.
        UserWarning
            If a feature with the same name has already been declared
            but with a different type and definition.
        """
        if feature.name in self.feats_dict:
            old_feat = self.feats_dict[feature.name]

            if feature.is_equal(old_feat, ignore_feat_type=True):
                if feature.feat_type == old_feat.feat_type:
                    msg = (
                        f"An identical Feature '{feature.name}' "
                        f"has already been declared."
                    )
                    warnings.warn(msg)
                else:
                    msg = (
                        f"An identical Feature '{feature.name}' has already been "
                        f"declared but with a different type ({old_feat.feat_type}). "
                        f"The feature will be overwritten."
                    )
                    warnings.warn(msg)
                    self.feats_dict[feature.name] = feature
            else:
                if feature.feat_type == old_feat.feat_type:
                    msg = (
                        f"A Feature called '{feature.name}' has already been declared "
                        f"but with a different definition. "
                        f"The feature will be overwritten."
                    )
                    warnings.warn(msg)
                    self.feats_dict[feature.name] = feature
                else:
                    msg = (
                        f"A Feature called '{feature.name}' has already been declared "
                        f"but with a different type ({old_feat.feat_type}) "
                        f"and definition. The feature will be overwritten."
                    )
                    warnings.warn(msg)
                    self.feats_dict[feature.name] = feature
        else:
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
        feat_ID = cycle_ID_Feature()
        feat_cells = cells_Feature()
        feat_length = cycle_length_Feature()
        feat_level = level_Feature()
        for feat in [feat_ID, feat_cells, feat_length, feat_level]:
            if feat.name not in self.feats_dict:
                self._add_feature(feat)
                self._protect_feature(feat.name)

    def _remove_feature(
        self,
        feature_name: str,
    ) -> None:
        """
        Remove the specified feature from the FeaturesDeclaration.

        Parameters
        ----------
        feature_name : str
            The name of the feature to remove.

        Raises
        ------
        ValueError
            If the feature type is invalid.
        UserWarning
            If the feature is protected and cannot be removed.
        """
        if feature_name not in self.feats_dict:
            raise KeyError(
                f"Feature '{feature_name}' does not exist in the declared features."
            )
        if feature_name in self._protected_feats:
            msg = (
                f"Feature '{feature_name}' is protected and cannot be removed. "
                "Unprotect the feature before modifying it."
            )
            warnings.warn(msg)
        else:
            del self.feats_dict[feature_name]

    def _remove_features(
        self,
        feature_names: list[str],
    ) -> None:
        """
        Remove the specified features from the FeaturesDeclaration.

        Parameters
        ----------
        feature_names : list[str]
            The names of the features to remove.
        """
        for feature_name in feature_names:
            self._remove_feature(feature_name)

    def _rename_feature(
        self,
        feature_name: str,
        new_name: str,
    ) -> None:
        """
        Rename a specified feature.

        Parameters
        ----------
        feature_name : str
            The current name of the feature to rename.
        new_name : str
            The new name for the feature.

        Raises
        ------
        KeyError
            If the feature does not exist in the declared features.
        UserWarning
            If the feature is protected and cannot be modified.
        """
        if feature_name not in self.feats_dict:
            raise KeyError(
                f"Feature '{feature_name}' does not exist in the declared features."
            )
        if feature_name in self._protected_feats:
            msg = (
                f"Feature '{feature_name}' is protected and cannot be modified. "
                "Unprotect the feature before modifying it."
            )
            warnings.warn(msg)
        else:
            self.feats_dict[new_name] = self.feats_dict.pop(feature_name)
            self.feats_dict[new_name]._rename(new_name)

    def _modify_feature_description(
        self,
        feature_name: str,
        new_description: str,
    ) -> None:
        """
        Modify the description of a specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature whose description is to be modified.
        new_description : str
            The new description for the feature.

        Raises
        ------
        KeyError
            If the feature does not exist in the declared features.
        UserWarning
            If the feature is protected and cannot be modified
            (i.e. it is in the list of protected features).
        """
        if feature_name not in self.feats_dict:
            raise KeyError(
                f"Feature '{feature_name}' does not exist in the declared features."
            )
        if feature_name in self._protected_feats:
            msg = (
                f"Feature '{feature_name}' is protected and cannot be modified. "
                "Unprotect the feature before modifying it."
            )
            warnings.warn(msg)
        else:
            self.feats_dict[feature_name]._modify_description(new_description)

    def _protect_feature(self, feature_name: str) -> None:
        """
        Protect the specified feature from being modified or removed.

        Parameters
        ----------
        feature_name : str
            The name of the feature to protect.

        Raises
        ------
        UserWarning
            If the feature does not exist in the declared features.
        """
        if feature_name not in self.feats_dict:
            msg = (
                f"Feature '{feature_name}' does not exist in the declared features "
                "and cannot be protected."
            )
            warnings.warn(msg)

        if feature_name not in self._protected_feats:
            self._protected_feats.append(feature_name)

    def _unprotect_feature(self, feature_name: str) -> None:
        """
        Unprotect the specified feature.

        Parameters
        ----------
        feature_name : str
            The name of the feature to unprotect.

        Raises
        ------
        UserWarning
            If the feature does not exist in the declared features.
        """
        if feature_name not in self.feats_dict:
            msg = (
                f"Feature '{feature_name}' does not exist in the declared features "
                "and cannot be unprotected."
            )
            warnings.warn(msg)

        if feature_name in self._protected_feats:
            self._protected_feats.remove(feature_name)

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
        for feat in self.feats_dict.values():
            if feat.unit in units:
                units[feat.unit].append(feat.name)
            else:
                units[feat.unit] = [feat.name]
        return units


if __name__ == "__main__":

    # Basic testing of the Feature and FeaturesDeclaration classes.
    # TODO: do this properly in test_feature.py.

    # Add features
    fd = FeaturesDeclaration()
    fd._add_feature(cell_ID_Feature())
    fd._add_features(
        [
            frame_Feature(),
            lineage_ID_Feature(),
        ]
    )
    # for k, v in fd.feats_dict.items():
    #     print(k, v)

    # Add identical feature
    fd._add_feature(cell_ID_Feature())
    print()

    # Add different type feature
    tmp_feat = cell_ID_Feature()
    tmp_feat.feat_type = "edge"
    print(tmp_feat)
    fd._add_feature(tmp_feat)
    print(fd.feats_dict["cell_ID"])

    # Add different definition feature
    tmp_feat = cell_ID_Feature()
    tmp_feat.description = "new description"
    fd._add_feature(tmp_feat)
    print(fd.feats_dict["cell_ID"])

    # Get feats dict
    # print(fd.get_node_feats().keys())
    # print(fd.get_edge_feats().keys())
    # print(fd.get_lin_feats().keys())

    # Remove feat
    fd._remove_feature("frame")
    # print(fd.feats_dict.keys())

    # Remove feat with type
    fd._remove_feature("lineage_ID", "node")
    # for k, v in fd.feats_dict.items():
    #     print(k, v)

    # Remove feat with type, but last type so in fact remove feat
    fd._remove_feature("lineage_ID", "lineage")
    # print(fd.feats_dict.keys())

    # Remove feat with multi type
    fd._add_feature(lineage_ID_Feature())
    fd._remove_feature("lineage_ID")
    # print(fd.feats_dict.keys())

    # Invalid feat name
    # fd._remove_feature("cel_ID")

    # Invalid feat type
    # fd._remove_feature("cell_ID", "nod")

    # Rename feature
    fd._rename_feature("cell_ID", "cell_ID_new")
    # print(fd.feats_dict.keys(), fd.feats_dict["cell_ID_new"].name)

    # Modify description
    fd._modify_feature_description("cell_ID_new", "New description")
    # print(fd.feats_dict["cell_ID_new"])

    print(cell_ID_Feature().is_equal(cell_ID_Feature()))
    print(cell_ID_Feature().is_equal(lineage_ID_Feature()))
