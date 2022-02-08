#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Importation of ImageJ TrackMate results (XML file) as a Python network
for tracks analysis.
"""

__author__ = "Laura Xénard"
__contact__ = "laura.xenard@pasteur.fr"
__copyright__ = "GNU GPLv3"
__date__ = "2022-02-07"
__version__ = "0.1"

import argparse
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt
import networkx as nx


def add_model_info(graph, element):
    """Add graph attributes from an XML element.

    Args:
        graph (nx.Graph): Graph on which to add attributes.
        element (ET.Element): Element holding the information to be added.
        
    Returns:
        nx.Graph: The updated graph.
    """
    for k, v in element.attrib.items():
        graph.graph[k] = v
    element.clear()
    return graph


def add_all_nodes(graph, iterator, ancestor):
    """Add nodes and their attributes to a graph.

    All the elements that are descendants of `ancestor` are explored.

    Args:
        graph (nx.Graph): Graph on which to add nodes.
        iterator (ET.iterparse): XML element iterator.
        ancestor (ET.Element): Element encompassing the information to add.
    """
    event, element = next(iterator)

    while (event, element) != ('end', ancestor):
        event, element = next(iterator)
        if event == 'start' and element.tag == 'Spot': 
            node_id = element.attrib.pop('ID')
            graph.add_node(node_for_adding=node_id, attr=element.attrib)
            element.clear()


def add_all_edges(graph, iterator, ancestor):
    """Add edges andnx.draw(graph, with_labels=True, font_weight='bold')
    plt.show().iterparse): XML element iterator.
        ancestor (ET.Element): Element encompassing the information to add.
    """
    event, element = next(iterator)
    while (event, element) != ('end', ancestor):
        event, element = next(iterator)
        if event == 'start' and element.tag == 'Edge': 
            entry_node = element.attrib.pop('SPOT_SOURCE_ID')
            exit_node = element.attrib.pop('SPOT_TARGET_ID')
            graph.add_edge(entry_node, exit_node, attr=element.attrib)
            element.clear()
               

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("xml", help="path of the XML file to process")
    args = parser.parse_args()

    # Creation of a graph that will hold all the tracks described
    # in the XML file. This means that if there's more than one track,
    # the resulting graph will be disconnected.
    graph = nx.Graph()

    # So as not to load the entire XML file into memory at once, we're 
    # using an iterator to browse over the tags one by one.
    # The events 'start' and 'end' correspond respectively to the opening 
    # and the closing of the considered tag.
    it = ET.iterparse(args.xml, events=['start', 'end'])

    for event, element in it:

        # Adding the model information as graph attributes.
        if element.tag == 'Model' and event == 'start':
            graph = add_model_info(graph, element)

        # Adding the spots as nodes.
        if element.tag == 'AllSpots' and event == 'start':
            add_all_nodes(graph, it, element)

        # Adding the tracks as edges.
        if element.tag == 'AllTracks' and event == 'start':
            add_all_edges(graph, it, element)




    print(graph)
    print(nx.number_connected_components(graph))    

    nx.draw(graph, with_labels=True, font_weight='bold')
    plt.show()
