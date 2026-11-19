#!/usr/bin/env python3

"""Reader for TrackMate XML files."""

import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

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
from pycellin.io.utils import (
    _check_fusions,
    _split_graph_into_lineages,
    _update_lineage_prop_key,
    _update_lineages_ids_key,
    _update_node_prop_key,
)
from pycellin.properties.core import create_cell_id_property, create_time_property
from pycellin.properties.morphology import create_cell_contour_property
from pycellin.utils import _check_literal_type

logger = logging.getLogger(__name__)

#: What the loader keeps of the spots outside tracks. As in TrackMate, visible spots
#: have a VISIBILITY of 1. The signature of read_trackmate_xml() repeats these values,
#: so that its documentation shows them: they need to be changed together.
_LoneSpotsOption = Literal["none", "visible", "all"]
#: What the loader keeps of the tracks. As in TrackMate, visible tracks are listed in
#: FilteredTracks. The signature of read_trackmate_xml() repeats these values too.
_TracksOption = Literal["visible", "all"]


def _get_units(
    element: ET._Element,
) -> dict[str, str]:
    """
    Extract units information from an XML element and return it as a dictionary.

    This function deep copies the attributes of the XML element into a dictionary,
    then clears the element to free up memory. A missing spatial or time unit is set
    to the default value of TrackMate, ``"pixel"`` or ``"frame"``, with a logged
    warning.

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
        units["spatialunits"] = "pixel"
        logger.warning(
            "No spatial units found in the XML file. Setting to TrackMate "
            "default value 'pixel'."
        )
    if "timeunits" not in units:
        units["timeunits"] = "frame"
        logger.warning(
            "No time units found in the XML file. Setting to TrackMate "
            "default value 'frame'."
        )
    element.clear()  # We won't need it anymore so we free up some memory.
    # .clear() does not delete the element: it only removes all subelements
    # and clears or sets to `None` all attributes.
    return units


def _get_props_dict(
    iterator: ET.iterparse,
    ancestor: ET._Element,
) -> list[dict[str, str]]:
    """
    Get all the properties of `ancestor` and return them as a list.

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


def _dimension_to_unit(
    trackmate_prop: dict[str, str], units: dict[str, str]
) -> str | None:
    """
    Convert the dimension of a property to its unit.

    ``FRAME`` has no dimension in TrackMate, but its unit is ``"frame"``, so that it
    can be the reference time property of a model.

    Parameters
    ----------
    trackmate_prop : dict[str, str]
        The property to convert.
    units : dict[str, str]
        The units of the TrackMate model.

    Returns
    -------
    str | None
        The unit of the property, or None if it has no unit.

    Raises
    ------
    ValueError
        If the dimension of the property is unknown.
    """
    if trackmate_prop["feature"] == "FRAME":
        return "frame"
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
        case "RATE":
            return "1/" + units["timeunits"]
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
    Convert a TrackMate property to a Pycellin one to add it to the properties metadata.

    Parameters
    ----------
    trackmate_prop : dict[str, str]
        The property to add.
    prop_type : str
        The tag of the declaration of the property: ``"SpotFeatures"``,
        ``"EdgeFeatures"`` or ``"TrackFeatures"``, for a node, edge or lineage
        property.
    props_md : PropsMetadata
        The `PropsMetadata` object to add the property to.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model
        (``timeunits`` and ``spatialunits``).

    Raises
    ------
    ValueError
        If the property type is invalid.
        If the dimension of the property is unknown.
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
        lineage_type="cell",
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
    Add all the TrackMate model properties to a `PropsMetadata` object.

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
        The `PropsMetadata` object to add the properties to.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model
        (``timeunits`` and ``spatialunits``).

    Raises
    ------
    ValueError
        If features are declared under an unknown tag, or if a feature has an
        unknown dimension.
    """
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        # Features stored in the FeatureDeclarations tag.
        props = _get_props_dict(iterator, element)
        for prop in props:
            # 'name' is the display name of spots and tracks, not a feature, but files
            # written by earlier versions of Pycellin can declare it.
            if prop["feature"] != "name" or element.tag == "EdgeFeatures":
                _convert_and_add_prop(prop, element.tag, props_md, units)

        # Feature used in Spot tags but not declared in the FeatureDeclarations tag.
        if element.tag == "SpotFeatures":
            name_prop = Property(
                identifier="cell_name",
                name="cell name",
                description="Name of the spot",
                provenance="TrackMate",
                prop_type="node",
                lineage_type="cell",
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
                lineage_type="cell",
                dtype="string",
            )
            props_md._add_prop(name_prop)
        element.clear()
        event, element = next(iterator)


def _convert_attributes(
    attributes: dict[str, str],
    props: dict[str, Property],
    prop_type: str,
    undeclared: dict[str, set[str]] | None = None,
) -> None:
    """
    Convert the values of `attributes` from string to the correct data type.

    The type to convert to is given by the properties metadata that stores all
    the properties info. The values of attributes that the file doesn't declare
    are left as strings: their data type is inferred once the whole file is read,
    by ``_declare_undeclared_attributes()``.

    Parameters
    ----------
    attributes : dict[str, str]
        The dictionary whose values we want to convert.
    props : dict[str, Property]
        The dictionary of properties that contains the information on how to convert
        the values of `attributes`.
    prop_type : str
        The type of the property to convert (``"node"``, ``"edge"`` or
        ``"lineage"``).
    undeclared : dict[str, set[str]] | None, default=None
        The keys of the attributes that the file doesn't declare, by property type,
        to which the undeclared keys of `attributes` are added. If None, they are
        not recorded.

    Raises
    ------
    ValueError
        If a property has an invalid dtype (not ``"int"``, ``"float"`` nor
        ``"string"``).
        If a value cannot be converted to the data type of its property.
    """
    # TODO: Rewrite this.
    for key, value in attributes.items():
        if key == "name" and prop_type != "edge":
            # Display name of spots and tracks, even when links have a 'name' property.
            pass
        elif key in props:
            match props[key].dtype:
                case "int":
                    # Missing values are written as NaN, which int() can't parse.
                    int_value = None if value == "NaN" else int(value)
                    attributes[key] = int_value  # type: ignore
                case "float":
                    attributes[key] = float(value)  # type: ignore
                case "string":
                    pass  # Nothing to do.
                case _:
                    raise ValueError(f"Invalid data type: {props[key].dtype}")
        elif key == "ID":
            # IDs are always integers.
            attributes[key] = int(value)  # type: ignore
        elif key == "ROI_N_POINTS":
            # This attribute is a special case (stored as a tag text instead of tag
            # attribute) and will be converted later, in _add_ROI_coordinates().
            pass
        elif undeclared is not None:
            undeclared.setdefault(prop_type, set()).add(key)


def _infer_attribute_dtype(values: list[str]) -> str:
    """
    Infer the data type of attribute values read as strings.

    The values are integers if they all are, NaN being a missing value as for
    declared integer features, else real numbers if they all are, else strings.

    Parameters
    ----------
    values : list[str]
        The values whose data type to infer.

    Returns
    -------
    str
        ``"int"``, ``"float"`` or ``"str"``.
    """
    numbers = [value for value in values if value != "NaN"]
    try:
        for value in numbers:
            int(value)
    except ValueError:
        pass
    else:
        if numbers:
            return "int"
    try:
        for value in values:
            float(value)
    except ValueError:
        return "str"
    return "float"


def _convert_attribute_value(value: str, dtype: str) -> int | float | str | None:
    """
    Convert an attribute value read as a string to a data type.

    Parameters
    ----------
    value : str
        The value to convert.
    dtype : str
        The data type to convert to: ``"int"``, ``"float"`` or ``"str"``. NaN
        integers become None.

    Returns
    -------
    int | float | str | None
        The converted value.
    """
    match dtype:
        case "int":
            return None if value == "NaN" else int(value)
        case "float":
            return float(value)
        case _:
            return value


def _declare_undeclared_attributes(
    undeclared: dict[str, set[str]],
    graph: nx.DiGraph,
    tracks_attributes: list[dict[str, Any]],
    props_md: PropsMetadata,
) -> None:
    """
    Convert and declare the attributes that the file doesn't declare.

    The data type of such an attribute is inferred from its values, see
    ``_infer_attribute_dtype()``, and it is declared without unit. An attribute of
    several kinds of elements, e.g. of spots and tracks, gets a single declaration
    with several property types. Only the spots, edges and tracks that are kept
    are considered.

    Parameters
    ----------
    undeclared : dict[str, set[str]]
        The keys of the attributes that the file doesn't declare, by property type.
    graph : nx.DiGraph
        The graph holding the spots and edges that are kept.
    tracks_attributes : list[dict[str, Any]]
        The attributes of the tracks.
    props_md : PropsMetadata
        The properties metadata to add the declarations to.

    Notes
    -----
    A warning is logged if some attributes are not declared in the file.
    """
    kept_tracks = {track_id for _, track_id in graph.nodes(data="TRACK_ID")}
    attrs_dicts = {
        "node": [attrs for _, attrs in graph.nodes(data=True)],
        "edge": [attrs for _, _, attrs in graph.edges(data=True)],
        "lineage": [
            attrs for attrs in tracks_attributes if attrs.get("TRACK_ID") in kept_tracks
        ],
    }
    prop_types: dict[str, list[str]] = {}
    for prop_type in ("node", "edge", "lineage"):
        for key in undeclared.get(prop_type, set()):
            prop_types.setdefault(key, []).append(prop_type)

    element_names = {"node": "spots", "edge": "edges", "lineage": "tracks"}
    loaded = []
    for key, types in sorted(prop_types.items()):
        dicts = [attrs for t in types for attrs in attrs_dicts[t] if key in attrs]
        if not dicts:
            continue  # Only on spots or tracks that were filtered out.
        dtype = _infer_attribute_dtype([attrs[key] for attrs in dicts])
        for attrs in dicts:
            attrs[key] = _convert_attribute_value(attrs[key], dtype)
        prop = Property(
            identifier=key,
            name=key,
            description="Attribute not declared in the TrackMate file",
            provenance="unknown",
            prop_type=types,
            lineage_type="cell",
            dtype=dtype,
        )
        props_md._add_prop(prop)
        elements = ", ".join(element_names[t] for t in types)
        loaded.append(f"'{key}' ({elements}, {dtype})")
    if loaded:
        logger.warning(
            f"Attributes not declared in the TrackMate file: {', '.join(loaded)}. "
            "They were loaded with the data type of their values, and no unit."
        )


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
        If the ``ROI_N_POINTS`` attribute is not found in the attributes dict.
    """
    if "ROI_N_POINTS" not in attribs:
        raise KeyError(
            "No key 'ROI_N_POINTS' in the attributes of current element "
            f"'{element.tag}'."
        )

    n_points = int(attribs["ROI_N_POINTS"])
    if element.text:
        points_coordinates = element.text.split()
        points_coordinates = [float(x) for x in points_coordinates]  # type: ignore
        points_dimension = len(points_coordinates) // n_points
        it = [iter(points_coordinates)] * points_dimension
        points_coordinates = list(zip(*it))  # type: ignore
        attribs["cell_contour"] = points_coordinates
    else:
        attribs["cell_contour"] = None

    del attribs["ROI_N_POINTS"]  # redundant with the new "cell_contour" attribute


def _add_all_nodes(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    props_md: PropsMetadata,
    graph: nx.DiGraph,
    undeclared: dict[str, set[str]] | None = None,
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
    undeclared : dict[str, set[str]] | None, default=None
        The keys of the attributes that the file doesn't declare, by property type,
        to which the undeclared node attributes are added. If None, they are not
        recorded.

    Returns
    -------
    bool
        True if the model has segmentation data, False otherwise.

    Raises
    ------
    ValueError
        If a node attribute cannot be converted to the expected type.
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
            _convert_attributes(attribs, props_md.properties, "node", undeclared)

            # The ROI coordinates are not stored in a tag attribute but in
            # the tag text. So we need to extract then format them.
            # In case of a single-point detection, the `ROI_N_POINTS` attribute
            # is not present.
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
                logger.warning(msg)
            finally:
                element.clear()

    return segmentation


def _add_edge(
    element: ET._Element,
    props_md: PropsMetadata,
    graph: nx.DiGraph,
    current_track_id: int,
    undeclared: dict[str, set[str]] | None = None,
) -> None:
    """
    Add an edge between two nodes in the graph based on the XML element.

    This function extracts source and target node identifiers from the
    given XML element, along with any additional attributes defined
    within. It then adds an edge between these nodes in the specified
    graph. If the nodes have a ``TRACK_ID`` attribute, it ensures consistency
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
    undeclared : dict[str, set[str]] | None, default=None
        The keys of the attributes that the file doesn't declare, by property type,
        to which the undeclared edge attributes are added. If None, they are not
        recorded.

    Raises
    ------
    ValueError
        If an edge attribute cannot be converted to the expected type, or if a spot
        of the edge is already in another track.
    """
    attribs = deepcopy(element.attrib)
    _convert_attributes(attribs, props_md.properties, "edge", undeclared)
    try:
        entry_node_id = int(attribs["SPOT_SOURCE_ID"])
        exit_node_id = int(attribs["SPOT_TARGET_ID"])
    except KeyError as err:
        msg = (
            f"No key {err} in the attributes of current element '{element.tag}'. "
            f"Not adding this edge to the graph."
        )
        logger.warning(msg)
    else:
        graph.add_edge(entry_node_id, exit_node_id)
        nx.set_edge_attributes(graph, {(entry_node_id, exit_node_id): attribs})
        # Adding the current track ID to the nodes of the newly created
        # edge. This will be useful later to filter nodes by track and
        # add the saved tracks attributes (as returned by this method).
        for node_id in (entry_node_id, exit_node_id):
            track_id = graph.nodes[node_id].setdefault("TRACK_ID", current_track_id)
            if track_id != current_track_id:
                raise ValueError(
                    f"Spot {node_id} is in tracks {track_id} and {current_track_id}, "
                    "but a spot can only be in one track. Please check the XML file."
                )
    finally:
        element.clear()


def _build_tracks(
    iterator: ET.iterparse,
    ancestor: ET._Element,
    props_md: PropsMetadata,
    graph: nx.DiGraph,
    undeclared: dict[str, set[str]] | None = None,
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
    graph : nx.DiGraph
        The graph to which the edges and their attributes will be added.
    undeclared : dict[str, set[str]] | None, default=None
        The keys of the attributes that the file doesn't declare, by property type,
        to which the undeclared edge and track attributes are added. If None, they
        are not recorded.

    Returns
    -------
    list[dict[str, Any]]
        A list of dictionaries, each representing the attributes for a
        track.

    Raises
    ------
    KeyError
        If a Track element has no ``TRACK_ID`` attribute.
    ValueError
        If an edge or track attribute cannot be converted to the expected type, if
        an Edge element is outside any Track element, or if a spot is in several
        tracks.
    """
    tracks_attributes = []
    current_track_id = None
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        # Saving the current track information.
        if element.tag == "Track" and event == "start":
            attribs = deepcopy(element.attrib)
            _convert_attributes(attribs, props_md.properties, "lineage", undeclared)
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
            if current_track_id is None:
                raise ValueError(
                    "An Edge element is outside any Track element. Please check the "
                    "XML file."
                )
            _add_edge(element, props_md, graph, current_track_id, undeclared)

        event, element = next(iterator)

    return tracks_attributes


def _get_filtered_tracks_id(
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
        List of track IDs to identify the tracks to keep.

    Notes
    -----
    A warning is logged for each element without a ``TRACK_ID`` attribute, which is
    ignored.
    """
    filtered_tracks_id = []
    event, element = next(iterator)
    while (event, element) != ("end", ancestor):
        if element.tag == "TrackID" and event == "start":
            attribs = deepcopy(element.attrib)
            try:
                filtered_tracks_id.append(int(attribs["TRACK_ID"]))
            except KeyError as err:
                msg = (
                    f"No key {err} in the attributes of current element "
                    f"'{element.tag}'. Ignoring this track."
                )
                logger.warning(msg)
        event, element = next(iterator)

    return filtered_tracks_id


def _update_props_metadata(
    props_md: PropsMetadata,
    units: dict[str, str],
    segmentation: bool,
) -> None:
    """
    Update the properties metadata to match Pycellin conventions.

    Parameters
    ----------
    props_md : PropsMetadata
        The properties metadata to update.
    units : dict[str, str]
        The temporal and spatial units of the TrackMate model
        (``timeunits`` and ``spatialunits``).
    segmentation : bool
        True if the model has segmentation data, False otherwise.

    Raises
    ------
    KeyError
        If the ``POSITION_X``, ``POSITION_Y`` or ``TRACK_ID`` property is missing in
        the properties metadata.
    ValueError
        If a feature already has the identifier that Pycellin gives to another
        feature, e.g. ``cell_x`` for ``POSITION_X``.
    """
    # Node properties.
    prop_cell_id = create_cell_id_property("TrackMate")
    props_md._add_prop(prop_cell_id)
    for axis in ["x", "y", "z"]:
        if axis == "z" and not props_md._has_prop("POSITION_Z"):
            continue  # 2D data has no z coordinate, see _remove_z_coordinates().
        props_md._change_prop_identifier(f"POSITION_{axis.upper()}", f"cell_{axis}")
        props_md._change_prop_description(
            f"cell_{axis}", f"{axis.upper()} coordinate of the cell"
        )
    if segmentation:
        roi_coord_prop = create_cell_contour_property(
            provenance="TrackMate",
            unit=units["spatialunits"],
        )
        props_md._add_prop(roi_coord_prop)

    # Edge properties. They are optional: Mastodon files don't have them.
    for axis in ["x", "y", "z"]:
        if props_md._has_prop(f"EDGE_{axis.upper()}_LOCATION"):
            props_md._change_prop_identifier(
                f"EDGE_{axis.upper()}_LOCATION", f"link_{axis}"
            )
            desc = (
                f"{axis.upper()} coordinate of the link, "
                "i.e. mean coordinate of its two cells"
            )
            props_md._change_prop_description(f"link_{axis}", desc)

    # Lineage properties.
    props_md._change_prop_identifier("TRACK_ID", "lineage_id")
    props_md._change_prop_description("lineage_id", "Unique identifier of the lineage")
    props_md.properties["lineage_id"].prop_type = (
        PropertyType.NODE | PropertyType.LINEAGE
    )
    # Cell and cycle lineages share their lineage ID, as with the other readers.
    props_md.properties["lineage_id"].lineage_type = "both"
    prop_filtered_track = Property(
        identifier="FilteredTrack",
        name="FilteredTrack",
        description="True if the track was not filtered out in TrackMate",
        provenance="TrackMate",
        prop_type="lineage",
        lineage_type="cell",
        dtype="int",
    )
    props_md._add_prop(prop_filtered_track)
    for axis in ["x", "y", "z"]:
        if props_md._has_prop(f"TRACK_{axis.upper()}_LOCATION"):
            props_md._change_prop_identifier(
                f"TRACK_{axis.upper()}_LOCATION", f"lineage_{axis}"
            )
            desc = (
                f"{axis.upper()} coordinate of the lineage, "
                "i.e. mean coordinate of its cells"
            )
            props_md._change_prop_description(f"lineage_{axis}", desc)


def _update_location_related_props(
    lineage: CellLineage,
    props_md: PropsMetadata,
) -> None:
    """
    Update properties related to location of lineage, nodes and edges in a lineage.

    Only the coordinates that `props_md` declares are renamed, so that 2D data gets
    no z coordinate. A single-cell lineage, from a spot outside tracks, gets the
    position of its cell as lineage location, if `props_md` declares one.

    Parameters
    ----------
    lineage : CellLineage
        The lineage to update.
    props_md : PropsMetadata
        The properties metadata, whose location properties are already renamed by
        ``_update_props_metadata()``.
    """
    axes = {
        prefix: [
            axis for axis in ("x", "y", "z") if props_md._has_prop(f"{prefix}_{axis}")
        ]
        for prefix in ("cell", "link", "lineage")
    }

    # Nodes
    for _, data in lineage.nodes(data=True):
        for axis in axes["cell"]:
            data[f"cell_{axis}"] = data.pop(f"POSITION_{axis.upper()}", None)

    # Edges
    # Mastodon does not have the EDGE_{axis}_LOCATION so we have to check
    # existence first
    if lineage.edges():
        first_edge = next(iter(lineage.edges(data=True)))
        has_edge_location = any(
            f"EDGE_{axis.upper()}_LOCATION" in first_edge[2] for axis in axes["link"]
        )
        if has_edge_location:
            for _, _, data in lineage.edges(data=True):
                for axis in axes["link"]:
                    data[f"link_{axis}"] = data.pop(
                        f"EDGE_{axis.upper()}_LOCATION", None
                    )
        # else:
        #     # If the EDGE_{axis}_LOCATION properties are not present, we compute
        #     # the mean coordinate of the two nodes of the edge.
        #     for u, v, data in lineage.edges(data=True):
        #         for axis in ["x", "y", "z"]:
        #             coord_u = lineage.nodes[u][f"cell_{axis}"]
        #             coord_v = lineage.nodes[v][f"cell_{axis}"]
        #             data[f"link_{axis}"] = (coord_u + coord_v) / 2

    # Lineage
    if "TRACK_X_LOCATION" in lineage.graph:
        for axis in axes["lineage"]:
            lineage.graph[f"lineage_{axis}"] = lineage.graph.pop(
                f"TRACK_{axis.upper()}_LOCATION", None
            )
    else:
        if len(lineage) == 1:
            # This is a one-node lineage from TrackMate, i.e. a spot outside tracks.
            # TrackMate writes no track for it, so it has no TRACK_X_LOCATION,
            # TRACK_Y_LOCATION or TRACK_Z_LOCATION. Since TrackMate places a track
            # at the mean position of its spots, it gets the position of its cell.
            node = next(iter(lineage.nodes))
            for axis in axes["lineage"]:
                lineage.graph[f"lineage_{axis}"] = lineage.nodes[node][f"cell_{axis}"]
        # else:
        #     # Mastodon does not have the TRACK_{axis}_LOCATION, so we compute the mean
        #     # coordinate of the lineage.
        #     for axis in ["x", "y", "z"]:
        #         coords = [
        #             data[f"cell_{axis}"] for _, data in lineage.nodes(data=True)
        #         ]
        #         lineage.graph[f"lineage_{axis}"] = sum(coords) / len(coords)


def _filter_spots_and_tracks(
    graph: nx.DiGraph,
    lone_spots: _LoneSpotsOption,
    tracks: _TracksOption,
    visible_tracks: set[int] | None,
) -> None:
    """
    Remove from the graph the spots outside tracks and the tracks not to load.

    The spots of a track are kept or removed with it, whatever their ``VISIBILITY``.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph holding all the spots and links of the file. The spots in a track
        have a ``TRACK_ID`` attribute.
    lone_spots : _LoneSpotsOption
        Spots outside tracks to keep: none (``"none"``), only the visible ones
        (``"visible"``: ``VISIBILITY`` of 1, or no ``VISIBILITY``), or all (``"all"``).
    tracks : _TracksOption
        Tracks to keep: only the visible ones (``"visible"``: listed in
        FilteredTracks), or all (``"all"``).
    visible_tracks : set[int] | None
        IDs of the tracks listed in FilteredTracks, or None when the file has no
        FilteredTracks tag: all tracks are then visible.
    """
    to_remove = []
    for node, data in graph.nodes(data=True):
        track_id = data.get("TRACK_ID")
        if track_id is None:
            hidden = data.get("VISIBILITY") == 0
            if lone_spots == "none" or (lone_spots == "visible" and hidden):
                to_remove.append(node)
        elif (
            tracks == "visible"
            and visible_tracks is not None
            and track_id not in visible_tracks
        ):
            to_remove.append(node)
    graph.remove_nodes_from(to_remove)


def _is_3d(graph: nx.DiGraph, num_slices: int | None) -> bool:
    """
    Tell whether the spots of a TrackMate file are in 3D.

    TrackMate gives every spot a ``POSITION_Z``, of 0 for a 2D image. The spots are
    in 3D if one of them has a nonzero ``POSITION_Z``, or if the image has several
    slices. Without any ``POSITION_Z``, they are in 2D.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph holding all the spots of the file, before filtering, so that the
        result doesn't depend on the spots and tracks to load.
    num_slices : int | None
        Number of slices of the image, or None if the file doesn't give it.

    Returns
    -------
    bool
        True if the spots are in 3D, False if they are in 2D.
    """

    def is_zero(value: Any) -> bool:
        # The values of an undeclared attribute are still strings.
        try:
            return float(value) == 0
        except (TypeError, ValueError):
            return False  # Kept: a z that can't be read could be nonzero.

    z_values = [z for _, z in graph.nodes(data="POSITION_Z") if z is not None]
    if not z_values:
        return False
    if num_slices is not None and num_slices > 1:
        return True
    return not all(is_zero(z) for z in z_values)


def _remove_z_coordinates(
    graph: nx.DiGraph,
    tracks_attributes: list[dict[str, Any]],
    props_md: PropsMetadata,
) -> None:
    """
    Remove the z coordinates of the spots, edges and tracks of 2D data.

    TrackMate gives them a ``POSITION_Z``, ``EDGE_Z_LOCATION`` and
    ``TRACK_Z_LOCATION`` of 0 in 2D, which are removed with their declarations.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph holding the spots and edges.
    tracks_attributes : list[dict[str, Any]]
        The attributes of the tracks.
    props_md : PropsMetadata
        The properties metadata to remove the declarations from.
    """
    for _, data in graph.nodes(data=True):
        data.pop("POSITION_Z", None)
    for _, _, data in graph.edges(data=True):
        data.pop("EDGE_Z_LOCATION", None)
    for attributes in tracks_attributes:
        attributes.pop("TRACK_Z_LOCATION", None)
    for feature in ("POSITION_Z", "EDGE_Z_LOCATION", "TRACK_Z_LOCATION"):
        if props_md._has_prop(feature):
            props_md._remove_prop(feature)


def _parse_model_tag(
    xml_path: str | Path,
    lone_spots: _LoneSpotsOption,
    tracks: _TracksOption,
    num_slices: int | None = None,
) -> tuple[dict[str, str], PropsMetadata, Data]:
    """
    Read an XML file and convert the model data into several graphs.

    Each TrackMate track and its associated data described in the XML file
    are modeled as NetworkX directed graphs. Spots are modeled as graph
    nodes, and edges as graph edges. Spot, edge and track properties are
    stored in node, edge and graph attributes, respectively.

    Parameters
    ----------
    xml_path : str | Path
        Path of the XML file to process.
    lone_spots : _LoneSpotsOption
        Spots outside tracks to keep: none (``"none"``), only the visible ones
        (``"visible"``), or all (``"all"``).
    tracks : _TracksOption
        Tracks to keep: only the visible ones (``"visible"``), or all (``"all"``).
    num_slices : int | None, default=None
        Number of slices of the image, from the settings of the file, or None if
        unknown. With several slices, the spots are in 3D even if all of them have
        a ``POSITION_Z`` of 0, see ``_is_3d()``.

    Returns
    -------
    tuple[dict[str, str], PropsMetadata, Data]
        A tuple containing the space and time units, the properties metadata
        and the data of the model. 2D data has no z coordinate.

    Raises
    ------
    ValueError
        If an attribute of a spot, edge or track cannot be converted to the data
        type of its feature, or if a feature has an unknown dimension.
        If an Edge element is outside any Track element, or if a spot is in several
        tracks.
        If several disconnected parts of the graph have the same track ID.
        If a feature already has the identifier that Pycellin gives to another
        feature, e.g. ``cell_x`` for ``POSITION_X``.
    KeyError
        If a Track element has no ``TRACK_ID`` attribute.
        If the file has no ``POSITION_X``, ``POSITION_Y`` or ``TRACK_ID`` feature.
    """
    props_md = PropsMetadata()
    # Keys of the attributes that the file doesn't declare, by property type.
    undeclared: dict[str, set[str]] = {}
    # IDs of the tracks listed in FilteredTracks. None if the file has no such tag.
    visible_tracks: set[int] | None = None
    # A file without AllSpots or AllTracks element has no spots or no tracks.
    segmentation = False
    tracks_attributes: list[dict[str, Any]] = []

    # Creation of a graph that will hold all the tracks described
    # in the XML file. This means that if there's more than one track,
    # the resulting graph will be disconnected.
    graph: nx.DiGraph = nx.DiGraph()

    # So as not to load the entire XML file into memory at once, we're
    # using an iterator to browse over the tags one by one.
    # The events 'start' and 'end' correspond respectively to the opening
    # and the closing of the considered tag. The iterator stops before the end of
    # the file, so the file is opened here, to be closed in any case.
    with open(xml_path, "rb") as file:
        it = ET.iterparse(file, events=["start", "end"])
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
                segmentation = _add_all_nodes(it, element, props_md, graph, undeclared)
                root.clear()

            # Adding the tracks as edges.
            if element.tag == "AllTracks" and event == "start":
                tracks_attributes = _build_tracks(
                    it, element, props_md, graph, undeclared
                )
                root.clear()

            # Getting the tracks visible in TrackMate.
            if element.tag == "FilteredTracks" and event == "start":
                visible_tracks = set(_get_filtered_tracks_id(it, element))

            if element.tag == "Model" and event == "end":
                break  # We are not interested in the following data.

    # 2D data has no z coordinate. This is decided on all the spots, before filtering,
    # so that the spots and tracks to load don't change the dimension of the model.
    is_3d = _is_3d(graph, num_slices)

    # The spots and tracks are filtered once all of them are read, since files written
    # by other tools can have the spots after the tracks.
    _filter_spots_and_tracks(graph, lone_spots, tracks, visible_tracks)
    if not is_3d:
        _remove_z_coordinates(graph, tracks_attributes, props_md)

    # Now that all the values are read, we can infer the data type of the attributes
    # that the file doesn't declare.
    _declare_undeclared_attributes(undeclared, graph, tracks_attributes, props_md)

    # We want one lineage per track, so we need to split the graph
    # into its connected components. Only the loaded tracks give their attributes.
    # The spots outside tracks get the IDs after all the track IDs of the file, so
    # that their IDs don't depend on the tracks loaded and are never those of a
    # hidden track.
    loaded_track_ids = {track_id for _, track_id in graph.nodes(data="TRACK_ID")}
    lineages = _split_graph_into_lineages(
        graph,
        lin_props=[
            attrs
            for attrs in tracks_attributes
            if attrs["TRACK_ID"] in loaded_track_ids
        ],
        lineage_id_key="TRACK_ID",
        reserved_ids=[attrs["TRACK_ID"] for attrs in tracks_attributes],
    )

    # For Pycellin compatibility, some TrackMate properties have to be renamed.
    # We only rename properties that are either essential to the functioning of
    # Pycellin or confusing (e.g. "name" is a spot and a track property).
    _update_props_metadata(props_md, units, segmentation)
    _update_lineages_ids_key(lineages, "TRACK_ID")
    for lin in lineages:
        for key_name, new_key in [
            ("TRACK_ID", "lineage_id"),  # mandatory
            ("ID", "cell_id"),  # mandatory
            ("name", "cell_name"),  # confusing
        ]:
            _update_node_prop_key(lin, key_name, new_key)
        _update_lineage_prop_key(lin, "name", "lineage_name")
        _update_location_related_props(lin, props_md)

        # Adding if each track was present in the 'FilteredTracks' tag
        # because this info is needed when reconstructing TrackMate XMLs
        # from graphs. Without the tag, all tracks are visible.
        lin.graph["FilteredTrack"] = (
            visible_tracks is None or lin.graph["lineage_id"] in visible_tracks
        )

    # Without spots to load, the graph gives a single empty lineage, left out as in
    # read_ctc().
    data = Data({lin.graph["lineage_id"]: lin for lin in lineages if len(lin) > 0})
    return units, props_md, data


def _get_specific_tags(
    xml_path: str | Path,
    tag_names: list[str],
) -> dict[str, ET._Element]:
    """
    Extract specific tags from an XML file and return them in a dictionary.

    This function parses an XML file, searching for specific tag names
    provided by the user. Once a tag is found, it is deep copied and
    stored in a dictionary with the tag name as the key. The whole file is
    searched for each tag name, and the last element found with this name is
    kept.

    Parameters
    ----------
    xml_path : str | Path
        The file path of the XML file to be parsed.
    tag_names : list[str]
        A list of tag names to search for in the XML file.

    Returns
    -------
    dict[str, ET._Element]
        A dictionary where each key is a tag name from `tag_names` that
        was found in the XML file, and the corresponding value is the
        deep copied ``ET._Element`` object for that tag.
    """
    dict_tags = {}
    for tag in tag_names:
        with open(xml_path, "rb") as file:
            for _, element in ET.iterparse(file, tag=tag):
                dict_tags[element.tag] = deepcopy(element)
    return dict_tags


def _get_trackmate_version(
    xml_path: str | Path,
) -> str:
    """
    Extract the version of TrackMate used to generate the XML file.

    Parameters
    ----------
    xml_path : str | Path
        The file path of the XML file to be parsed.

    Returns
    -------
    str
        The version of TrackMate used to generate the XML file. If the file has no
        TrackMate element, or if this element has no version, ``"unknown"`` is
        returned.
    """
    with open(xml_path, "rb") as file:
        for _, element in ET.iterparse(file, tag="TrackMate"):
            return str(element.attrib.get("version", "unknown"))
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
        If the ``timeinterval`` attribute cannot be converted to float.
    KeyError
        If the ``timeinterval`` attribute is missing, or if the ImageData element
        is not found in the settings.
    """
    for element in settings.iterchildren("ImageData"):
        try:
            return float(element.attrib["timeinterval"])
        except KeyError:
            raise KeyError(
                "The 'timeinterval' attribute is missing in the 'ImageData' element."
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
        The pixel width, height and depth in the TrackMate model, with the
        ``pixel_width``, ``pixel_height`` and ``pixel_depth`` keys.

    Raises
    ------
    ValueError
        If the ``pixelwidth``, ``pixelheight`` or ``voxeldepth`` attribute
        cannot be converted to float.
    KeyError
        If the ``pixelwidth``, ``pixelheight`` or ``voxeldepth`` attribute is
        missing, or if the ImageData element is not found in the settings.
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
                raise KeyError(
                    f"The {key_TM} attribute is missing in the 'ImageData' element."
                )
            except ValueError:
                raise ValueError(
                    f"The {key_TM} attribute cannot be converted to float."
                )
        return pixel_size

    raise KeyError("The 'ImageData' element is not found in the settings.")


def _get_num_slices(settings: ET._Element) -> int | None:
    """
    Extract the number of slices of the image of the TrackMate model.

    Parameters
    ----------
    settings : ET._Element
        The XML element containing the settings of the TrackMate model.

    Returns
    -------
    int | None
        The ``nslices`` attribute of the ImageData element, or None if the file
        doesn't give it as an integer.
    """
    for element in settings.iterchildren("ImageData"):
        try:
            return int(element.attrib["nslices"])
        except (KeyError, ValueError):
            return None
    return None


def _add_missing_position_t(
    data: Data,
    props_md: PropsMetadata,
    frame_interval: float,
    time_unit: str,
) -> None:
    """
    Compute ``POSITION_T`` from ``FRAME`` when no spot of the file has it.

    TrackMate requires ``FRAME`` but not ``POSITION_T``, which it defines as
    ``FRAME`` times the frame interval of the image. Files not written by TrackMate
    can lack it.

    Parameters
    ----------
    data : Data
        The data of the model, whose cells get ``POSITION_T``.
    props_md : PropsMetadata
        The properties metadata, where ``POSITION_T`` is declared if it is not
        already.
    frame_interval : float
        The time interval between two frames of the image, in `time_unit`.
    time_unit : str
        The temporal unit of the TrackMate model.

    Notes
    -----
    A warning is logged if ``POSITION_T`` is computed, since its values don't come
    from the file.
    """
    cells = [
        cell for lin in data.cell_lineages.values() for _, cell in lin.nodes(data=True)
    ]
    if not cells or any("POSITION_T" in cell for cell in cells):
        return

    for cell in cells:
        cell["POSITION_T"] = cell["FRAME"] * frame_interval
    if not props_md._has_prop("POSITION_T"):
        props_md._add_prop(
            create_time_property(
                unit=time_unit,
                custom_identifier="POSITION_T",
                custom_name="T",
                custom_description="Time of the detection, computed from FRAME",
            )
        )
    logger.warning(
        "No spot of the file has 'POSITION_T': it is computed from 'FRAME' and the "
        f"frame interval of the image ({frame_interval} {time_unit})."
    )


def read_trackmate_xml(
    path: str | Path,
    *,
    reference_time_prop: str = "POSITION_T",
    lone_spots: Literal["none", "visible", "all"] = "none",
    tracks: Literal["visible", "all"] = "visible",
) -> Model:
    """
    Read a TrackMate XML file and convert the tracks data to directed acyclic graphs.

    Each TrackMate track and its associated data described in the XML file
    are modeled as NetworkX directed graphs. Spots are modeled as graph
    nodes, and edges as graph edges. Spot, edge and track properties are
    stored in node, edge and graph attributes, respectively.
    The rest of the information contained in the XML file is stored either
    as a metadata dict (TrackMate version, log, settings...) or in the `Model`
    properties metadata.

    Parameters
    ----------
    path : str | Path
        Path of the XML file to process.
    reference_time_prop : str, default="POSITION_T"
        Name of the property that contains the time information of the model.
        ``POSITION_T`` is the one TrackMate uses. TrackMate doesn't require it, so
        if no spot has it, it is computed from ``FRAME`` and the frame interval of
        the image, with a warning. ``FRAME`` counts the time in frames, with a time
        step of 1. Any other property must match the time unit and time step of
        the TrackMate model (i.e. the properties of the image on which TrackMate
        was applied).
    lone_spots : Literal["none", "visible", "all"], default="none"
        Spots outside tracks to load, each as a single-cell lineage: ``"none"``,
        ``"visible"`` for only the spots that TrackMate shows, i.e. that passed its
        spot filters (``VISIBILITY`` of 1, or no ``VISIBILITY``), or ``"all"``.
    tracks : Literal["visible", "all"], default="visible"
        Tracks to load, with all their spots: ``"visible"`` for only the tracks
        that TrackMate shows, i.e. that passed its track filters (listed in
        FilteredTracks, or all of them without this tag), or ``"all"``.

    Returns
    -------
    Model
        A Pycellin `Model` that contains all the data from the TrackMate XML file.

    Raises
    ------
    ValueError
        If `lone_spots` or `tracks` is not one of its options.
        If a value of the file cannot be converted to its data type, if a feature
        has an unknown dimension, or if a spot is in several tracks.
    KeyError
        If a track has no ``TRACK_ID``, if the file has no Settings element, or if
        its ImageData element is missing or lacks the pixel size or, unless
        `reference_time_prop` is ``"FRAME"``, the frame interval.

    Notes
    -----
    Each track becomes a lineage with the ID of the track. The spots outside tracks
    loaded with `lone_spots` become single-cell lineages with the next IDs after all
    the track IDs of the file, so that their IDs don't depend on `tracks`. When the
    file gives the location of tracks, these lineages get the position of their
    spot, since TrackMate places a track at the mean position of its spots.

    TrackMate gives every spot a z coordinate, of 0 for a 2D image. Pycellin keeps
    it only for 3D data, i.e. when a spot has a nonzero ``POSITION_Z`` or when the
    image has several slices. Models of 2D data have no ``cell_z``, ``link_z`` or
    ``lineage_z``, and no pixel depth; `write_trackmate_xml` writes these
    coordinates back as 0.
    """
    if not _check_literal_type(lone_spots, _LoneSpotsOption):
        raise ValueError(
            f"'lone_spots' must be 'none', 'visible' or 'all', not {lone_spots!r}."
        )
    if not _check_literal_type(tracks, _TracksOption):
        raise ValueError(f"'tracks' must be 'visible' or 'all', not {tracks!r}.")
    # The TrackMate info that is not in the `Model` tag goes in the metadata. The
    # settings are read first: the number of slices of the image tells 3D data.
    dict_tags = _get_specific_tags(
        path, ["Log", "Settings", "GUIState", "DisplaySettings"]
    )
    num_slices = _get_num_slices(dict_tags["Settings"])
    units, props_md, data = _parse_model_tag(path, lone_spots, tracks, num_slices)

    pixel_size = _get_pixel_size(dict_tags["Settings"])
    time_step: int | float
    if reference_time_prop == "FRAME":
        # Frames are counted one by one, whatever the frame interval of the image.
        time_unit = "frame"
        time_step = 1
    else:
        time_unit = units["timeunits"]
        time_step = _get_time_step(dict_tags["Settings"])  # the frame interval
        if reference_time_prop == "POSITION_T":
            _add_missing_position_t(data, props_md, time_step, time_unit)
    metadata: dict[str, Any] = {}
    metadata["reference_time_prop"] = reference_time_prop
    # Dimensions info.
    metadata["space_unit"] = units["spatialunits"]
    metadata["time_unit"] = time_unit
    metadata["time_step"] = time_step
    metadata["pixel_width"] = pixel_size.get("pixel_width")
    metadata["pixel_height"] = pixel_size.get("pixel_height")
    # 2D data has no pixel depth. The voxel depth of the file stays in its settings,
    # which a TrackMate export writes back.
    if props_md._has_prop("cell_z"):
        metadata["pixel_depth"] = pixel_size.get("pixel_depth")
    else:
        metadata["pixel_depth"] = None
    # Traceability info.
    metadata["name"] = Path(path).stem
    metadata["file_path"] = path
    metadata["provenance"] = "TrackMate"
    metadata["trackmate_version"] = _get_trackmate_version(path)
    # The rest of the tags.
    for tag_name, tag in dict_tags.items():
        element_string = ET.tostring(tag, encoding="utf-8").decode()
        metadata[tag_name] = element_string

    model = Model(metadata, props_md, data)
    _check_fusions(model)  # Pycellin DOES NOT support fusion events

    return model


if __name__ == "__main__":
    """
    Quick demo with sample data.
    """
    xml = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Ecoli_growth_on_agar_pad.xml"
    )
    model = read_trackmate_xml(
        xml,
        lone_spots="all",
        tracks="all",
    )

    print(model)
    for lin in model.get_cell_lineages():
        print(lin)
    print("\nModel metadata:")
    print(model.model_metadata)
    print("\nProperties and their types:")
    for prop_id, prop in model.props_metadata.properties.items():
        print(f"  - {prop_id}  -> {prop.prop_type}")
