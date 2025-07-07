#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Features in the XML file are not in the same order as a file that was exported
directly from TrackMate.
I've tested quickly and it doesn't seem to be a problem for TrackMate.
"""

import copy
import math
import numbers
import re
from typing import Any
import warnings

from lxml import etree as ET
import networkx as nx

from pycellin.classes.exceptions import ProtectedFeatureError
from pycellin.classes.model import Model
from pycellin.classes.feature import FeaturesDeclaration, Feature
from pycellin.classes.lineage import CellLineage
from pycellin.io.trackmate.loader import load_TrackMate_XML


def _unit_to_dimension(
    feat: Feature,
) -> str:
    """
    Convert a unit to a dimension.

    Parameters
    ----------
    unit : str
        Unit to convert.

    Returns
    -------
    str
        Dimension corresponding to the unit.

    Warns
    -----
    UserWarning
        If the unit is not recognized or if the feature is not recognized.
    """
    # TODO: finish this function and try to make it less nightmarish
    unit = feat.unit
    name = feat.name
    # desc = feat.description
    provenance = feat.provenance

    # TrackMate features
    # Mapping between TrackMate features and their dimensions.
    trackmate_feats = {
        # Spot features
        "QUALITY": "QUALITY",
        "POSITION_X": "POSITION",
        "POSITION_Y": "POSITION",
        "POSITION_Z": "POSITION",
        "POSITION_T": "TIME",
        "FRAME": "NONE",
        "RADIUS": "LENGTH",
        "VISIBILITY": "NONE",
        "MANUAL_SPOT_COLOR": "NONE",
        "ELLIPSE_X0": "LENGTH",
        "ELLIPSE_Y0": "LENGTH",
        "ELLIPSE_MAJOR": "LENGTH",
        "ELLIPSE_MINOR": "LENGTH",
        "ELLIPSE_THETA": "ANGLE",
        "ELLIPSE_ASPECTRATIO": "NONE",
        "AREA": "AREA",
        "PERIMETER": "LENGTH",
        "CIRCULARITY": "NONE",
        "SOLIDITY": "NONE",
        "SHAPE_INDEX": "NONE",
        # Edge features
        "SPOT_SOURCE_ID": "NONE",
        "SPOT_TARGET_ID": "NONE",
        "LINK_COST": "COST",
        "DIRECTIONAL_CHANGE_RATE": "ANGLE_RATE",
        "SPEED": "VELOCITY",
        "DISPLACEMENT": "LENGTH",
        "EDGE_TIME": "TIME",
        "EDGE_X_LOCATION": "POSITION",
        "EDGE_Y_LOCATION": "POSITION",
        "EDGE_Z_LOCATION": "POSITION",
        "MANUAL_EDGE_COLOR": "NONE",
        # Track features
        "TRACK_INDEX": "NONE",
        "TRACK_ID": "NONE",
        "NUMBER_SPOTS": "NONE",
        "NUMBER_GAPS": "NONE",
        "NUMBER_SPLITS": "NONE",
        "NUMBER_MERGES": "NONE",
        "NUMBER_COMPLEX": "NONE",
        "LONGEST_GAP": "NONE",
        "TRACK_DURATION": "TIME",
        "TRACK_START": "TIME",
        "TRACK_STOP": "TIME",
        "TRACK_DISPLACEMENT": "LENGTH",
        "TRACK_X_LOCATION": "POSITION",
        "TRACK_Y_LOCATION": "POSITION",
        "TRACK_Z_LOCATION": "POSITION",
        "TRACK_MEAN_SPEED": "VELOCITY",
        "TRACK_MAX_SPEED": "VELOCITY",
        "TRACK_MIN_SPEED": "VELOCITY",
        "TRACK_MEDIAN_SPEED": "VELOCITY",
        "TRACK_STD_SPEED": "VELOCITY",
        "TRACK_MEAN_QUALITY": "QUALITY",
        "TOTAL_DISTANCE_TRAVELED": "LENGTH",
        "MAX_DISTANCE_TRAVELED": "LENGTH",
        "MEAN_STRAIGHT_LINE_SPEED": "VELOCITY",
        "LINEARITY_OF_FORWARD_PROGRESSION": "NONE",
        "MEAN_DIRECTIONAL_CHANGE_RATE": "ANGLE_RATE",
        "DIVISION_TIME_MEAN": "TIME",
        "DIVISION_TIME_STD": "TIME",
        "CONFINEMENT_RATIO": "NONE",
    }
    # Channel dependent features.
    channel_feats = {
        "MEAN_INTENSITY_CH": "INTENSITY",
        "MEDIAN_INTENSITY_CH": "INTENSITY",
        "MIN_INTENSITY_CH": "INTENSITY",
        "MAX_INTENSITY_CH": "INTENSITY",
        "TOTAL_INTENSITY_CH": "INTENSITY",
        "STD_INTENSITY_CH": "INTENSITY",
        "CONTRAST_CH": "NONE",
        "SNR_CH": "NONE",
    }

    # Pycellin features.
    pycellin_feats = {
        # Cell features.
        "angle": "ANGLE",
        "cell_displacement": "LENGTH",
        "cell_length": "LENGTH",
        "cell_speed": "VELOCITY",
        "cell_width": "LENGTH",
        # Cycle features.
        "branch_total_displacement": "LENGTH",
        "branch_mean_displacement": "LENGTH",
        "branch_mean_speed": "VELOCITY",
        "cells": "NONE",
        "cycle_completeness": "NONE",
        "cycle_duration": "NONE",
        "cycle_ID": "NONE",
        "cycle_length": "NONE",
        "division_time": "TIME",
        "division_rate": "TIME",  # TODO: check if this is correct
        "level": "NONE",
        "straightness": "NONE",
    }
    if name == "absolute_age":
        if unit == "frame":
            pycellin_feats["absolute_age"] = "NONE"
        else:
            pycellin_feats["absolute_age"] = "TIME"
    elif name == "relative_age":
        if unit == "frame":
            pycellin_feats["relative_age"] = "NONE"
        else:
            pycellin_feats["relative_age"] = "TIME"

    if name in trackmate_feats:
        dimension = trackmate_feats[name]

    elif provenance == "TrackMate":
        if name in trackmate_feats:
            dimension = trackmate_feats[name]
        else:
            dimension = None
            for key, dim in channel_feats.items():
                if name.startswith(key):
                    dimension = dim
                    break
            if dimension is None:
                msg = (
                    f"'{name}' is a feature listed as coming from TrackMate"
                    f" but it is not a known feature of TrackMate. Dimension is set"
                    f" to NONE."
                )
                warnings.warn(msg)
                # I'm using NONE here, which is already used in TM, for example
                # with the FRAME or VISIBILITY features. I tried to use UNKNOWN
                # but it's a dimension not recognized by TM and it crashes.
                dimension = "NONE"

    elif provenance == "pycellin":
        try:
            dimension = pycellin_feats[name]
        except KeyError:
            try:
                dimension = trackmate_feats[name]
            except KeyError:
                msg = (
                    f"'{name}' is a feature listed as coming from pycellin"
                    f" but it is not a known feature of either pycellin or TrackMate. "
                    f" Dimension is set to NONE."
                )
                warnings.warn(msg)
                dimension = "NONE"

    else:
        match unit:
            case "pixel":
                if name.lower() in ["x", "y", "z"]:
                    dimension = "POSITION"
                else:
                    dimension = "LENGTH"
            case "none" | "frame":
                dimension = "NONE"
        # TODO: It's going to be a nightmare to deal with all the possible cases.
        # Is it even possible? Maybe I could ask the user for a file with
        # a feature-dimension mapping. For now, I just set the dimension to NONE.
        msg = (
            f"Cannot infer dimension for feature '{name}'. "
            f"Dimension is set to NONE."
        )
        warnings.warn(msg)
        dimension = "NONE"

    assert dimension is not None
    return dimension


def _transform_name(name: str) -> str:
    """
    Transform a feature name to a more user-friendly format, close to TrackMate's.

    Parameters
    ----------
    name : str
        Name of the feature to transform.

    Returns
    -------
    str
        The transformed name.

    Notes
    -----
    The transformation consists in:
    - replacing underscores by spaces,
    - lowercasing the words, except for some exceptions,
    - capitalizing the first letter of the name,
    - handling specific cases for positions.
    """
    if name in ["POSITION_X", "POSITION_Y", "POSITION_Z", "POSITION_T"]:
        new_name = name[-1]
    elif name in ["EDGE_X_LOCATION", "EDGE_Y_LOCATION", "EDGE_Z_LOCATION"]:
        new_name = "Edge " + name.split("_")[1]
    elif name in ["TRACK_X_LOCATION", "TRACK_Y_LOCATION", "TRACK_Z_LOCATION"]:
        new_name = "Track mean " + name.split("_")[1]
    else:
        exceptions = {"X", "Y", "Z", "T", "ID", "SNR"}
        name = name.replace("_", " ")

        def transform_word(match):
            word = match.group(0)
            return word if word in exceptions else word.lower()

        new_name = re.sub(r"\b\w+\b", transform_word, name)
        new_name = new_name[0].upper() + new_name[1:]
    return new_name


def _convert_feature(
    feat: Feature,
) -> dict[str, str]:
    """
    Convert a pycellin feature to a TrackMate feature.

    Parameters
    ----------
    feat : Feature
        Feature to convert.

    Returns
    -------
    dict[str, str]
        Dictionary of the converted feature.
    """
    trackmate_feat = {}
    trackmate_feat["feature"] = feat.name
    # TrackMate uses the `name` attribute as the display name of the feature in the GUI.
    # So we need to convert the name to a more user-friendly format.
    trackmate_feat["name"] = _transform_name(feat.name)
    trackmate_feat["shortname"] = feat.name.lower()
    trackmate_feat["dimension"] = _unit_to_dimension(feat)
    if feat.data_type == "int":
        trackmate_feat["isint"] = "true"
    else:
        trackmate_feat["isint"] = "false"

    return trackmate_feat


def _write_FeatureDeclarations(
    xf: ET.xmlfile,
    model: Model,
) -> None:
    """
    Write the FeatureDeclarations XML tag into a TrackMate XML file.

    The features declaration is divided in three parts: spot features,
    edge features, and track features. But they are all processed
    in the same way.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    model : Model
        Model containing the data to write.
    """
    xf.write(f"\n{' '*4}")
    with xf.element("FeatureDeclarations"):
        features_type = ["SpotFeatures", "EdgeFeatures", "TrackFeatures"]
        for f_type in features_type:
            xf.write(f"\n{' '*6}")
            with xf.element(f_type):
                xf.write(f"\n{' '*8}")
                match f_type:
                    case "SpotFeatures":
                        features = model.get_node_features()
                    case "EdgeFeatures":
                        features = model.get_edge_features()
                    case "TrackFeatures":
                        features = model.get_lineage_features()
                first_feat_written = False
                for feat in features.values():
                    trackmate_feat = _convert_feature(feat)
                    if trackmate_feat:
                        if first_feat_written:
                            xf.write(f"\n{' '*8}")
                        else:
                            first_feat_written = True
                        xf.write(ET.Element("Feature", trackmate_feat))
                xf.write(f"\n{' '*6}")
        xf.write(f"\n{' '*4}")


def _value_to_str(
    value: Any,
) -> str:
    """
    Convert a value to its associated string.

    Indeed, ET.write() method only accepts to write strings.
    However, TrackMate is only able to read Spot, Edge and Track
    features that can be parsed as numeric by Java.

    Parameters
    ----------
    value : Any
        Value to convert to string.

    Returns
    -------
    str
        The string equivalent of `value`.
    """
    if isinstance(value, bool):
        return "1" if value else "0"
    elif isinstance(value, numbers.Number):
        if math.isnan(value):
            return "NaN"
        elif math.isinf(value):
            if value > 0:
                return "Infinity"
            else:
                return "-Infinity"
        else:
            return str(value)
    elif isinstance(value, str):
        return value
    else:
        return str(value)


def _create_Spot(
    lineage: CellLineage,
    node: int,
) -> ET._Element:
    """
    Create an XML Spot Element representing a node of a Lineage.

    Parameters
    ----------
    lineage : CellLineage
        Lineage containing the node to create.
    node : int
        ID of the node in the lineage.

    Returns
    -------
    ET._Element
        The newly created Spot Element.
    """
    exluded_keys = ["TRACK_ID", "ROI_coords"]
    n_attr = {
        k: _value_to_str(v)
        for k, v in lineage.nodes[node].items()
        if k not in exluded_keys
    }
    if "ROI_coords" in lineage.nodes[node]:
        n_attr["ROI_N_POINTS"] = str(len(lineage.nodes[node]["ROI_coords"]))
        # The text of a Spot is the coordinates of its ROI points, in a flattened list.
        coords = [item for pt in lineage.nodes[node]["ROI_coords"] for item in pt]
    else:
        # No segmentation mask, so we set the ROI_N_POINTS to 0.
        n_attr["ROI_N_POINTS"] = "0"

    el_node = ET.Element("Spot", n_attr)
    if "ROI_coords" in lineage.nodes[node]:
        el_node.text = " ".join(map(str, coords))
    return el_node


def _write_AllSpots(
    xf: ET.xmlfile,
    data: dict[int, CellLineage],
) -> None:
    """
    Write the nodes/spots data into an XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    data : dict[int, CellLineage]
        Cell lineages containing the data to write.
    """
    xf.write(f"\n{' '*4}")
    lineages = data.values()
    nb_nodes = sum([len(lin) for lin in lineages])
    with xf.element("AllSpots", {"nspots": str(nb_nodes)}):
        # For each frame, nodes can be spread over several lineages
        # so we first need to identify all of the existing frames.
        frames = set()  # type: set[int]
        for lin in lineages:
            frames.update(nx.get_node_attributes(lin, "FRAME").values())

        # Then at each frame, we can find the nodes and write its data.
        for frame in frames:
            xf.write(f"\n{' '*6}")
            with xf.element("SpotsInFrame", {"frame": str(frame)}):
                for lin in lineages:
                    nodes = [n for n in lin.nodes() if lin.nodes[n]["FRAME"] == frame]
                    for node in nodes:
                        xf.write(f"\n{' '*8}")
                        xf.write(_create_Spot(lin, node))
                xf.write(f"\n{' '*6}")
        xf.write(f"\n{' '*4}")


def _write_AllTracks(
    xf: ET.xmlfile,
    data: dict[int, CellLineage],
) -> None:
    """
    Write the tracks data into an XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    data : dict[int, CellLineage]
        Cell lineages containing the data to write.
    """
    xf.write(f"\n{' '*4}")
    with xf.element("AllTracks"):
        for lineage in data.values():
            # We have track tags to add only for tracks with several spots,
            # so one-node tracks are to be ignored. In pycellin, a one-node
            # lineage is identified by a negative ID.
            if lineage.graph["TRACK_ID"] < 0:
                continue

            # Track tags.
            xf.write(f"\n{' '*6}")
            exluded_keys = ["Model", "FilteredTrack"]
            t_attr = {
                k: _value_to_str(v)
                for k, v in lineage.graph.items()
                if k not in exluded_keys
            }
            with xf.element("Track", t_attr):
                # Edge tags.
                for edge in lineage.edges.data():
                    xf.write(f"\n{' '*8}")
                    e_attr = {k: _value_to_str(v) for k, v in edge[2].items()}
                    xf.write(ET.Element("Edge", e_attr))
                xf.write(f"\n{' '*6}")
        xf.write(f"\n{' '*4}")


def _write_track_id(xf: ET.xmlfile, lineage: CellLineage) -> None:
    """
    Helper function to write a track ID to the XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    lineage : CellLineage
        Cell lineage containing the data to write.

    Raises
    ------
    KeyError
        If the lineage does not have a TRACK_ID attribute.
    """
    try:
        if lineage.graph["TRACK_ID"] < 0:
            # We don't want to write the track ID for one-node lineages.
            return
    except KeyError as err:
        raise KeyError("The lineage does not have a TRACK_ID attribute.") from err
    xf.write(f"\n{' '*6}")
    t_attr = {"TRACK_ID": str(lineage.graph["TRACK_ID"])}
    xf.write(ET.Element("TrackID", t_attr))


def _write_FilteredTracks(
    xf: ET.xmlfile,
    data: dict[int, CellLineage],
    has_FilteredTracks: bool,
) -> None:
    """
    Write the filtered tracks data into an XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    data : dict[int, CellLineage]
        Cell lineages containing the data to write.
    has_FilteredTracks : bool
        Flag indicating if the model contains filtered tracks.

    Raises
    ------
    KeyError
        If the lineage does not have a TRACK_IDif lineage.graph["TRACK_ID"] < 0: attribute.
    """
    xf.write(f"\n{' '*4}")
    with xf.element("FilteredTracks"):
        if has_FilteredTracks:
            for lineage in data.values():
                if lineage.graph["FilteredTrack"]:
                    _write_track_id(xf, lineage)
        else:
            # If there are no filtered tracks, we need to add all the tracks
            # because TrackMate only displays tracks that are in this tag.
            for lineage in data.values():
                _write_track_id(xf, lineage)
        xf.write(f"\n{' '*4}")
    xf.write(f"\n{' '*2}")


def _update_nodes(lineage: CellLineage) -> None:
    """
    Update the node features in the lineage to match TrackMate requirements.

    Parameters
    ----------
    lineage : CellLineage
        Lineage whose nodes to update.
    """
    for _, data in lineage.nodes(data=True):
        data["ID"] = data.pop("cell_ID")
        data["FRAME"] = data.pop("frame")
        data["VISIBILITY"] = 1
        try:
            data["name"] = data.pop("cell_name")
        except KeyError:
            pass  # Not a mandatory feature.
        # Position features.
        for axis in ["X", "Y", "Z"]:
            try:
                data[f"POSITION_{axis}"] = data.pop(f"cell_{axis.lower()}")
            except KeyError:
                # This feature is mandatory in TrackMate for x, y and z dimensions.
                if axis in ["X", "Y"]:
                    raise KeyError(
                        f"A mandatory TrackMate feature is missing: "
                        f"POSITION_{axis}."
                    )
                else:
                    # We add the missing z dimension.
                    data[f"POSITION_{axis}"] = 0.0


def _update_edges(lineage: CellLineage) -> None:
    """
    Update the edge features in the lineage to match TrackMate requirements.

    Parameters
    ----------
    lineage : CellLineage
        Lineage whose edges to update.
    """
    for source_node, target_node, data in lineage.edges(data=True):
        # Mandatory TrackMate features.
        if "SPOT_SOURCE_ID" not in data:
            data["SPOT_SOURCE_ID"] = source_node
        if "SPOT_TARGET_ID" not in data:
            data["SPOT_TARGET_ID"] = target_node
        # Position features.
        for axis in ["X", "Y", "Z"]:
            try:
                data[f"EDGE_{axis}_LOCATION"] = data.pop(f"link_{axis.lower()}")
            except KeyError:
                pass  # Not a mandatory feature.


def _update_lineages(lineage: CellLineage) -> None:
    """
    Update the lineage features to match TrackMate requirements.

    Parameters
    ----------
    lineage : CellLineage
        Lineage whose graph to update.
    """
    # Mandatory TrackMate feature.
    lineage.graph["TRACK_ID"] = lineage.graph.pop("lineage_ID")
    try:
        lineage.graph["name"] = lineage.graph.pop("lineage_name")
    except KeyError:
        pass  # Not a mandatory feature.
    # Position features.
    for axis in ["X", "Y", "Z"]:
        try:
            lineage.graph[f"TRACK_{axis}_LOCATION"] = lineage.graph.pop(
                f"lineage_{axis.lower()}"
            )
        except KeyError:
            pass  # Not a mandatory feature.


def _update_model_data(model: Model) -> None:
    """
    Update the data in the model to match TrackMate requirements.

    Parameters
    ----------
    model : Model
        Model whose data to update.
    """
    for lin in model.data.cell_data.values():
        _update_nodes(lin)
        _update_edges(lin)
        _update_lineages(lin)


def _remove_non_numeric_features(model: Model) -> None:
    """
    Completely remove non-numeric features from the model.

    Parameters
    ----------
    model : Model
        Model to modify.

    Warns
    -----
    UserWarning
        If some features are not numeric and will not be exported to TrackMate.
        This is the case for features with string, list, or other non-numeric
        values that TrackMate cannot handle.

    Notes
    -----
    This is necessary because TrackMate does not support non-numeric features.
    Boolean features are considered numeric and are converted to integers
    (1 for True, 0 for False).
    """
    valid_dtype = [
        "int",
        "integer",
        "float",
        "complex",
        "bool",
        "boolean",
        "fraction",
        "decimal",
        "number",
        "numeric",
        "real",
        "rational",
    ]
    to_remove = [
        name
        for name, feat in model.get_features().items()
        if feat.provenance != "TrackMate" and feat.data_type.lower() not in valid_dtype
    ]
    if to_remove:
        for name in to_remove:
            try:
                model.remove_feature(name)
            except ProtectedFeatureError:
                model.feat_declaration._unprotect_feature(name)
                model.remove_feature(name)
        plural = True if len(to_remove) > 1 else False
        msg = (
            f"Ignoring feature{'s' if plural else ''} "
            f"{', '.join(to_remove)}. {'They are' if plural else 'It is'} "
            f"not numeric and won't be supported by TrackMate."
        )
        warnings.warn(msg)


def _rename_features(fd: FeaturesDeclaration) -> None:
    """
    Rename some features in the feature declaration to match TrackMate requirements.

    Parameters
    ----------
    fd : FeaturesDeclaration
        Feature declaration to modify.
    """
    fd._unprotect_feature("lineage_ID")
    fd._rename_feature("lineage_ID", "TRACK_ID")
    fd._modify_feature_description("TRACK_ID", "Track ID")
    fd._unprotect_feature("frame")
    fd._rename_feature("frame", "FRAME")


def _remove_features(fd: FeaturesDeclaration) -> None:
    """
    Remove some features from the feature declaration.

    Parameters
    ----------
    fd : FeaturesDeclaration
        Feature declaration to modify.

    Notes
    -----
    While TrackMate has these features (maybe under a different name but in that
    case renaming comes later), they are absent from the FeatureDeclarations tag
    in the TrackMate XML file.
    """
    fd._unprotect_feature("cell_ID")
    fd._remove_feature("cell_ID")
    for feature in ["cell_name", "lineage_name", "FilteredTrack", "ROI_coords"]:
        try:
            fd._remove_feature(feature)
        except KeyError:
            # Classic TrackMate feature but not mandatory.
            pass


def _add_mandatory_features(fd: FeaturesDeclaration) -> None:
    """
    Add mandatory features to the feature declaration.

    This is necessary because TrackMate requires some features to be present
    in the model, even if they are not used in pycellin.

    Parameters
    ----------
    fd : FeaturesDeclaration
        Feature declaration to modify.
    """
    if not fd._has_feature("SPOT_SOURCE_ID"):
        source_feat = Feature(
            name="SPOT_SOURCE_ID",
            description="Source spot ID",
            provenance="TrackMate",
            feat_type="edge",
            lin_type="CellLineage",
            data_type="int",
            unit="NONE",
        )
        fd._add_feature(source_feat)
    if not fd._has_feature("SPOT_TARGET_ID"):
        target_feat = Feature(
            name="SPOT_TARGET_ID",
            description="Target spot ID",
            provenance="TrackMate",
            feat_type="edge",
            lin_type="CellLineage",
            data_type="int",
            unit="NONE",
        )
        fd._add_feature(target_feat)
    if not fd._has_feature("VISIBILITY"):
        visibility_feat = Feature(
            name="VISIBILITY",
            description="Visibility",
            provenance="TrackMate",
            feat_type="node",
            lin_type="CellLineage",
            data_type="int",
            unit="NONE",
        )
        fd._add_feature(visibility_feat)


def _update_location_features(fd: FeaturesDeclaration) -> None:
    """
    Update location features in the feature declaration to match TrackMate requirements.

    This function renames the cell_x, cell_y, cell_z, link_x, link_y, link_z,
    lineage_x, lineage_y, and lineage_z features to their TrackMate equivalents.

    Parameters
    ----------
    fd : FeaturesDeclaration
        Feature declaration to modify.

    Raises
    ------
    KeyError
        If a mandatory feature is missing in the feature declaration.
    """
    for axis in ["x", "y", "z"]:
        try:
            fd._rename_feature(f"cell_{axis}", f"POSITION_{axis.upper()}")
        except KeyError:
            # This feature is mandatory in TrackMate for x, y and z dimensions.
            if axis in ["x", "y"]:
                raise KeyError(
                    f"A feature mandatory for TrackMate export is missing: "
                    f"cell_{axis}."
                )
            else:
                # We add the missing z dimension.
                fd._add_feature(
                    Feature(
                        name=f"POSITION_{axis.upper()}",
                        description=f"Cell {axis.upper()} coordinate",
                        provenance="TrackMate",
                        feat_type="node",
                        lin_type="CellLineage",
                        data_type="float",
                        unit="pixel",
                    )
                )
        try:
            fd._rename_feature(f"link_{axis}", f"EDGE_{axis.upper()}_LOCATION")
        except KeyError:
            pass  # Not a mandatory feature.
        try:
            fd._rename_feature(f"lineage_{axis}", f"TRACK_{axis.upper()}_LOCATION")
        except KeyError:
            pass  # Not a mandatory feature.


def _update_feature_declarations(model: Model) -> None:
    """
    Update the feature declarations in the model to match TrackMate requirements.


    Parameters
    ----------
    model : Model
        Model whose feature declarations to update.
    """
    fd = model.feat_declaration
    _rename_features(fd)
    _remove_features(fd)
    _add_mandatory_features(fd)
    _update_location_features(fd)


def _prepare_model_for_export(
    model: Model,
) -> None:
    """
    Prepare a pycellin model for export to TrackMate format.

    This function updates the model to match TrackMate requirements
    and removes non-numeric features that TrackMate cannot handle.

    Parameters
    ----------
    model : Model
        Model to prepare for export.
    """
    _update_feature_declarations(model)
    _update_model_data(model)
    _remove_non_numeric_features(model)


def _write_metadata_tag(
    xf: ET.xmlfile,
    metadata: dict[str, Any],
    tag: str,
) -> None:
    """
    Write the specified XML tag into a TrackMate XML file.

    If the tag is not present in the metadata, an empty tag will be
    written.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    metadata : dict[str, Any]
        Dictionary that may contain the metadata to write.
    tag : str
        XML tag to write.
    """
    if tag in metadata:
        xml_element = ET.fromstring(metadata[tag])
        xf.write(xml_element)
    else:
        xf.write(ET.Element(tag))


def _ask_units(
    feat_declaration: FeaturesDeclaration,
) -> dict[str, str]:
    """
    Ask the user to check units consistency and to give unique spatio-temporal units.

    Parameters
    ----------
    feat_declaration : FeaturesDeclaration
        Declaration of the features. It contains the unit of each feature.

    Returns
    -------
    dict[str, str]
        Dictionary containing the spatial and temporal units of the features.
    """
    print(
        "TrackMate requires a unique spatial unit, and a unique temporal unit. "
        "Please check below that your spatial and temporal units are the same "
        "across all features. If not, convert your features to the same unit "
        "before reattempting to export to TrackMate format."
    )
    model_units = feat_declaration._get_units_per_features()
    for unit, feats in model_units.items():
        print(f"{unit}: {feats}")
    trackmate_units = {}
    trackmate_units["spatialunits"] = input("Please type the spatial unit: ")
    trackmate_units["temporalunits"] = input("Please type the temporal unit: ")
    print(f"Using the following units for TrackMate export: {trackmate_units}")
    return trackmate_units


def export_TrackMate_XML(
    model: Model,
    xml_path: str,
    units: dict[str, str] | None = None,
    propagate_cycle_features: bool = False,
) -> Model:
    """
    Write an XML file readable by TrackMate from a pycellin model.

    Parameters
    ----------
    model : Model
        pycellin model containing the data to write.
    xml_path : str
        Path of the XML file to write.
    units : dict[str, str], optional
        Dictionary containing the spatial and temporal units of the model.
        If not specified, the user will be asked to provide them. Format is:
        {"spatialunits": "your_unit", "temporalunits": "your_unit"}, e.g.
        {"spatialunits": "pixel", "temporalunits": "sec"}.
    propagate_cycle_features : bool, optional
        If True, cycle features will be propagated to cell lineages before export.
        Useful if you want to export the cycle features to TrackMate
        and have them accessible in the tracks. Default is False.

    Returns
    -------
    model_copy : Model
        The model as it was exported, including all the modifications done by the
        exporter (removal of incompatible features, propagation of cycle features...).
        This is a copy of the original model, so the original model is not modified.

    Warnings
    --------
    Quantitative analysis of cell cycle features should not be done on cell
    lineages after propagation of cycle features, UNLESS you account for cell
    cycle length. Otherwise you will introduce a bias in your quantification.
    Indeed, after propagation, cycle features (like division time) become
    over-represented in long cell cycles since these features are propagated on each
    node of the cell cycle in cell lineages, whereas they are stored only once
    per cell cycle on the cycle node in cycle lineages.
    """
    # We don't want to modify the original model.
    model_copy = copy.deepcopy(model)
    if propagate_cycle_features:
        model_copy.propagate_cycle_features()

    if not units:
        units = _ask_units(model_copy.feat_declaration)
    if "TrackMate_version" in model_copy.metadata:
        tm_version = model_copy.metadata["TrackMate_version"]
    else:
        tm_version = "unknown"
    has_FilteredTrack = model_copy.has_feature("FilteredTrack")
    _prepare_model_for_export(model_copy)

    with ET.xmlfile(xml_path, encoding="utf-8", close=True) as xf:
        xf.write_declaration()
        with xf.element("TrackMate", {"version": tm_version}):
            xf.write("\n  ")
            _write_metadata_tag(xf, model_copy.metadata, "Log")
            xf.write("\n  ")
            with xf.element("Model", units):
                _write_FeatureDeclarations(xf, model_copy)
                _write_AllSpots(xf, model_copy.data.cell_data)
                _write_AllTracks(xf, model_copy.data.cell_data)
                _write_FilteredTracks(xf, model_copy.data.cell_data, has_FilteredTrack)
            xf.write("\n  ")
            for tag in ["Settings", "GUIState", "DisplaySettings"]:
                _write_metadata_tag(xf, model_copy.metadata, tag)
                if tag == "DisplaySettings":
                    xf.write("\n")
                else:
                    xf.write("\n  ")
    return model_copy


if __name__ == "__main__":

    xml_in = "sample_data/FakeTracks.xml"
    # xml_out = "sample_data/results/FakeTracks_TMtoTM.xml"
    xml_out = "/home/laura/FakeTracks_exported_TM.xml"

    # xml_in = "sample_data/Celegans-5pc-17timepoints.xml"
    # xml_out = "sample_data/Celegans-5pc-17timepoints_exported_TM.xml"

    model = load_TrackMate_XML(xml_in, keep_all_spots=True, keep_all_tracks=True)
    # print(model.feat_declaration)
    # model.remove_feature("VISIBILITY")

    model.add_cycle_data()
    model.propagate_cycle_features(
        features=["cells"],
    )
    # model.add_absolute_age()
    # model.add_relative_age(in_time_unit=True)
    # model.add_cell_displacement()
    # model.update()
    # lin0 = model.data.cell_data[0]
    # lin0.plot(
    #     node_hover_features=["cell_ID", "cell_x", "cell_y", "cell_z"],
    #     edge_hover_features=["link_x", "link_y", "link_z"],
    # )
    # print(model.feat_declaration)
    export_TrackMate_XML(
        model, xml_out, {"spatialunits": "pixel", "temporalunits": "sec"}
    )
    # print()
    # print(model.feat_declaration)
