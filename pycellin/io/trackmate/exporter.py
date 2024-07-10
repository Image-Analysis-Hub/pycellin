#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from pkg_resources import get_distribution
from typing import Any

from lxml import etree as ET
import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.feature import FeaturesDeclaration, Feature
from pycellin.classes.data import CoreData
from pycellin.classes.lineage import CellLineage


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
            _write_tag(xf, model.metadata, tag)
            xf.write("\n\t")
            _write_Model(xf, model)
            xf.write("\n\t")
            for tag in ["Settings", "GUIState", "DisplaySettings"]:
                _write_tag(xf, model.metadata, tag)
                xf.write("\n\t")
