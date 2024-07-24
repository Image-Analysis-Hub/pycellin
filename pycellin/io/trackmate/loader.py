#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from pkg_resources import get_distribution
from typing import Any

from lxml import etree as ET
import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.feature import FeaturesDeclaration, Feature
from pycellin.classes.data import CoreData
from pycellin.classes.lineage import CellLineage

# TODO: update all docstrings
# TODO: switch from TM features name to Pycellin (track => lineage, spot => node,
# upper case => lower case)
# ID => cell_ID
# TRACK_ID => lin_ID
# TODO: maybe TRACK_ID / lineage_ID should not be added as a node feature,
# and a fonction get_lineage_ID() should be implemented instead?


def _get_units(
    element: ET._Element,
) -> dict[str, str]:
    """
    Extracts units information from an XML element and returns it as a dictionary.

    This function deep copies the attributes of the XML element into a dictionary,
    then clears the element to free up memory.

    Parameters
    ----------
    element : ET._Element
        The XML element holding the units information.

    Returns
    -------
    dict[str, str]
        A dictionary where the keys are the attribute names and the values are the
        corresponding attribute values (units information).
    """
    units = deepcopy(element.attrib)
    element.clear()  # We won't need it anymore so we free up some memory.
    # .clear() does not delete the element: it only removes all subelements
    # and clears or sets to `None` all attributes.
    return units


def _get_features_dict(
    iterator: ET.iterparse,
    ancestor: ET._Element,
) -> dict[str, str]:
    """
    Get all the features of ancestor and return them as a list.

    The ancestor is either a SpotFeatures, EdgeFeatures or a TrackFeatures tag.

    Parameters
    ----------
    iterator : ET.iterparse
        An iterator over XML elements.
    ancestor : ET._Element
        The XML element that encompasses the information to be added.

    Returns
    -------
    list
        List of features contained in the ancestor element.
    """
    features = []
    event, element = next(iterator)  # Feature.
    while (event, element) != ("end", ancestor):
        if element.tag == "Feature" and event == "start":
            attribs = deepcopy(element.attrib)
            features.append(attribs)
        element.clear()
        event, element = next(iterator)
    return features


def _dimension_to_unit(trackmate_feature, units):
    """
    Convert the dimension of a feature to its unit.

    Parameters
    ----------
    trackmate_feature : dict[str, str]
        The feature to convert.
    units : dict[str, str]
        The units of the TrackMate model.

    Returns
    -------
    str
        The unit of the feature.
    """
    dimension = trackmate_feature["dimension"]
    match dimension:
        case "NONE" | "QUALITY" | "VISIBILITY" | "RATIO" | "INTENSITY" | "COST":
            return "none"
        case "LENGTH" | "POSITION":
            return units["spatialunits"]
        case "VELOCITY":
            return units["spatialunits"] + "/" + units["timeunits"]
        case "AREA":
            return units["spatialunits"] + "^2"
        case "TIME":
            return units["timeunits"]
        case "ANGLE":
            return "rad"
        case "ANGLE_RATE":
            return "rad/" + units["timeunits"]
        case _:
            raise ValueError(f"Invalid dimension: {dimension}")


def _convert_and_add_feature(
    trackmate_feature: dict[str, str],
    feature_type: str,
    feat_declaration: FeaturesDeclaration,
    units: dict[str, str],
):
    """
    Convert a TrackMate feature to a Pycellin one and add it to the features declaration.

    Parameters
    ----------
    trackmate_feature : dict[str, str]
        The feature to add.
    feature_type : str
        The type of the feature to add (node, edge, or lineage).
    feat_declaration : FeaturesDeclaration
        The FeaturesDeclaration object to add the feature to.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model.
    """
    feat_name = trackmate_feature["feature"]
    feat_description = trackmate_feature["name"]
    feat_lineage_type = "CellLineage"
    if trackmate_feature["isint"] == "true":
        feat_data_type = "int"
    else:
        feat_data_type = "float"
    feat_provenance = "TrackMate"
    feat_unit = _dimension_to_unit(trackmate_feature, units)

    feature = Feature(
        feat_name,
        feat_description,
        feat_lineage_type,
        feat_provenance,
        feat_data_type,
        feat_unit,
    )

    match feature_type:
        case "SpotFeatures":
            feat_type = "node"
        case "EdgeFeatures":
            feat_type = "edge"
        case "TrackFeatures":
            feat_type = "lineage"
        case _:
            raise ValueError(f"Invalid feature type: {feature_type}")
    feat_declaration._add_feature(feature, feat_type)


def _add_all_features(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    feat_declaration: FeaturesDeclaration,
    units: dict[str, str],
):
    """
    Add all the TrackMate model features to a FeaturesDeclaration object.

    The model features are divided in 3 categories: SpotFeatures, EdgeFeatures and
    TrackFeatures. Those features are regrouped under the FeatureDeclarations tag.
    Some other features are used in the Spot and Track tags but are not declared in
    the FeatureDeclarations tag.

    Parameters
    ----------
    iterator : ET.iterparse
        An iterator over XML elements.
    ancestor : ET._Element
        The XML element that encompasses the information to be added.
    """
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        # Features stored in the FeatureDeclarations tag.
        features = _get_features_dict(iterator, element)
        for feat in features:
            _convert_and_add_feature(feat, element.tag, feat_declaration, units)
        # Features used in Spot tags but not declared in the FeatureDeclarations tag.
        if element.tag == "SpotFeatures":
            name_feat = Feature(
                "name", "Name of the spot", "CellLineage", "TrackMate", "string", "none"
            )
            roi_coord_feat = Feature(
                "ROI_coords",
                "List of coordinates of the region of interest",
                "CellLineage",
                "TrackMate",
                "float",
                units["spatialunits"],
            )
            feat_declaration._add_features([name_feat, roi_coord_feat], ["node"] * 2)
        # Feature used in Track tags but not declared in the FeatureDeclarations tag.
        if element.tag == "TrackFeatures":
            name_feat = Feature(
                "name",
                "Name of the track",
                "CellLineage",
                "TrackMate",
                "string",
                "none",
            )
            feat_declaration._add_feature(name_feat, "lineage")
        element.clear()
        event, element = next(iterator)


def _convert_attributes(
    attributes: dict[str, str],
    features: dict[str, CellLineage],
):
    """
    Convert the values of `attributes` from string to int or float.

    The type to convert to is given by the features declaration that stores all
    the features info.

    Parameters
    ----------
    attributes : dict[str, str]
        The dictionary whose values we want to convert.
    features : dict[str, CellLineage]
        The dictionary of features that contains the information on how to convert
        the values of `attributes`.

    Raises
    ------
    ValueError
        If a feature has an invalid data_type (not "int", "float" nor "string").
    KeyError
        If a feature is not found in the features declaration nor treated as a
        special case.
    """
    # TODO: Rewrite this.
    for key in attributes:
        if key in features:
            match features[key].data_type:
                case "int":
                    attributes[key] = int(attributes[key])
                case "float":
                    attributes[key] = float(attributes[key])
                case "string":
                    pass  # Nothing to do.
                case _:
                    raise ValueError(f"Invalid data type: {features[key]['data_type']}")
        elif key == "ID":
            attributes[key] = int(attributes[key])  # IDs are always integers.
        elif key == "name":
            # "name" is a string so we don't need to convert it.
            pass
        elif key == "ROI_N_POINTS":
            # This attribute is a special case (stored as a tag text instead of tag
            # attribute) and will be converted later, in _add_ROI_coordinates().
            pass
        else:
            raise KeyError(f"Feature {key} not found in the features declaration.")


def _convert_ROI_coordinates(
    element: ET._Element,
    attribs: dict[str, Any],
):
    """
    Extract, format and add ROI coordinates to the attributes dict.

    Parameters
    ----------
    element : ET._Element
        Element from which to extract ROI coordinates.
    attribs : dict[str, Any]
        Attributes dict to update with ROI coordinates.

    Raises
    ------
    KeyError
        If the "ROI_N_POINTS" attribute is not found in the attributes dict.
    """
    if "ROI_N_POINTS" not in attribs:
        raise KeyError(
            f"No key 'ROI_N_POINTS' in the attributes of current element '{element.tag}'."
        )
    n_points = int(attribs["ROI_N_POINTS"])
    if element.text:
        points_coordinates = element.text.split()
        points_coordinates = [float(x) for x in points_coordinates]
        points_dimension = len(points_coordinates) // n_points
        it = [iter(points_coordinates)] * points_dimension
        points_coordinates = list(zip(*it))
        attribs["ROI_coords"] = points_coordinates
    else:
        attribs["ROI_coords"] = None


def _add_all_nodes(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    feat_declaration: FeaturesDeclaration,
    graph: nx.DiGraph,
) -> None:
    """
    Add nodes and their attributes to a graph.

    All the elements that are descendants of `ancestor` are explored.

    Parameters
    ----------
    iterator : ET.iterparse
        An iterator over XML elements.
    ancestor : ET._Element
        The XML element that encompasses the information to be added.
    feat_declaration : FeaturesDeclaration
        An object holding the features declaration information used to convert the
        node attributes.
    graph : nx.DiGraph
        Graph to add the nodes to.
    """
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        event, element = next(iterator)
        if element.tag == "Spot" and event == "end":
            # All items in element.attrib are parsed as strings but most
            # of them (if not all) are numbers. So we need to do a
            # conversion based on these attributes type (attribute `isint`)
            # as defined in the features declaration.
            attribs = deepcopy(element.attrib)
            try:
                _convert_attributes(attribs, feat_declaration.node_feats)
            except ValueError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise
            except KeyError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise

            # The ROI coordinates are not stored in a tag attribute but in
            # the tag text. So we need to extract then format them.
            try:
                _convert_ROI_coordinates(element, attribs)
            except KeyError as err:
                print(err)
                # TODO: check the behavior when the key is not found.
                # Does it happen when TrackMate do a single-point segmentation?

            # Now that all the node attributes have been updated, we can add
            # them to the graph.
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


def _add_edge(
    element: ET._Element,
    feat_declaration: FeaturesDeclaration,
    graph: nx.DiGraph,
    current_track_id: int,
):
    """
    Add an edge between two nodes in the graph based on the XML element.

    This function extracts source and target node identifiers from the
    given XML element, along with any additional attributes defined
    within. It then adds an edge between these nodes in the specified
    graph. If the nodes have a 'TRACK_ID' attribute, it ensures consistency
    with the current track ID.

    Parameters
    ----------
    element : ET._Element
        The XML element containing edge information.
    feat_declaration : FeaturesDeclaration
        An object holding the features declaration information used
        to convert the edge attributes.
    graph : nx.DiGraph
        The graph to which the edge and its attributes will be added.
    current_track_id : int
        Track ID of the track holding the edge.

    Raises
    ------
    AssertionError
        If the 'TRACK_ID' attribute of either the source or target node
        does not match the current track ID, indicating an inconsistency
        in track assignment.
    """
    attribs = deepcopy(element.attrib)
    _convert_attributes(attribs, feat_declaration.edge_feats)
    try:
        entry_node_id = attribs["SPOT_SOURCE_ID"]
        exit_node_id = attribs["SPOT_TARGET_ID"]
    except KeyError as err:
        print(
            f"No key {err} in the attributes of "
            f"current element '{element.tag}'. "
            f"Not adding this edge to the graph."
        )
    else:
        graph.add_edge(entry_node_id, exit_node_id)
        nx.set_edge_attributes(graph, {(entry_node_id, exit_node_id): attribs})
        # Adding the current track ID to the nodes of the newly created
        # edge. This will be useful later to filter nodes by track and
        # add the saved tracks attributes (as returned by this method).
        error_msg = f"Incoherent track ID for nodes {entry_node_id} and {exit_node_id}."
        entry_node = graph.nodes[entry_node_id]
        if "TRACK_ID" not in entry_node:
            entry_node["TRACK_ID"] = current_track_id
        else:
            assert entry_node["TRACK_ID"] == current_track_id, error_msg
        exit_node = graph.nodes[exit_node_id]
        if "TRACK_ID" not in exit_node:
            exit_node["TRACK_ID"] = current_track_id
        else:
            assert exit_node["TRACK_ID"] == current_track_id, error_msg
    finally:
        element.clear()


def _build_tracks(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    feat_declaration: FeaturesDeclaration,
    graph: nx.DiGraph,
) -> list[dict[str, Any]]:
    """
    Add edges and their attributes to a graph based on the XML elements.

    This function explores all elements that are descendants of the
    specified `ancestor` element, adding edges and their attributes to
    the provided graph. It iterates through the XML elements using
    the provided iterator, extracting and processing relevant information
    to construct track attributes.

    Parameters
    ----------
    iterator : ET.iterparse
        An iterator over XML elements.
    ancestor : ET._Element
        The XML element that encompasses the information to be added.
    feat_declaration : FeaturesDeclaration
        An object holding the features declaration information used
        to convert the edge and tracks attributes.
    graph: nx.DiGraph
        The graph to which the edges and their attributes will be added.

    Returns
    -------
    list[dict[str, Any]]
        A list of dictionaries, each representing the attributes for a
        track.
    """
    tracks_attributes = []
    current_track_id = None
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):

        # Saving the current track information.
        if element.tag == "Track" and event == "start":
            attribs = deepcopy(element.attrib)
            _convert_attributes(attribs, feat_declaration.lin_feats)
            tracks_attributes.append(attribs)
            current_track_id = attribs["TRACK_ID"]

        # Edge creation.
        if element.tag == "Edge" and event == "start":
            _add_edge(element, feat_declaration, graph, current_track_id)

        event, element = next(iterator)

    return tracks_attributes


def _get_filtered_tracks_ID(
    iterator: ET.iterparse,
    ancestor: ET._Element,
) -> list[int]:
    """
    Extract and return a list of track IDs to identify the tracks to keep.

    Parameters
    ----------
    iterator : ET.iterparse
        An iterator over XML elements.
    ancestor : ET._Element
        The XML element that encompasses the information to be added.

    Returns
    -------
    list[int]
        List of tracks ID to identify the tracks to keep.
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


def _add_tracks_info(
    lineages: list[CellLineage],
    tracks_attributes: list[dict[str, Any]],
):
    """
    Update each CellLineage in the list with corresponding track attributes.

    This function iterates over a list of CellLineage objects,
    attempting to match each lineage with its corresponding track
    attributes based on the 'TRACK_ID' attribute present in the
    lineage nodes. It then updates the lineage graph with these
    attributes.

    Parameters
    ----------
    lineages : list[CellLineage]
        A list of the lineages to update.
    tracks_attributes : list[dict[str, Any]]
        A list of dictionaries, where each dictionary contains
        attributes for a specific track, identified by a 'TRACK_ID' key.

    Raises
    ------
    ValueError
        If a lineage is found to contain nodes with multiple distinct
        'TRACK_ID' values, indicating an inconsistency in track ID
        assignment.
    """
    for lin in lineages:
        # Finding the dict of attributes matching the track.
        tmp = set(t_id for _, t_id in lin.nodes(data="TRACK_ID"))

        if not tmp:
            # 'tmp' is empty because there's no nodes in the current graph.
            # Even if it can't be updated, we still want to return this graph.
            continue
        elif tmp == {None}:
            # Happens when all the nodes do not have a TRACK_ID attribute.
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

        # Adding the attributes to the lineage.
        for k, v in current_track_attr.items():
            lin.graph[k] = v


def _split_graph_into_lineages(
    graph: CellLineage,
    tracks_attributes: list[dict[str, Any]],
) -> list[CellLineage]:
    """
    Split a graph into several subgraphs, each representing a lineage.

    Parameters
    ----------
    lineage : CellLineage
        The graph to split.
    tracks_attributes : list[dict[str, Any]]
        A list of dictionaries, where each dictionary contains TrackMate
        attributes for a specific track, identified by a 'TRACK_ID' key.

    Returns
    -------
    list[CellLineage]
        A list of subgraphs, each representing a lineage.
    """
    # One subgraph is created per lineage, so each subgraph is
    # a connected component of `graph`.
    lineages = [graph.subgraph(c).copy() for c in nx.weakly_connected_components(graph)]
    del graph  # Redondant with the subgraphs.

    # Adding TrackMate tracks attributes to each lineage.
    try:
        _add_tracks_info(lineages, tracks_attributes)
    except ValueError as err:
        print(err)
        # The program is in an impossible state so we need to stop.
        raise

    return lineages


def _update_features_declaration(
    feat_declaration: FeaturesDeclaration,
):
    """
    Update the features declaration to match Pycellin conventions.

    Parameters
    ----------
    feat_declaration : FeaturesDeclaration
        The features declaration to update.
    """
    # Lineage features.
    feat_declaration._rename_feature("TRACK_ID", "lineage_ID", "lineage")
    feat_declaration._modify_feature_description(
        "lineage_ID", "Unique identifier of the lineage", "lineage"
    )
    feat_filtered_track = Feature(
        "FilteredTrack",
        "True if the track was not filtered out in TrackMate",
        "CellLineage",
        "TrackMate",
        "int",
        "none",
    )
    feat_declaration._add_feature(feat_filtered_track, "lineage")

    # Node features.
    feat_cell_id = Feature(
        "cell_ID",
        "Unique identifier of the cell",
        "CellLineage",
        "TrackMate",
        "int",
        "none",
    )
    feat_declaration._add_feature(feat_cell_id, "node")
    feat_declaration._modify_feature_description(
        "cell_ID", "Unique identifier of the cell", "node"
    )
    feat_declaration._rename_feature("FRAME", "frame", "node")


def _parse_model_tag(
    xml_path: str,
    keep_all_spots: bool,
    keep_all_tracks: bool,
) -> tuple[FeaturesDeclaration, CoreData]:
    """
    Read an XML file and convert the model data into several graphs.

    Each TrackMate track and its associated data described in the XML file
    are modeled as networkX directed graphs. Spots are modeled as graph
    nodes, and edges as graph edges. All data pertaining to the model
    itself such as units, spot features, etc. are stored in each graph as
    graph attributes.

    Parameters
    ----------
    xml_path : str
        Path of the XML file to process.
    keep_all_spots : bool
        True to keep the spots filtered out in TrackMate, False otherwise.
    keep_all_tracks : bool
        True to keep the tracks filtered out in TrackMate, False otherwise.

    Returns
    -------
    tuple[FeaturesDeclaration, CoreData]
        TODO
    """
    fd = FeaturesDeclaration()

    # Creation of a graph that will hold all the tracks described
    # in the XML file. This means that if there's more than one track,
    # the resulting graph will be disconnected.
    graph = nx.Digraph()

    # So as not to load the entire XML file into memory at once, we're
    # using an iterator to browse over the tags one by one.
    # The events 'start' and 'end' correspond respectively to the opening
    # and the closing of the considered tag.
    it = ET.iterparse(xml_path, events=["start", "end"])
    _, root = next(it)  # Saving the root of the tree for later cleaning.

    for event, element in it:
        # Get the temporal and spatial units of the model. They will be
        # injected into each Feature.
        if element.tag == "Model" and event == "start":
            units = _get_units(element)
            root.clear()  # Cleaning the tree to free up some memory.
            # All the browsed subelements of `root` are deleted.

        # Get the spot, edge and track features and add them to the
        # features declaration.
        if element.tag == "FeatureDeclarations" and event == "start":
            _add_all_features(it, element, fd, units)
            root.clear()

        # Adding the spots as nodes.
        if element.tag == "AllSpots" and event == "start":
            _add_all_nodes(it, element, fd, graph)
            root.clear()

        # Adding the tracks as edges.
        if element.tag == "AllTracks" and event == "start":
            tracks_attributes = _build_tracks(it, element, fd, graph)
            root.clear()

            # Removal of filtered spots / nodes.
            if not keep_all_spots:
                # Those nodes belong to no tracks: they have a degree of 0.
                lone_nodes = [n for n, d in graph.degree if d == 0]
                graph.remove_nodes_from(lone_nodes)

        # Filtering out tracks and adding tracks attribute.
        if element.tag == "FilteredTracks" and event == "start":
            # Removal of filtered tracks.
            id_to_keep = _get_filtered_tracks_ID(it, element)
            if not keep_all_tracks:
                to_remove = [
                    n for n, t in graph.nodes(data="TRACK_ID") if t not in id_to_keep
                ]
                graph.remove_nodes_from(to_remove)

        if element.tag == "Model" and event == "end":
            break  # We are not interested in the following data.

    # We want one lineage per track, so we need to split the graph
    # into its connected components.
    lineages = _split_graph_into_lineages(graph, tracks_attributes)

    # For Pycellin compatibility, some TrackMate features have to be renamed.
    _update_features_declaration(fd)

    # Updating the lineage graph.
    for lin in lineages:
        for node, track_id in lin.nodes(data="TRACK_ID"):
            if track_id:
                lin.nodes[node]["lineage_ID"] = track_id
                lin.nodes[node].pop("TRACK_ID")
        if "TRACK_ID" in lin.graph:
            lin.graph["lineage_ID"] = lin.graph.pop("TRACK_ID")
    # TODO the same for frame and cell_ID, and refactor in a unique function
    # _update_node_features() to avoid code duplication.

    # Also adding if each track was present in the 'FilteredTracks'
    # tag because this info is needed when reconstructing TM XMLs
    # from graphs.
    data = {}
    for lin in lineages:
        if "lineage_ID" in lin.graph:
            data[lin.graph["lineage_ID"]] = lin
            if lin.graph["lineage_ID"] in id_to_keep:
                lin.graph["FilteredTrack"] = True
            else:
                lin.graph["FilteredTrack"] = False
        else:
            assert len(lin) == 1, "Lineage ID not found and not a one-node lineage."
            node = [n for n in lin.nodes][0]
            # In this case the lineage ID is not an int...
            # Maybe use negative values?
            lin_id = f"Node_{node}"
            data[lin_id] = lin

    return fd, CoreData(data)


def _get_specific_tags(
    xml_path: str,
    tag_names: list[str],
) -> dict[str, ET._Element]:
    """
    Extract specific tags from an XML file and returns them in a dictionary.

    This function parses an XML file, searching for specific tag names
    provided by the user. Once a tag is found, it is deep copied and
    stored in a dictionary with the tag name as the key. The search
    stops when all specified tags have been found or the end of the
    file is reached.

    Parameters
    ----------
    xml_path : str
        The file path of the XML file to be parsed.
    tag_names : list[str]
        A list of tag names to search for in the XML file.

    Returns
    -------
    dict[str, ET._Element]
        A dictionary where each key is a tag name from `tag_names` that
        was found in the XML file, and the corresponding value is the
        deep copied `ET._Element` object for that tag.
    """
    it = ET.iterparse(xml_path, events=["start", "end"])
    dict_tags = {}
    for event, element in it:
        if event == "start" and element.tag in tag_names:
            dict_tags[element.tag] = deepcopy(element)
            tag_names.remove(element.tag)
            if not tag_names:
                # All the tags have been found.
                break

        if event == "end":
            element.clear()

    return dict_tags


def _get_trackmate_version(
    xml_path: str,
) -> str:
    """
    Extract the version of TrackMate used to generate the XML file.

    Parameters
    ----------
    xml_path : str
        The file path of the XML file to be parsed.

    Returns
    -------
    str
        The version of TrackMate used to generate the XML file.
    """
    it = ET.iterparse(xml_path, events=["start", "end"])
    for event, element in it:
        if event == "start" and element.tag == "TrackMate":
            version = str(element.attrib["version"])
            return version


def load_TrackMate_XML(
    xml_path: str,
    keep_all_spots: bool = False,
    keep_all_tracks: bool = False,
) -> Model:
    """
    Read a TrackMate XML file and convert the tracks data to directed acyclic graphs.

    Each TrackMate track and its associated data described in the XML file
    are modeled as networkX directed graphs. Spots are modeled as graph
    nodes, and edges as graph edges. Spot, edge and track features are
    stored in node, edge and graph attributes, respectively.
    The rest of the information contained in the XML file is stored either
    as a metadata dict (TrackMate version, log, settings...) or in the Model
    features declaration.

    Parameters
    ----------
    xml_path : str
        Path of the XML file to process.
    keep_all_spots : bool, optional
        True to keep the spots filtered out in TrackMate, False otherwise.
        False by default.
    keep_all_tracks : bool, optional
        True to keep the tracks filtered out in TrackMate, False otherwise.
        False by default.

    Returns
    -------
    Model
        A Pycellin Model that contains all the data from the TrackMate XML file.
    """
    feat_declaration, data = _parse_model_tag(xml_path, keep_all_spots, keep_all_tracks)

    # Add in the metadata all the TrackMate info that was not in the
    # TrackMate XML `Model` tag.
    metadata = {}
    metadata["Name"] = Path(xml_path).stem
    metadata["Provenance"] = "TrackMate"
    metadata["Date"] = datetime.now()
    metadata["Pycellin_version"] = get_distribution("pycellin").version
    metadata["TrackMate_version"] = _get_trackmate_version(xml_path)
    dict_tags = _get_specific_tags(
        xml_path, ["Log", "Settings", "GUIState", "DisplaySettings"]
    )
    for tag_name, tag in dict_tags.items():
        element_string = ET.tostring(tag, encoding="utf-8").decode()
        metadata[tag_name] = element_string

    model = Model(metadata, feat_declaration, data)
    return model


if __name__ == "__main__":

    xml = "sample_data/FakeTracks.xml"
    # xml = "sample_data/FakeTracks_no_tracks.xml"

    # trackmate_version = _get_trackmate_version(xml)
    # print(trackmate_version)

    # elem = _get_specific_tags(xml, ["Settings", "Log"])
    # print(elem)
    # element_string = ET.tostring(elem["Settings"], encoding="utf-8").decode()
    # print(element_string)
    # elem_from_string = ET.fromstring(element_string)
    # print(elem_from_string)
    # print(elem_from_string.tag)

    model = load_TrackMate_XML(xml, keep_all_spots=True, keep_all_tracks=True)
    # print(model.metadata)
    # print(model.feat_declaration)
    # print(model.coredata)

    # for id, lin in model.coredata.data.items():
    #     print(f"ID: {id} - {lin}")

    model.coredata.data[0].plot_with_plotly()

    # TODO: for now one-node graph do not have track features like "real" lineages.
    # Should I add these features even if the value is None for consistency?
