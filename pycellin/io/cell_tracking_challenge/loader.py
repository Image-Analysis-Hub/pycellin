#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from itertools import pairwise
from pathlib import Path
from pkg_resources import get_distribution
from typing import Any, Tuple, List, Dict

import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.feature import FeaturesDeclaration, Feature
from pycellin.classes.data import CoreData
from pycellin.classes.lineage import CellLineage

# TODO: add CTC file format description
# TODO: add FeaturesDeclaration and create proper model
# TODO: decide on the name of the standard Pycellin features
# I think lower case is easier to read and allows for occasional use
# of upper case for abreviations.
# Snake case would be consistent with Python naming conventions.


def _read_track_line(
    line: str,
    current_node_id: int,
) -> Tuple[List[Tuple[int, Dict[str, Any]]], int]:
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

    # Creating the nodes of the current track, with their respective attributes.
    nodes = []
    for frame in range(start_frame, end_frame + 1):
        node_attrs = {
            "ID": current_node_id,
            "FRAME": frame,
            "TRACK": track_id,
            "PARENT": parent_track,
        }
        nodes.append((current_node_id, node_attrs))
        current_node_id += 1

    return nodes, current_node_id


def _add_nodes_and_edges(
    graph: nx.DiGraph,
    nodes: List[Tuple[int, Dict[str, Any]]],
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
    nodes: List[Tuple[int, Dict[str, Any]]],
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

    # Linking the current track and the parent track.
    if parent_track != 0:
        # Finding the last node of the parent track.
        parent_nodes = [
            (node, data["FRAME"])
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
    lineage.graph["TRACK_ID"] = lineage_id
    for _, data in lineage.nodes(data=True):
        data["TRACK_ID"] = lineage_id

        # Removing attributes that are not useful anymore.
        if "TRACK" in data:
            del data["TRACK"]
        if "PARENT" in data:
            del data["PARENT"]


def load_CTC_file(
    file_path: str,
) -> Model:

    metadata = {}
    metadata["Name"] = Path(file_path).stem
    metadata["Provenance"] = "CTC"
    metadata["Date"] = datetime.now()
    metadata["Pycellin_version"] = get_distribution("pycellin").version

    feat_declaration = FeaturesDeclaration()

    graph = nx.DiGraph()
    current_node_id = 0
    with open(file_path) as file:
        for line in file:
            nodes, current_node_id = _read_track_line(line, current_node_id)
            _add_nodes_and_edges(graph, nodes)
            _merge_tracks(graph, nodes)

    # We want one lineage per connected component of the graph.
    lineages = [
        CellLineage(graph.subgraph(c).copy())
        for c in nx.weakly_connected_components(graph)
    ]

    # Adding a unique TRACK_ID to each lineage and their nodes.
    lin_id = 0  # lineage ID
    for lin in lineages:
        _update_node_attributes(lin, lin_id)
        lin_id += 1

    for lin in lineages:
        print(f'{lin.graph["TRACK_ID"]} - {lin}')
        lin.plot_with_plotly()

    # model = Model(metadata, feat_declaration, data)
    # return model


if __name__ == "__main__":

    ctc_file = "C:/Users/haiba/Documents/01_RES/res_track.txt"
    model = load_CTC_file(ctc_file)
