#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import get_args
import warnings

from pycellin.custom_types import FeatureType, LineageType
from pycellin.utils import check_literal_type


class Feature:
    """ """

    def __init__(
        self,
        identifier: str,
        name: str,
        description: str,
        provenance: str,
        feat_type: FeatureType,
        lin_type: LineageType,
        dtype: str,
        unit: str | None = None,
    ) -> None:
        """
        Constructs all the necessary attributes for the Feature object.

        Parameters
        ----------
        identifier : str
            A unique identifier for the feature.
        name : str
            A human-readable name for the feature.
        description : str
            A description of the feature.
        provenance : str
            The provenance of the feature (TrackMate, CTC, pycellin, custom...).
        feat_type : FeatureType
            The type of the feature: `node`, `edge` or `lineage.
        lin_type : LineageType
            The type of lineage the feature is associated with: `CellLineage`,
            `CycleLineage`, or `Lineage` for both.
        dtype : str
            The data type of the feature (int, float, string).
        unit : str, optional
            The unit of the feature (e.g. µm, min, cell).

        Raises
        ------
        ValueError
            If the feature type or the lineage type is not a valid value.
        """
        self.identifier = identifier
        self.name = name
        self.description = description
        self.provenance = provenance
        if not check_literal_type(feat_type, FeatureType):
            raise ValueError(f"Feature type must be one of {', '.join(get_args(FeatureType))}.")
        self.feat_type = feat_type
        if not check_literal_type(lin_type, LineageType):
            raise ValueError(f"Lineage type must be one of {', '.join(get_args(LineageType))}.")
        self.lin_type = lin_type
        self.dtype = dtype
        self.unit = unit

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Feature):
            return NotImplemented
        return (
            self.identifier == other.identifier
            and self.name == other.name
            and self.description == other.description
            and self.provenance == other.provenance
            and self.feat_type == other.feat_type
            and self.lin_type == other.lin_type
            and self.dtype == other.dtype
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
            f"Feature(identifier={self.identifier!r}, name={self.name!r}, "
            f"description={self.description!r}, provenance={self.provenance!r}, "
            f"feat_type={self.feat_type!r}, lin_type={self.lin_type!r}, "
            f"dtype={self.dtype!r}, unit={self.unit!r})"
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
            f"Feature '{self.identifier}'\n"
            f"  Name: {self.name}\n"
            f"  Description: {self.description}\n"
            f"  Provenance: {self.provenance}\n"
            f"  Type: {self.feat_type}\n"
            f"  Lineage type: {self.lin_type}\n"
            f"  Data type: {self.dtype}\n"
            f"  Unit: {self.unit}"
        )
        return string

    def _change_identifier(self, new_identifier: str) -> None:
        """
        Change the identifier of the feature.

        Parameters
        ----------
        new_identifier : str
            The new identifier of the feature.

        Raises
        ------
        ValueError
            If the new identifier is not a string.
        """
        if not isinstance(new_identifier, str):
            raise ValueError("Feature identifier must be a string.")
        self.identifier = new_identifier

    def _change_name(self, new_name: str) -> None:
        """
        Change the name of the feature.

        Parameters
        ----------
        new_name : str
            The new name of the feature.

        Raises
        ------
        ValueError
            If the new name is not a string.
        """
        if not isinstance(new_name, str):
            raise ValueError("Feature name must be a string.")
        self.name = new_name

    def _change_description(self, new_description: str) -> None:
        """
        Change the description of the feature.

        Parameters
        ----------
        new_description : str
            The new description of the feature.

        Raises
        ------
        ValueError
            If the new description is not a string.
        """
        if not isinstance(new_description, str):
            raise ValueError("Feature description must be a string.")
        self.description = new_description

    def _change_provenance(self, new_provenance: str) -> None:
        """
        Change the provenance of the feature.

        Parameters
        ----------
        new_provenance : str
            The new provenance of the feature.

        Raises
        ------
        ValueError
            If the new provenance is not a string.
        """
        if not isinstance(new_provenance, str):
            raise ValueError("Feature provenance must be a string.")
        self.provenance = new_provenance

    # Is this really needed?
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
        if not isinstance(other, Feature):
            return NotImplemented
        if ignore_feat_type:
            return (
                self.identifier == other.identifier
                and self.description == other.description
                and self.provenance == other.provenance
                and self.lin_type == other.lin_type
                and self.dtype == other.dtype
                and self.unit == other.unit
            )
        else:
            return self == other


def frame_Feature(provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier="frame",
        name="frame",
        description="Frame number of the cell ",
        provenance=provenance,
        feat_type="node",
        lin_type="CellLineage",
        dtype="int",
        unit="frame",
    )
    return feat


def cell_ID_Feature(provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier="cell_ID",
        name="cell ID",
        description="Unique identifier of the cell",
        provenance=provenance,
        feat_type="node",
        lin_type="CellLineage",
        dtype="int",
    )
    return feat


def lineage_ID_Feature(provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier="lineage_ID",
        name="lineage ID",
        description="Unique identifier of the lineage",
        provenance=provenance,
        feat_type="lineage",
        lin_type="Lineage",
        dtype="int",
    )
    return feat


def cell_coord_Feature(unit: str, axis: str, provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier=f"cell_{axis}",
        name=f"cell {axis}",
        description=f"{axis.upper()} coordinate of the cell",
        provenance=provenance,
        feat_type="node",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )
    return feat


def link_coord_Feature(unit: str, axis: str, provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier=f"link_{axis}",
        name=f"link {axis}",
        description=(
            f"{axis.upper()} coordinate of the link, i.e. mean coordinate of its two cells"
        ),
        provenance=provenance,
        feat_type="edge",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )
    return feat


def lineage_coord_Feature(unit: str, axis: str, provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier=f"lineage_{axis}",
        name=f"lineage {axis}",
        description=(
            f"{axis.upper()} coordinate of the lineage, i.e. mean coordinate of its cells"
        ),
        provenance=provenance,
        feat_type="lineage",
        lin_type="CellLineage",
        dtype="float",
        unit=unit,
    )
    return feat


def cycle_ID_Feature(provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier="cycle_ID",
        name="cycle ID",
        description=(
            "Unique identifier of the cell cycle, i.e. cell_ID of the last cell in the cell cycle"
        ),
        provenance=provenance,
        feat_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )
    return feat


def cells_Feature(provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier="cells",
        name="cells",
        description="cell_IDs of the cells in the cell cycle, in chronological order",
        provenance=provenance,
        feat_type="node",
        lin_type="CycleLineage",
        dtype="list[int]",
    )
    return feat


def cycle_length_Feature(provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier="cycle_length",
        name="cycle length",
        description="Number of cells in the cell cycle, minding gaps",
        provenance=provenance,
        feat_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )
    return feat


def cycle_duration_Feature(provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier="cycle_duration",
        name="cycle duration",
        description="Number of frames in the cell cycle, regardless of gaps",
        provenance=provenance,
        feat_type="node",
        lin_type="CycleLineage",
        dtype="int",
        unit="frame",
    )
    return feat


def level_Feature(provenance: str = "pycellin") -> Feature:
    feat = Feature(
        identifier="level",
        name="level",
        description=(
            "Level of the cell cycle in the lineage, "
            "i.e. number of cell cycles upstream of the current one"
        ),
        provenance=provenance,
        feat_type="node",
        lin_type="CycleLineage",
        dtype="int",
    )
    return feat


class FeaturesDeclaration:
    """
    The FeaturesDeclaration class is used to store the features that are
    associated with the nodes, edges, and lineages of cell lineage graphs.

    Attributes
    ----------
    feats_dict : dict[str, Feature]
        A dictionary of features where the keys are the feature identifiers and
        the values are the Feature objects.
    protected_feats : list[str]
        A list of feature identifiers that are protected from being modified or removed.

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
        self.feats_dict = feats_dict if feats_dict is not None else {}
        self._protected_feats = protected_feats if protected_feats is not None else []
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
        feat_id: str,
    ) -> bool:
        """
        Check if the FeaturesDeclaration contains the specified feature.

        Parameters
        ----------
        feat_id : str
            The identifier of the feature to check.

        Returns
        -------
        bool
            True if the feature has been declared, False otherwise.
        """
        if feat_id in self.feats_dict:
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
            raise ValueError(f"Feature type must be one of {', '.join(get_args(FeatureType))}.")
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
            raise ValueError(f"Lineage type must be one of {', '.join(get_args(LineageType))}.")
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

    def _add_feature(self, feature: Feature, overwrite: bool = False) -> None:
        """
        Add the specified feature to the FeaturesDeclaration.

        Parameters
        ----------
        feature : Feature
            The feature to add.
        overwrite : bool, optional
            Whether to overwrite an existing feature with the same identifier.
            If False (default), existing features will not be overwritten but a
            warning will be issued. If True, existing features will be overwritten.

        Warns
        -----
        UserWarning
            If a feature with the same identifier already exists and overwrite=True.
            The existing feature will be overwritten.
        UserWarning
            If a feature with the same identifier already exists and overwrite=False.
            The existing feature will NOT be overwritten.
        """
        if feature.identifier in self.feats_dict:
            old_feat = self.feats_dict[feature.identifier]
            if feature.feat_type == old_feat.feat_type:
                txt = "with the same type"
            else:
                txt = "with a different type"

            if overwrite:
                msg = f"A Feature '{feature.identifier}' already exists {txt}. Overwriting the old Feature."
                warnings.warn(msg, stacklevel=2)
                self.feats_dict[feature.identifier] = feature
            else:
                msg = f"A Feature '{feature.identifier}' already exists {txt}. Not overwriting the old Feature."
                warnings.warn(msg, stacklevel=2)
        else:
            self.feats_dict[feature.identifier] = feature

    def _add_features(
        self,
        features: list[Feature],
        overwrite: bool = False,
    ) -> None:
        """
        Add the specified features to the FeaturesDeclaration.

        Parameters
        ----------
        features : list[Feature]
            The features to add.
        overwrite : bool, optional
            Whether to overwrite existing features with the same identifier.
            If False (default), existing features will not be overwritten but a
            warning will be issued. If True, existing features will be overwritten.
        """
        for feature in features:
            self._add_feature(feature, overwrite=overwrite)

    def _add_cycle_lineage_features(self) -> None:
        """
        Add the basic features of cell cycle lineages.
        """
        feat_ID = cycle_ID_Feature()
        feat_cells = cells_Feature()
        feat_length = cycle_length_Feature()
        feat_duration = cycle_duration_Feature()
        feat_level = level_Feature()
        for feat in [feat_ID, feat_cells, feat_length, feat_duration, feat_level]:
            if feat.identifier not in self.feats_dict:
                self._add_feature(feat)
                self._protect_feature(feat.identifier)

    def _remove_feature(
        self,
        feat_id: str,
    ) -> None:
        """
        Remove the specified feature from the FeaturesDeclaration.

        Parameters
        ----------
        feat_id : str
            The identifier of the feature to remove.

        Raises
        ------
        ValueError
            If the feature type is invalid.
        UserWarning
            If the feature is protected and cannot be removed.
        """
        if feat_id not in self.feats_dict:
            raise KeyError(f"Feature '{feat_id}' does not exist in the declared features.")
        if feat_id in self._protected_feats:
            msg = (
                f"Feature '{feat_id}' is protected and cannot be removed. "
                "Unprotect the feature before modifying it."
            )
            warnings.warn(msg)
        else:
            del self.feats_dict[feat_id]

    def _remove_features(
        self,
        feat_ids: list[str],
    ) -> None:
        """
        Remove the specified features from the FeaturesDeclaration.

        Parameters
        ----------
        feat_ids : list[str]
            The identifiers of the features to remove.
        """
        for feat_id in feat_ids:
            self._remove_feature(feat_id)

    def _change_feature_identifier(
        self,
        feat_id: str,
        new_id: str,
    ) -> None:
        """
        Change the identifier of a specified feature.

        Parameters
        ----------
        feat_id : str
            The current identifier of the feature.
        new_id : str
            The new identifier for the feature.

        Raises
        ------
        KeyError
            If the feature does not exist in the declared features.
        UserWarning
            If the feature is protected and cannot be modified.
        """
        if feat_id not in self.feats_dict:
            raise KeyError(f"Feature '{feat_id}' does not exist in the declared features.")
        if feat_id in self._protected_feats:
            msg = (
                f"Feature '{feat_id}' is protected and cannot be modified. "
                "Unprotect the feature before modifying it."
            )
            warnings.warn(msg)
        else:
            self.feats_dict[new_id] = self.feats_dict.pop(feat_id)
            self.feats_dict[new_id]._change_identifier(new_id)

    def _change_feature_name(self, feat_id: str, new_name: str) -> None:
        """
        Change the name of a specified feature.

        Parameters
        ----------
        feat_id : str
            The identifier of the feature whose name is to be changed.
        new_name : str
            The new name for the feature.
        """
        if feat_id not in self.feats_dict:
            raise KeyError(f"Feature '{feat_id}' does not exist in the declared features.")
        if feat_id in self._protected_feats:
            msg = (
                f"Feature '{feat_id}' is protected and cannot be modified. "
                "Unprotect the feature before modifying it."
            )
            warnings.warn(msg)
        else:
            self.feats_dict[feat_id]._change_name(new_name)

    def _change_feature_description(
        self,
        feat_id: str,
        new_description: str,
    ) -> None:
        """
        Change the description of a specified feature.

        Parameters
        ----------
        feat_id : str
            The identifier of the feature whose description is to be changed.
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
        if feat_id not in self.feats_dict:
            raise KeyError(f"Feature '{feat_id}' does not exist in the declared features.")
        if feat_id in self._protected_feats:
            msg = (
                f"Feature '{feat_id}' is protected and cannot be modified. "
                "Unprotect the feature before modifying it."
            )
            warnings.warn(msg)
        else:
            self.feats_dict[feat_id]._change_description(new_description)

    def _protect_feature(self, feat_id: str) -> None:
        """
        Protect the specified feature from being modified or removed.

        Parameters
        ----------
        feat_id : str
            The identifier of the feature to protect.

        Raises
        ------
        UserWarning
            If the feature does not exist in the declared features.
        """
        if feat_id not in self.feats_dict:
            msg = (
                f"Feature '{feat_id}' does not exist in the declared features "
                "and cannot be protected."
            )
            warnings.warn(msg)

        if feat_id not in self._protected_feats:
            self._protected_feats.append(feat_id)

    def _unprotect_feature(self, feat_id: str) -> None:
        """
        Unprotect the specified feature.

        Parameters
        ----------
        feat_id : str
            The identifier of the feature to unprotect.

        Raises
        ------
        UserWarning
            If the feature does not exist in the declared features.
        """
        if feat_id not in self.feats_dict:
            msg = (
                f"Feature '{feat_id}' does not exist in the declared features "
                "and cannot be unprotected."
            )
            warnings.warn(msg)

        if feat_id in self._protected_feats:
            self._protected_feats.remove(feat_id)

    def _get_units_per_features(self) -> dict[str, list[str]]:
        """
        Return a dict of units and the features associated with each unit.

        The method iterates over the node, edge, and lineage features
        of the features declaration object, grouping them by unit.

        Returns
        -------
        dict[str, list[str]]
            A dictionary where the keys are units and the values are lists
            of feature identifiers. For example:
            {'unit1': ['feature1', 'feature2'], 'unit2': ['feature3']}.
        """
        units = {}  # type: dict[str, list[str]]
        for feat in self.feats_dict.values():
            if feat.unit in units:
                units[feat.unit].append(feat.identifier)
            else:
                units[feat.unit] = [feat.identifier]
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
    fd._remove_feature("lineage_ID")
    # for k, v in fd.feats_dict.items():
    #     print(k, v)

    # Remove feat with type, but last type so in fact remove feat
    fd._remove_feature("lineage_ID")
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
    fd._change_feature_identifier("cell_ID", "cell_ID_new")
    # print(fd.feats_dict.keys(), fd.feats_dict["cell_ID_new"].name)

    # Modify description
    fd._change_feature_description("cell_ID_new", "New description")
    # print(fd.feats_dict["cell_ID_new"])

    print(cell_ID_Feature().is_equal(cell_ID_Feature()))
    print(cell_ID_Feature().is_equal(lineage_ID_Feature()))
