#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy

from lxml import etree as ET

import networkx as nx



def add_graph_attrib_from_element(graph, element):
    """Add graph attributes from an XML element.

    Args:
        graph (nx.DiGraph): Graph on which to add attributes.
        element (ET.Element): Element holding the information to be added.
        
    Returns:
        nx.DiGraph: The updated graph.
    """
    graph.graph['Model'] = deepcopy(element.attrib)
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
            attribs = deepcopy(element.attrib)
            try:
                features[attribs['feature']] = attribs
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


def add_ROI_coordinates(element, attribs):
    """Extract, format and add ROI coordinates to the attributes dict.

    Args:
        element (ET.Element): Element from which to extract ROI coordinates.
        attribs (dict): Attributes dict to update with ROI coordinates.
    """
    try:
        n_points = int(attribs['ROI_N_POINTS'])
    except KeyError as err:
        print(f"No key {err} in the attributes of current element "
              f"'{element.tag}'. ")
    else:        
        points_coordinates = element.text.split()
        points_coordinates = [float(x) for x in points_coordinates]
        points_dimension = len(points_coordinates) // n_points
        it = [iter(points_coordinates)] * points_dimension
        points_coordinates = list(zip(*it))
        attribs['ROI_N_POINTS'] = points_coordinates

           
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
            attribs = deepcopy(element.attrib)
            try:
                convert_attributes(attribs,
                                   graph.graph['Model']['SpotFeatures'])
            except ValueError as err:
                print(f'ERROR: {err} Please check the XML file.')
                raise
            except KeyError as err:
                print(f'ERROR: {err} Please check the XML file.')
                raise

            # The ROI coordinates are not stored in a tag attribute but in
            # the tag text. So we need to extract then format them.
            add_ROI_coordinates(element, attribs)             

            # Now that all the node attributes have been updated, we can add
            # it to the graph.
            try:
                graph.add_nodes_from([(int(attribs['ID']), attribs)])
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
    attribs = deepcopy(element.attrib)
    convert_attributes(attribs,
                       graph.graph['Model']['EdgeFeatures'])
    try:
        entry_node = attribs['SPOT_SOURCE_ID']
        exit_node = attribs['SPOT_TARGET_ID']
    except KeyError as err:
        print(f"No key {err} in the attributes of "
              f"current element '{element.tag}'. "
              f"Not adding this edge to the graph.")
    else:
        graph.add_edge(entry_node, exit_node)
        nx.set_edge_attributes(graph, 
                               {(entry_node, exit_node): attribs})
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
        attribs = deepcopy(element.attrib)
        convert_attributes(attribs,
                           graph.graph['Model']['TrackFeatures'])
        tracks_attributes.append(attribs)
        try:
            current_track_id = attribs['TRACK_ID']
        except KeyError as err:
            print(f"No key {err} in the attributes of "
                  f"current element '{element.tag}'. "
                  f"Not adding the {err} edge to the graph.")
            current_track_id = None        

    while (event, element) != ('end', ancestor):
        event, element = next(iterator)

        # Saving the current track information.
        if element.tag == 'Track' and event == 'start':
            attribs = deepcopy(element.attrib)
            convert_attributes(attribs,
                               graph.graph['Model']['TrackFeatures'])
            tracks_attributes.append(attribs)
            try:
                current_track_id = attribs['TRACK_ID']
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
    attribs = deepcopy(element.attrib)
    try:
        filtered_tracks_ID.append(int(attribs['TRACK_ID']))
    except KeyError as err:
        print(f"No key {err} in the attributes of current element "
              f"'{element.tag}'. Ignoring this track.")
        
    while (event, element) != ('end', ancestor):
        event, element = next(iterator)          
        if element.tag == 'TrackID' and event == 'start':
            attribs = deepcopy(element.attrib)
            try:
                filtered_tracks_ID.append(int(attribs['TRACK_ID']))
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


def read_model(xml_path: str, keep_all_spots: bool, 
               keep_all_tracks: bool, one_graph: bool) -> list[nx.DiGraph]:
    """Read an XML file and convert the model data into several graphs. 

    Each TrackMate track and its associated data described in the XML file
    are modeled as networkX directed graphs. Spots are modeled as graph
    nodes, and edges as graph edges. All data pertaining to the model
    itself such as units, spot features, etc. are stored in each graph as 
    graph attributes.
    
    Args:
        xml_path (str): Path of the XML file to process.
        keep_all_spots (bool): True to keep the spots filtered out in 
            TrackMate, False otherwise.
        keep_all_tracks (bool): True to keep the tracks filtered out in 
            TrackMate, False otherwise.
        one_graph (bool): True to create only one graph (probably 
            disconnected) that contains all nodes and edges, False to 
            create a graph (connected) per track .

    Returns:
        list[nx.DiGraph]: List of graphs modeling the tracks.
    """
    
    # Creation of a graph that will hold all the tracks described
    # in the XML file. This means that if there's more than one track,
    # the resulting graph will be disconnected.
    graph = nx.DiGraph()

    # So as not to load the entire XML file into memory at once, we're
    # using an iterator to browse over the tags one by one.
    # The events 'start' and 'end' correspond respectively to the opening
    # and the closing of the considered tag.
    it = ET.iterparse(xml_path, events=['start', 'end'])
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
            if not keep_all_spots:
                # Those nodes belong to no tracks: they have a degree of 0.
                lone_nodes = [n for n, d in graph.degree if d == 0]
                graph.remove_nodes_from(lone_nodes)

        # Filtering out tracks and adding tracks attribute.
        if element.tag == 'FilteredTracks' and event == 'start':

            # Removal of filtered tracks / graphs.
            if not keep_all_tracks:
                id_to_keep = get_filtered_tracks_ID(it, element)
                to_remove = [n for n, t in graph.nodes(data='TRACK_ID') 
                             if t not in id_to_keep]
                graph.remove_nodes_from(to_remove)

            # Subgraphs creation.
            if not one_graph:
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

        if element.tag == 'Model' and event == 'end':
            break  # We are not interested in the following data.

    if one_graph:
        return [graph]
    else:
        return graphs


def read_settings(xml_path: str) -> ET._Element:
    """Extract the TrackMate settings of a TrackMate XML file.

    Args:
        xml_path (str): Path of the XML file to process.

    Returns:
        ET._Element: Element holding all the TrackMate settings.
    """

    it = ET.iterparse(xml_path, events=['start', 'end'])
    _, root = next(it)

    for event, element in it:

        if element.tag != 'Settings':
            root.clear()
            
        if element.tag == 'Settings' and event == 'end':
            settings = deepcopy(element)

    # # To explore the settings:
    # print(type(settings))
    # print(settings)
    # print(settings.tag)
    # print(settings.attrib)

    # for child in settings:
    #     print(child.tag, child. attrib)

    # for descendant in settings.iterdescendants():
    #     print(descendant.tag, descendant. attrib)

    return settings    
    