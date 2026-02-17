#!/usr/bin/env python3

import importlib
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any

import networkx as nx
from lxml import etree as ET

from pycellin.classes import (
    CellLineage,
    Data,
    Model,
    Property,
    PropsMetadata,
)
from pycellin.custom_types import PropertyType
from pycellin.graph.properties.core import create_cell_id_property
from pycellin.io.utils import (
    _split_graph_into_lineages,
    check_fusions,
    _update_node_prop_key,
    _update_lineage_prop_key,
    _update_lineages_IDs_key,
)


# TODO: convert "POSITION_T" into "time"


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
    units: dict[str, str] = {}
    if element.attrib:
        units = deepcopy(element.attrib)
    if "spatialunits" not in units:
        units["spatialunits"] = "pixel"  # TrackMate default value.
        msg = "WARNING: No spatial units found in the XML file. Setting to 'pixel'."
        warnings.warn(msg)
    if "timeunits" not in units:
        units["timeunits"] = "frame"  # TrackMate default value.
        msg = "WARNING: No time units found in the XML file. Setting to 'frame'."
        warnings.warn(msg)
    element.clear()  # We won't need it anymore so we free up some memory.
    # .clear() does not delete the element: it only removes all subelements
    # and clears or sets to `None` all attributes.
    return units


def _get_props_dict(
    iterator: ET.iterparse,
    ancestor: ET._Element,
) -> list[dict[str, str]]:
    """
    Get all the properties of ancestor and return them as a list.

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
        A list of dictionaries, each representing a property.
    """
    props = []
    event, element = next(iterator)  # Feature.
    while (event, element) != ("end", ancestor):
        if element.tag == "Feature" and event == "start":
            attribs = deepcopy(element.attrib)
            props.append(attribs)
        element.clear()
        event, element = next(iterator)
    return props


def _dimension_to_unit(trackmate_prop, units) -> str | None:
    """
    Convert the dimension of a property to its unit.

    Parameters
    ----------
    trackmate_prop : dict[str, str]
        The property to convert.
    units : dict[str, str]
        The units of the TrackMate model.

    Returns
    -------
    str | None
        The unit of the property.
    """
    dimension = trackmate_prop["dimension"]
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


def _convert_and_add_prop(
    trackmate_prop: dict[str, str],
    prop_type: str,
    props_md: PropsMetadata,
    units: dict[str, str],
) -> None:
    """
    Convert a TrackMate property to a pycellin one to add it to the properties metadata.

    Parameters
    ----------
    trackmate_prop : dict[str, str]
        The property to add.
    prop_type : str
        The type of the property to add (node, edge, or lineage).
    props_md : PropsMetadata
        The PropsMetadata object to add the property to.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model
        (`timeunits` and `spatialunits`).

    Raises
    ------
    ValueError
        If the property type is invalid.
    """
    if trackmate_prop["isint"] == "true":
        prop_dtype = "int"
    else:
        prop_dtype = "float"

    match prop_type:
        case "SpotFeatures":
            prop_type = "node"
        case "EdgeFeatures":
            prop_type = "edge"
        case "TrackFeatures":
            prop_type = "lineage"
        case _:
            raise ValueError(f"Invalid property type: {prop_type}")
    prop = Property(
        identifier=trackmate_prop["feature"],
        name=trackmate_prop["name"],
        description=trackmate_prop["name"],
        provenance="TrackMate",
        prop_type=prop_type,
        lin_type="CellLineage",
        dtype=prop_dtype,
        unit=_dimension_to_unit(trackmate_prop, units),
    )

    props_md._add_prop(prop)


def _add_all_props(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    props_md: PropsMetadata,
    units: dict[str, str],
) -> None:
    """
    Add all the TrackMate model properties to a PropsMetadata object.

    The model properties are divided in 3 categories: SpotFeatures, EdgeFeatures and
    TrackFeatures. Those properties are regrouped under the FeatureDeclarations tag.
    Some other properties are used in the Spot and Track tags but are not declared in
    the FeatureDeclarations tag.

    Parameters
    ----------
    iterator : ET.iterparse
        An iterator over XML elements.
    ancestor : ET._Element
        The XML element that encompasses the information to be added.
    props_md : PropsMetadata
        The PropsMetadata object to add the properties to.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model
        (`timeunits` and `spatialunits`).
    """
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        # Features stored in the FeatureDeclarations tag.
        props = _get_props_dict(iterator, element)
        for prop in props:
            _convert_and_add_prop(prop, element.tag, props_md, units)

        # Feature used in Spot tags but not declared in the FeatureDeclarations tag.
        if element.tag == "SpotFeatures":
            name_prop = Property(
                identifier="cell_name",
                name="cell name",
                description="Name of the spot",
                provenance="TrackMate",
                prop_type="node",
                lin_type="CellLineage",
                dtype="string",
            )
            props_md._add_prop(name_prop)

        # Feature used in Track tags but not declared in the FeatureDeclarations tag.
        if element.tag == "TrackFeatures":
            name_prop = Property(
                identifier="lineage_name",
                name="lineage name",
                description="Name of the track",
                provenance="TrackMate",
                prop_type="lineage",
                lin_type="CellLineage",
                dtype="string",
            )
            props_md._add_prop(name_prop)
        element.clear()
        event, element = next(iterator)


def _convert_attributes(
    attributes: dict[str, str],
    props: dict[str, Property],
    prop_type: PropertyType,
) -> None:
    """
    Convert the values of `attributes` from string to the correct data type.

    The type to convert to is given by the properties metadata that stores all
    the properties info.

    Parameters
    ----------
    attributes : dict[str, str]
        The dictionary whose values we want to convert.
    props : dict[str, Property]
        The dictionary of properties that contains the information on how to convert
        the values of `attributes`.
    prop_type : PropertyType
        The type of the property to convert (node, edge, or lineage).

    Raises
    ------
    ValueError
        If a property has an invalid dtype (not "int", "float" nor "string").

    Warns
    -----
    UserWarning
        If a property is not found in the properties metadata.
    """
    # TODO: Rewrite this.
    for key in attributes:
        if key in props:
            match props[key].dtype:
                case "int":
                    attributes[key] = int(attributes[key])  # type: ignore
                case "float":
                    attributes[key] = float(attributes[key])  # type: ignore
                case "string":
                    pass  # Nothing to do.
                case _:
                    raise ValueError(f"Invalid data type: {props[key].dtype}")
        elif key == "ID":
            # IDs are always integers.
            attributes[key] = int(attributes[key])  # type: ignore
        elif key == "name":
            # "name" is a string so we don't need to convert it.
            pass
        elif key == "ROI_N_POINTS":
            # This attribute is a special case (stored as a tag text instead of tag
            # attribute) and will be converted later, in _add_ROI_coordinates().
            pass
        else:
            msg = f"{prop_type.capitalize()} property {key} not found in the properties metadata."
            warnings.warn(msg)
            # In that case we add a stub version of the property to the properties
            # declaration. The user will need to manually update the property later on.
            missing_prop = Property(
                identifier=key,
                name=key,
                description="unknown",
                provenance="unknown",
                prop_type=prop_type,
                lin_type="CellLineage",
                dtype="unknown",
                unit="unknown",
            )
            props[key] = missing_prop


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
            f"No key 'ROI_N_POINTS' in the attributes of current element '{element.tag}'."
        )
    n_points = int(attribs["ROI_N_POINTS"])
    if element.text:
        points_coordinates = element.text.split()
        points_coordinates = [float(x) for x in points_coordinates]  # type: ignore
        points_dimension = len(points_coordinates) // n_points
        it = [iter(points_coordinates)] * points_dimension
        points_coordinates = list(zip(*it))  # type: ignore
        attribs["ROI_coords"] = points_coordinates
    else:
        attribs["ROI_coords"] = None


def _add_all_nodes(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    props_md: PropsMetadata,
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
    props_md : PropsMetadata
        An object holding the properties metadata information used to convert the
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
        If a node attribute is not found in the properties metadata.
    """
    segmentation = False
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        event, element = next(iterator)
        if element.tag == "Spot" and event == "end":
            # All items in element.attrib are parsed as strings but most
            # of them (if not all) are numbers. So we need to do a
            # conversion based on these attributes type (attribute `isint`)
            # as defined in the properties metadata.
            attribs = deepcopy(element.attrib)
            try:
                _convert_attributes(attribs, props_md.props, "node")
            except ValueError as err:
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
                msg = (
                    f"No key {err} in the attributes of current element "
                    f"'{element.tag}'. Not adding this node to the graph."
                )
                warnings.warn(msg)
            finally:
                element.clear()

    return segmentation


def _add_edge(
    element: ET._Element,
    props_md: PropsMetadata,
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
    props_md : PropsMetadata
        An object holding the properties metadata information used
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
    try:
        _convert_attributes(attribs, props_md.props, "edge")
    except ValueError as err:
        print(f"ERROR: {err} Please check the XML file.")
        raise
    try:
        entry_node_id = int(attribs["SPOT_SOURCE_ID"])
        exit_node_id = int(attribs["SPOT_TARGET_ID"])
    except KeyError as err:
        msg = (
            f"No key {err} in the attributes of current element '{element.tag}'. "
            f"Not adding this edge to the graph."
        )
        warnings.warn(msg)
    else:
        graph.add_edge(entry_node_id, exit_node_id)
        nx.set_edge_attributes(graph, {(entry_node_id, exit_node_id): attribs})
        # Adding the current track ID to the nodes of the newly created
        # edge. This will be useful later to filter nodes by track and
        # add the saved tracks attributes (as returned by this method).
        err_msg = f"Incoherent track ID for nodes {entry_node_id} and {exit_node_id}."
        entry_node = graph.nodes[entry_node_id]
        if "TRACK_ID" not in entry_node:
            entry_node["TRACK_ID"] = current_track_id
        else:
            assert entry_node["TRACK_ID"] == current_track_id, err_msg
        exit_node = graph.nodes[exit_node_id]
        if "TRACK_ID" not in exit_node:
            exit_node["TRACK_ID"] = current_track_id
        else:
            assert exit_node["TRACK_ID"] == current_track_id, err_msg
    finally:
        element.clear()


def _build_tracks(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    props_md: PropsMetadata,
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
    props_md : PropsMetadata
        An object holding the properties metadata information used
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
            try:
                _convert_attributes(attribs, props_md.props, "lineage")
            except ValueError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise
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
            assert current_track_id is not None, "No current track ID."
            _add_edge(element, props_md, graph, current_track_id)

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
        msg = (
            f"No key {err} in the attributes of current element "
            f"'{element.tag}'. Ignoring this track."
        )
        warnings.warn(msg)

    while (event, element) != ("end", ancestor):
        event, element = next(iterator)
        if element.tag == "TrackID" and event == "start":
            attribs = deepcopy(element.attrib)
            try:
                filtered_tracks_ID.append(int(attribs["TRACK_ID"]))
            except KeyError as err:
                msg = (
                    f"No key {err} in the attributes of current element "
                    f"'{element.tag}'. Ignoring this track."
                )
                warnings.warn(msg)

    return filtered_tracks_ID


def _update_props_metadata(
    props_md: PropsMetadata,
    units: dict[str, str],
    segmentation: bool,
) -> None:
    """
    Update the properties metadata to match pycellin conventions.

    Parameters
    ----------
    props_md : PropsMetadata
        The properties metadata to update.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model
        (`timeunits` and `spatialunits`).
    segmentation : bool
        True if the model has segmentation data, False otherwise.
    """
    # Node properties.
    prop_cell_ID = create_cell_id_property("TrackMate")
    props_md._add_prop(prop_cell_ID)
    props_md._protect_prop("cell_ID")
    for axis in ["x", "y", "z"]:
        props_md._change_prop_identifier(f"POSITION_{axis.upper()}", f"cell_{axis}")
        props_md._change_prop_description(f"cell_{axis}", f"{axis.upper()} coordinate of the cell")
    props_md._change_prop_identifier("FRAME", "frame")
    props_md._protect_prop("frame")
    if segmentation:
        roi_coord_prop = Property(
            identifier="ROI_coords",
            name="ROI coords",
            description="List of coordinates of the region of interest",
            provenance="TrackMate",
            prop_type="node",
            lin_type="CellLineage",
            dtype="float",
            unit=units["spatialunits"],
        )
        props_md._add_prop(roi_coord_prop)

    # Edge properties.
    if "EDGE_X_LOCATION" in props_md.props:
        for axis in ["x", "y", "z"]:
            props_md._change_prop_identifier(f"EDGE_{axis.upper()}_LOCATION", f"link_{axis}")
            desc = f"{axis.upper()} coordinate of the link, i.e. mean coordinate of its two cells"
            props_md._change_prop_description(f"link_{axis}", desc)

    # Lineage properties.
    props_md._change_prop_identifier("TRACK_ID", "lineage_ID")
    props_md._change_prop_description("lineage_ID", "Unique identifier of the lineage")
    props_md._protect_prop("lineage_ID")
    prop_filtered_track = Property(
        identifier="FilteredTrack",
        name="FilteredTrack",
        description="True if the track was not filtered out in TrackMate",
        provenance="TrackMate",
        prop_type="lineage",
        lin_type="CellLineage",
        dtype="int",
    )
    props_md._add_prop(prop_filtered_track)
    if "TRACK_X_LOCATION" in props_md.props:
        for axis in ["x", "y", "z"]:
            props_md._change_prop_identifier(f"TRACK_{axis.upper()}_LOCATION", f"lineage_{axis}")
            desc = f"{axis.upper()} coordinate of the lineage, i.e. mean coordinate of its cells"
            props_md._change_prop_description(f"lineage_{axis}", desc)


def _update_location_related_props(
    lineage: CellLineage,
) -> None:
    """
    Update properties related to location of lineage, nodes and edges in a lineage.

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    """
    # Nodes
    for _, data in lineage.nodes(data=True):
        for axis in ["x", "y", "z"]:
            data[f"cell_{axis}"] = data.pop(f"POSITION_{axis.upper()}", None)

    # Edges
    # Mastodon does not have the EDGE_{axis}_LOCATION so we have to check existence first
    if lineage.edges():
        first_edge = next(iter(lineage.edges(data=True)))
        has_edge_location = any(
            f"EDGE_{axis.upper()}_LOCATION" in first_edge[2] for axis in ["x", "y", "z"]
        )
        if has_edge_location:
            for _, _, data in lineage.edges(data=True):
                for axis in ["x", "y", "z"]:
                    data[f"link_{axis}"] = data.pop(f"EDGE_{axis.upper()}_LOCATION", None)
        # else:
        #     # If the EDGE_{axis}_LOCATION properties are not present, we compute the mean
        #     # coordinate of the two nodes of the edge.
        #     for u, v, data in lineage.edges(data=True):
        #         for axis in ["x", "y", "z"]:
        #             coord_u = lineage.nodes[u][f"cell_{axis}"]
        #             coord_v = lineage.nodes[v][f"cell_{axis}"]
        #             data[f"link_{axis}"] = (coord_u + coord_v) / 2
    else:
        has_edge_location = False

    # Lineage
    if "TRACK_X_LOCATION" in lineage.graph:
        for axis in ["x", "y", "z"]:
            lineage.graph[f"lineage_{axis}"] = lineage.graph.pop(
                f"TRACK_{axis.upper()}_LOCATION", None
            )
    else:
        if len(lineage) == 1 and has_edge_location:
            # This is a one-node lineage from TrackMate.
            # One-node graph don't have the TRACK_X_LOCATION, TRACK_Y_LOCATION
            # and TRACK_Z_LOCATION properties in the graph, so we have to create it.
            node = [n for n in lineage.nodes][0]
            for axis in ["x", "y", "z"]:
                lineage.graph[f"lineage_{axis}"] = lineage.nodes[node][f"cell_{axis}"]
        # else:
        #     # Mastodon does not have the TRACK_{axis}_LOCATION, so we compute the mean
        #     # coordinate of the lineage.
        #     for axis in ["x", "y", "z"]:
        #         coords = [data[f"cell_{axis}"] for _, data in lineage.nodes(data=True)]
        #         lineage.graph[f"lineage_{axis}"] = sum(coords) / len(coords)


def _parse_model_tag(
    xml_path: str,
    keep_all_spots: bool,
    keep_all_tracks: bool,
) -> tuple[dict[str, str], PropsMetadata, Data]:
    """
    Read an XML file and convert the model data into several graphs.

    Each TrackMate track and its associated data described in the XML file
    are modeled as networkX directed graphs. Spots are modeled as graph
    nodes, and edges as graph edges. Spot, edge and track properties are
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
    tuple[dict[str, str], PropsMetadata, Data]
        A tuple containing the space and time units, the properties metadata
        and the data of the model.
    """
    props_md = PropsMetadata()

    # Creation of a graph that will hold all the tracks described
    # in the XML file. This means that if there's more than one track,
    # the resulting graph will be disconnected.
    graph: nx.DiGraph = nx.DiGraph()

    # So as not to load the entire XML file into memory at once, we're
    # using an iterator to browse over the tags one by one.
    # The events 'start' and 'end' correspond respectively to the opening
    # and the closing of the considered tag.
    it = ET.iterparse(xml_path, events=["start", "end"])
    _, root = next(it)  # Saving the root of the tree for later cleaning.

    for event, element in it:
        # Get the temporal and spatial units of the model. They will be
        # injected into each Property.
        if element.tag == "Model" and event == "start":
            units = _get_units(element)
            root.clear()  # Cleaning the tree to free up some memory.
            # All the browsed subelements of `root` are deleted.

        # Get the spot, edge and track properties and add them to the
        # properties metadata.
        if element.tag == "FeatureDeclarations" and event == "start":
            _add_all_props(it, element, props_md, units)
            root.clear()

        # Adding the spots as nodes.
        if element.tag == "AllSpots" and event == "start":
            segmentation = _add_all_nodes(it, element, props_md, graph)
            root.clear()

        # Adding the tracks as edges.
        if element.tag == "AllTracks" and event == "start":
            tracks_attributes = _build_tracks(it, element, props_md, graph)
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
                to_remove = [n for n, t in graph.nodes(data="TRACK_ID") if t not in id_to_keep]
                graph.remove_nodes_from(to_remove)

        if element.tag == "Model" and event == "end":
            break  # We are not interested in the following data.

    # We want one lineage per track, so we need to split the graph
    # into its connected components.
    lineages = _split_graph_into_lineages(
        graph,
        lin_props=tracks_attributes,
        lineage_ID_key="TRACK_ID",
    )

    # For pycellin compatibility, some TrackMate properties have to be renamed.
    # We only rename properties that are either essential to the functioning of
    # pycellin or confusing (e.g. "name" is a spot and a track property).
    _update_props_metadata(props_md, units, segmentation)
    _update_lineages_IDs_key(lineages, "TRACK_ID")
    for lin in lineages:
        for key_name, new_key in [
            ("TRACK_ID", "lineage_ID"),  # mandatory
            ("ID", "cell_ID"),  # mandatory
            ("FRAME", "frame"),  # mandatory
            ("name", "cell_name"),  # confusing
        ]:
            _update_node_prop_key(lin, key_name, new_key)
        _update_lineage_prop_key(lin, "name", "lineage_name")
        _update_location_related_props(lin)

        # Adding if each track was present in the 'FilteredTracks' tag
        # because this info is needed when reconstructing TrackMate XMLs
        # from graphs.
        if lin.graph["lineage_ID"] in id_to_keep:
            lin.graph["FilteredTrack"] = True
        else:
            lin.graph["FilteredTrack"] = False

    return units, props_md, Data({lin.graph["lineage_ID"]: lin for lin in lineages})


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
    dict_tags = {}
    for tag in tag_names:
        it = ET.iterparse(xml_path, tag=tag)
        for _, element in it:
            dict_tags[element.tag] = deepcopy(element)
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
        The version of TrackMate used to generate the XML file. If the
        version cannot be found, "unknown" is returned.
    """
    it = ET.iterparse(xml_path, tag="TrackMate")
    for _, element in it:
        version = str(element.attrib["version"])
        return version
    return "unknown"


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
    for element in settings.iterchildren("ImageData"):
        try:
            return float(element.attrib["timeinterval"])
        except KeyError:
            raise KeyError("The 'timeinterval' attribute is missing in the 'ImageData' element.")
        except ValueError:
            raise ValueError("The 'timeinterval' attribute cannot be converted to float.")

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
    for element in settings.iterchildren("ImageData"):
        pixel_size = {}
        for key_TM, key_pycellin in zip(
            ["pixelwidth", "pixelheight", "voxeldepth"],
            ["pixel_width", "pixel_height", "pixel_depth"],
        ):
            try:
                pixel_size[key_pycellin] = float(element.attrib[key_TM])
            except KeyError:
                raise KeyError(f"The {key_TM} attribute is missing in the 'ImageData' element.")
            except ValueError:
                raise ValueError(f"The {key_TM} attribute cannot be converted to float.")
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
    nodes, and edges as graph edges. Spot, edge and track properties are
    stored in node, edge and graph attributes, respectively.
    The rest of the information contained in the XML file is stored either
    as a metadata dict (TrackMate version, log, settings...) or in the Model
    properties metadata.

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
        A pycellin Model that contains all the data from the TrackMate XML file.
    """
    units, props_md, data = _parse_model_tag(xml_path, keep_all_spots, keep_all_tracks)

    # Add in the metadata all the TrackMate info that was not in the
    # TrackMate XML `Model` tag.
    dict_tags = _get_specific_tags(xml_path, ["Log", "Settings", "GUIState", "DisplaySettings"])
    pixel_size = _get_pixel_size(dict_tags["Settings"])
    metadata: dict[str, Any] = {}
    metadata["reference_time_property"] = "POSITION_T"
    # Dimensions info
    # TODO: currently we can have frame as reference time property but seconds as unit
    # Maybe remove time_unit and time_step from metadata?
    metadata["space_unit"] = units["spatialunits"]
    metadata["time_unit"] = units["timeunits"]
    metadata["time_step"] = _get_time_step(dict_tags["Settings"])
    metadata["pixel_width"] = pixel_size.get("pixel_width")
    metadata["pixel_height"] = pixel_size.get("pixel_height")
    metadata["pixel_depth"] = pixel_size.get("pixel_depth")
    # Traceability info
    metadata["name"] = Path(xml_path).stem
    metadata["file_location"] = xml_path
    metadata["provenance"] = "TrackMate"
    metadata["TrackMate_version"] = _get_trackmate_version(xml_path)
    # The rest of the tags
    for tag_name, tag in dict_tags.items():
        element_string = ET.tostring(tag, encoding="utf-8").decode()
        metadata[tag_name] = element_string

    model = Model(metadata, props_md, data)
    check_fusions(model)  # pycellin DOES NOT support fusion events

    return model


if __name__ == "__main__":
    # xml = "sample_data/FakeTracks.xml"
    # xml = "sample_data/FakeTracks_no_tracks.xml"
    xml = "sample_data/Ecoli_growth_on_agar_pad.xml"
    # xml = "sample_data/Ecoli_growth_on_agar_pad_with_fusions.xml"
    # xml = "sample_data/Celegans-5pc-17timepoints.xml"

    model = load_TrackMate_XML(xml)  # , keep_all_spots=True, keep_all_tracks=True)
    print(model)
    print(model.props_metadata)
    # print(model.model_metadata.pycellin_version)
    # print(model.model_metadata)
    # print(model.props_md.node_props.keys())
    # print(model.data)
    # for lin in model.get_cell_lineages():
    #     print(lin)

    lineage = model.data.cell_data[0]
    # for n in lineage.nodes(data=True):
    #     print(n)
    # lineage.plot(node_hover_props=["cell_ID", "cell_name"])

    # lineage = model.data.cell_data[0]
    # lineage.plot(node_hover_props=["cell_ID", "cell_name"])
