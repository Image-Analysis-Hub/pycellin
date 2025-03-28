#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Features in the XML file are not in the same order as a file that was exported 
directly from TrackMate.
I've tested quickly and it doesn't seem to be a problem for TrackMate.
"""


import math
from typing import Any, Union

from lxml import etree as ET
import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.feature import FeaturesDeclaration, Feature
from pycellin.classes.data import Data
from pycellin.classes.lineage import CellLineage
from pycellin.io.trackmate.loader import load_TrackMate_XML


# TODO: finish this function
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
        "CONFINEMENT_RATIO": "NONE",
        "MEAN_STRAIGHT_LINE_SPEED": "VELOCITY",
        "LINEARITY_OF_FORWARD_PROGRESSION": "NONE",
        "MEAN_DIRECTIONAL_CHANGE_RATE": "ANGLE_RATE",
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

    if provenance == "TrackMate":
        if name in trackmate_feats:
            dimension = trackmate_feats[name]
        else:
            dimension = None
            for key, dim in channel_feats.items():
                if name.startswith(key):
                    dimension = dim
                    break
            if dimension is None:
                print(
                    f"WARNING: {name} is a feature listed as coming from TrackMate"
                    f" but it is not a known feature of TrackMate. Dimension is set"
                    f" to NONE."
                )
                # I'm using NONE here, which is already used in TM, for example
                # with the FRAME or VISIBILITY features. I tried to use UNKNOWN
                # but it's a dimension not recognized by TM and it crashes.
                dimension = "NONE"

    elif provenance == "Pycellin":
        dimension = "TODO1"

    else:
        match unit:
            case "pixel":
                if name.lower() in ["x", "y", "z"]:
                    dimension = "POSITION"
                else:
                    dimension = "LENGTH"
            case "none" | "frame":
                dimension = "NONE"
        # It's going to be a nightmare to deal with all the possible cases.
        # Is it even possible? I should ask the user for a file with
        # a feature-dimension mapping.
        dimension = "TODO2"

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
    # pycellin?
    # I can also use the provenance field to ientify which features come
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

    el_node = ET.Element("Spot", n_attr)
    if "ROI_coords" in lineage.nodes[node]:
        el_node.text = " ".join(map(str, coords))
    return el_node


def _write_AllSpots(
    xf: ET.xmlfile,
    data: Data,
) -> None:
    """
    Write the nodes/spots data into an XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    data : Data
        Lineages containing the data to write.
    """
    xf.write(f"\n{' '*4}")
    lineages = data.values()
    nb_nodes = sum([len(lin) for lin in lineages])
    with xf.element("AllSpots", {"nspots": str(nb_nodes)}):
        # For each frame, nodes can be spread over several lineages
        # so we first need to identify all of the existing frames.
        frames = set()
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
    data: Data,
) -> None:
    """
    Write the tracks data into an XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    data : Data
        Lineages containing the data to write.
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


def _write_FilteredTracks(
    xf: ET.xmlfile,
    data: Data,
) -> None:
    """
    Write the filtered tracks data into an XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    data : Data
        Lineages containing the data to write.z
    """
    xf.write(f"\n{' '*4}")
    with xf.element("FilteredTracks"):
        for lineage in data.values():
            if "TRACK_ID" in lineage.graph and lineage.graph["FilteredTrack"]:
                xf.write(f"\n{' '*6}")
                t_attr = {"TRACK_ID": str(lineage.graph["TRACK_ID"])}
                xf.write(ET.Element("TrackID", t_attr))
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
    """
    # Update of the features declaration.
    fd = model.feat_declaration
    fd._unprotect_feature("lineage_ID")
    fd._rename_feature("lineage_ID", "TRACK_ID")
    fd._modify_feature_description("TRACK_ID", "Track ID")
    fd._remove_features(["FilteredTrack", "lineage_name"])
    fd._unprotect_feature("frame")
    fd._rename_feature("frame", "FRAME")
    fd._unprotect_feature("cell_ID")
    fd._remove_features(["cell_ID", "cell_name"])
    if "ROI_coords" in fd.feats_dict:
        fd._remove_feature("ROI_coords")
    # Location related features.
    for axis in ["x", "y", "z"]:
        fd._rename_feature(f"cell_{axis}", f"POSITION_{axis.upper()}")
        fd._rename_feature(f"link_{axis}", f"EDGE_{axis.upper()}_LOCATION")
        fd._rename_feature(f"lineage_{axis}", f"TRACK_{axis.upper()}_LOCATION")

    # Update of the data.
    for lin in model.data.cell_data.values():
        for _, data in lin.nodes(data=True):
            data["ID"] = data.pop("cell_ID")
            data["FRAME"] = data.pop("frame")
            for axis in ["X", "Y", "Z"]:
                data[f"POSITION_{axis}"] = data.pop(f"cell_{axis.lower()}")

        for _, _, data in lin.edges(data=True):
            for axis in ["X", "Y", "Z"]:
                data[f"EDGE_{axis}_LOCATION"] = data.pop(f"link_{axis.lower()}")

        lin.graph["TRACK_ID"] = lin.graph.pop("lineage_ID")
        for axis in ["X", "Y", "Z"]:
            lin.graph[f"TRACK_{axis}_LOCATION"] = lin.graph.pop(
                f"lineage_{axis.lower()}"
            )


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
    units: dict[str, str] = None,
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
    # FIXME: Copy the model to avoid modifying the original one.

    if not units:
        units = _ask_units(model.feat_declaration)
    if "TrackMate_version" in model.metadata:
        tm_version = model.metadata["TrackMate_version"]
    else:
        tm_version = "unknown"
    _prepare_model_for_export(model)

    with ET.xmlfile(xml_path, encoding="utf-8", close=True) as xf:
        xf.write_declaration()
        with xf.element("TrackMate", {"version": tm_version}):
            xf.write("\n  ")
            _write_metadata_tag(xf, model.metadata, "Log")
            xf.write("\n  ")
            with xf.element("Model", units):
                _write_FeatureDeclarations(xf, model)
                _write_AllSpots(xf, model.data.cell_data)
                _write_AllTracks(xf, model.data.cell_data)
                _write_FilteredTracks(xf, model.data.cell_data)
            xf.write("\n  ")
            for tag in ["Settings", "GUIState", "DisplaySettings"]:
                _write_metadata_tag(xf, model.metadata, tag)
                if tag == "DisplaySettings":
                    xf.write("\n")
                else:
                    xf.write("\n  ")


if __name__ == "__main__":

    xml_in = "sample_data/FakeTracks.xml"
    xml_out = "sample_data/results/FakeTracks_exported_TM.xml"

    model = load_TrackMate_XML(xml_in, keep_all_spots=True, keep_all_tracks=True)
    # print(model.feat_declaration)
    lin0 = model.data.cell_data[0]
    # lin0.plot(
    #     node_hover_features=["cell_ID", "cell_x", "cell_y", "cell_z"],
    #     edge_hover_features=["link_x", "link_y", "link_z"],
    # )
    export_TrackMate_XML(
        model, xml_out, {"spatialunits": "pixel", "temporalunits": "sec"}
    )
