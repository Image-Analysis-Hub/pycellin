#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from importlib.metadata import version
from pathlib import Path
import pickle
from typing import Tuple

import networkx as nx

# Small change of API between version 2 and 3 of networkx.
# Cf https://networkx.org/documentation/stable/release/migration_guide_from_2.x_to_3.0.html
NX_VERSION = version("networkx")

if NX_VERSION.startswith("2."):

    def load_graph(path: str) -> nx.DiGraph:
        return nx.read_gpickle(path)

    def save_graph(graph: nx.DiGraph, path: str):
        nx.write_gpickle(graph, path, protocol=5)

elif NX_VERSION.startswith("3."):

    def load_graph(path: Path) -> nx.DiGraph:
        with open(path, "rb") as f:
            graph = pickle.load(f)
        return graph

    def save_graph(graph: nx.DiGraph, path: str):
        with open(path, "wb") as f:
            pickle.dump(graph, f, pickle.HIGHEST_PROTOCOL)

else:
    err = (
        f"Unsupported networkx version ({NX_VERSION}). "
        "Version 2.x or 3.x is required."
    )
    raise RuntimeError(err)


def load_graphs(dir: str) -> Tuple(list[nx.DiGraph], list[str]):
    """Load all the files identified as graphs (.gz) from a directory.

    The two output lists are aligned.

    Parameters
    ----------
    dir : str
        Directory containing the graphs to load.

    Returns
    -------
    list of nx.DiGraph
        The graphs that have been loaded.
    list of str
        The files from which the graphs have been loaded.
    """
    graphs = []
    files = []
    for f in Path(dir).glob("*.gz"):
        graphs.append(load_graph(f))
        files.append(f)
    return graphs, files


def export_graph(graph: nx.DiGraph, xmlpath: str):
    """Export a graph object as a gpickle file.

    The graph is exported in the same folder than the XML file
    it originates from. The gpickle is named after the XML file and the
    graph name.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph to save.
    xmlpath : str
        Path of the XML file of the graph.
    """
    xmlpath = Path(xmlpath)

    # Determining how to name the graph file.
    if graph.number_of_nodes() == 1:
        # This can happen when args.keep_all_spots is set to True. In that
        # case, there will be unconnected nodes. Each node is a graph by
        # itself but the graph is unnamed. So we're using the node ID instead
        # of the graph name.
        node_id = [nid for _, nid in graph.nodes(data="ID")][0]
        output = xmlpath.with_name(xmlpath.stem + f"_Node_{node_id}.gz")
    elif nx.number_weakly_connected_components(graph) != 1:
        # This can happen when args.one_graph is set to True. In that case,
        # all tracks are regrouped in a same disconnected graph. The name of
        # the graph is the name of the XML file.
        output = xmlpath.with_name(xmlpath.stem + ".gz")
    else:
        output = xmlpath.with_name(xmlpath.stem + f"_{graph.graph['name']}.gz")

    save_graph(graph, output)
