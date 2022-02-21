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
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt
import networkx as nx


def add_graph_attrib_from_element(graph, element):
    """Add graph attributes from an XML element.

    Args:
        graph (nx.DiGraph): Graph on which to add attributes.
        element (ET.Element): Element holding the information to be added.
        
    Returns:
        nx.DiGraph: The updated graph.
    """
    graph.graph['Model'] = element.attrib
    # for k, v in element.attrib.items():
    #     graph.graph[k] = v
    element.clear()  # We won't need it anymore so we free up some memory.
    # .clear() does not delete the element: it only removes all subelements 
    # and clears or sets to `None` all attributes.
    return graph

def get_features_dict(iterator, ancestor):
    """Get all the features of ancestor and return them as a dictionary.

    Args:
        iterator (ET.iterparse): XML element iterator.
        ancestor (ET.Element): Element encompassing the information to add.

    Returns:
        dict: Features contained in the ancestor element.
    """
    features = dict()
    event, element = next(iterator)  # Feature.
    while (event, element) != ('end', ancestor):
        if element.tag == 'Feature' and event == 'start':
            try:
                features[element.attrib['feature']] = element.attrib
            except KeyError as err:
                print(f"No key {err} in the attributes of "
                      f"current element '{element.tag}'. "
                      f"Not adding this feature to the graph.")
        element.clear()
        event, element = next(iterator)
    return features
            

def add_all_features(graph, iterator, ancestor) -> nx.DiGraph:
    """Add all the model features and their attributes to the graph.

    The model features are divided in 3 categories: spots, edges and 
    tracks features.
    Those features are regrouped under the tag FeatureDeclarations.

    Args:
        graph (nx.DiGraph): Graph on which to add features.
        iterator (ET.iterparse): XML element iterator.
        ancestor (ET.Element): Element encompassing the information to add.

    Returns:
        nx.DiGraph: The updated graph.
    """
    event, element = next(iterator)
    while (event, element) != ('end', ancestor):
        features = get_features_dict(iterator, element)
        graph.graph['Model'][element.tag] = features
        element.clear()
        event, element = next(iterator)
    return graph   


def convert_attributes(attributes: dict, features: dict):
    """Convert the values of `attributes` from string to int or float.

    The type to convert to is given by the dictionary of features with
    the key 'isint'.    

    Args:
        attributes (dict): The dictionary whose values we want to convert.
        features (dict): The dictionary holding the type information to use.

    Raises:
        KeyError: If the 'isint' feature attribute doesn't exist.
        ValueError: If the value of the 'isint' feature attribute is invalid.
    """
    for key in attributes:
        if key == 'ID':
            attributes[key] = int(attributes[key])  # IDs are always integers.
        elif key in features:
            if 'isint' not in features[key]:
                raise KeyError(f"No 'isint' feature attribute in "
                               f"FeatureDeclarations.")
            if features[key]['isint'].lower() == 'true':
                attributes[key] = int(attributes[key])
            elif features[key]['isint'].lower() == 'false':
                try: 
                    attributes[key] = float(attributes[key])
                except ValueError:
                    pass  # Not an int nor a float so we let it be.
            else:
                raise ValueError(f"'{features[key]['isint']}' is an invalid"
                                 f" feature attribute value for 'isint'.")


def add_ROI_coordinates(element):
    """Extract, format and add ROI coordinates to the element attributes.

    Args:
        element (ET.Element): Element from which to extract ROI coordinates.
    """
    try:
        n_points = int(element.attrib['ROI_N_POINTS'])
    except KeyError as err:
        print(f"No key {err} in the attributes of current element "
              f"'{element.tag}'. ")
    else:        
        points_coordinates = element.text.split()
        points_coordinates = [float(x) for x in points_coordinates]
        points_dimension = len(points_coordinates) // n_points
        it = [iter(points_coordinates)] * points_dimension
        points_coordinates = list(zip(*it))
        element.attrib['ROI_N_POINTS'] = points_coordinates

           
def add_all_nodes(graph, iterator, ancestor):
    """Add nodes and their attributes to a graph.

    All the elements that are descendants of `ancestor` are explored.

    Args:
        graph (nx.DiGraph): Graph on which to add nodes.
        iterator (ET.iterparse): XML element iterator.
        ancestor (ET.Element): Element encompassing the information to add.
    """
    event, element = next(iterator)
    while (event, element) != ('end', ancestor):
        event, element = next(iterator)          
        if element.tag == 'Spot' and event == 'end': 
            # All items in element.attrib are parsed as strings but most
            # of them (if not all) are numbers. So we need to do a
            # conversion based on these attributes type (attribute `isint`)
            # as defined in the FeaturesDeclaration tag.
            try:
                convert_attributes(element.attrib,
                                   graph.graph['Model']['SpotFeatures'])
            except ValueError as err:
                print(f'ERROR: {err} Please check the XML file.')
                raise
            except KeyError as err:
                print(f'ERROR: {err} Please check the XML file.')
                raise

            # The ROI coordinates are not stored in a tag attribute but in
            # the tag text. So we need to extract then format them.
            add_ROI_coordinates(element)             

            # Now that all the node attributes have been updated, we can add
            # it to the graph.
            try:
                graph.add_nodes_from([(int(element.attrib['ID']),
                                       element.attrib)])
            except KeyError as err:
                print(f"No key {err} in the attributes of "
                      f"current element '{element.tag}'. "
                      f"Not adding this node to the graph.")
            finally:
                element.clear()


def add_edge_from_element(graph, element, current_track_id):
    """Add an edge and its attributes from an XML element.

    Args:
        graph (nx.DiGraph): Graph on which to add the edge.
        element (ET.Element): Element holding the information to be added.
        current_track_id (str): Track ID of the track holding the edge. 
    """
    convert_attributes(element.attrib,
                       graph.graph['Model']['EdgeFeatures'])
    try:
        entry_node = element.attrib['SPOT_SOURCE_ID']
        exit_node = element.attrib['SPOT_TARGET_ID']
    except KeyError as err:
        print(f"No key {err} in the attributes of "
              f"current element '{element.tag}'. "
              f"Not adding this edge to the graph.")
    else:
        graph.add_edge(entry_node, exit_node)
        nx.set_edge_attributes(graph, 
                               {(entry_node, exit_node): element.attrib})
        # Adding the current track ID to the nodes of the newly created
        # edge. This will be useful later to filter nodes by track and
        # add the saved tracks attributes (as returned by this method).
        graph.nodes[entry_node]['TRACK_ID'] = current_track_id
        graph.nodes[exit_node]['TRACK_ID'] = current_track_id
    finally:
        element.clear()
        

def add_all_edges(graph, iterator, ancestor):
    """Add edges and their attributes to a graph.

    All the elements that are descendants of `ancestor` are explored.

    Args:
        graph (nx.DiGraph): Graph on which to add edges.
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
        # TODO: refactor this chunk that appears twice in this method.
        convert_attributes(element.attrib,
                           graph.graph['Model']['TrackFeatures'])
        tracks_attributes.append(element.attrib)
        try:
            current_track_id = element.attrib['TRACK_ID']
        except KeyError as err:
            print(f"No key {err} in the attributes of "
                  f"current element '{element.tag}'. "
                  f"Not adding the {err} edge to the graph.")
            current_track_id = None         

    while (event, element) != ('end', ancestor):
        event, element = next(iterator)

        # Saving the current track information.
        if element.tag == 'Track' and event == 'start':
            convert_attributes(element.attrib,
                               graph.graph['Model']['TrackFeatures'])
            tracks_attributes.append(element.attrib)
            try:
                current_track_id = element.attrib['TRACK_ID']
            except KeyError as err:
                print(f"No key {err} in the attributes of "
                      f"current element '{element.tag}'. "
                      f"Not adding the {err} edge to the graph.")
                current_track_id = None

        # Edge creation.
        if element.tag == 'Edge' and event == 'start': 
            add_edge_from_element(graph, element, current_track_id)
            
    return tracks_attributes


def get_filtered_tracks_ID(iterator, ancestor):
    """Get the list of IDs of the tracks to keep.

    Args:
        iterator (ET.iterparse): XML element iterator.
        ancestor (ET.Element): Element encompassing the information to add.

    Returns:
        list(str): List of tracks ID to keep.
    """
    filtered_tracks_ID = []
    event, element = next(iterator)
    try:
        filtered_tracks_ID.append(int(element.attrib['TRACK_ID']))
    except KeyError as err:
        print(f"No key {err} in the attributes of current element "
              f"'{element.tag}'. Ignoring this track.")
        
    while (event, element) != ('end', ancestor):
        event, element = next(iterator)          
        if element.tag == 'TrackID' and event == 'start':
            try:
                filtered_tracks_ID.append(int(element.attrib['TRACK_ID']))
            except KeyError as err:
                print(f"No key {err} in the attributes of current element "
                      f"'{element.tag}'. Ignoring this track.")
            
    return filtered_tracks_ID         
    

def add_tracks_info(graphs, tracks_attributes):
    """Add track attributes to each corresponding graph.

    Args:
        graphs (list(nx.DiGraph)): List of graphs to update.
        tracks_attributes (list(dict)): Dictionaries of tracks attributes.

    Raises:
        ValueError: If several different track IDs are found for one track.

    Returns:
        list(nx.DiGraph): List of the updated graphs.
    """
    updated_graphs = []
    for graph in graphs:
        
        # Finding the dict of attributes matching the track.
        tmp = set(t_id for n, t_id in graph.nodes(data='TRACK_ID'))

        if not tmp:
            # 'tmp' is empty because there's no nodes in the current graph.
            # Even if it can't be updated, we still want to return this graph.
            updated_graphs.append(graph)
            continue
        elif tmp == {None}:
            # Happens when all the nodes do not have a TRACK_ID attribute.
            updated_graphs.append(graph)
            continue
        elif None in tmp:
            # Happens when at least one node does not have a TRACK_ID 
            # attribute, so we clean 'tmp' and carry on.
            tmp.remove(None)
        elif len(tmp) != 1:
            raise ValueError('Impossible state: several IDs for one track.')
    
        current_track_id = list(tmp)[0]
        current_track_attr = [d_attr for d_attr in tracks_attributes 
                              if d_attr['TRACK_ID'] == current_track_id][0]

        # Adding the attributes to the graph.
        for k, v in current_track_attr.items():
            graph.graph[k] = v
        updated_graphs.append(graph)

    return updated_graphs


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
    output = input.with_name(input.stem + f"_{graph.graph['name']}.gz")
    nx.write_gpickle(graph, output, protocol=5)
        
             

if __name__ == "__main__":

    start = time.process_time()
    print('Starting conversion...')

    parser = argparse.ArgumentParser()
    parser.add_argument("xml", help="path of the XML file to process")
    parser.add_argument("-e", "--export", action="store_true",
                        help="export the obtained graphs as gpickle files")
    parser.add_argument("-s", "--keep_all_spots", action="store_true",
                        help="keep the spots filtered out in TrackMate")
    parser.add_argument("-t", "--keep_all_tracks", action="store_true",
                        help="keep the tracks filtered out in TrackMate")
    parser.add_argument("-p", "--plot_graph", action="store_true",
                        help="plot the obtained graphs")
    args = parser.parse_args()

    # Creation of a graph that will hold all the tracks described
    # in the XML file. This means that if there's more than one track,
    # the resulting graph will be disconnected.
    graph = nx.DiGraph()

    # So as not to load the entire XML file into memory at once, we're
    # using an iterator to browse over the tags one by one.
    # The events 'start' and 'end' correspond respectively to the opening
    # and the closing of the considered tag.
    it = ET.iterparse(args.xml, events=['start', 'end'])
    _, root = next(it)  # Saving the root of the tree for later cleaning.

    for event, element in it:

        # Adding the model information as graph attributes.
        if element.tag == 'Model' and event == 'start':  # Add units.
            graph = add_graph_attrib_from_element(graph, element)
            root.clear()  # Cleaning the tree to free up some memory.
            # All the browsed subelements of `root` are deleted.
        # Add features declaration for spot, edge and track features.
        if element.tag == 'FeatureDeclarations' and event == 'start':
            graph = add_all_features(graph, it, element)
            root.clear()
        
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

            # Removal of filtered tracks / graphs.
            if not args.keep_all_tracks:
                id_to_keep = get_filtered_tracks_ID(it, element)
                to_remove = [n for n, t in graph.nodes(data='TRACK_ID') 
                             if t not in id_to_keep]
                graph.remove_nodes_from(to_remove)

            # Subgraphs creation.
            # One subgraph is created per track, so each subgraph is
            # a connected component of `graph`.
            graphs = [graph.subgraph(c).copy() 
                      for c in nx.weakly_connected_components(graph)]
            del graph  # Redondant with the subgraphs.

            # Adding the tracks attributes as graphs attributes.
            try:
                graphs = add_tracks_info(graphs, tracks_attributes)
            except ValueError as err:
                print(err)
                # The program is in an impossible state so we need to stop.
                raise

    # Exporting the graphs.
    if args.export:
        for graph in graphs:
            export_graph(graph, args.xml)

    # Basic visualisation.
    if args.plot_graph:
        for graph in graphs:
            pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog='dot')
            nx.draw(graph, pos, with_labels=True, arrows=True, 
                    font_weight='bold')
            plt.show()

    p_time = time.process_time() - start
    print(f'...done in {(p_time // 60):.0f} min {(p_time % 60):.2f} s.')
    print(f'{len(graphs)} tracks have been exported.')