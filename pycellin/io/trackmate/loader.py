#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy
from datetime import datetime
import importlib
from pathlib import Path
from typing import Any
import warnings

from lxml import etree as ET
import networkx as nx

from pycellin.classes import Model
from pycellin.classes import FeaturesDeclaration, Feature, cell_ID_Feature
from pycellin.classes import Data
from pycellin.classes import CellLineage


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
    if element.attrib:
        units = deepcopy(element.attrib)
    else:
        units = {}
    if "spatialunits" not in units:
        units["spatialunits"] = "pixel"  # TrackMate default value.
        print("WARNING: No spatial units found in the XML file. Setting to 'pixel'.")
    if "timeunits" not in units:
        units["timeunits"] = "frame"  # TrackMate default value.
        print("WARNING: No time units found in the XML file. Setting to 'frame'.")
    element.clear()  # We won't need it anymore so we free up some memory.
    # .clear() does not delete the element: it only removes all subelements
    # and clears or sets to `None` all attributes.
    return units


def _get_features_dict(
    iterator: ET.iterparse,
    ancestor: ET._Element,
) -> list[dict[str, str]]:
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
    list[dict[str, str]]
        A list of dictionaries, each representing a feature.
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


def _dimension_to_unit(trackmate_feature, units) -> str:
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
            return None
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
    fdec: FeaturesDeclaration,
    units: dict[str, str],
) -> None:
    """
    Convert a TrackMate feature to a Pycellin one to add it to the features declaration.

    Parameters
    ----------
    trackmate_feature : dict[str, str]
        The feature to add.
    feature_type : str
        The type of the feature to add (node, edge, or lineage).
    fdec : FeaturesDeclaration
        The FeaturesDeclaration object to add the feature to.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model
        (`timeunits` and `spatialunits`).

    Raises
    ------
    ValueError
        If the feature type is invalid.
    """
    feat_name = trackmate_feature["feature"]
    feat_description = trackmate_feature["name"]
    feat_provenance = "TrackMate"
    feat_lineage_type = "CellLineage"
    if trackmate_feature["isint"] == "true":
        feat_data_type = "int"
    else:
        feat_data_type = "float"
    feat_unit = _dimension_to_unit(trackmate_feature, units)

    match feature_type:
        case "SpotFeatures":
            feat_type = "node"
        case "EdgeFeatures":
            feat_type = "edge"
        case "TrackFeatures":
            feat_type = "lineage"
        case _:
            raise ValueError(f"Invalid feature type: {feature_type}")
    feature = Feature(
        feat_name,
        feat_description,
        feat_provenance,
        feat_type,
        feat_lineage_type,
        feat_data_type,
        feat_unit,
    )

    fdec._add_feature(feature)


def _add_all_features(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    fdec: FeaturesDeclaration,
    units: dict[str, str],
) -> None:
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
    fdec : FeaturesDeclaration
        The FeaturesDeclaration object to add the features to.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model
        (`timeunits` and `spatialunits`).
    """
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        # Features stored in the FeatureDeclarations tag.
        features = _get_features_dict(iterator, element)
        for feat in features:
            _convert_and_add_feature(feat, element.tag, fdec, units)

        # Features used in Spot tags but not declared in the FeatureDeclarations tag.
        if element.tag == "SpotFeatures":
            name_feat = Feature(
                name="cell_name",
                description="Name of the spot",
                provenance="TrackMate",
                feat_type="node",
                lin_type="CellLineage",
                data_type="string",
            )
            fdec._add_feature(name_feat)

        # Feature used in Track tags but not declared in the FeatureDeclarations tag.
        if element.tag == "TrackFeatures":
            name_feat = Feature(
                name="lineage_name",
                description="Name of the track",
                provenance="TrackMate",
                feat_type="lineage",
                lin_type="CellLineage",
                data_type="string",
            )
            fdec._add_feature(name_feat)
        element.clear()
        event, element = next(iterator)


def _convert_attributes(
    attributes: dict[str, str],
    features: dict[str, Feature],
) -> None:
    """
    Convert the values of `attributes` from string to the correct data type.

    The type to convert to is given by the features declaration that stores all
    the features info.

    Parameters
    ----------
    attributes : dict[str, str]
        The dictionary whose values we want to convert.
    features : dict[str, Feature]
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
                    raise ValueError(f"Invalid data type: {features[key].data_type}")
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
) -> None:
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
            f"No key 'ROI_N_POINTS' in the attributes "
            f"of current element '{element.tag}'."
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
    fdec: FeaturesDeclaration,
    graph: nx.DiGraph,
) -> bool:
    """
    Add nodes and their attributes to a graph and return the presence of segmentation.

    All the elements that are descendants of `ancestor` are explored.

    Parameters
    ----------
    iterator : ET.iterparse
        An iterator over XML elements.
    ancestor : ET._Element
        The XML element that encompasses the information to be added.
    fdec : FeaturesDeclaration
        An object holding the features declaration information used to convert the
        node attributes.
    graph : nx.DiGraph
        Graph to add the nodes to.

    Returns
    -------
    bool
        True if the model has segmentation data, False otherwise

    Raises
    ------
    ValueError
        If a node attribute cannot be converted to the expected type.
    KeyError
        If a node attribute is not found in the features declaration.
    """
    segmentation = False
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
                _convert_attributes(attribs, fdec.feats_dict)
            except ValueError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise
            except KeyError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise

            # The ROI coordinates are not stored in a tag attribute but in
            # the tag text. So we need to extract then format them.
            # In case of a single-point detection, the `ROI_N_POINTS` attribute
            # is not present.
            if segmentation:
                try:
                    _convert_ROI_coordinates(element, attribs)
                except KeyError as err:
                    print(err)
            else:
                if "ROI_N_POINTS" in attribs:
                    segmentation = True
                    _convert_ROI_coordinates(element, attribs)

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

    return segmentation


def _add_edge(
    element: ET._Element,
    fdec: FeaturesDeclaration,
    graph: nx.DiGraph,
    current_track_id: int,
) -> None:
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
    fdec : FeaturesDeclaration
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
    _convert_attributes(attribs, fdec.feats_dict)
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
    fdec: FeaturesDeclaration,
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
    fdec : FeaturesDeclaration
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
            _convert_attributes(attribs, fdec.feats_dict)
            tracks_attributes.append(attribs)
            try:
                current_track_id = attribs["TRACK_ID"]
            except KeyError as err:
                message = (
                    f"No key {err} in the attributes of current element "
                    f"'{element.tag}'. Please check the XML file."
                )
                raise KeyError(message)

        # Edge creation.
        if element.tag == "Edge" and event == "start":
            _add_edge(element, fdec, graph, current_track_id)

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

    Raises
    ------
    KeyError
        If the "TRACK_ID" attribute is not found
        in the attributes of the current element.
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
) -> None:
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
    graph: nx.DiGraph,
    tracks_attributes: list[dict[str, Any]],
) -> list[CellLineage]:
    """
    Split a graph into several subgraphs, each representing a lineage.

    Parameters
    ----------
    lineage : nx.DiGraph
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
    lineages = [
        CellLineage(graph.subgraph(c).copy())
        for c in nx.weakly_connected_components(graph)
    ]
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
    fdec: FeaturesDeclaration,
    units: dict[str, str],
    segmentation: bool,
) -> None:
    """
    Update the features declaration to match Pycellin conventions.

    Parameters
    ----------
    fdec : FeaturesDeclaration
        The features declaration to update.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model
        (`timeunits` and `spatialunits`).
    segmentation : bool
        True if the model has segmentation data, False otherwise.
    """
    # Node features.
    feat_cell_ID = cell_ID_Feature("TrackMate")
    fdec._add_feature(feat_cell_ID)
    fdec._protect_feature("cell_ID")
    for axis in ["x", "y", "z"]:
        fdec._rename_feature(f"POSITION_{axis.upper()}", f"cell_{axis}")
        fdec._modify_feature_description(
            f"cell_{axis}", f"{axis.upper()} coordinate of the cell"
        )
    fdec._rename_feature("FRAME", "frame")
    fdec._protect_feature("frame")
    if segmentation:
        roi_coord_feat = Feature(
            name="ROI_coords",
            description="List of coordinates of the region of interest",
            provenance="TrackMate",
            feat_type="node",
            lin_type="CellLineage",
            data_type="float",
            unit=units["spatialunits"],
        )
        fdec._add_feature(roi_coord_feat)

    # Edge features.
    if "EDGE_X_LOCATION" in fdec.feats_dict:
        for axis in ["x", "y", "z"]:
            fdec._rename_feature(f"EDGE_{axis.upper()}_LOCATION", f"link_{axis}")
            desc = (
                f"{axis.upper()} coordinate of the link, "
                "i.e. mean coordinate of its two cells"
            )
            fdec._modify_feature_description(f"link_{axis}", desc)

    # Lineage features.
    fdec._rename_feature("TRACK_ID", "lineage_ID")
    fdec._modify_feature_description("lineage_ID", "Unique identifier of the lineage")
    fdec._protect_feature("lineage_ID")
    feat_filtered_track = Feature(
        name="FilteredTrack",
        description="True if the track was not filtered out in TrackMate",
        provenance="TrackMate",
        feat_type="lineage",
        lin_type="CellLineage",
        data_type="int",
    )
    fdec._add_feature(feat_filtered_track)
    if "TRACK_X_LOCATION" in fdec.feats_dict:
        for axis in ["x", "y", "z"]:
            fdec._rename_feature(f"TRACK_{axis.upper()}_LOCATION", f"lineage_{axis}")
            desc = (
                f"{axis.upper()} coordinate of the lineage, "
                "i.e. mean coordinate of its cells"
            )
            fdec._modify_feature_description(f"lineage_{axis}", desc)


def _update_node_feature_key(
    lineage: CellLineage,
    old_key: str,
    new_key: str,
) -> None:
    """
    Update the key of a feature in all the nodes of a lineage.

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    old_key : str
        The old key of the feature.
    new_key : str
        The new key of the feature.
    """
    for node in lineage.nodes:
        if old_key in lineage.nodes[node]:
            lineage.nodes[node][new_key] = lineage.nodes[node].pop(old_key)


def _update_TRACK_ID(
    lineage: CellLineage,
) -> None:
    """
    Update the TRACK_ID feature in the nodes and in the graph of a lineage.

    In the case of a one-node lineage, TRACK_ID does not exist in the graph
    nor in the nodes. So we define the lineage_ID as minus the node ID.
    That way, it is easy to discriminate between one-node lineages
    (negative IDs) and multi-nodes lineages (positive IDs).

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    """
    if "TRACK_ID" in lineage.graph:
        lineage.graph["lineage_ID"] = lineage.graph.pop("TRACK_ID")
    else:
        # One-node graph don't have the TRACK_ID feature in the graph
        # or in the nodes, so we have to create it.
        # We set the ID of a one-node lineage to the negative of the node ID.
        assert len(lineage) == 1, "TRACK_ID not found and not a one-node lineage."
        node = [n for n in lineage.nodes][0]
        lineage.graph["lineage_ID"] = -node


def _update_location_related_features(
    lineage: CellLineage,
) -> None:
    """
    Update features related to location of lineage, nodes and edges in a lineage.

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    """
    # Nodes
    for _, data in lineage.nodes(data=True):
        for axis in ["x", "y", "z"]:
            data[f"cell_{axis}"] = data.pop(f"POSITION_{axis.upper()}")

    # Edges
    for _, _, data in lineage.edges(data=True):
        for axis in ["x", "y", "z"]:
            data[f"link_{axis}"] = data.pop(f"EDGE_{axis.upper()}_LOCATION")

    # Lineage
    if "TRACK_X_LOCATION" in lineage.graph:
        for axis in ["x", "y", "z"]:
            lineage.graph[f"lineage_{axis}"] = lineage.graph.pop(
                f"TRACK_{axis.upper()}_LOCATION"
            )
    else:
        # One-node graph don't have the TRACK_X_LOCATION, TRACK_Y_LOCATION
        # and TRACK_Z_LOCATION features in the graph, so we have to create it.
        assert (
            len(lineage) == 1
        ), "TRACK_X_LOCATION not found and not a one-node lineage."
        node = [n for n in lineage.nodes][0]
        for axis in ["x", "y", "z"]:
            lineage.graph[f"lineage_{axis}"] = lineage.nodes[node][f"cell_{axis}"]


def _parse_model_tag(
    xml_path: str,
    keep_all_spots: bool,
    keep_all_tracks: bool,
) -> tuple[dict[str, str], FeaturesDeclaration, Data]:
    """
    Read an XML file and convert the model data into several graphs.

    Each TrackMate track and its associated data described in the XML file
    are modeled as networkX directed graphs. Spots are modeled as graph
    nodes, and edges as graph edges. Spot, edge and track features are
    stored in node, edge and graph attributes, respectively.

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
    tuple[dict[str, str], FeaturesDeclaration, Data]
        A tuple containing the space and time units, the features declaration
        and the data of the model.
    """
    fd = FeaturesDeclaration()

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
            segmentation = _add_all_nodes(it, element, fd, graph)
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
    # We only rename features that are essential to the functioning of Pycellin.
    _update_features_declaration(fd, units, segmentation)
    for lin in lineages:
        for key_name, new_key in [
            ("ID", "cell_ID"),
            ("FRAME", "frame"),
        ]:
            _update_node_feature_key(lin, key_name, new_key)
        _update_TRACK_ID(lin)
        _update_location_related_features(lin)

        # Adding if each track was present in the 'FilteredTracks' tag
        # because this info is needed when reconstructing TrackMate XMLs
        # from graphs.
        if lin.graph["lineage_ID"] in id_to_keep:
            lin.graph["FilteredTrack"] = True
        else:
            lin.graph["FilteredTrack"] = False

    return units, fd, Data({lin.graph["lineage_ID"]: lin for lin in lineages})


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


def _get_time_step(settings: ET._Element) -> float:
    """
    Extract the time step of the TrackMate model.

    Parameters
    ----------
    settings : ET._Element
        The XML element containing the settings of the TrackMate model.

    Returns
    -------
    float
        The time step in the TrackMate model.

    Raises
    ------
    ValueError
        If the 'timeinterval' attribute is missing or cannot be converted to float.
    KeyError
        If the 'ImageData' element is not found in the settings.
    """
    for element in settings.iterchildren():
        if element.tag == "ImageData":
            try:
                return float(element.attrib["timeinterval"])
            except KeyError:
                raise KeyError(
                    "The 'timeinterval' attribute is missing "
                    "in the 'ImageData' element."
                )
            except ValueError:
                raise ValueError(
                    "The 'timeinterval' attribute cannot be converted to float."
                )

    raise KeyError("The 'ImageData' element is not found in the settings.")


def _get_pixel_size(settings: ET._Element) -> dict[str, float]:
    """
    Extract the pixel size of the TrackMate model.

    Parameters
    ----------
    settings : ET._Element
        The XML element containing the settings of the TrackMate model.

    Returns
    -------
    dict[str, float]
        The pixel width and heigth in the TrackMate model.

    Raises
    ------
    ValueError
        If the 'pixelwidth', 'pixelheight' or 'voxeldepth' attribute
        cannot be converted to float.
    KeyError
        If the 'pixelwidth', 'pixelheight' or 'voxeldepth' attribute is missing,
        or if the 'ImageData' element is not found in the settings.
    """
    for element in settings.iterchildren():
        if element.tag == "ImageData":
            pixel_size = {}
            for key_TM, key_pycellin in zip(
                ["pixelwidth", "pixelheight", "voxeldepth"],
                ["width", "height", "depth"],
            ):
                try:
                    pixel_size[key_pycellin] = float(element.attrib[key_TM])
                except KeyError:
                    raise KeyError(
                        f"The {key_TM} attribute is missing "
                        "in the 'ImageData' element."
                    )
                except ValueError:
                    raise ValueError(
                        f"The {key_TM} attribute cannot be converted to float."
                    )
            return pixel_size

    raise KeyError("The 'ImageData' element is not found in the settings.")


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
    units, fdec, data = _parse_model_tag(xml_path, keep_all_spots, keep_all_tracks)

    # Add in the metadata all the TrackMate info that was not in the
    # TrackMate XML `Model` tag.
    metadata = {}
    metadata["name"] = Path(xml_path).stem
    metadata["file_location"] = xml_path
    metadata["provenance"] = "TrackMate"
    metadata["date"] = datetime.now()
    metadata["space_unit"] = units["spatialunits"]
    metadata["time_unit"] = units["timeunits"]
    try:
        version = importlib.metadata.version("pycellin")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    metadata["pycellin_version"] = version
    metadata["TrackMate_version"] = _get_trackmate_version(xml_path)
    dict_tags = _get_specific_tags(
        xml_path, ["Log", "Settings", "GUIState", "DisplaySettings"]
    )
    metadata["time_step"] = _get_time_step(dict_tags["Settings"])
    metadata["pixel_size"] = _get_pixel_size(dict_tags["Settings"])
    for tag_name, tag in dict_tags.items():
        element_string = ET.tostring(tag, encoding="utf-8").decode()
        metadata[tag_name] = element_string

    model = Model(metadata, fdec, data)

    # Pycellin DOES NOT support fusion events.
    all_fusions = model.get_fusions()
    if all_fusions:
        # TODO: link toward correct documentation when it is written.
        fusion_warning = (
            f"Unsupported data, {len(all_fusions)} cell fusions detected. "
            "It is advised to deal with them before any other processing, "
            "especially for tracking related features. Crashes and incorrect "
            "results can occur. See documentation for more details."
        )
        warnings.warn(fusion_warning)

    return model


if __name__ == "__main__":

    # import math

    # xml = "sample_data/FakeTracks.xml"
    # xml = "sample_data/FakeTracks_no_tracks.xml"
    xml = "sample_data/Ecoli_growth_on_agar_pad.xml"
    # xml = "sample_data/Ecoli_growth_on_agar_pad_with_fusions.xml"
    # xml = "E:/Pasteur/LS_data/LStoLX/230328GreffeGakaYFPMyogTdtmdxFDBTryplen1-movie01-01-Scene-15-TR37-A01.xml"

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
    print(model)
    print(model.feat_declaration)
    print(model.metadata["pycellin_version"])
    # print(model.metadata)
    # print(model.fdec.node_feats.keys())
    # print(model.data)

    # lineage = model.data.cell_data[0]

    # print(lineage, type(lineage))
    # # print(lin.nodes)
    # closest_cells = model.data.get_closest_cells(2046, lineage)
    # for cell, lin in closest_cells:
    #     print(math.dist(lineage.nodes[2046]["location"], lin.nodes[cell]["location"]))

    # for id, lin in model.data.cell_data.items():
    #     print(f"ID: {id} - {lin}")

    # for lin in model.data.cell_data.values():
    #     if len(lin) > 1:
    #         lin.plot()

    # print(model.data.cell_data[-2094].nodes[2094])
    # model.data.cell_data[0].plot()

    # TODO: for now one-node graph do not have track features like "real" lineages.
    # Should I add these features even if the value is None for consistency?
