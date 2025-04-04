#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
loader.py

This module is part of the Pycellin package.

This module provides functions to load and process trackpy data into Pycellin models.
It includes a function to load a trackpy file into Pycellin model and helper functions
to create metadata, features, and lineage graphs.

References:
- trackpy: D. B. Allan, T. Caswell, N. C. Keim, C. M. van der Weland R. W. Verweij,
“soft-matter/trackpy: v0.6.4”. Zenodo, Jul. 10, 2024. doi: 10.5281/zenodo.12708864.
- trackpy GitHub: https://github.com/soft-matter/trackpy
"""

from datetime import datetime
import importlib
from typing import Any

import networkx as nx
import pandas as pd

from pycellin.classes.model import Model
from pycellin.classes.feature import (
    FeaturesDeclaration,
    cell_ID_Feature,
    frame_Feature,
    lineage_ID_Feature,
)


def _create_metadata() -> dict[str, Any]:
    """
    Create a dictionary of basic Pycellin metadata for a given file.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the generated metadata.
    """
    metadata = {}  # type: dict[str, Any]
    metadata["provenance"] = "trackpy"
    # TODO: switch the other loader to str
    metadata["date"] = str(datetime.now())
    metadata["time_unit"] = "frame"
    metadata["time_step"] = 1
    # TODO: Maybe ask the user for the time unit and time step.
    try:
        version = importlib.metadata.version("pycellin")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    metadata["pycellin_version"] = version
    return metadata


def _create_FeaturesDeclaration() -> FeaturesDeclaration:
    """
    Return a FeaturesDeclaration object populated with Pycellin basic features.

    Returns
    -------
    FeaturesDeclaration
        An instance of FeaturesDeclaration populated with cell and lineage
        identification features.
    """
    feat_declaration = FeaturesDeclaration()
    cell_ID_feat = cell_ID_Feature()
    frame_feat = frame_Feature()
    lin_ID_feat = lineage_ID_Feature()
    for feat in [cell_ID_feat, frame_feat, lin_ID_feat]:
        feat_declaration._add_feature(feat)
        feat_declaration._protect_feature(feat.name)

    return feat_declaration


def load_trackpy_dataframe(df: pd.DataFrame) -> Model:
    """
    Load a trackpy DataFrame into a Pycellin model.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing trackpy data.

    Returns
    -------
    Model
        A Pycellin model populated with the trackpy data.
    """
    graph = nx.DiGraph()
    current_node_id = 0

    # Add nodes.
    for _, row in df.iterrows():
        node_id = current_node_id
        graph.add_node(node_id, **row.to_dict())
        current_node_id += 1

    # Add edges.

    # Split into lineages.

    metadata = _create_metadata()
    feat_declaration = _create_FeaturesDeclaration()

    # Create a Pycellin model
    model = Model(
        metadata=metadata,
        fd=feat_declaration,
    )

    return model


if __name__ == "__main__":

    import pickle

    folder = "/mnt/data/Code/trackpy-examples-master/sample_data/"
    tracks = "FakeTracks_trackpy.pkl"

    df = pd.read_pickle(folder + tracks)
    print(df.shape)
