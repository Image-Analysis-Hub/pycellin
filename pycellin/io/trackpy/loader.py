#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
loader.py

This module is part of the pycellin package.

This module provides functions to load and process trackpy data into pycellin models.
It includes a function to load a trackpy file into a pycellin model and helper functions
to create metadata, properties, and lineage graphs.

References:
- trackpy: D. B. Allan, T. Caswell, N. C. Keim, C. M. van der Weland R. W. Verweij,
“soft-matter/trackpy: v0.6.4”. Zenodo, Jul. 10, 2024. doi: 10.5281/zenodo.12708864.
- trackpy GitHub: https://github.com/soft-matter/trackpy
"""

import importlib
from datetime import datetime
from itertools import pairwise
from typing import Any

import networkx as nx
import pandas as pd

from pycellin.classes import (
    CellLineage,
    Data,
    Model,
    PropsMetadata,
)
from pycellin.graph.properties.core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_frame_property,
    create_lineage_id_property,
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
        CellLineage(graph.subgraph(c).copy()) for c in nx.weakly_connected_components(graph)
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
    Create a dictionary of basic pycellin metadata for a given file.

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


def _create_PropsMetadata(props: list[str], metadata: dict[str, Any]) -> PropsMetadata:
    """
    Return a PropsMetadata object populated with the needed properties.

    Parameters
    ----------
    props : list[str]
        List of properties to be included in the PropsMetadata.
    metadata : dict[str, Any]
        Metadata dictionary containing information about the data.

    Returns
    -------
    PropsMetadata
        An instance of PropsMetadata populated with pycellin and trackpy properties.
    """
    props_md = PropsMetadata()

    # Pycellin mandatory properties.
    cell_ID_prop = create_cell_id_property()
    frame_prop = create_frame_property()
    lin_ID_prop = create_lineage_id_property()
    for prop in [cell_ID_prop, frame_prop, lin_ID_prop]:
        props_md._add_prop(prop)
        props_md._protect_prop([prop.identifier])

    # Trackpy properties.
    for axis in ["x", "y", "z"]:
        if axis in props:
            prop = create_cell_coord_property(
                unit=metadata["space_unit"], axis=axis, provenance="trackpy"
            )
            props_md._add_prop(prop)
    # TODO: add props for other trackpy properties

    return props_md


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
    Load a trackpy DataFrame into a pycellin model.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame containing trackpy data.

    Returns
    -------
    Model
        A pycellin model populated with the trackpy data.
    """
    # Build the lineages.
    graph = nx.DiGraph()
    _add_nodes(graph, df)
    props = df.columns.to_list()
    particles = df["particle"].unique()
    del df  # Free memory.
    _add_edges(graph, particles)
    # Split the graph into lineages.
    data = _split_into_lineages(graph)
    del graph  # # Redondant with the subgraphs.

    # Create a pycellin model.
    md = _create_metadata(space_unit, pixel_width, pixel_height, pixel_depth, time_unit, time_step)
    fd = _create_PropsMetadata(props, md)
    model = Model(md, fd, Data(data))

    return model


if __name__ == "__main__":
    folder = "E:/Pasteur/Code/trackpy-examples-master/sample_data/"
    tracks = "FakeTracks_trackpy.pkl"

    df = pd.read_pickle(folder + tracks)
    print(df.shape)
    print(df.head())

    model = load_trackpy_dataframe(df)
    print(model.model_metadata)
    # for lin in model.get_cell_lineages():
    #     lin.plot(node_hover_props=["cell_ID", "frame", "particle"])
