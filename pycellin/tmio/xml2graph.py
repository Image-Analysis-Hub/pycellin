#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Create networkX directed graphs from TrackMate results (XML file).
"""


import argparse
from importlib.metadata import version
from pathlib import Path
import pickle
import time

import matplotlib.pyplot as plt
import networkx as nx

from xml_utils import read_TrackMate_XML

# TODO: right now there's one graph per track. So one XML => several graphs.
# What would be better is to have by default only one file: a forest of graph.
# With the option to specifically ask for one file per graph.


def export_graph(graph: nx.DiGraph, input: str):
    """Export a graph object as a gpickle file.

    The graph is exported in the same folder than the XML file
    it originates from. The gpickle is named after the XML file and the
    graph name.

    Args:
        graph (nx.DiGraph): The graph to export.
        input (str): Path of the XML file of the graph.
    """
    input = Path(input)
    if graph.number_of_nodes() == 1:
        # This can happen when args.keep_all_spots is set to True. In that
        # case, there will be unconnected nodes. Each node is a graph by
        # itself but the graph is unnamed. So we're using the node ID instead
        # of the graph name.
        node_id = [nid for _, nid in graph.nodes(data="ID")][0]
        output = input.with_name(input.stem + f"_Node_{node_id}.gz")
    elif nx.number_weakly_connected_components(graph) != 1:
        # This can happen when args.one_graph is set to True. In that case,
        # all tracks are regrouped in a same disconnected graph. The name of
        # the graph is the name of the XML file.
        output = input.with_name(input.stem + ".gz")
    else:
        output = input.with_name(input.stem + f"_{graph.graph['name']}.gz")

    # Small change of API between version 2 and 3 of networkx.
    # Cf https://networkx.org/documentation/stable/release/migration_guide_from_2.x_to_3.0.html
    nx_version = version("networkx")
    if nx_version.startswith("2."):
        nx.write_gpickle(graph, output, protocol=5)
    elif nx_version.startswith("3."):
        with open(output, "wb") as f:
            pickle.dump(graph, f, pickle.HIGHEST_PROTOCOL)
    else:
        err = (
            f"Unsupported networkx version ({nx_version}). "
            "Version 2.x or 3.x is required."
        )
        raise RuntimeError(err)


if __name__ == "__main__":
    start = time.process_time()
    print("Starting conversion...")

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help=("TrackMate xml file to process"))
    parser.add_argument(
        "-s",
        "--keep_all_spots",
        action="store_true",
        help=("keep the spots that were filtered out in TrackMate"),
    )
    parser.add_argument(
        "-t",
        "--keep_all_tracks",
        action="store_true",
        help=("keep the tracks that were filtered out in TrackMate"),
    )
    parser.add_argument(
        "-p", "--plot_graph", action="store_true", help="plot the obtained graphs"
    )
    parser.add_argument(
        "-o",
        "--one_graph",
        action="store_true",
        help=(
            "create only one graph instead of one per track. "
            "Useful when there is no tracking in the xml, only spots detection."
        ),
    )
    args = parser.parse_args()

    graphs = read_TrackMate_XML(
        args.input, args.keep_all_spots, args.keep_all_tracks, args.one_graph
    )

    for graph in graphs:
        export_graph(graph, args.input)
    p_time = time.process_time() - start
    print(f"...done in {(p_time // 60):.0f} min {(p_time % 60):.2f} s.")
    print(
        f'{len(graphs)} track{"s have" if len(graphs) > 1 else " has"}'
        f" been exported."
    )

    # Basic visualisation.
    if args.plot_graph:
        for graph in graphs:
            pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog="dot")
            nx.draw(graph, pos, with_labels=True, arrows=True, font_weight="bold")
            plt.show()
