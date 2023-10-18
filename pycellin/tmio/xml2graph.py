#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Create networkX directed graphs from TrackMate results (XML file).
"""

import argparse
from importlib.metadata import version
from pathlib import Path
import pickle
import time

import matplotlib.pyplot as plt
import networkx as nx

from xml_utils import read_TrackMate_XML
from pycellin.graph.io import export_graph

# TODO: right now there's one graph per track. So one XML => several graphs.
# What would be better is to have by default only one file: a forest of graph.
# With the option to specifically ask for one file per graph.

# TODO: add output argument to be able to decide where to save the files.


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
