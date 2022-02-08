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
    element.clear()  # We won't need it anymore so we free up some memory.
    # .clear() does not delete the element: it only removes all subelements 
    # and clears or sets to `None` all attributes.
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
    """Add edges and their attributes to a graph.

    All the elements that are descendants of `ancestor` are explored.

    Args:
        graph (nx.Graph): Graph on which to add edges.
        iterator (ET.iterparse): XML element iterator.
        ancestor (ET.Element): Element encompassing the information to add.

    Returns:
        list(dict): A dictionary of attributes for every track.
    """
    tracks_attributes = []
    event, element = next(iterator)
    # Initialisation of current track information.
    if element.tag == 'Track' and event == 'start':
        # This condition is a bit of an overkill since the XML structure
        # SHOULD stay the same but better safe than sorry.
        tracks_attributes.append(element.attrib)
        current_track_id = element.attrib['TRACK_ID']

    while (event, element) != ('end', ancestor):
        event, element = next(iterator)

        # Saving the current track information.
        if element.tag == 'Track' and event == 'start':
            tracks_attributes.append(element.attrib)
            current_track_id = element.attrib['TRACK_ID']

        # Edge creation.
        if event == 'start' and element.tag == 'Edge': 
            entry_node = element.attrib.pop('SPOT_SOURCE_ID')
            exit_node = element.attrib.pop('SPOT_TARGET_ID')
            graph.add_edge(entry_node, exit_node, attr=element.attrib)
            element.clear()
            # Adding the current track ID to the nodes of the newly created
            # edge. This will be useful later to filter nodes by track and
            # add the saved tracks attributes (as returned by this method).
            graph.nodes[entry_node]['TRACK_ID'] = current_track_id
            graph.nodes[exit_node]['TRACK_ID'] = current_track_id
            
    return tracks_attributes


def add_tracks_info(graphs, tracks_attributes):
    """Add track attributes to each corresponding graph.

    Args:
        graphs (nx.Graph): List of graphs to update.
        tracks_attributes (list(dict)): Dictionaries of tracks attributes.

    Returns:
        list(nx.Graph): List of the updated graphs.
    """
    updated_graphs = []
    for i, graph in enumerate(graphs):

        # Finding the dict of attributes matching the track.
        tmp = set(t for n, t in graph.nodes(data='TRACK_ID'))
        assert len(tmp) == 1, ('Impossible state: several IDs for one track')
        current_track_id = list(tmp)[0]
        current_track_attr = [d_attr for d_attr in tracks_attributes 
                              if d_attr['TRACK_ID'] == current_track_id][0]

        # Adding the attributes to the graph.
        for k, v in current_track_attr.items():
            graph.graph[k] = v
        updated_graphs.append(graph)

    return updated_graphs
             

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("xml", help="path of the XML file to process")
    parser.add_argument("-s", "--keep_all_spots", action="store_true",
                        help="keep the spots filtered out in TrackMate")
    args = parser.parse_args()

    # TODO: filter out spurious tracks by default. Add an option to keep them.

    # Creation of a graph that will hold all the tracks described
    # in the XML file. This means that if there's more than one track,
    # the resulting graph will be disconnected.
    graph = nx.Graph()

    # So as not to load the entire XML file into memory at once, we're
    # using an iterator to browse over the tags one by one.
    # The events 'start' and 'end' correspond respectively to the opening
    # and the closing of the considered tag.
    it = ET.iterparse(args.xml, events=['start', 'end'])
    _, root = next(it)  # Saving the root of the tree for later cleaning.

    for event, element in it:

        # Adding the model information as graph attributes.
        if element.tag == 'Model' and event == 'start':
            graph = add_model_info(graph, element)
            root.clear()  # Cleaning the tree to free up some memory.
            # All the browsed subelements of `root` are deleted.

        # Adding the spots as nodes.
        if element.tag == 'AllSpots' and event == 'start':
            add_all_nodes(graph, it, element)
            root.clear()

        # Adding the tracks as edges.
        if element.tag == 'AllTracks' and event == 'start':
            tracks_attributes = add_all_edges(graph, it, element)
            root.clear()

            # Removal of filtered spots / nodes.
            if not args.keep_all_spots:
                # Those nodes belong to no tracks: they have a degree of 0.
                lone_nodes = [n for n, d in graph.degree if d == 0]
                graph.remove_nodes_from(lone_nodes)

        # Filtering out tracks and adding tracks attribute.
        if element.tag == 'FilteredTracks' and event == 'start':

            # Subgraphs creation.
            # One subgraph is created per track, so each subgraph is
            # a connected component of `graph`.
            graphs = [graph.subgraph(c).copy() 
                      for c in nx.connected_components(graph)]
            del graph  # Redondant with the subgraphs.

            # Adding the tracks attributes as graphs attributes.
            graphs = add_tracks_info(graphs, tracks_attributes)

        # TODO: add Settings as graph attributes. Is everything relevant?

    # Very basic visualisation.
    for graph in graphs:
        print(graph)
        print(graph.graph)
        nx.draw(graph, with_labels=True, font_weight='bold')
        plt.show()