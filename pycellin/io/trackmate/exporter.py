#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Features in the XML file are not in the same order as a file that was exported
directly from TrackMate.
I've tested quickly and it doesn't seem to be a problem for TrackMate.
"""


import copy
import math
from typing import Any, Union
import warnings

from lxml import etree as ET
import networkx as nx

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
        "cells": "NONE",
        "cycle_duration": "NONE",
        "cycle_ID": "NONE",
        "cycle_length": "NONE",
        "division_time": "TIME",
        "division_rate": "TIME",  # TODO: check if this is correct
        "level": "NONE",
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

    elif provenance == "Pycellin":
        try:
            dimension = pycellin_feats[name]
        except KeyError:
            try:
                dimension = trackmate_feats[name]
            except KeyError:
                msg = (
                    f"'{name}' is a feature listed as coming from Pycellin"
                    f" but it is not a known feature of either Pycellin or TrackMate. "
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


def _convert_feature(
    feat: Feature,
) -> dict[str, str]:
    """
    Convert a Pycellin feature to a TrackMate feature.

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
    trackmate_feat["name"] = feat.description
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
    value: Union[int, float, str],
) -> str:
    """
    Convert a value to its associated string.

    Indeed, ET.write() method only accepts to write strings.
    However, TrackMate is only able to read Spot, Edge and Track
    features that can be parsed as numeric by Java.

    Parameters
    ----------
    value : Union[int, float, str]
        Value to convert to string.

    Returns
    -------
    str
        The string equivalent of `value`.
    """
    # TODO: Should this function take care of converting non-numeric added
    # features to numeric ones (like GEN_ID)? Or should it be done in
    # Pycellin?
    # I can also use the provenance field to identify which features come
    # from TrackMate.
    if isinstance(value, str):
        return value
    elif math.isnan(value):
        return "NaN"
    elif math.isinf(value):
        if value > 0:
            return "Infinity"
        else:
            return "-Infinity"
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
            # so one-node tracks are to be ignored. In Pycellin, a one-node
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


def _prepare_model_for_export(
    model: Model,
) -> None:
    """
    Prepare a Pycellin model for export to TrackMate format.

    Some Pycellin features are a bit different from TrackMate features
    and need to be modified or deleted. For example, "lineage_ID" in Pycellin
    is "TRACK_ID" in TrackMate.

    Parameters
    ----------
    model : Model
        Model to prepare for export.

    Raises
    ------
    KeyError
        If a mandatory feature is missing in the model.
    """
    # Update of the features declaration.
    fd = model.feat_declaration
    fd._unprotect_feature("lineage_ID")
    fd._rename_feature("lineage_ID", "TRACK_ID")
    fd._modify_feature_description("TRACK_ID", "Track ID")
    fd._unprotect_feature("frame")
    fd._rename_feature("frame", "FRAME")
    fd._unprotect_feature("cell_ID")
    fd._remove_feature("cell_ID")
    for feature in ["cell_name", "lineage_name", "FilteredTrack", "ROI_coords"]:
        try:
            fd._remove_feature(feature)
        except KeyError:
            # This feature is a classic TrackMate feature but not mandatory.
            pass
    # Some features don't necessarily exist in Pycellin but are mandatory in TrackMate.
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

    # Location related features.
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

    # Update of the data.
    for lin in model.data.cell_data.values():
        # Nodes.
        for _, data in lin.nodes(data=True):
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

        # Edges.
        for source_node, target_node, data in lin.edges(data=True):
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

        # Lineages.
        lin.graph["TRACK_ID"] = lin.graph.pop("lineage_ID")
        try:
            lin.graph["name"] = lin.graph.pop("lineage_name")
        except KeyError:
            pass  # Not a mandatory feature.
        # Position features.
        for axis in ["X", "Y", "Z"]:
            try:
                lin.graph[f"TRACK_{axis}_LOCATION"] = lin.graph.pop(
                    f"lineage_{axis.lower()}"
                )
            except KeyError:
                pass  # Not a mandatory feature.


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
) -> None:
    """
    Write an XML file readable by TrackMate from a Pycellin model.

    Parameters
    ----------
    model : Model
        Pycellin model containing the data to write.
    xml_path : str
        Path of the XML file to write.
    units : dict[str, str], optional
        Dictionary containing the spatial and temporal units of the model.
        If not specified, the user will be asked to provide them.
    """
    # We don't want to modify the original model.
    model_copy = copy.deepcopy(model)

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
    del model_copy


if __name__ == "__main__":

    xml_in = "sample_data/FakeTracks.xml"
    # xml_out = "sample_data/results/FakeTracks_TMtoTM.xml"
    xml_out = "/home/laura/FakeTracks_exported_TM.xml"

    # xml_in = "sample_data/Celegans-5pc-17timepoints.xml"
    # xml_out = "sample_data/Celegans-5pc-17timepoints_exported_TM.xml"

    model = load_TrackMate_XML(xml_in, keep_all_spots=True, keep_all_tracks=True)
    # print(model.feat_declaration)
    model.remove_feature("VISIBILITY")
    # model.add_absolute_age()
    # model.add_relative_age(in_time_unit=True)
    # model.add_cell_displacement()
    # model.update()
    # lin0 = model.data.cell_data[0]
    # lin0.plot(
    #     node_hover_features=["cell_ID", "cell_x", "cell_y", "cell_z"],
    #     edge_hover_features=["link_x", "link_y", "link_z"],
    # )
    print(model.feat_declaration)
    export_TrackMate_XML(
        model, xml_out, {"spatialunits": "pixel", "temporalunits": "sec"}
    )
    print()
    print(model.feat_declaration)
