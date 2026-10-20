#!/usr/bin/env python3

"""
loader.py

This module is part of the pycellin package.

This module provides functions to load and process Cell Tracking Challenge (CTC) files
into pycellin models. It includes a function to load a CTC file into pycellin model
and helper functions to create metadata, properties, and lineage graphs.

References:
- CTC website: https://celltrackingchallenge.net/
- CTC tracking annotations conventions:
https://public.celltrackingchallenge.net/documents/Naming%20and%20file%20content%20conventions.pdf
"""

import logging
import re
import warnings
from itertools import pairwise
from pathlib import Path
from typing import Any

import networkx as nx
import tifffile
from skimage.measure import regionprops

from pycellin.classes import Data, Model, PropsMetadata
from pycellin.io.utils import _split_graph_into_lineages
from pycellin.properties.core import (
    create_cell_coord_property,
    create_cell_id_property,
    create_frame_property,
    create_lineage_id_property,
    create_time_property,
)
from pycellin.properties.morphology import (
    _mask_to_polygons,
    create_cell_contour_property,
)

logger = logging.getLogger(__name__)

# Units of the TIFF ResolutionUnit tag, except inches (2): a resolution in inches is
# most likely a print default such as 72 dpi, not a pixel size. Millimeters and
# micrometers are tifffile extensions of the TIFF standard.
_RESOLUTION_UNITS = {3: "cm", 4: "mm", 5: "µm"}

# TODO: what if the first frame is empty...?


def _get_label_img_paths(labels_path: str | Path) -> list[Path]:
    """
    Return the paths of the label images of a folder, sorted by name.

    Parameters
    ----------
    labels_path : str | Path
        The path to the folder of label images.

    Returns
    -------
    list[Path]
        The paths of the .tif files of the folder.

    Raises
    ------
    ValueError
        If `labels_path` is not a folder, or if it holds no .tif file.
    """
    if not Path(labels_path).is_dir():
        raise ValueError(
            f"'labels_path' must be a folder of label images, but '{labels_path}' "
            "is not a folder."
        )
    list_paths = sorted(Path(labels_path).glob("*.tif"))
    if len(list_paths) == 0:
        raise ValueError(f"No label images found in the directory: {labels_path}")
    return list_paths


def _integrate_label_imgs_metadata(
    metadata: dict[str, Any], label_img_path: str | Path
) -> None:
    """
    Fill the space unit and pixel size missing from the metadata with a label image's.

    The pixel size is read from the TIFF resolution tags, in the unit of the
    ResolutionUnit tag or, for ImageJ images, in the unit of the ImageJ metadata,
    which also gives the pixel depth. A resolution without unit gives no physical
    pixel size: the space unit is then 'pixel', with pixels of size 1. So does a
    resolution in inches, most likely a print default such as 72 dpi.

    Parameters
    ----------
    metadata : dict[str, Any]
        The metadata dictionary of the model. Its values have priority over the ones
        of the label image.
    label_img_path : str | Path
        The path to a label image.

    Warns
    -----
    UserWarning
        If the resolution of the label image, in inches, is ignored while the
        metadata lacks the space unit or the pixel width or height.
    """
    with tifffile.TiffFile(label_img_path) as tif:
        tags = tif.pages[0].tags
        imagej_md = tif.imagej_metadata or {}

    # ImageJ writes non-ASCII characters as escapes, e.g. "\u00B5m" for "µm".
    imagej_unit = re.sub(
        r"\\u([0-9a-fA-F]{4})",
        lambda match: chr(int(match.group(1), 16)),
        str(imagej_md.get("unit", "")),
    )
    resolution_unit = tags["ResolutionUnit"].value if "ResolutionUnit" in tags else 1
    if imagej_unit not in ("", "pixel", "pixels"):
        space_unit = imagej_unit
        pixel_depth = float(imagej_md.get("spacing", 1.0))
    elif resolution_unit in _RESOLUTION_UNITS:
        space_unit = _RESOLUTION_UNITS[resolution_unit]
        pixel_depth = 1.0
    else:
        space_unit = "pixel"
        pixel_depth = 1.0
        calibrated = {"space_unit", "pixel_width", "pixel_height"} <= metadata.keys()
        if resolution_unit == 2 and not calibrated:
            warnings.warn(
                f"Ignoring the resolution of label image '{label_img_path}', given in "
                "inches: it is most likely a print default such as 72 dpi, not a "
                "pixel size. Give 'space_unit', 'pixel_width' and 'pixel_height' to "
                "load_CTC_file() to calibrate the cell positions.",
                stacklevel=4,
            )

    pixel_sizes = []
    for tag in ("XResolution", "YResolution"):
        # A resolution is a number of pixels per unit, written as a fraction.
        if space_unit != "pixel" and tag in tags and tags[tag].value[0] != 0:
            pixels, per_unit = tags[tag].value
            pixel_sizes.append(per_unit / pixels)
        else:
            pixel_sizes.append(1.0)

    metadata.setdefault("space_unit", space_unit)
    metadata.setdefault("pixel_width", pixel_sizes[0])
    metadata.setdefault("pixel_height", pixel_sizes[1])
    metadata.setdefault("pixel_depth", pixel_depth)


def _create_metadata(
    file_path: str,
    labels_path: str | Path | None = None,
    space_unit: str | None = None,
    pixel_width: float | None = None,
    pixel_height: float | None = None,
    pixel_depth: float | None = None,
    time_unit: str | None = None,
    time_step: float | None = None,
) -> dict[str, Any]:
    """
    Create a dictionary of basic pycellin metadata for a given file.

    Parameters
    ----------
    file_path : str
        The path to the file for which metadata is being created.
    labels_path : str | Path, optional
        The path to the folder of label images, if any.
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
        The temporal unit of the data. If not provided, it will be set to None
        by default.
    time_step : float, optional
        The time step in the temporal unit. If not provided, it will be set to 1.0
        by default.

    Returns
    -------
    dict[str, Any]
        A dictionary containing the generated metadata.
    """
    metadata: dict[str, Any] = {}
    metadata["name"] = Path(file_path).stem
    metadata["file_location"] = file_path
    metadata["provenance"] = "CTC"

    if time_unit is not None:
        metadata["time_unit"] = time_unit
    else:
        metadata["time_unit"] = None
    if time_step is not None:
        metadata["time_step"] = time_step
    else:
        metadata["time_step"] = 1

    complete_metadata_flag = [0, 0, 0, 0]
    if space_unit is not None:
        metadata["space_unit"] = space_unit
        complete_metadata_flag[0] = 1
    if pixel_width is not None:
        metadata["pixel_width"] = pixel_width
        complete_metadata_flag[1] = 1
    if pixel_height is not None:
        metadata["pixel_height"] = pixel_height
        complete_metadata_flag[2] = 1
    if pixel_depth is not None:
        metadata["pixel_depth"] = pixel_depth
        complete_metadata_flag[3] = 1

    if labels_path is not None:
        metadata["label_imgs_location"] = labels_path
    if sum(complete_metadata_flag) < 4:
        if labels_path is not None:
            # Hopefully all label images have the same metadata.
            label_img_path = _get_label_img_paths(labels_path)[0]
            _integrate_label_imgs_metadata(metadata, label_img_path)
        else:
            if complete_metadata_flag[0] == 0:
                metadata["space_unit"] = "pixel"
            if complete_metadata_flag[1] == 0:
                metadata["pixel_width"] = 1.0
            if complete_metadata_flag[2] == 0:
                metadata["pixel_height"] = 1.0
            if complete_metadata_flag[3] == 0:
                metadata["pixel_depth"] = 1.0

    return metadata


def _create_PropsMetadata(
    seg_data: bool, time_unit: str | None, space_unit: str
) -> PropsMetadata:
    """
    Return a PropsMetadata object populated with pycellin basic properties.

    Parameters
    ----------
    seg_data : bool
        A boolean indicating whether segmentation data is available.
    time_unit : str | None
        The temporal unit of the data, used as the unit of the time property.
    space_unit : str
        The spatial unit of the data, used as the unit of the cell positions and
        contours.

    Returns
    -------
    PropsMetadata
        An instance of PropsMetadata populated with cell and lineage
        identification properties, and with the frame and time properties.
    """
    props_md = PropsMetadata()
    cell_id_prop = create_cell_id_property()
    frame_prop = create_frame_property(provenance="CTC")
    time_prop = create_time_property(unit=time_unit, provenance="CTC")
    lin_id_prop = create_lineage_id_property()
    for prop in [cell_id_prop, frame_prop, time_prop, lin_id_prop]:
        props_md._add_prop(prop)
    if seg_data:
        # TODO: deal with z dimension
        cell_x_prop = create_cell_coord_property(
            unit=space_unit, axis="x", provenance="CTC"
        )
        cell_y_prop = create_cell_coord_property(
            unit=space_unit, axis="y", provenance="CTC"
        )
        cell_contour_prop = create_cell_contour_property(
            unit=space_unit, custom_provenance="CTC"
        )
        props_md._add_props([cell_x_prop, cell_y_prop, cell_contour_prop])

    return props_md


def _read_track_line(
    line: str,
    current_node_id: int,
) -> tuple[list[tuple[int, dict[str, Any]]], int]:
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
            "cell_id": current_node_id,
            "frame": frame,
            "TRACK": track_id,
            "PARENT": parent_track,
        }
        nodes.append((current_node_id, node_attrs))
        current_node_id += 1
    return nodes, current_node_id


def _add_nodes_and_edges(
    graph: nx.DiGraph,
    nodes: list[tuple[int, dict[str, Any]]],
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
    nodes: list[tuple[int, dict[str, Any]]],
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
        parent_node = max(parent_nodes, key=lambda x: x[1])
        graph.add_edge(parent_node[0], nodes[0][0])


def _remove_track_attributes(graph: nx.DiGraph) -> None:
    """
    Remove the node attributes that were only needed for graph construction.

    The 'TRACK' and 'PARENT' attributes are used to merge tracks and to match
    segmentation labels to nodes. They are obsolete once the graph is complete.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph whose node attributes are to be cleaned.
    """
    for _, data in graph.nodes(data=True):
        data.pop("TRACK", None)
        data.pop("PARENT", None)


def _extract_seg_data(
    label_img_path: str,
    pixel_width: float = 1.0,
    pixel_height: float = 1.0,
) -> tuple[list[int], list[list[float]], list[list[tuple[float, float]]]]:
    """
    Extract segmentation data from a label image.

    This function reads a label image and extracts the labels, centroids,
    and contours of the regions in the image. Coordinates are converted from
    pixels to the space unit with the pixel size.

    Parameters
    ----------
    label_img_path : str
        The path to the label image file.
    pixel_width : float, optional
        The pixel width in the space unit. Default is 1.0.
    pixel_height : float, optional
        The pixel height in the space unit. Default is 1.0.

    Returns
    -------
    Tuple[List[int], List[List[float]], List[List[Tuple[float, float]]]]
        A tuple containing three lists:
        - labels: a list of unique labels in the image.
        - centroids: a list of centroids for each label, where each centroid
            is represented as a (x, y) tuple of coordinates.
        - contours: a list of contours for each label, where each contour
            is represented as a list of (x, y) coordinates relative to the centroid.

    Raises
    ------
    ValueError
        If the label image is not 2D.
    """
    label_img = tifffile.imread(label_img_path)
    if label_img.ndim != 2:
        raise ValueError(
            f"Label image '{label_img_path}' has shape {label_img.shape}: only 2D "
            "label images, one per frame, are supported for now."
        )
    regions = regionprops(label_img)
    labels = []
    centroids = []
    contours = []
    fragmented_labels = []
    for props in regions:
        # Label.
        labels.append(props.label)
        # Centroid.
        y0, x0 = props.centroid  # skimage returns (row, column) format
        centroids.append([float(x0 * pixel_width), float(y0 * pixel_height)])
        # Contour: outline of the largest piece of the label, holes filled.
        polygons = _mask_to_polygons(props.image)
        if len(polygons) > 1:
            fragmented_labels.append(props.label)
        # The polygon is in (x, y) coordinates of the label bounding box,
        # but the contours need to be given relatively to the label centroid.
        min_row, min_col = props.bbox[:2]
        contour = [
            (
                float((x + min_col - x0) * pixel_width),
                float((y + min_row - y0) * pixel_height),
            )
            for x, y in polygons[0].exterior.coords
        ]
        contours.append(contour)
    if fragmented_labels:
        logger.warning(
            f"Labels {fragmented_labels} of '{label_img_path}' are made of several "
            "pieces: their contour only covers the largest piece."
        )
    return labels, centroids, contours


def _index_cells(graph: nx.DiGraph) -> dict[tuple[int, int], list[int]]:
    """
    Index the cells of the graph by frame and track.

    Parameters
    ----------
    graph : nx.DiGraph
        The directed graph representing the lineage data, whose nodes still have
        their 'TRACK' attribute.

    Returns
    -------
    dict[tuple[int, int], list[int]]
        The cells of each (frame, track) pair, a single one in a valid CTC file.
    """
    cells: dict[tuple[int, int], list[int]] = {}
    for node, data in graph.nodes(data=True):
        cells.setdefault((data["frame"], data["TRACK"]), []).append(node)
    return cells


def _integrate_seg_data(
    graph: nx.DiGraph,
    cells: dict[tuple[int, int], list[int]],
    frame: int,
    labels: list[int],
    centroids: list[list[float]],
    contours: list[list[tuple[float, float]]],
) -> None:
    """
    Integrate segmentation data into the Pycellin model.

    This function updates the Pycellin model with segmentation data
    for a specific frame. It identifies the graph nodes to update thanks to the
    frame and labels and adds the following properties to each node:
    - the centroids as cell positions (cell_x, cell_y),
    - the centroid-relative contours of the cells (cell_contour).

    Parameters
    ----------
    graph: nx.DiGraph
        The directed graph representing the lineage data.
    cells : dict[tuple[int, int], list[int]]
        The cells of the graph indexed by frame and track (see `_index_cells()`).
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
        node = cells.get((frame, label), [])
        if len(node) < 1:
            raise ValueError(f"Label {label} not found in the graph for frame {frame}.")
        elif len(node) > 1:
            raise ValueError(f"Multiple nodes found for label {label} in frame {frame}.")
        node = node[0]
        # Updating the nodes.
        graph.nodes[node]["cell_x"] = centroid[0]
        graph.nodes[node]["cell_y"] = centroid[1]
        graph.nodes[node]["cell_contour"] = contour


def load_CTC_file(
    ctc_path: str | Path,
    labels_path: str | Path | None = None,
    space_unit: str | None = None,
    pixel_width: float | None = None,
    pixel_height: float | None = None,
    pixel_depth: float | None = None,
    time_unit: str | None = None,
    time_step: float | None = None,
) -> Model:
    """
    Create a pycellin model out of a Cell Tracking Challenge (CTC) text file.

    The CTC tracking format does not support fusion events and does not allow
    gaps right after division events.
    If only 'ctc_path' is given, only track topology is read. To load
    cell positions and contours into the model, 'labels_path' must also be given.
    The label images must be in the same format as the CTC format,
    i.e. a single 2D image per frame with a single label per cell. 3D label
    images are not supported yet.
    The label images names must end in '<frame_number>.tif' (e.g. 000.tif,
    02.tif, 0155.tif, etc.).
    For the space unit and pixel size, priority is given to the values given by the
    user. If not provided, pycellin will try to read them from the label images
    (TIFF resolution tags, with the unit of the ImageJ metadata for ImageJ images).
    A resolution in inches, most likely a print default such as 72 dpi, is ignored.
    If it fails or if no label images are given, default values will be used.
    Cell positions and contours are in the space unit: their pixel coordinates
    are multiplied by the pixel width and height.
    Cell times are stored in two node properties: 'frame', read from the CTC file,
    and 'time', equal to frame * time_step and expressed in time_unit. 'time' is
    the reference time property of the model.

    Parameters
    ----------
    ctc_path : str | Path
        The path to the CTC text file that contains the tracking data.
    labels_path : str | Path, optional
        The path to the folder of label images, if any. If not provided, only the
        track topology will be read. If the space unit and pixel size are not
        directly provided by the user, they will be read from the label images.
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
        The temporal unit of the data. If not provided, it will be set to None
        by default.
    time_step : float, optional
        The time step in the temporal unit. If not provided, it will be set to 1
        by default.

    Returns
    -------
    Model
        The created pycellin model.

    Raises
    ------
    ValueError
        If 'labels_path' is not a folder of .tif label images, if a label image is
        not 2D or its name doesn't end with a frame number, or if a label matches
        no cell or several cells of its frame.

    Warns
    -----
    UserWarning
        If the resolution of the label images is in inches, and therefore ignored,
        while the space unit or the pixel width or height is not given.
    """
    # The label images are checked before the CTC file is read.
    label_img_paths = []
    if labels_path is not None:
        label_img_paths = _get_label_img_paths(labels_path)

    graph = nx.DiGraph()
    current_node_id = 0
    with open(ctc_path) as file:
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

    md = _create_metadata(
        ctc_path,
        labels_path=labels_path,
        space_unit=space_unit,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        pixel_depth=pixel_depth,
        time_unit=time_unit,
        time_step=time_step,
    )

    # Adding the segmentation data, if any, in the space unit.
    if label_img_paths:
        cells = _index_cells(graph)
        pattern = r"(\d+)\.tif"
        for label_img_path in label_img_paths:
            # The image is read first, so that a stack holding all the frames gets
            # the error on its shape rather than on its name.
            labels, centroids, contours = _extract_seg_data(
                str(label_img_path), md["pixel_width"], md["pixel_height"]
            )
            match = re.search(pattern, str(label_img_path))
            try:
                frame = int(match.group(1))
            except AttributeError:
                raise ValueError(
                    f"Can't parse frame value: file name {label_img_path} "
                    f"does not match the expected pattern."
                )
            _integrate_seg_data(graph, cells, frame, labels, centroids, contours)

    _remove_track_attributes(graph)

    # The reference time property is the physical time, so that the time step and
    # time unit apply to it. Timepoints are then derived from it by the model.
    for _, node_data in graph.nodes(data=True):
        node_data["time"] = float(node_data["frame"] * md["time_step"])

    # One lineage per connected component of the graph.
    lineages = _split_graph_into_lineages(graph)
    data = {lin.graph["lineage_id"]: lin for lin in lineages if len(lin) > 0}

    props_md = _create_PropsMetadata(
        labels_path is not None, md["time_unit"], md["space_unit"]
    )
    model = Model(
        model_metadata=md,
        props_metadata=props_md,
        data=Data(data),
        reference_time_property="time",
    )
    return model


if __name__ == "__main__":
    """
    Quick demo with sample data.
    """
    ctc_file = (
        Path(__file__).resolve().parents[3] / "sample_data" / "FakeTracks_TMtoCTC.txt"
    )
    # ctc_file = (
    #     Path(__file__).resolve().parents[3]
    #     / "sample_data"
    #     / "Ecoli_growth_on_agar_pad_TMtoCTC.txt"
    # )
    model = load_CTC_file(ctc_file)  # , labels_path)

    print(model)
    print("\nModel metadata:")
    print(model.model_metadata)
    print("\nProperties and their types:")
    for prop_id, prop in model.props_metadata.props.items():
        print(f"  - {prop_id}  -> {prop.prop_type}")
