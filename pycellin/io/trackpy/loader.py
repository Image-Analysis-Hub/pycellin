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
    cell_coord_Feature,
)


def _add_nodes(graph: nx.DiGraph, df: pd.DataFrame) -> None:
    """
    Add nodes to the graph from the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing trackpy data.
    graph : nx.DiGraph
        The graph to which nodes will be added.
    """
    current_node_id = 0
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        row_dict["frame"] = int(row_dict["frame"])
        row_dict["particle"] = int(row_dict["particle"])
        graph.add_node(current_node_id, **row_dict)
        graph.nodes[current_node_id]["cell_ID"] = current_node_id
        current_node_id += 1


def _add_edges(graph: nx.DiGraph, particles: list) -> None:
    """
    Add edges to the graph based on particle trajectories.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which edges will be added.
    particles : list
        List of unique particle identifiers.
    """
    for particle in particles:
        # We need to link cells that have the same 'particle' value and are in frames
        # that follows each other. Since there can be gaps in trackpy trajectories,
        # we can't rely on the fact that frames will be truly consecutive.
        candidates = [
            (node, frame)
            for node, frame in graph.nodes(data="frame")
            if graph.nodes[node]["particle"] == particle
        ]
        candidates.sort(key=lambda x: x[1])
        for (n1, _), (n2, _) in pairwise(candidates):
            graph.add_edge(n1, n2)


def _split_into_lineages(graph: nx.DiGraph) -> dict[int, CellLineage]:
    """
    Split the graph into cell lineages and assign lineage IDs.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to be split into cell lineages.

    Returns
    -------
    dict[int, CellLineage]
        A dictionary mapping lineage IDs to CellLineage objects.
    """
    # We want one lineage per connected component of the graph.
    lineages = [
        CellLineage(graph.subgraph(c).copy())
        for c in nx.weakly_connected_components(graph)
    ]
    data = {}
    current_node_id = 0
    for lin in lineages:
        lin.graph["lineage_ID"] = current_node_id
        data[current_node_id] = lin
        current_node_id += 1
    return data


def _create_metadata(
    space_unit: str | None = None,
    pixel_width: float | None = None,
    pixel_height: float | None = None,
    pixel_depth: float | None = None,
    time_unit: str | None = None,
    time_step: float | None = None,
) -> dict[str, Any]:
    """
    Create a dictionary of basic Pycellin metadata for a given file.

    Parameters
    ----------
    space_unit : str, optional
        The spatial unit of the data. If not provided, it will be set to 'pixel'
        by default.
    pixel_width : float, optional
        The pixel width in the spatial unit. If not provided, it will be set to 1.0
        by default.
    pixel_height : float, optional
        The pixel height in the spatial unit. If not provided, it will be set to 1.0
        by default.
    pixel_depth : float, optional
        The pixel depth in the spatial unit. If not provided, it will be set to 1.0
        by default.
    time_unit : str, optional
        The temporal unit of the data. If not provided, it will be set to 'frame'
        by default.
    time_step : float, optional
        The time step in the temporal unit. If not provided, it will be set to 1.0
        by default.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the generated metadata.
    """
    metadata = {}  # type: dict[str, Any]
    metadata["provenance"] = "trackpy"
    metadata["date"] = str(datetime.now())
    try:
        version = importlib.metadata.version("pycellin")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    metadata["Pycellin_version"] = version

    # Units.
    if space_unit is not None:
        metadata["space_unit"] = space_unit
    else:
        metadata["space_unit"] = "pixel"
    metadata["pixel_size"] = {}
    if pixel_width is not None:
        metadata["pixel_size"]["width"] = pixel_width
    else:
        metadata["pixel_size"]["width"] = 1.0
    if pixel_height is not None:
        metadata["pixel_size"]["height"] = pixel_height
    else:
        metadata["pixel_size"]["height"] = 1.0
    if pixel_depth is not None:
        metadata["pixel_size"]["depth"] = pixel_depth
    else:
        metadata["pixel_size"]["depth"] = 1.0
    if time_unit is not None:
        metadata["time_unit"] = time_unit
    else:
        metadata["time_unit"] = "frame"
    if time_step is not None:
        metadata["time_step"] = time_step
    else:
        metadata["time_step"] = 1.0

    return metadata


def _create_FeaturesDeclaration(
    features: list[str], metadata: dict[str, Any]
) -> FeaturesDeclaration:
    """
    Return a FeaturesDeclaration object populated with the needed features.

    Parameters
    ----------
    features : list[str]
        List of features to be included in the FeaturesDeclaration.
    metadata : dict[str, Any]
        Metadata dictionary containing information about the data.

    Returns
    -------
    FeaturesDeclaration
        An instance of FeaturesDeclaration populated with Pycellin and trackpy features.
    """
    fd = FeaturesDeclaration()

    # Pycellin mandatory features.
    cell_ID_feat = cell_ID_Feature()
    frame_feat = frame_Feature()
    lin_ID_feat = lineage_ID_Feature()
    for feat in [cell_ID_feat, frame_feat, lin_ID_feat]:
        fd._add_feature(feat)
        fd._protect_feature(feat.name)

    # Trackpy features.
    for axis in ["x", "y", "z"]:
        if axis in features:
            feat = cell_coord_Feature(
                unit=metadata["space_unit"], axis=axis, provenance="trackpy"
            )
            fd._add_feature(feat)
    # TODO: add fd for other trackpy features

    return fd


def load_trackpy_dataframe(
    df: pd.DataFrame,
    space_unit: str | None = None,
    pixel_width: float | None = None,
    pixel_height: float | None = None,
    pixel_depth: float | None = None,
    time_unit: str | None = None,
    time_step: float | None = None,
) -> Model:
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
    # Build the lineages.
    graph = nx.DiGraph()
    _add_nodes(graph, df)
    features = df.columns.to_list()
    particles = df["particle"].unique()
    del df  # Free memory.
    _add_edges(graph, particles)
    # Split the graph into lineages.
    data = _split_into_lineages(graph)
    del graph  # # Redondant with the subgraphs.

    # Create a Pycellin model.
    md = _create_metadata(
        space_unit, pixel_width, pixel_height, pixel_depth, time_unit, time_step
    )
    fd = _create_FeaturesDeclaration(features, md)
    model = Model(md, fd, Data(data))

    return model


if __name__ == "__main__":

    folder = "E:/Pasteur/Code/trackpy-examples-master/sample_data/"
    tracks = "FakeTracks_trackpy.pkl"

    df = pd.read_pickle(folder + tracks)
    print(df.shape)
    print(df.head())

    model = load_trackpy_dataframe(df)
    print(model.metadata)
    # for lin in model.get_cell_lineages():
    #     lin.plot(node_hover_features=["cell_ID", "frame", "particle"])
