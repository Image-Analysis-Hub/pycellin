#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy
import math
from typing import Any, Union

from lxml import etree as ET
import networkx as nx


### xml2graph ###


def add_graph_attrib_from_element(
    graph: nx.DiGraph,
    element: ET.Element,
) -> nx.DiGraph:
    """Add graph attributes from an XML element.

    Args:
        graph (nx.DiGraph): Graph on which to add attributes.
        element (ET.Element): Element holding the information to be added.

    Returns:
        nx.DiGraph: The updated graph.
    """
    graph.graph["Model"] = deepcopy(element.attrib)
    element.clear()  # We won't need it anymore so we free up some memory.
    # .clear() does not delete the element: it only removes all subelements
    # and clears or sets to `None` all attributes.
    return graph


def get_features_dict(
    iterator: ET.iterparse,
    ancestor: ET.Element,
) -> dict[str, str]:
    """Get all the features of ancestor and return them as a dictionary.

    Args:
        iterator (ET.iterparse): XML element iterator.
        ancestor (ET.Element): Element encompassing the information to add.

    Returns:
        dict: Features contained in the ancestor element.
    """
    features = dict()
    event, element = next(iterator)  # Feature.
    while (event, element) != ("end", ancestor):
        if element.tag == "Feature" and event == "start":
            attribs = deepcopy(element.attrib)
            try:
                features[attribs["feature"]] = attribs
            except KeyError as err:
                print(
                    f"No key {err} in the attributes of "
                    f"current element '{element.tag}'. "
                    f"Not adding this feature to the graph."
                )
        element.clear()
        event, element = next(iterator)
    return features


def add_all_features(
    graph: nx.DiGraph,
    iterator: ET.iterparse,
    ancestor: ET.Element,
) -> nx.DiGraph:
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
    while (event, element) != ("end", ancestor):
        features = get_features_dict(iterator, element)
        graph.graph["Model"][element.tag] = features
        element.clear()
        event, element = next(iterator)
    return graph


def convert_attributes(
    attributes: dict[str, str],
    features: dict[str, dict[str, str]],
):
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
        if key == "ID":
            attributes[key] = int(attributes[key])  # IDs are always integers.
        elif key in features:
            if "isint" not in features[key]:
                raise KeyError(
                    f"No 'isint' feature attribute in " f"FeatureDeclarations."
                )
            if features[key]["isint"].lower() == "true":
                attributes[key] = int(attributes[key])
            elif features[key]["isint"].lower() == "false":
                try:
                    attributes[key] = float(attributes[key])
                except ValueError:
                    pass  # Not an int nor a float so we let it be.
            else:
                raise ValueError(
                    f"'{features[key]['isint']}' is an invalid"
                    f" feature attribute value for 'isint'."
                )


def add_ROI_coordinates(
    element: ET.Element,
    attribs: dict[str, Any],
):
    """Extract, format and add ROI coordinates to the attributes dict.

    Args:
        element (ET.Element): Element from which to extract ROI coordinates.
        attribs (dict): Attributes dict to update with ROI coordinates.
    """
    try:
        n_points = int(attribs["ROI_N_POINTS"])
    except KeyError as err:
        print(
            f"No key {err} in the attributes of current element " f"'{element.tag}'. "
        )
    else:
        if element.text:
            points_coordinates = element.text.split()
            points_coordinates = [float(x) for x in points_coordinates]
            points_dimension = len(points_coordinates) // n_points
            it = [iter(points_coordinates)] * points_dimension
            points_coordinates = list(zip(*it))
            attribs["ROI_N_POINTS"] = points_coordinates
        else:
            attribs["ROI_N_POINTS"] = None


def add_all_nodes(
    graph: nx.DiGraph,
    iterator: ET.iterparse,
    ancestor: ET.Element,
):
    """Add nodes and their attributes to a graph.

    All the elements that are descendants of `ancestor` are explored.

    Args:
        graph (nx.DiGraph): Graph on which to add nodes.
        iterator (ET.iterparse): XML element iterator.
        ancestor (ET.Element): Element encompassing the information to add.
    """
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        event, element = next(iterator)
        if element.tag == "Spot" and event == "end":
            # All items in element.attrib are parsed as strings but most
            # of them (if not all) are numbers. So we need to do a
            # conversion based on these attributes type (attribute `isint`)
            # as defined in the FeaturesDeclaration tag.
            attribs = deepcopy(element.attrib)
            try:
                convert_attributes(attribs, graph.graph["Model"]["SpotFeatures"])
            except ValueError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise
            except KeyError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise

            # The ROI coordinates are not stored in a tag attribute but in
            # the tag text. So we need to extract then format them.
            add_ROI_coordinates(element, attribs)

            # Now that all the node attributes have been updated, we can add
            # it to the graph.
            try:
                graph.add_nodes_from([(int(attribs["ID"]), attribs)])
            except KeyError as err:
                print(
                    f"No key {err} in the attributes of "
                    f"current element '{element.tag}'. "
                    f"Not adding this node to the graph."
                )
            finally:
                element.clear()


def add_edge_from_element(
    graph: nx.DiGraph,
    element: ET.Element,
    current_track_id: str,
):
    """Add an edge and its attributes from an XML element.

    Args:
        graph (nx.DiGraph): Graph on which to add the edge.
        element (ET.Element): Element holding the information to be added.
        current_track_id (str): Track ID of the track holding the edge.
    """
    attribs = deepcopy(element.attrib)
    convert_attributes(attribs, graph.graph["Model"]["EdgeFeatures"])
    try:
        entry_node = attribs["SPOT_SOURCE_ID"]
        exit_node = attribs["SPOT_TARGET_ID"]
    except KeyError as err:
        print(
            f"No key {err} in the attributes of "
            f"current element '{element.tag}'. "
            f"Not adding this edge to the graph."
        )
    else:
        graph.add_edge(entry_node, exit_node)
        nx.set_edge_attributes(graph, {(entry_node, exit_node): attribs})
        # Adding the current track ID to the nodes of the newly created
        # edge. This will be useful later to filter nodes by track and
        # add the saved tracks attributes (as returned by this method).
        graph.nodes[entry_node]["TRACK_ID"] = current_track_id
        graph.nodes[exit_node]["TRACK_ID"] = current_track_id
    finally:
        element.clear()


def add_all_edges(
    graph: nx.DiGraph,
    iterator: ET.iterparse,
    ancestor: ET.Element,
) -> list[dict[str, Any]]:
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
    if element.tag == "Track" and event == "start":
        # This condition is a bit of an overkill since the XML structure
        # SHOULD stay the same but better safe than sorry.
        # TODO: refactor this chunk that appears twice in this method.
        attribs = deepcopy(element.attrib)
        convert_attributes(attribs, graph.graph["Model"]["TrackFeatures"])
        tracks_attributes.append(attribs)
        try:
            current_track_id = attribs["TRACK_ID"]
        except KeyError as err:
            print(
                f"No key {err} in the attributes of "
                f"current element '{element.tag}'. "
                f"Not adding the {err} edge to the graph."
            )
            current_track_id = None

    while (event, element) != ("end", ancestor):
        event, element = next(iterator)

        # Saving the current track information.
        if element.tag == "Track" and event == "start":
            attribs = deepcopy(element.attrib)
            convert_attributes(attribs, graph.graph["Model"]["TrackFeatures"])
            tracks_attributes.append(attribs)
            try:
                current_track_id = attribs["TRACK_ID"]
            except KeyError as err:
                print(
                    f"No key {err} in the attributes of "
                    f"current element '{element.tag}'. "
                    f"Not adding the {err} edge to the graph."
                )
                current_track_id = None

        # Edge creation.
        if element.tag == "Edge" and event == "start":
            add_edge_from_element(graph, element, current_track_id)

    return tracks_attributes


def get_filtered_tracks_ID(
    iterator: ET.iterparse,
    ancestor: ET.Element,
) -> list[str]:
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
        filtered_tracks_ID.append(int(attribs["TRACK_ID"]))
    except KeyError as err:
        print(
            f"No key {err} in the attributes of current element "
            f"'{element.tag}'. Ignoring this track."
        )

    while (event, element) != ("end", ancestor):
        event, element = next(iterator)
        if element.tag == "TrackID" and event == "start":
            attribs = deepcopy(element.attrib)
            try:
                filtered_tracks_ID.append(int(attribs["TRACK_ID"]))
            except KeyError as err:
                print(
                    f"No key {err} in the attributes of current element "
                    f"'{element.tag}'. Ignoring this track."
                )

    return filtered_tracks_ID


def add_tracks_info(
    graphs: list[nx.DiGraph],
    tracks_attributes: list[dict[str, Any]],
) -> list[nx.DiGraph]:
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
        tmp = set(t_id for n, t_id in graph.nodes(data="TRACK_ID"))

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
            raise ValueError("Impossible state: several IDs for one track.")

        current_track_id = list(tmp)[0]
        current_track_attr = [
            d_attr
            for d_attr in tracks_attributes
            if d_attr["TRACK_ID"] == current_track_id
        ][0]

        # Adding the attributes to the graph.
        for k, v in current_track_attr.items():
            graph.graph[k] = v
        updated_graphs.append(graph)

    return updated_graphs


def read_model(
    xml_path: str,
    keep_all_spots: bool,
    keep_all_tracks: bool,
    one_graph: bool,
) -> list[nx.DiGraph]:
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
    it = ET.iterparse(xml_path, events=["start", "end"])
    _, root = next(it)  # Saving the root of the tree for later cleaning.

    for event, element in it:
        # Adding the model information as graph attributes.
        if element.tag == "Model" and event == "start":  # Add units.
            graph = add_graph_attrib_from_element(graph, element)
            root.clear()  # Cleaning the tree to free up some memory.
            # All the browsed subelements of `root` are deleted.

        # Add features declaration for spot, edge and track features.
        if element.tag == "FeatureDeclarations" and event == "start":
            graph = add_all_features(graph, it, element)
            root.clear()

        # Adding the spots as nodes.
        if element.tag == "AllSpots" and event == "start":
            add_all_nodes(graph, it, element)
            root.clear()

        # Adding the tracks as edges.
        if element.tag == "AllTracks" and event == "start":
            tracks_attributes = add_all_edges(graph, it, element)
            root.clear()

            # Removal of filtered spots / nodes.
            if not keep_all_spots:
                # Those nodes belong to no tracks: they have a degree of 0.
                lone_nodes = [n for n, d in graph.degree if d == 0]
                graph.remove_nodes_from(lone_nodes)

        # Filtering out tracks and adding tracks attribute.
        if element.tag == "FilteredTracks" and event == "start":
            # Removal of filtered tracks / graphs.
            id_to_keep = get_filtered_tracks_ID(it, element)
            if not keep_all_tracks:
                to_remove = [
                    n for n, t in graph.nodes(data="TRACK_ID") if t not in id_to_keep
                ]
                graph.remove_nodes_from(to_remove)

            # Subgraphs creation.
            if not one_graph:
                # One subgraph is created per track, so each subgraph is
                # a connected component of `graph`.
                graphs = [
                    graph.subgraph(c).copy()
                    for c in nx.weakly_connected_components(graph)
                ]
                del graph  # Redondant with the subgraphs.

                # Adding the tracks attributes as graphs attributes.
                try:
                    graphs = add_tracks_info(graphs, tracks_attributes)
                except ValueError as err:
                    print(err)
                    # The program is in an impossible state so we need to stop.
                    raise

                # Also adding if each track was present in the 'FilteredTracks'
                # tag because this info is needed when reconstructing TM XMLs
                # from graphs.
                for graph in graphs:
                    if "TRACK_ID" in graph.graph:
                        if graph.graph["TRACK_ID"] in id_to_keep:
                            graph.graph["FilteredTrack"] = True
                        else:
                            graph.graph["FilteredTrack"] = False

        if element.tag == "Model" and event == "end":
            break  # We are not interested in the following data.

    if one_graph:
        return [graph]
    else:
        return graphs


def read_settings(
    xml_path: str,
) -> ET._Element:
    """Extract the TrackMate settings of a TrackMate XML file.

    Args:
        xml_path (str): Path of the XML file to process.

    Returns:
        ET._Element: Element holding all the TrackMate settings.
    """
    it = ET.iterparse(xml_path, events=["start", "end"])
    _, root = next(it)

    for event, element in it:
        if element.tag != "Settings":
            root.clear()
        if element.tag == "Settings" and event == "end":
            settings = deepcopy(element)

    return settings


### graph2xml ###


def write_FeatureDeclarations(
    xf: ET.xmlfile,
    graphs: list[nx.DiGraph],
) -> None:
    """Write the feature declarations into an XML file.

    The feature declarations are divided in three parts: spot features,
    edge features, and track features.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write.
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write("\n\t\t")
    with xf.element("FeatureDeclarations"):
        features_type = ["SpotFeatures", "EdgeFeatures", "TrackFeatures"]
        for f_type in features_type:
            # We need to check that all graphs have the same features
            # definition.
            dict_feats = {k: graphs[0].graph["Model"].get(k, None) for k in [f_type]}
            for graph in graphs[1:]:
                tmp_dict = {k: graph.graph["Model"].get(k, None) for k in [f_type]}
                assert dict_feats == tmp_dict

            # Actual writing.
            xf.write("\n\t\t\t")
            with xf.element(f_type):
                xf.write("\n\t\t\t\t")
                # For each type of features, data is stored as a dict of dict.
                # E.g. for SpotFeatures:
                # {'QUALITY': {'feature': 'QUALITY', 'name': 'Quality'...},
                #  'POSITION_X': {'feature': 'POSITION_X', 'name': 'X'...},
                #  ...}
                for v_feats in dict_feats.values():
                    dict_length = len(v_feats)
                    for i, v in enumerate(v_feats.values()):
                        el_feat = ET.Element("Feature", v)
                        xf.write(el_feat)
                        if i != dict_length - 1:
                            xf.write("\n\t\t\t\t")
                xf.write("\n\t\t\t")
        xf.write("\n\t\t")


def value_to_str(
    value: Union[int, float, str],
) -> str:
    """Convert a value to its associated string.

    Indeed, ET.write() method only accepts to write strings.
    However, TrackMate is only able to read Spot, Edge and Track
    features that can be parsed as numeric by Java.

    Args:
        value (Union[int, float, str]): Value to convert to string.

    Returns:
        str: The string equivalent of `value`.
    """
    # TODO: Should this function take care of converting non-numeric added
    # features to numeric ones (like GEN_ID)? Or should it be done in
    # pycellin?
    if isinstance(value, str):
        return value
    elif math.isnan(value):
        return "NaN"
    elif math.isinf(value):
        if value > 0:
            return "Infinity"
        else:
            return "-Infinity"
    else:
        return str(value)


def create_Spot(
    graph: nx.DiGraph,
    node: int,
) -> ET._Element:
    """Create an XML Spot Element representing a graph node.

    Args:
        graph (nx.DiGraph): Graph containing the node to create.
        node (int): ID of the node in the graph.

    Returns:
        ET._Element: The newly created Spot Element.
    """
    # Building Spot attributes.
    exluded_keys = ["TRACK_ID", "ROI_N_POINTS"]
    n_attr = {
        k: value_to_str(v)
        for k, v in graph.nodes[node].items()
        if k not in exluded_keys
    }
    n_attr["ROI_N_POINTS"] = str(len(graph.nodes[node]["ROI_N_POINTS"]))

    # Building Spot text: coordinates of ROI points.
    coords = [item for pt in graph.nodes[node]["ROI_N_POINTS"] for item in pt]

    el_node = ET.Element("Spot", n_attr)
    el_node.text = " ".join(map(str, coords))
    return el_node


def write_AllSpots(
    xf: ET.xmlfile,
    graphs: list[nx.DiGraph],
) -> None:
    """Write the nodes/spots data into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write.
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write("\n\t\t")
    nb_nodes = sum([len(graph) for graph in graphs])
    with xf.element("AllSpots", {"nspots": str(nb_nodes)}):
        # For each frame, nodes can be spread over several graphs so we first
        # need to identify all of the existing frames.
        frames = set()
        for graph in graphs:
            frames.update(nx.get_node_attributes(graph, "FRAME").values())

        # Then at each frame, we can find the nodes and write its data.
        for frame in frames:
            xf.write("\n\t\t\t")
            with xf.element("SpotsInFrame", {"frame": str(frame)}):
                for graph in graphs:
                    nodes = [
                        n for n in graph.nodes() if graph.nodes[n]["FRAME"] == frame
                    ]
                    for node in nodes:
                        xf.write("\n\t\t\t\t")
                        xf.write(create_Spot(graph, node))
                xf.write("\n\t\t\t")
        xf.write("\n\t\t")


def write_AllTracks(
    xf: ET.xmlfile,
    graphs: list[nx.DiGraph],
) -> None:
    """Write the tracks data into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write.
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write("\n\t\t")
    with xf.element("AllTracks"):
        for graph in graphs:
            # We have track tags to add only if there was a tracking done
            # in the first place. A graph with no TRACK_ID attribute has
            # no tracking associated.
            if "TRACK_ID" not in graph.graph:
                continue

            # Track tags.
            xf.write("\n\t\t\t")
            exluded_keys = ["Model", "FilteredTrack"]
            t_attr = {
                k: value_to_str(v)
                for k, v in graph.graph.items()
                if k not in exluded_keys
            }
            with xf.element("Track", t_attr):
                # Edge tags.
                for edge in graph.edges.data():
                    xf.write("\n\t\t\t\t")
                    e_attr = {k: value_to_str(v) for k, v in edge[2].items()}
                    xf.write(ET.Element("Edge", e_attr))
                xf.write("\n\t\t\t")
        xf.write("\n\t\t")


def write_FilteredTracks(
    xf: ET.xmlfile,
    graphs: list[nx.DiGraph],
) -> None:
    """Write the filtered tracks data into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write.
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    xf.write("\n\t\t")
    with xf.element("FilteredTracks"):
        for graph in graphs:
            if "TRACK_ID" in graph.graph and graph.graph["FilteredTrack"]:
                xf.write("\n\t\t\t")
                t_attr = {"TRACK_ID": str(graph.graph["TRACK_ID"])}
                xf.write(ET.Element("TrackID", t_attr))
        xf.write("\n\t\t")
    xf.write("\n\t")


def write_Model(
    xf: ET.xmlfile,
    graphs: list[nx.DiGraph],
) -> None:
    """Write all the model data into an XML file.

    This includes Features declarations, spots, tracks and filtered
    tracks.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write.
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
    """
    # Checking that each and every graph have the same features.
    # It should be the case but better safe than sorry.
    dict_units = {
        k: graphs[0].graph["Model"].get(k, None) for k in ("spatialunits", "timeunits")
    }
    if len(graphs) > 1:
        for graph in graphs[1:]:
            tmp_dict = {
                k: graph.graph["Model"].get(k, None)
                for k in ("spatialunits", "timeunits")
            }
            assert dict_units == tmp_dict

    with xf.element("Model", dict_units):
        write_FeatureDeclarations(xf, graphs)
        write_AllSpots(xf, graphs)
        write_AllTracks(xf, graphs)
        write_FilteredTracks(xf, graphs)


def write_Settings(
    xf: ET.xmlfile,
    settings: ET._Element,
) -> None:
    """Write the given TrackMate settings into an XML file.

    Args:
        xf (ET.xmlfile): Context manager for the XML file to write.
        settings (ET._Element): Element holding all the settings to write.
    """
    xf.write(settings, pretty_print=True)


def write_TrackMate_XML(
    graphs: list[nx.DiGraph],
    settings: ET._Element,
    xml_path: str,
) -> None:
    """Write an XML file readable by TrackMate from networkX graphs data.

    Args:
        graphs (list[nx.DiGraph]): Graphs containing the data to write.
        settings (ET._Element): Element holding all the settings to write.
        xml_path (str): Path of the XML file to write.
    """
    with ET.xmlfile(xml_path, encoding="utf-8", close=True) as xf:
        xf.write_declaration()
        # TODO: deal with the problem of unknown version.
        with xf.element("TrackMate", {"version": "unknown"}):
            xf.write("\n\t")
            write_Model(xf, graphs)
            xf.write("\n\t")
            write_Settings(xf, settings)
