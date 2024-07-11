#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from typing import Any, Union

from lxml import etree as ET
import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.feature import FeaturesDeclaration, Feature
from pycellin.classes.data import CoreData
from pycellin.classes.lineage import CellLineage
from pycellin.io.trackmate.loader import load_TrackMate_XML


# TODO: find a way to write this fuction, see with JY
def _unit_to_dimension(feat: Feature) -> str:
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
    desc = feat.description
    match unit:
        case "pixel":
            if "position" in name.lower() or name.lower() in ["x", "y", "z"]:
                # Does not work if POSITION_T
                dimension = "POSITION"
            else:
                dimension = "LENGTH"
        case "none" | "frame":
            dimension = "NONE"
    # It's going to be a nightmare to deal with all the possible cases.
    dimension = "TODO"
    return dimension


def _convert_feature(feat: Feature) -> dict[str, str]:
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
    match feat.name:
        case "ID" | "name":
            # These features do not exist in TrackMate features declaration.
            pass
        case "ROI_COORDINATES":
            pass
        case _:
            trackmate_feat["feature"] = feat.name
            trackmate_feat["name"] = feat.description
            trackmate_feat["shortname"] = feat.name.lower()
            trackmate_feat["dimension"] = _unit_to_dimension(feat)
            if feat.data_type == "int":
                trackmate_feat["isint"] = "true"
            else:
                trackmate_feat["isint"] = "false"

    return trackmate_feat


def _write_FeatureDeclarations(xf: ET.xmlfile, model: Model) -> None:
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
                        features = model.feat_declaration.node_feats
                    case "EdgeFeatures":
                        features = model.feat_declaration.edge_feats
                    case "TrackFeatures":
                        features = model.feat_declaration.lin_feats
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
    # print(value, type(value))

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
    # Building Spot attributes.
    # print(lineage.nodes[node].keys())
    # I have a feature ROI_N_POINTS and I shouldn't.
    # print(lineage.nodes[node]["ROI_N_POINTS"])

    exluded_keys = ["TRACK_ID", "ROI_COORDINATES"]
    n_attr = {
        k: _value_to_str(v)
        for k, v in lineage.nodes[node].items()
        if k not in exluded_keys
    }
    n_attr["ROI_N_POINTS"] = str(len(lineage.nodes[node]["ROI_COORDINATES"]))

    # Building Spot text: coordinates of ROI points.
    coords = [item for pt in lineage.nodes[node]["ROI_COORDINATES"] for item in pt]

    el_node = ET.Element("Spot", n_attr)
    el_node.text = " ".join(map(str, coords))
    return el_node


def _write_AllSpots(xf: ET.xmlfile, model: Model) -> None:
    xf.write(f"\n{' '*4}")
    lineages = model.coredata.data.values()
    nb_nodes = sum([len(lin) for lin in lineages])
    with xf.element("AllSpots", {"nspots": str(nb_nodes)}):
        # For each frame, nodes can be spread over several graphs so we first
        # need to identify all of the existing frames.
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


def _write_tag(xf: ET.xmlfile, metadata: dict[str, Any], tag: str) -> None:
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


def _ask_units(feat_declaration: FeaturesDeclaration) -> dict[str, str]:
    """
    Ask the user to check units consistency and to give a unique spatial and a unique temporal units.

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
    model_units = feat_declaration.get_units_per_features()
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

    if not units:
        units = _ask_units(model.feat_declaration)

    with ET.xmlfile(xml_path, encoding="utf-8", close=True) as xf:
        xf.write_declaration()

        if "TrackMate_version" in model.metadata:
            tm_version = model.metadata["TrackMate_version"]
        else:
            tm_version = "unknown"

        with xf.element("TrackMate", {"version": tm_version}):
            xf.write("\n  ")
            _write_tag(xf, model.metadata, "Log")
            xf.write("\n  ")
            with xf.element("Model", units):
                _write_FeatureDeclarations(xf, model)
                _write_AllSpots(xf, model)
                # _write_AllTracks(xf, model)
                # _write_FilteredTracks(xf, model)
            xf.write("\n  ")
            for tag in ["Settings", "GUIState", "DisplaySettings"]:
                _write_tag(xf, model.metadata, tag)
                if tag == "DisplaySettings":
                    xf.write("\n")
                else:
                    xf.write("\n  ")


if __name__ == "__main__":

    xml_in = "sample_data/FakeTracks.xml"
    xml_out = "sample_data/FakeTracks_exported.xml"

    model = load_TrackMate_XML(xml_in, keep_all_spots=True, keep_all_tracks=True)
    # print(model.feat_declaration.node_feats)
    # model.metadata.pop("GUIState")
    export_TrackMate_XML(
        model, xml_out, {"spatialunits": "pixel", "temporalunits": "sec"}
    )
