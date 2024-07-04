#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy
import math
from pathlib import Path
from typing import Any, Union

from lxml import etree as ET
import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.metadata import Metadata
from pycellin.classes.data import CoreData
from pycellin.classes.lineage import CellLineage

# TODO: update all docstrings
# TODO: switch from nx.Digraph to CellLineage


def _convert_attributes(
    attributes: dict[str, str],
    features: dict[str, dict[str, str]],
):
    """
    Convert the values of `attributes` from string to int or float.

    The type to convert to is given by the dictionary of features with
    the key 'isint'.

    Parameters
    ----------
    attributes : dict[str, str]
        The dictionary whose values we want to convert.
    features : dict[str, dict[str, str]]
        The dictionary holding the type information to use.

    Raises
    ------
    KeyError
        If the 'isint' feature attribute doesn't exist.
    ValueError
        If the value of the 'isint' feature attribute is invalid.
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


def _add_ROI_coordinates(
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
    graph: nx.DiGraph,
    iterator: ET.iterparse,
    ancestor: ET._Element,
) -> None:
    """
    Add nodes and their attributes to a graph.

    All the elements that are descendants of `ancestor` are explored.

    Parameters
    ----------
    graph : nx.DiGraph
        Graph on which to add nodes.
    iterator : ET.iterparse
        XML element iterator.
    ancestor : ET._Element
        Element encompassing the information to add.
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
                _convert_attributes(attribs, graph.graph["Model"]["SpotFeatures"])
            except ValueError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise
            except KeyError as err:
                print(f"ERROR: {err} Please check the XML file.")
                raise

            # The ROI coordinates are not stored in a tag attribute but in
            # the tag text. So we need to extract then format them.
            _add_ROI_coordinates(element, attribs)

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
        # # Adding the model information as graph attributes.
        # # TODO: this is metadata
        # if element.tag == "Model" and event == "start":  # Add units.
        #     add_graph_attrib_from_element(graph, element)
        #     root.clear()  # Cleaning the tree to free up some memory.
        #     # All the browsed subelements of `root` are deleted.

        # # Add features declaration for spot, edge and track features.
        # # TODO: this is metadata
        # if element.tag == "FeatureDeclarations" and event == "start":
        #     add_all_features(graph, it, element)
        #     root.clear()

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
                    add_tracks_info(graphs, tracks_attributes)
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
