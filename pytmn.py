#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Importation of ImageJ TrackMate results (XML file) as a Python network
for tracks analysis.
"""

__author__ = "Laura Xénard"
__contact__ = "laura.xenard@pasteur.fr"
__copyright__ = "GNU GPLv3"
__date__ = "2022-02-07"
__version__ = "0.2"

import argparse
from pathlib import Path
import time

import matplotlib.pyplot as plt
import networkx as nx

import XML_reader


def export_graph(graph, input):
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
        node_id = [nid for _, nid in graph.nodes(data='ID')][0]
        output = input.with_name(input.stem + f"_Node_{node_id}.gz")
    elif nx.number_weakly_connected_components(graph) != 1:
        # This can happen when args.one_graph is set to True. In that case,
        # all tracks are regrouped in a same disconnected graph. The name of
        # the graph is the name of the XML file.
        output = input.with_name(input.stem + ".gz")
    else:
        output = input.with_name(input.stem + f"_{graph.graph['name']}.gz")
    nx.write_gpickle(graph, output, protocol=5)


if __name__ == "__main__":

    start = time.process_time()
    print('Starting conversion...')

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help=("path of the file to process, TrackMate"
                                       " xml or tracks gpickle"))
    parser.add_argument("-r", "--read_xml", action="store_true",
                        help=("read the given TrackMate xml file, convert the "
                              "tracks to directed graphs and export them to "
                              "gpickle files"))
    parser.add_argument("-w", "--write_xml", action="store_true",
                        help=("read the given gpickle file and export the "
                              "tracks in a TrackMate xml file"))
    parser.add_argument("-s", "--keep_all_spots", action="store_true",
                        help=("in reader mode, keep the spots filtered out in "
                              "TrackMate"))
    parser.add_argument("-t", "--keep_all_tracks", action="store_true",
                        help=("in reader mode, keep the tracks filtered out in"
                              " TrackMate"))
    parser.add_argument("-p", "--plot_graph", action="store_true",
                        help="plot the obtained graphs")
    parser.add_argument("-o", "--one_graph", action="store_true",
                        help=("in reader mode, create only one graph instead "
                              "of one per track. Useful when there is no "
                              "tracking in the xml, only spots detection."))
    args = parser.parse_args()

    # From TM xml to directed graphs.
    if args.read_xml:
        graphs = XML_reader.read_model(args.input, args.keep_all_spots,
                                       args.keep_all_tracks,
                                       args.one_graph)

        for graph in graphs:
            export_graph(graph, args.input)
        p_time = time.process_time() - start
        print(f'...done in {(p_time // 60):.0f} min {(p_time % 60):.2f} s.')
        print(f'{len(graphs)} track{"s have" if len(graphs) > 1 else " has"}'
              f' been exported.')

    # From directed graphs to TM xml.
    if args.write_xml:
        pass

    # Basic visualisation.
    if args.plot_graph:
        for graph in graphs:
            pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog='dot')
            nx.draw(graph, pos, with_labels=True, arrows=True,
                    font_weight='bold')
            plt.show()
