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
import xml.etree.ElementTree as et

import networkx as nx


def add_model_info(graph, element):
    """Add graph attributes from an XML element.

    Args:
        graph (nx.Graph): Graph on which to add attributes.
        element (et.Element): Element holding the information to be added.

    Returns:
        nx.Graph: The updated graph.
    """
    
    for k, v in element.attrib.items():
        graph.graph[k] = v
    return graph
   

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("xml", help="path of the XML file to process")
    args = parser.parse_args()

    # Creation of a graph that will hold all the tracks described
    # in the XML file. This means that if there's more than one track,
    # the resulting graph will be disconnected.
    graph = nx.Graph()

    # So as not to load the entire XML file into memory, we're using an
    # iterator to browse over the tags one by one.
    # The events 'start' and 'end' correspond respectively to the opening 
    # and the closing of the considered tag.
    it = et.iterparse(args.xml, events=['start', 'end'])

    for event, element in it:

        # Adding the model information as graph attributes.
        if element.tag == 'Model' and event == 'start':
            graph = add_model_info(graph, element)

        
            

    print(graph)
    print(graph.graph)
            
