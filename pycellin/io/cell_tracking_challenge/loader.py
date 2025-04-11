#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
loader.py

This module is part of the Pycellin package.

This module provides functions to load and process Cell Tracking Challenge (CTC) files
into Pycellin models. It includes a function to load a CTC file into Pycellin model
and helper functions to create metadata, features, and lineage graphs.

References:
- CTC website: https://celltrackingchallenge.net/
- CTC tracking annotations conventions:
https://public.celltrackingchallenge.net/documents/Naming%20and%20file%20content%20conventions.pdf
"""

from datetime import datetime
import importlib
from itertools import pairwise
from pathlib import Path
import re
from typing import Any, Tuple

import networkx as nx
from skimage.measure import regionprops, find_contours
import tifffile

from pycellin.classes.feature import (
    Feature,
    FeaturesDeclaration,
    cell_ID_Feature,
    frame_Feature,
    lineage_ID_Feature,
    cell_coord_Feature,
)
from pycellin.classes import CellLineage, Data, Model

# TODO: what if the first frame is empty...?


def _integrate_label_imgs_metadata(metadata: dict[str, Any], labels_path: str) -> None:
    """
    Integrate metadata from label images into the Pycellin model metadata.

    This function extracts metadata from label images and integrates it
    into the provided metadata dictionary. Priority is given to the metadata
    already present in the dictionary. If the metadata is not present,
    it will be extracted from the label images.

    Parameters
    ----------
    metadata : dict[str, Any]
        The metadata dictionary of the model to which the label images metadata
        will be added.
    labels_path : str
        The path to the label images directory.
    """
    list_paths = sorted(Path(labels_path).glob("*.tif"))
    if len(list_paths) == 0:
        raise ValueError(f"No label images found in the directory: {labels_path}")
    metadata["label_imgs_location"] = labels_path
    # Read metadata from the first label image. Hopefully all label images
    # have the same metadata. I would be worried if they don't.
    with tifffile.TiffFile(list_paths[0]) as tif:
        # TODO: Look into a more robust way to deal with all the different
        # metadata formats. I'm pretty sure I'm missing a lot here, like ImageJ tif.
        tags = tif.pages[0].tags

        # Check and set space_unit
        if "space_unit" not in metadata:
            if "ResolutionUnit" in tags and tags.get("ResolutionUnit") is not None:
                resunit = tags.get("ResolutionUnit").value
                match resunit:
                    case 1:  # None
                        metadata["space_unit"] = "pixel"
                    case 2:  # inch
                        metadata["space_unit"] = "inch"
                    case 3:  # cm
                        metadata["space_unit"] = "cm"
            else:
                metadata["space_unit"] = "pixel"

        # Check and set pixel_width
        if "pixel_size" not in metadata or "width" not in metadata["pixel_size"]:
            if "XResolution" in tags and tags.get("XResolution") is not None:
                xres = tags.get("XResolution").value
                metadata["pixel_size"]["width"] = xres[1] / xres[0]
            else:
                metadata["pixel_size"]["width"] = 1.0

        # Check and set pixel_height
        if "pixel_size" not in metadata or "height" not in metadata["pixel_size"]:
            if "YResolution" in tags and tags.get("YResolution") is not None:
                yres = tags.get("YResolution").value
                metadata["pixel_size"]["height"] = yres[1] / yres[0]
            else:
                metadata["pixel_size"]["height"] = 1.0

        # Check and set pixel_depth
        if "pixel_size" not in metadata or "depth" not in metadata["pixel_size"]:
            if "ZResolution" in tags and tags.get("ZResolution") is not None:
                zres = tags.get("ZResolution").value
                metadata["pixel_size"]["depth"] = zres[1] / zres[0]
            else:
                metadata["pixel_size"]["depth"] = 1.0


def _create_metadata(
    file_path: str,
    labels_path: str | None = None,
    space_unit: str | None = None,
    pixel_width: float | None = None,
    pixel_height: float | None = None,
    pixel_depth: float | None = None,
    time_unit: str | None = None,
    time_step: float | None = None,
) -> dict[str, Any]:
    """
    Create a dictionary of basic Pycellin metadata for a given file.

    Parameters
    ----------
    file_path : str
        The path to the file for which metadata is being created.
    labels_path : str, optional
        The path to the label images, if any.
    space_unit : str, optional
        The spatial unit of the data. If not provided, it will be set to 'pixel'
        by default.
    pixel_width : float, optional
        The pixel width in the spatial unit. If not provided, it will be set to 1.0
        by default.
    pixel_height : float, optional
        The pixel height in the spatial unit. If not provided, it will be set to 1.0
        by default.
    pixel_depth : float, optional
        The pixel depth in the spatial unit. If not provided, it will be set to 1.0
        by default.
    time_unit : str, optional
        The temporal unit of the data. If not provided, it will be set to 'frame'
        by default.
    time_step : float, optional
        The time step in the temporal unit. If not provided, it will be set to 1.0
        by default.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the generated metadata.
    """
    metadata = {}  # type: dict[str, Any]
    metadata["name"] = Path(file_path).stem
    metadata["file_location"] = file_path
    metadata["provenance"] = "CTC"
    metadata["date"] = str(datetime.now())
    try:
        version = importlib.metadata.version("pycellin")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    metadata["Pycellin_version"] = version

    if time_unit is not None:
        metadata["time_unit"] = time_unit
    else:
        metadata["time_unit"] = "frame"
    if time_step is not None:
        metadata["time_step"] = time_step
    else:
        metadata["time_step"] = 1

    complete_metadata_flag = [0, 0, 0, 0]
    metadata["pixel_size"] = {}
    if space_unit is not None:
        metadata["space_unit"] = space_unit
        complete_metadata_flag[0] = 1
    if pixel_width is not None:
        metadata["pixel_size"]["width"] = pixel_width
        complete_metadata_flag[1] = 1
    if pixel_height is not None:
        metadata["pixel_size"]["height"] = pixel_height
        complete_metadata_flag[2] = 1
    if pixel_depth is not None:
        metadata["pixel_size"]["depth"] = pixel_depth
        complete_metadata_flag[3] = 1

    if sum(complete_metadata_flag) < 4:
        if labels_path is not None:
            _integrate_label_imgs_metadata(metadata, labels_path)
        else:
            if complete_metadata_flag[0] == 0:
                metadata["space_unit"] = "pixel"
            if complete_metadata_flag[1] == 0:
                metadata["pixel_size"]["width"] = 1.0
            if complete_metadata_flag[2] == 0:
                metadata["pixel_size"]["height"] = 1.0
            if complete_metadata_flag[3] == 0:
                metadata["pixel_size"]["depth"] = 1.0

    return metadata


def _create_FeaturesDeclaration(seg_data: bool) -> FeaturesDeclaration:
    """
    Return a FeaturesDeclaration object populated with Pycellin basic features.

    Parameters
    ----------
    seg_data : bool
        A boolean indicating whether segmentation data is available.

    Returns
    -------
    FeaturesDeclaration
        An instance of FeaturesDeclaration populated with cell and lineage
        identification features.
    """
    feat_declaration = FeaturesDeclaration()
    cell_ID_feat = cell_ID_Feature()
    frame_feat = frame_Feature()
    lin_ID_feat = lineage_ID_Feature()
    for feat in [cell_ID_feat, frame_feat, lin_ID_feat]:
        feat_declaration._add_feature(feat)
        feat_declaration._protect_feature(feat.name)
    if seg_data:
        # TODO: deal with z dimension
        # TODO: put the real unit, pixel is juste a placeholder for now
        cell_x_feat = cell_coord_Feature(unit="pixel", axis="x", provenance="CTC")
        cell_y_feat = cell_coord_Feature(unit="pixel", axis="y", provenance="CTC")
        roi_coords_feat = Feature(
            name="ROI_coords",
            description="List of coordinates of the region of interest",
            provenance="CTC",
            feat_type="node",
            lin_type="CellLineage",
            data_type="float",
            unit="pixel",
        )
        feat_declaration._add_features([cell_x_feat, cell_y_feat, roi_coords_feat])

    return feat_declaration


def _read_track_line(
    line: str,
    current_node_id: int,
) -> Tuple[list[Tuple[int, dict[str, Any]]], int]:
    """
    Parse a single track line to generate a list of the nodes present in the track.

    This function takes a line of text representing a track in the CTC format.
    It generates a node with a globally unique node ID for each frame within
    the start and end frame range, and stores the node's attributes in a dictionary.

    Parameters
    ----------
    line : str
        A string containing space-separated values representing a track.
    current_node_id : int
        The starting node ID to use for the first node in this track,
        which will be incremented for each subsequent node.

    Returns
    -------
    Tuple[List[Tuple[int, Dict[str, Any]]], int]
        A tuple containing a list of nodes generated from the track line,
        where each node is represented as a tuple containing the node ID
        and a dictionary of attributes, and the next available node ID
        after generating all nodes for this track.
    """
    track_id, start_frame, end_frame, parent_track = [int(el) for el in line.split()]
    nodes = []
    for frame in range(start_frame, end_frame + 1):
        node_attrs = {
            "cell_ID": current_node_id,
            "frame": frame,
            "TRACK": track_id,
            "PARENT": parent_track,
        }
        nodes.append((current_node_id, node_attrs))
        current_node_id += 1
    return nodes, current_node_id


def _add_nodes_and_edges(
    graph: nx.DiGraph,
    nodes: list[Tuple[int, dict[str, Any]]],
) -> None:
    """
    Add nodes and edges to a directed graph from a list of nodes.

    This function adds all the nodes in the list to the specified directed graph.
    Then, for each pair of consecutive nodes in the list,
    it adds a directed edge from the first node to the second.

    Parameters
    ----------
    graph : nx.DiGraph
        The directed graph to which the nodes and edges will be added.
    nodes : List[Tuple[int, Dict[str, Any]]]
        A list of tuples, where each tuple contains an integer representing
        the node identifier and a dictionary representing the node's attributes.
    """
    graph.add_nodes_from(nodes)
    for n1, n2 in pairwise(nodes):
        graph.add_edge(n1[0], n2[0])


def _merge_tracks(
    graph: nx.DiGraph,
    nodes: list[Tuple[int, dict[str, Any]]],
) -> None:
    """
    Merge a track with its parent track in the directed graph.

    This is done by adding an edge from the last node of the parent track
    to the first node of the current track.

    Parameters
    ----------
    graph : nx.DiGraph
        The directed graph to which the tracks belong.
    nodes : List[Tuple[int, Dict[str, Any]]]
        A list of tuples, where each tuple contains an integer representing
        the node identifier and a dictionary representing the node's attributes.
    """
    parent_track = nodes[0][1]["PARENT"]
    if parent_track != 0:
        # Finding the last node of the parent track.
        parent_nodes = [
            (node, data["frame"])
            for node, data in graph.nodes(data=True)
            if data["TRACK"] == parent_track
        ]
        parent_node = sorted(parent_nodes, key=lambda x: x[1])[-1]
        graph.add_edge(parent_node[0], nodes[0][0])


def _update_node_attributes(
    lineage: CellLineage,
    lineage_id: int,
) -> None:
    """
    Update the nodes attributes in a lineage graph.

    This function assigns a new unique track ID to the entire lineage
    and to each node within it. It also cleans up the node attributes
    by removing the 'TRACK' and 'PARENT' attributes, that were only needed
    for graph construction.

    Parameters
    ----------
    lineage : CellLineage
        The lineage graph whose node attributes are to be updated.
    lineage_id : int
        The new track ID to be assigned to the lineage graph and its nodes.
    """
    lineage.graph["lineage_ID"] = lineage_id
    for _, data in lineage.nodes(data=True):
        # Removing obsolete attributes.
        if "TRACK" in data:
            del data["TRACK"]
        if "PARENT" in data:
            del data["PARENT"]


def _extract_seg_data(
    label_img_path: str,
) -> Tuple[list[int], list[list[float]], list[list[Tuple[float, float]]]]:
    """
    Extract segmentation data from a label image.

    This function reads a label image and extracts the labels, centroids,
    and contours of the regions in the image.

    Parameters
    ----------
    label_img_path : str
        The path to the label image file.
    Returns
    -------
    Tuple[List[int], List[List[float]], List[List[Tuple[float, float]]]]
        A tuple containing three lists:
        - labels: a list of unique labels in the image.
        - centroids: a list of centroids for each label, where each centroid
            is represented as a (x, y) tuple of coordinates.
        - contours: a list of contours for each label, where each contour
            is represented as a list of (x, y) coordinates relative to the centroid.
    """
    label_img = tifffile.imread(label_img_path)
    regions = regionprops(label_img)
    labels = []
    centroids = []
    contours = []
    for props in regions:
        # Label.
        labels.append(props.label)
        # Centroid.
        y0, x0 = props.centroid  # skimage returns (row, column) format
        centroids.append([x0, y0])
        # Contours.
        contour = find_contours(label_img == props.label, level=0.5)
        assert len(contour) == 1, "Expected exactly one contour."
        # The contours need to be given:
        # - relatively to the label centroid
        # - in the format (x, y) and not the default (row, column) yielded by skimage.
        contour = [(float(x - x0), float(y - y0)) for y, x in contour[0]]
        contours.append(contour)
    return labels, centroids, contours


def _integrate_seg_data(
    graph: nx.DiGraph,
    frame: int,
    labels: list[int],
    centroids: list[list[float]],
    contours: list[list[Tuple[float, float]]],
) -> None:
    """
    Integrate segmentation data into the Pycellin model.

    This function updates the Pycellin model with segmentation data
    for a specific frame. It identifies the graph nodes to update thanks to the
    frame and labels and adds the following attributes to each node:
    - the centroids as cell positions (cell_x, cell_y),
    - the contours as cell ROIs (ROI_coords).

    Parameters
    ----------
    graph: nx.DiGraph
        The directed graph representing the lineage data.
    frame : int
        The frame number for which the segmentation data is being integrated.
    labels : List[int]
        A list of unique labels in the image.
    centroids : List[List[float]]
        A list of centroids for each label, where each centroid
        is represented as a (x, y) tuple of coordinates.
    contours : List[List[Tuple[float, float]]]
        A list of contours for each label, where each contour
        is represented as a list of (x, y) coordinates relative to the centroid.

    Raises
    ------
    ValueError
        If a label is not found in the graph for the specified frame,
        or if multiple nodes are found for a label in the same frame.
    """
    for label, centroid, contour in zip(labels, centroids, contours):
        # Finding the node in the graph that corresponds to the label.
        node = [
            n
            for n in graph.nodes
            if graph.nodes[n]["frame"] == frame and graph.nodes[n]["TRACK"] == label
        ]
        if len(node) < 1:
            raise ValueError(f"Label {label} not found in the graph for frame {frame}.")
        elif len(node) > 1:
            raise ValueError(
                f"Multiple nodes found for label {label} in frame {frame}."
            )
        node = node[0]
        # Updating the nodes.
        graph.nodes[node]["cell_x"] = centroid[0]
        graph.nodes[node]["cell_y"] = centroid[1]
        graph.nodes[label]["ROI_coords"] = contour


def load_CTC_file(
    res_file_path: str,
    labels_path: str | None = None,
    space_unit: str | None = None,
    pixel_width: float | None = None,
    pixel_height: float | None = None,
    pixel_depth: float | None = None,
    time_unit: str | None = None,
    time_step: float | None = None,
) -> Model:
    """
    Create a Pycellin model out of a Cell Tracking Challenge (CTC) text file.

    The CTC tracking format does not support fusion events and does not allow
    gaps right after division events.
    If only 'res_file_path' is given, only track topology is read. To load
    cell positions into the model, 'labels_path' must also be given.
    The label images must be in the same format as the CTC format,
    i.e. a single image per frame with a single label per cell.
    The label images names must end in '<frame_number>.tif' (e.g. 000.tif,
    02.tif, 0155.tif, etc.).
    For image metadata, priority is given to the img_metadata given by the user.
    If not provided, Pycellin will try to extract the metadata from the label images.
    If it fails or if no label images are given, default values will be used.

    Parameters
    ----------
    res_file_path : str
        The path to the CTC text file that contains the tracking data.
    labels_path : str, optional
        The path to the label images, if any. If not provided, only the
        track topology will be read. If image metadata is not directly provided
        by the user, the metadata will be extracted from the label images.
        If it fails default values will be used.
    space_unit : str, optional
        The spatial unit of the data. If not provided or not infered from the label
        images, it will be set to 'pixel' by default.
    pixel_width : float, optional
        The pixel width in the spatial unit. If not provided or not infered from the
        label images, it will be set to 1.0 by default.
    pixel_height : float, optional
        The pixel height in the spatial unit. If not provided or not infered from the
        label images, it will be set to 1.0 by default.
    pixel_depth : float, optional
        The pixel depth in the spatial unit. If not provided or not infered from the
        label images, it will be set to 1.0 by default.
    time_unit : str, optional
        The temporal unit of the data. If not provided, it will be set to 'frame'
        by default.
    time_step : float, optional
        The time step in the temporal unit. If not provided, it will be set to 1.0
        by default.

    Returns
    -------
    Model
        The created Pycellin model.
    """
    graph = nx.DiGraph()
    current_node_id = 0
    with open(res_file_path) as file:
        nodes_from_tracks = []
        # The lines in the file are read sequentially to create the nodes.
        # However, nothing ensures that parent nodes are created before
        # being referenced by their children.
        # nodes_from_tracks keeps track of the nodes created for each track
        # so that they can be merged later.
        for line in file:
            nodes, current_node_id = _read_track_line(line, current_node_id)
            nodes_from_tracks.append(nodes)
            _add_nodes_and_edges(graph, nodes)

    # Merging tracks that are part of the same lineage.
    for nodes in nodes_from_tracks:
        _merge_tracks(graph, nodes)

    # Adding the segmentation data, if any.
    if labels_path:
        if Path(labels_path).is_dir():
            list_paths = sorted(Path(labels_path).glob("*.tif"))
            if len(list_paths) == 0:
                raise ValueError(
                    f"No label images found in the directory: {labels_path}"
                )
            pattern = r"(\d+)\.tif"
            for label_img_path in list_paths:
                match = re.search(pattern, str(label_img_path))
                try:
                    frame = int(match.group(1))
                except AttributeError:
                    raise ValueError(
                        f"Can't parse frame value: file name {label_img_path} "
                        f"does not match the expected pattern."
                    )
                labels, centroids, contours = _extract_seg_data(str(label_img_path))
                _integrate_seg_data(graph, frame, labels, centroids, contours)

    # We want one lineage per connected component of the graph.
    lineages = [
        CellLineage(graph.subgraph(c).copy())
        for c in nx.weakly_connected_components(graph)
    ]

    # Adding a unique lineage_ID to each lineage and their nodes.
    lin_ID = 0
    for lin in lineages:
        _update_node_attributes(lin, lin_ID)
        lin_ID += 1
    data = {}
    for lin in lineages:
        if "lineage_ID" in lin.graph:
            data[lin.graph["lineage_ID"]] = lin
        else:
            assert len(lin) == 1, "Lineage ID not found and not a one-node lineage."
            node = [n for n in lin.nodes][0]
            # We set the ID of a one-node lineage to the negative of the node ID.
            lin_ID = -node
            lin.graph["lineage_ID"] = lin_ID
            data[lin_ID] = lin

    md = _create_metadata(
        res_file_path,
        labels_path=labels_path,
        space_unit=space_unit,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        pixel_depth=pixel_depth,
        time_unit=time_unit,
        time_step=time_step,
    )
    fd = _create_FeaturesDeclaration(labels_path is not None)
    model = Model(md, fd, Data(data))
    return model


if __name__ == "__main__":

    ctc_file = "sample_data/FakeTracks_TMtoCTC.txt"
    ctc_file = "sample_data/Ecoli_growth_on_agar_pad_TMtoCTC.txt"
    ctc_file = (
        "/mnt/data/Films_Laure/Benchmarks/CTC/"
        "EvaluationSoftware/testing_dataset/03_RES/res_track.txt"
    )

    ctc_file = "/mnt/data/Code/pycellin/TrackMate/01_RES/res_track.txt"
    labels_path = "/mnt/data/Code/pycellin/TrackMate/01_RES"
    # labels_path = "/mnt/data/Benchmarks/Segmentation/03_RES"

    model = load_CTC_file(ctc_file, labels_path)
    print(model)
    print(model.feat_declaration)
    print(model.data)

    # for lin_id, lin in model.data.cell_data.items():
    #     print(f"{lin_id} - {lin}")
    #     lin.plot()

    # model.add_cycle_data()
    # for lin_id, lin in model.data.cycle_data.items():
    #     lin.plot()

    # print(model.data.cell_data[1].nodes(data=True))
