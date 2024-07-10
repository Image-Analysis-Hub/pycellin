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


def _write_Model(xf: ET.xmlfile, model: Model) -> None:
    """
    Write the Model XML tag to a TrackMate XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    model : Model
        Model containing the data to write.
    """
    pass


def _write_tag(xf: ET.xmlfile, metadata: dict[str, Any], tag: str) -> None:
    """
    Write the specified XML tag to a TrackMate XML file.

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
    # Write the tag if available, otherwise write an empty tag.
    pass


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
    with ET.xmlfile(xml_path, encoding="utf-8", close=True) as xf:
        xf.write_declaration()

        if "TrackMate_version" in model.metadata:
            tm_version = model.metadata["TrackMate_version"]
        else:
            tm_version = "unknown"

        with xf.element("TrackMate", {"version": tm_version}):
            xf.write("\n\t")
            _write_tag(xf, model.metadata, "Log")
            xf.write("\n\t")
            _write_Model(xf, model)
            xf.write("\n\t")
            for tag in ["Settings", "GUIState", "DisplaySettings"]:
                _write_tag(xf, model.metadata, tag)
                xf.write("\n\t")


if __name__ == "__main__":

    xml_in = "sample_data/FakeTracks.xml"
    xml_out = "sample_data/FakeTracks_exported.xml"

    model = load_TrackMate_XML(xml_in)
    export_TrackMate_XML(model, xml_out)
