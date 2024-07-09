#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy
import math
from pathlib import Path
from typing import Any, Union

from lxml import etree as ET
import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.metadata import Metadata, Feature
from pycellin.classes.data import CoreData
from pycellin.classes.lineage import CellLineage

# TODO: update all docstrings
# TODO: switch from nx.Digraph to CellLineage


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
        XML element iterator.
    ancestor : ET._Element
        Element encompassing the information to add.

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
            return units["spatialunits"] + "²"
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
    metadata: Metadata,
    units: dict[str, str],
):
    """
    Convert a TrackMate feature to a Pycellin one and add it to the metadata.

    Parameters
    ----------
    trackmate_feature : dict[str, str]
        The feature to add.
    feature_type : str
        The type of the feature to add (node, edge, or lineage).
    metadata : Metadata
        The metadata object to add the feature to.
    units : dict[str, str]
        The units of the TrackMate model.
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
    print(feature)

    match feature_type:
        case "SpotFeatures":
            feat_type = "node"
        case "EdgeFeatures":
            feat_type = "edge"
        case "TrackFeatures":
            feat_type = "lineage"
        case _:
            raise ValueError(f"Invalid feature type: {feature_type}")
    metadata._add_feature(feature, feat_type)


def _add_all_features(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    metadata: Metadata,
    units: dict[str, str],
):
    """
    Add all the TrackMate model features to a Metadata object.

    The model features are divided in 3 categories: SpotFeatures, EdgeFeatures and
    TrackFeatures. Those features are regrouped under the FeatureDeclarations tag.
    Some other features are used in the Spot and Track tags but are not declared in
    the FeatureDeclarations tag.

    Parameters
    ----------
    iterator : ET.iterparse
        XML element iterator.
    ancestor : ET._Element
        Element encompassing the information to add.
    """
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        # Features stored in the FeatureDeclarations tag.
        features = _get_features_dict(iterator, element)
        for feat in features:
            _convert_and_add_feature(feat, element.tag, metadata, units)
        # Features used in Spot tags but not declared in the FeatureDeclarations tag.
        if element.tag == "SpotFeatures":
            name_feat = Feature(
                "name", "Name of the spot", "CellLineage", "TrackMate", "string"
            )
            metadata._add_feature(name_feat, "node")
            id_feat = Feature(
                "ID", "Unique identifier of the spot", "CellLineage", "TrackMate", "int"
            )
            metadata._add_feature(id_feat, "node")
            roi_coord_feat = Feature(
                "ROI_COORDINATES",
                "List of coordinates of the region of interest",
                "CellLineage",
                "TrackMate",
                "float",
            )
            metadata._add_feature(roi_coord_feat, "node")
        # Feature used in Track tags but not declared in the FeatureDeclarations tag.
        if element.tag == "TrackFeatures":
            name_feat = Feature(
                "name", "Name of the track", "CellLineage", "TrackMate", "string"
            )
            metadata._add_feature(name_feat, "lineage")
        element.clear()
        event, element = next(iterator)


def _convert_attributes(
    attributes: dict[str, str],
    features: dict[str, CellLineage],
):
    """
    Convert the values of `attributes` from string to int or float.

    The type to convert to is given by the metadata that stores all the features info.

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
        If a feature has an invalid data_type (not "int", "float" nor "lineage").
    KeyError
        If a feature is not found in the metadata nor treated as a special case.
    """
    # TODO: should I add name and ID as features in the metadata...? ROI_N_POINT?
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
            raise KeyError(f"Feature {key} not found in the metadata.")


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


def _add_all_nodes(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    metadata: Metadata,
    lineage: CellLineage,
) -> None:
    """
    Add nodes and their attributes to a CellLineage.

    All the elements that are descendants of `ancestor` are explored.

    Parameters
    ----------
    iterator : ET.iterparse
        XML element iterator.
    ancestor : ET._Element
        Element encompassing the information to add.
    metadata : Metadata
        Metadata object holding the features information.
    lineage : CellLineage
        CellLineage to add the nodes to.
    """
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        event, element = next(iterator)
        if element.tag == "Spot" and event == "end":
            # All items in element.attrib are parsed as strings but most
            # of them (if not all) are numbers. So we need to do a
            # conversion based on these attributes type (attribute `isint`)
            # as defined in the metadata.
            attribs = deepcopy(element.attrib)
            try:
                _convert_attributes(attribs, metadata.node_feats)
            except ValueError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise
            except KeyError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise

            # The ROI coordinates are not stored in a tag attribute but in
            # the tag text. So we need to extract then format them.
            _convert_ROI_coordinates(element, attribs)

            # Now that all the node attributes have been updated, we can add
            # them to the Lineage.
            try:
                lineage.add_nodes_from([(int(attribs["ID"]), attribs)])
            except KeyError as err:
                print(
                    f"No key {err} in the attributes of "
                    f"current element '{element.tag}'. "
                    f"Not adding this node to the graph."
                )
            finally:
                element.clear()


def _add_edge_from_element(
    graph: nx.DiGraph,
    element: ET._Element,
    current_track_id: Any,
):
    """
    Add an edge and its attributes from an XML element.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph on which to add the edge.
    element : ET._Element
        Element holding the information to be added.
    current_track_id : Any
        Track ID of the track holding the edge.
    """
    attribs = deepcopy(element.attrib)
    _convert_attributes(attribs, graph.graph["Model"]["EdgeFeatures"])
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


# TODO: this methods add the edges to the graph but also gets the track attribute
# I don't see how to separate the two tasks while keeping a line by line parsing
# of the XML file, but I should at least rename this function to better reflect what
# it does.
def _add_all_edges(
    graph: nx.DiGraph,
    iterator: ET.iterparse,
    ancestor: ET._Element,
) -> list[dict[str, Any]]:
    """
    Add edges and their attributes to a graph.

    All the elements that are descendants of `ancestor` are explored.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph on which to add edges.
    iterator : ET.iterparse
        XML element iterator.
    ancestor : ET._Element
        Element encompassing the information to add.

    Returns
    -------
    list[dict[str, Any]]
        A dictionary of attributes for every track.
    """
    tracks_attributes = []
    event, element = next(iterator)
    current_track_id = None
    # Initialisation of current track information.
    if element.tag == "Track" and event == "start":
        # This condition is a bit of an overkill since the XML structure
        # SHOULD stay the same but better safe than sorry.
        # TODO: refactor this chunk that appears twice in this method.
        attribs = deepcopy(element.attrib)
        _convert_attributes(attribs, graph.graph["Model"]["TrackFeatures"])
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
            _convert_attributes(attribs, graph.graph["Model"]["TrackFeatures"])
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
            _add_edge_from_element(graph, element, current_track_id)

    return tracks_attributes


def _get_filtered_tracks_ID(
    iterator: ET.iterparse,
    ancestor: ET._Element,
) -> list[str]:
    """
    Get the list of IDs of the tracks to keep.

    Parameters
    ----------
    iterator : ET.iterparse
        XML element iterator.
    ancestor : ET._Element
        Element encompassing the information to add.

    Returns
    -------
    list[str]
        List of tracks ID to keep.
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
    graphs: list[nx.DiGraph],
    tracks_attributes: list[dict[str, Any]],
):
    """
    Add track attributes to each corresponding graph.

    Parameters
    ----------
    graphs : list[nx.DiGraph]
        List of graphs to update.
    tracks_attributes : list[dict[str, Any]]
        Dictionaries of tracks attributes.

    Raises
    ------
    ValueError
        If several different track IDs are found for one track.
    """
    for graph in graphs:
        # Finding the dict of attributes matching the track.
        tmp = set(t_id for n, t_id in graph.nodes(data="TRACK_ID"))

        if not tmp:
            # 'tmp' is empty because there's no nodes in the current graph.
            # Even if it can't be updated, we still want to return this graph.
            # updated_graphs.append(graph)
            continue
        elif tmp == {None}:
            # Happens when all the nodes do not have a TRACK_ID attribute.
            # updated_graphs.append(graph)
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


def _parse_model_tag(
    xml_path: str,
    keep_all_spots: bool,
    keep_all_tracks: bool,
    one_graph: bool,
) -> tuple[Metadata, CoreData]:
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
    one_graph : bool
        True to create only one graph (probably disconnected) that contains all
        nodes and edges, False to create a graph (connected) per track.

    Returns
    -------
    tuple[Metadata, CoreData]
        TODO
    """
    md = Metadata()

    # Creation of a graph that will hold all the tracks described
    # in the XML file. This means that if there's more than one track,
    # the resulting graph will be disconnected.
    lineage = CellLineage()

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

        # Get the spot, edge and track features and add them to the metadata.
        if element.tag == "FeatureDeclarations" and event == "start":
            _add_all_features(it, element, md, units)
            root.clear()

        # Adding the spots as nodes.
        if element.tag == "AllSpots" and event == "start":
            _add_all_nodes(it, element, md, lineage)
            root.clear()
            print(lineage.nodes[2004])

        # Adding the tracks as edges.
        if element.tag == "AllTracks" and event == "start":
            tracks_attributes = _add_all_edges(graph, it, element)
            root.clear()

            # Removal of filtered spots / nodes.
            if not keep_all_spots:
                # Those nodes belong to no tracks: they have a degree of 0.
                lone_nodes = [n for n, d in graph.degree if d == 0]
                graph.remove_nodes_from(lone_nodes)

        # Filtering out tracks and adding tracks attribute.
        if element.tag == "FilteredTracks" and event == "start":
            # Removal of filtered tracks / graphs.
            id_to_keep = _get_filtered_tracks_ID(it, element)
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
                    _add_tracks_info(graphs, tracks_attributes)
                except ValueError as err:
                    print(err)
                    # The program is in an impossible state so we need to stop.
                    raise

                # Also adding if each track was present in the 'FilteredTracks'
                # tag because this info is needed when reconstructing TM XMLs
                # from graphs.
                for g in graphs:
                    if "TRACK_ID" in g.graph:
                        if g.graph["TRACK_ID"] in id_to_keep:
                            g.graph["FilteredTrack"] = True
                        else:
                            g.graph["FilteredTrack"] = False

        if element.tag == "Model" and event == "end":
            break  # We are not interested in the following data.

    if one_graph:
        return [graph]
    else:
        return graphs


def load_TrackMate_XML(
    xml_path: str,
    keep_all_spots: bool = False,
    keep_all_tracks: bool = False,
    one_graph: bool = False,
) -> Model:
    """
    Read a TrackMate XML file and convert the tracks data to directed graphs.

    Each TrackMate track and its associated data described in the XML file
    are modeled as networkX directed graphs. Spots are modeled as graph
    nodes, and edges as graph edges. All data pertaining to the model
    itself such as units, spot features, etc. are stored in each graph as
    graph attributes.

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
    one_graph : bool, optional
        True to create only one graph (probably disconnected) that contains all
        nodes and edges, False to create a graph (connected) per track.
        False by default.

    Returns
    -------
    Model
        a Pycellin Model that contains the data from the TrackMate XML file.
    """
    # For now this function is just a wrapper for read_model, but in a future version
    # it will also take care of reading log, GUI state, settings and display settings.
    # log = read_log(xml_path)
    # gui_state = read_GUI_state(xml_path)
    # settings = read_settings(xml_path)
    # display_settings = read_display_settings(xml_path)

    metadata, data = _parse_model_tag(
        xml_path, keep_all_spots, keep_all_tracks, one_graph
    )
    model = Model(metadata, data, name=Path(xml_path).stem, provenance="TrackMate")
    return model


if __name__ == "__main__":

    xml = "sample_data/FakeTracks.xml"
    _parse_model_tag(xml, keep_all_spots=False, keep_all_tracks=False, one_graph=False)
