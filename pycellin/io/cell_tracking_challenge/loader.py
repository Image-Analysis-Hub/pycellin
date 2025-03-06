#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
loader.py

This module is part of the Pycellin package.

This module provides functions to load and process Cell Tracking Challenge (CTC) files
into Pycellin models. It includes a function to load a CTC file into Pycellin model
and helper functions to create metadata, features, and lineage graphs.

References:
- CTC website: https://celltrackingchallenge.net/
- CTC tracking annotations conventions:
https://public.celltrackingchallenge.net/documents/Naming%20and%20file%20content%20conventions.pdf
"""

from datetime import datetime
import importlib
from itertools import pairwise
from pathlib import Path
from typing import Any, Tuple

import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.feature import (
    FeaturesDeclaration,
    cell_ID_Feature,
    frame_Feature,
    lineage_ID_Feature,
)
from pycellin.classes.data import Data
from pycellin.classes.lineage import CellLineage


def _create_metadata(
    file_path: str,
) -> dict[str, Any]:
    """
    Create a dictionary of basic Pycellin metadata for a given file.

    Parameters
    ----------
    file_path : str
        The path to the file for which metadata is being created.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the generated metadata.
    """
    metadata = {}
    metadata["name"] = Path(file_path).stem
    metadata["file_location"] = file_path
    metadata["provenance"] = "CTC"
    metadata["date"] = datetime.now()
    metadata["time_unit"] = "frame"
    metadata["time_step"] = 1
    # TODO: is it possible to get space_unit with the labels data?
    # or a better time_unit with the images metadata?
    # or maybe ask the user...
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


def _read_track_line(
    line: str,
    current_node_id: int,
) -> Tuple[list[Tuple[int, dict[str, Any]]], int]:
    """
    Parse a single track line to generate a list of the nodes present in the track.

    This function takes a line of text representing a track in the CTC format.
    It generates a node with a globally unique node ID for each frame within
    the start and end frame range, and stores the node's attributes in a dictionary.

    Parameters
    ----------
    line : str
        A string containing space-separated values representing a track.
    current_node_id : int
        The starting node ID to use for the first node in this track,
        which will be incremented for each subsequent node.

    Returns
    -------
    Tuple[List[Tuple[int, Dict[str, Any]]], int]
        A tuple containing a list of nodes generated from the track line,
        where each node is represented as a tuple containing the node ID
        and a dictionary of attributes, and the next available node ID
        after generating all nodes for this track.
    """
    track_id, start_frame, end_frame, parent_track = [int(el) for el in line.split()]
    nodes = []
    for frame in range(start_frame, end_frame + 1):
        node_attrs = {
            "cell_ID": current_node_id,
            "frame": frame,
            "TRACK": track_id,
            "PARENT": parent_track,
        }
        nodes.append((current_node_id, node_attrs))
        current_node_id += 1
    return nodes, current_node_id


def _add_nodes_and_edges(
    graph: nx.DiGraph,
    nodes: list[Tuple[int, dict[str, Any]]],
) -> None:
    """
    Add nodes and edges to a directed graph from a list of nodes.

    This function adds all the nodes in the list to the specified directed graph.
    Then, for each pair of consecutive nodes in the list,
    it adds a directed edge from the first node to the second.

    Parameters
    ----------
    graph : nx.DiGraph
        The directed graph to which the nodes and edges will be added.
    nodes : List[Tuple[int, Dict[str, Any]]]
        A list of tuples, where each tuple contains an integer representing
        the node identifier and a dictionary representing the node's attributes.
    """
    graph.add_nodes_from(nodes)
    for n1, n2 in pairwise(nodes):
        graph.add_edge(n1[0], n2[0])


def _merge_tracks(
    graph: nx.DiGraph,
    nodes: list[Tuple[int, dict[str, Any]]],
) -> None:
    """
    Merge a track with its parent track in the directed graph.

    This is done by adding an edge from the last node of the parent track
    to the first node of the current track.

    Parameters
    ----------
    graph : nx.DiGraph
        The directed graph to which the tracks belong.
    nodes : List[Tuple[int, Dict[str, Any]]]
        A list of tuples, where each tuple contains an integer representing
        the node identifier and a dictionary representing the node's attributes.
    """
    parent_track = nodes[0][1]["PARENT"]
    if parent_track != 0:
        # Finding the last node of the parent track.
        parent_nodes = [
            (node, data["frame"])
            for node, data in graph.nodes(data=True)
            if data["TRACK"] == parent_track
        ]
        parent_node = sorted(parent_nodes, key=lambda x: x[1])[-1]
        graph.add_edge(parent_node[0], nodes[0][0])


def _update_node_attributes(
    lineage: CellLineage,
    lineage_id: int,
) -> None:
    """
    Update the nodes attributes in a lineage graph.

    This function assigns a new unique track ID to the entire lineage
    and to each node within it. It also cleans up the node attributes
    by removing the 'TRACK' and 'PARENT' attributes, that were only needed
    for graph construction.

    Parameters
    ----------
    lineage : CellLineage
        The lineage graph whose node attributes are to be updated.
    lineage_id : int
        The new track ID to be assigned to the lineage graph and its nodes.
    """
    lineage.graph["lineage_ID"] = lineage_id
    for _, data in lineage.nodes(data=True):
        # Removing obsolete attributes.
        if "TRACK" in data:
            del data["TRACK"]
        if "PARENT" in data:
            del data["PARENT"]


def load_CTC_file(
    file_path: str,
) -> Model:
    """
    Create a Pycellin model out of a Cell Tracking Challenge (CTC) text file.

    Only track topology is read: no cell segmentations are extracted
    from associated label images.
    The CTC tracking format does not support fusion events and does not allow
    gaps right after division events.

    Parameters
    ----------
    file_path : str
        The path to the CTC file that contains the tracking data.

    Returns
    -------
    Model
        The created Pycellin model.
    """
    graph = nx.DiGraph()
    current_node_id = 0
    with open(file_path) as file:
        nodes_from_tracks = []
        # The lines in the file are read sequentially to create the nodes.
        # However, nothing ensures that parent nodes are created before
        # being referenced by their children.
        # nodes_from_tracks keeps track of the nodes created for each track
        # so that they can be merged later.
        for line in file:
            nodes, current_node_id = _read_track_line(line, current_node_id)
            nodes_from_tracks.append(nodes)
            _add_nodes_and_edges(graph, nodes)

    # Merging tracks that are part of the same lineage.
    for nodes in nodes_from_tracks:
        _merge_tracks(graph, nodes)
    # We want one lineage per connected component of the graph.
    lineages = [
        CellLineage(graph.subgraph(c).copy())
        for c in nx.weakly_connected_components(graph)
    ]

    # Adding a unique lineage_ID to each lineage and their nodes.
    lin_ID = 0
    for lin in lineages:
        _update_node_attributes(lin, lin_ID)
        lin_ID += 1

    data = {}
    for lin in lineages:
        if "lineage_ID" in lin.graph:
            data[lin.graph["lineage_ID"]] = lin
        else:
            assert len(lin) == 1, "Lineage ID not found and not a one-node lineage."
            node = [n for n in lin.nodes][0]
            # We set the ID of a one-node lineage to the negative of the node ID.
            lin_ID = -node
            lin.graph["lineage_ID"] = lin_ID
            data[lin_ID] = lin

    model = Model(
        _create_metadata(file_path), _create_FeaturesDeclaration(), Data(data)
    )
    return model


if __name__ == "__main__":

    ctc_file = "sample_data/FakeTracks_TMtoCTC.txt"
    ctc_file = "sample_data/Ecoli_growth_on_agar_pad_TMtoCTC.txt"
    ctc_file = (
        "/mnt/data/Films_Laure/Benchmarks/CTC/"
        "EvaluationSoftware/testing_dataset/03_RES/res_track.txt"
    )
    model = load_CTC_file(ctc_file)
    print(model)
    print(model.feat_declaration)
    print(model.data)

    for lin_id, lin in model.data.cell_data.items():
        print(f"{lin_id} - {lin}")
        lin.plot()

    # model.add_cycle_data()
    # for lin_id, lin in model.data.cycle_data.items():
    #     lin.plot()

    # print(model.data.cell_data[1].nodes(data=True))
