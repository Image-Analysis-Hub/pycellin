#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy
from typing import Any

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
    return dimension


def _convert_feature(feat: Feature) -> dict[str, str]:
    pass


def _write_FeatureDeclarations(xf: ET.xmlfile, model: Model) -> None:
    """
    Write the FeatureDeclarations XML tag into a TrackMate XML file.

    The features declaration is divided in three parts: spot features,
    edge features, and track features.

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
                # Need to convert the Pycellin feature to a TrackMate one
                # _convert_feature(feat: Feature) -> dict[str, str]
                # I will use the name as shortname for the feature
                pass


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
    # TODO: Should I ask the user if the units are correct before moving to the next step?
    trackmate_units = {}
    trackmate_units["spatialunits"] = input("Please type the spatial unit: ")
    trackmate_units["temporalunits"] = input("Please type the temporal unit: ")
    print(f"Using the following units for TrackMate export: {trackmate_units}")
    return trackmate_units


def export_TrackMate_XML(
    model: Model,
    xml_path: str,
) -> None:
    """
    Write an XML file readable by TrackMate from a Pycellin model.

    Parameters
    ----------
    model : Model
        Pycellin model containing the data to write.
    xml_path : str
        Path of the XML file to write.
    """

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
                # _write_AllSpots(xf, model)
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

    model = load_TrackMate_XML(xml_in)
    # print(model.feat_declaration.node_feats)
    # model.metadata.pop("GUIState")
    export_TrackMate_XML(model, xml_out)
