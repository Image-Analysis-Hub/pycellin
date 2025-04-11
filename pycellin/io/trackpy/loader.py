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
from itertools import pairwise
from typing import Any

import networkx as nx
import pandas as pd

from pycellin.classes import (
    CellLineage,
    Data,
    FeaturesDeclaration,
    Model,
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
    metadata["date"] = str(datetime.now())
    metadata["time_unit"] = "frame"
    metadata["time_step"] = 1
    # TODO: Maybe ask the user for the time unit and time step.
    try:
        version = importlib.metadata.version("pycellin")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    metadata["Pycellin_version"] = version
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
        row_dict = row.to_dict()
        # 'frame' and 'particle' needs to be converted back to int.
        row_dict["frame"] = int(row_dict["frame"])
        row_dict["particle"] = int(row_dict["particle"])
        graph.add_node(current_node_id, **row_dict)
        graph.nodes[current_node_id]["cell_ID"] = current_node_id
        current_node_id += 1

    # Add edges.
    # We need to link cells that have the same 'particle' value and are in frames
    # that follows each other. Since there can be gaps in trackpy trajectories,
    # we can't rely on the fact that frames will be truly consecutive.
    particles = df["particle"].unique()
    del df  # Free memory.
    for particle in particles:
        candidates = [
            (node, frame)
            for node, frame in graph.nodes(data="frame")
            if graph.nodes[node]["particle"] == particle
        ]
        candidates.sort(key=lambda x: x[1])
        for (n1, _), (n2, _) in pairwise(candidates):
            graph.add_edge(n1, n2)

    # Split into lineages.
    # One subgraph is created per lineage, so each subgraph is
    # a connected component of `graph`.
    lineages = [
        CellLineage(graph.subgraph(c).copy())
        for c in nx.weakly_connected_components(graph)
    ]
    del graph  # Redondant with the subgraphs.
    # Each lineage needs to be assigned a lineage ID.
    data = {}  # type: dict[int, CellLineage]
    current_node_id = 0
    for lin in lineages:
        lin.graph["lineage_ID"] = current_node_id
        data[current_node_id] = lin
        current_node_id += 1

    # Create a Pycellin model
    metadata = _create_metadata()
    feat_declaration = _create_FeaturesDeclaration()
    model = Model(
        metadata=metadata,
        fd=feat_declaration,
        data=Data(data),
    )

    return model


if __name__ == "__main__":

    folder = "E:/Pasteur/Code/trackpy-examples-master/sample_data/"
    tracks = "FakeTracks_trackpy.pkl"

    df = pd.read_pickle(folder + tracks)
    print(df.shape)
    print(df.head())

    model = load_trackpy_dataframe(df)
    print(model)
    for lin in model.get_cell_lineages():
        lin.plot(node_hover_features=["cell_ID", "frame", "particle"])
