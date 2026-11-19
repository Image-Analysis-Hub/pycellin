#!/usr/bin/env python3

"""
Writer for TrackMate XML files.

Features in the XML file are not in the same order as a file that was exported
directly from TrackMate.
I've tested quickly and it doesn't seem to be a problem for TrackMate.
"""

import copy
import logging
import math
import numbers
import re
import warnings
from collections import Counter
from pathlib import Path
from typing import Any

import networkx as nx
from lxml import etree as ET

from pycellin.classes.lineage import CellLineage
from pycellin.classes.model import Model
from pycellin.classes.property import Property
from pycellin.classes.props_metadata import PropsMetadata
from pycellin.custom_types import PropertyType
from pycellin.exceptions import ProtectedPropertyError, PycellinWarning
from pycellin.io.utils import (
    _check_up_to_date,
    _get_cycle_props_message,
    _get_props_from_data,
    _identify_frame_prop,
    _relabel_nodes_in_place,
    _update_node_prop_key,
)
from pycellin.utils import _find_stack_level, _is_numeric_dtype, _normalize_dtype

logger = logging.getLogger(__name__)


def _unit_to_dimension(
    prop: Property,
) -> str:
    """
    Convert a unit to a dimension.

    Parameters
    ----------
    prop : Property
        The property for which to convert the unit.

    Returns
    -------
    str
        Dimension corresponding to the unit.

    Notes
    -----
    A warning is logged if the dimension cannot be determined, in which case the
    default dimension ``NONE`` is used.
    """
    # TODO: finish this function and try to make it less nightmarish
    unit = prop.unit
    name = prop.identifier
    # desc = prop.description
    provenance = prop.provenance

    # TrackMate features
    # Mapping between TrackMate features and their dimensions.
    trackmate_props = {
        # Spot features
        "QUALITY": "QUALITY",
        "POSITION_X": "POSITION",
        "POSITION_Y": "POSITION",
        "POSITION_Z": "POSITION",
        "POSITION_T": "TIME",
        "FRAME": "NONE",
        "RADIUS": "LENGTH",
        "VISIBILITY": "NONE",
        "MANUAL_SPOT_COLOR": "NONE",
        "ELLIPSE_X0": "LENGTH",
        "ELLIPSE_Y0": "LENGTH",
        "ELLIPSE_MAJOR": "LENGTH",
        "ELLIPSE_MINOR": "LENGTH",
        "ELLIPSE_THETA": "ANGLE",
        "ELLIPSE_ASPECTRATIO": "NONE",
        "AREA": "AREA",
        "PERIMETER": "LENGTH",
        "CIRCULARITY": "NONE",
        "SOLIDITY": "NONE",
        "SHAPE_INDEX": "NONE",
        # Edge features
        "SPOT_SOURCE_ID": "NONE",
        "SPOT_TARGET_ID": "NONE",
        "LINK_COST": "COST",
        "DIRECTIONAL_CHANGE_RATE": "ANGLE_RATE",
        "SPEED": "VELOCITY",
        "DISPLACEMENT": "LENGTH",
        "EDGE_TIME": "TIME",
        "EDGE_X_LOCATION": "POSITION",
        "EDGE_Y_LOCATION": "POSITION",
        "EDGE_Z_LOCATION": "POSITION",
        "MANUAL_EDGE_COLOR": "NONE",
        # Track features
        "TRACK_INDEX": "NONE",
        "TRACK_ID": "NONE",
        "NUMBER_SPOTS": "NONE",
        "NUMBER_GAPS": "NONE",
        "NUMBER_SPLITS": "NONE",
        "NUMBER_MERGES": "NONE",
        "NUMBER_COMPLEX": "NONE",
        "LONGEST_GAP": "NONE",
        "TRACK_DURATION": "TIME",
        "TRACK_START": "TIME",
        "TRACK_STOP": "TIME",
        "TRACK_DISPLACEMENT": "LENGTH",
        "TRACK_X_LOCATION": "POSITION",
        "TRACK_Y_LOCATION": "POSITION",
        "TRACK_Z_LOCATION": "POSITION",
        "TRACK_MEAN_SPEED": "VELOCITY",
        "TRACK_MAX_SPEED": "VELOCITY",
        "TRACK_MIN_SPEED": "VELOCITY",
        "TRACK_MEDIAN_SPEED": "VELOCITY",
        "TRACK_STD_SPEED": "VELOCITY",
        "TRACK_MEAN_QUALITY": "QUALITY",
        "TOTAL_DISTANCE_TRAVELED": "LENGTH",
        "MAX_DISTANCE_TRAVELED": "LENGTH",
        "MEAN_STRAIGHT_LINE_SPEED": "VELOCITY",
        "LINEARITY_OF_FORWARD_PROGRESSION": "NONE",
        "MEAN_DIRECTIONAL_CHANGE_RATE": "ANGLE_RATE",
        "DIVISION_TIME_MEAN": "TIME",
        "DIVISION_TIME_STD": "TIME",
        "CONFINEMENT_RATIO": "NONE",
    }
    # Channel dependent features.
    # Depending on the TrackMate version, we can have MEAN_INTENSITY or
    # MEAN_INTENSITY_CH1 when there is only one channel.
    channel_props = {
        "MEAN_INTENSITY": "INTENSITY",
        "MEDIAN_INTENSITY": "INTENSITY",
        "MIN_INTENSITY": "INTENSITY",
        "MAX_INTENSITY": "INTENSITY",
        "TOTAL_INTENSITY": "INTENSITY",
        "STD_INTENSITY": "INTENSITY",
        "CONTRAST": "NONE",
        "SNR": "NONE",
    }

    # Pycellin features.
    pycellin_props = {
        # Cell features.
        "cell_area": "AREA",
        "cell_circularity": "NONE",
        "cell_displacement": "LENGTH",
        "cell_mean_intensity": "INTENSITY",
        "cell_perimeter": "LENGTH",
        "cell_polygon": "NONE",  # not float nor int so won't be exported anyway
        "cell_solidity": "NONE",
        "cell_speed": "VELOCITY",
        "cell_total_intensity": "INTENSITY",
        "is_division": "NONE",
        "is_leaf": "NONE",
        "is_root": "NONE",
        "location_tag": "NONE",
        "normalized_age": "NONE",
        "pycellin_cell_id": "NONE",
        "rod_length": "LENGTH",
        "rod_width": "LENGTH",
        "timepoint": "NONE",
        "turning_angle": "ANGLE",
        # Cycle features.
        "cycle_total_displacement": "LENGTH",
        "cycle_mean_displacement": "LENGTH",
        "cycle_mean_speed": "VELOCITY",
        "cycle_mean_area": "AREA",
        "birth_area": "AREA",
        "division_area": "AREA",
        "cycle_mean_intensity": "INTENSITY",
        "birth_intensity": "INTENSITY",
        "division_intensity": "INTENSITY",
        "cells": "NONE",  # not float nor int so won't be exported anyway
        "is_complete_cycle": "NONE",
        "cycle_duration": "TIME",
        "cycle_end_time": "TIME",
        "cycle_id": "NONE",
        "cycle_num_cells": "NONE",
        "cycle_start_time": "TIME",
        "interdivision_time": "TIME",
        "inverse_interdivision_time": "RATE",
        "first_cell": "NONE",
        "last_cell": "NONE",
        "generation": "NONE",
        "mother_cycle": "NONE",
        "straightness": "NONE",
        # Lineage features.
        "num_cells": "NONE",
        "num_cycles": "NONE",
        "num_divisions": "NONE",
        "num_gaps": "NONE",
        "num_leaves": "NONE",
        "lineage_cell_depth": "NONE",
        "lineage_cycle_depth": "NONE",
        "lineage_duration": "TIME",
    }
    # TODO: I could regroup all the props starting with is_ or num_,
    # since their dimension should always be NONE
    if name == "absolute_age":
        if unit == "frame":
            pycellin_props["absolute_age"] = "NONE"
        else:
            pycellin_props["absolute_age"] = "TIME"
    elif name == "relative_age":
        if unit == "frame":
            pycellin_props["relative_age"] = "NONE"
        else:
            pycellin_props["relative_age"] = "TIME"
    elif name == "turning_angle" and unit == "degree":
        # TrackMate angles are in radians.
        pycellin_props["turning_angle"] = "NONE"

    dimension = None
    if name in trackmate_props:
        dimension = trackmate_props[name]
    if dimension is None:
        for key, dim in channel_props.items():
            if name.startswith(key):
                dimension = dim
                break

    if dimension is None and provenance == "TrackMate":
        if name in trackmate_props:
            dimension = trackmate_props[name]
        else:
            dimension = None
            for key, dim in channel_props.items():
                if name.startswith(key):
                    dimension = dim
                    break
            if dimension is None:
                msg = (
                    f"'{name}' is a property listed as coming from TrackMate"
                    f" but it is not a known property of TrackMate. Dimension is set"
                    f" to NONE."
                )
                logger.warning(msg)
                # I'm using NONE here, which is already used in TM, for example
                # with the FRAME or VISIBILITY features. I tried to use UNKNOWN
                # but it's a dimension not recognized by TM and it crashes.
                dimension = "NONE"

    if dimension is None and provenance == "Pycellin":
        try:
            dimension = pycellin_props[name]
        except KeyError:
            try:
                dimension = trackmate_props[name]
            except KeyError:
                msg = (
                    f"'{name}' is a property listed as coming from Pycellin"
                    f" but it is not a known property of either Pycellin or TrackMate. "
                    f"Dimension is set to NONE."
                )
                logger.warning(msg)
                dimension = "NONE"

    if dimension is None:
        # TODO: It's going to be a nightmare to deal with all the possible cases.
        # Is it even possible? Maybe I could ask the user for a file with
        # a property-dimension mapping. For now, I just set the dimension to NONE.
        match unit:
            case "pixel":
                if name.lower() in ["x", "y", "z"]:
                    dimension = "POSITION"
                else:
                    dimension = "LENGTH"
            case None | "frame":
                dimension = "NONE"
            case _:
                msg = (
                    f"Cannot infer dimension for property '{name}'. Dimension is "
                    "set to NONE."
                )
                logger.warning(msg)
                dimension = "NONE"

    assert dimension is not None
    return dimension


def _transform_name(name: str) -> str:
    """
    Transform a property name to a more user-friendly format, close to TrackMate's.

    Parameters
    ----------
    name : str
        Name of the property to transform.

    Returns
    -------
    str
        The transformed name.

    Notes
    -----
    The transformation consists in:

    - replacing underscores by spaces,
    - lowercasing the words, except for some exceptions,
    - capitalizing the first letter of the name,
    - handling specific cases for positions.
    """
    if name in ["POSITION_X", "POSITION_Y", "POSITION_Z", "POSITION_T"]:
        new_name = name[-1]
    elif name in ["EDGE_X_LOCATION", "EDGE_Y_LOCATION", "EDGE_Z_LOCATION"]:
        new_name = "Edge " + name.split("_")[1]
    elif name in ["TRACK_X_LOCATION", "TRACK_Y_LOCATION", "TRACK_Z_LOCATION"]:
        new_name = "Track mean " + name.split("_")[1]
    else:
        exceptions = {"X", "Y", "Z", "T", "ID", "SNR"}
        name = name.replace("_", " ")

        def transform_word(match):
            word = match.group(0)
            if word == "id":
                return "ID"
            return word if word in exceptions else word.lower()

        new_name = re.sub(r"\b\w+\b", transform_word, name)
        new_name = new_name[0].upper() + new_name[1:]
    return new_name


def _convert_prop_to_feat(
    prop: Property,
) -> dict[str, str]:
    """
    Convert a Pycellin property to a TrackMate feature.

    Parameters
    ----------
    prop : Property
        Property to convert.

    Returns
    -------
    dict[str, str]
        Dictionary of the converted feature.
    """
    trackmate_feat = {}
    trackmate_feat["feature"] = prop.identifier
    # TrackMate uses in the GUI the following attributes:
    # - `name` as the display name of the feature for filtering and plotting
    # - `shortname` as the display name of the feature in the nodes, edges and
    # tracks tables
    # So we need to convert the name to a more user-friendly format that is close
    # to what TrackMate is using.
    new_name = _transform_name(prop.identifier)
    trackmate_feat["name"] = new_name
    trackmate_feat["shortname"] = new_name
    trackmate_feat["dimension"] = _unit_to_dimension(prop)
    if _normalize_dtype(prop.dtype) == "int":
        trackmate_feat["isint"] = "true"
    else:
        trackmate_feat["isint"] = "false"

    return trackmate_feat


def _write_FeatureDeclarations(
    xf: ET.xmlfile,
    model: Model,
) -> None:
    """
    Write the FeatureDeclarations XML tag into a TrackMate XML file.

    The features declaration is divided in three parts: spot features,
    edge features, and track features. But they are all processed
    in the same way.

    Only the properties of cell lineages are declared, since TrackMate has no
    cycle lineages. Cycle properties are declared once propagated to the cell
    lineages (see `Model.get_cell_lineage_properties`). A property called
    ``name`` on cells or lineages isn't declared either: it is written as the display
    name of spots or tracks, which TrackMate doesn't read as a feature.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    model : Model
        Model containing the data to write.

    Raises
    ------
    ValueError
        If the feature type is unknown.
    """
    cell_props = model.get_cell_lineage_properties()
    xf.write(f"\n{' ' * 4}")
    with xf.element("FeatureDeclarations"):
        features_type = ["SpotFeatures", "EdgeFeatures", "TrackFeatures"]
        for f_type in features_type:
            xf.write(f"\n{' ' * 6}")
            with xf.element(f_type):
                xf.write(f"\n{' ' * 8}")
                match f_type:
                    case "SpotFeatures":
                        props = model.get_node_properties()
                    case "EdgeFeatures":
                        props = model.get_edge_properties()
                    case "TrackFeatures":
                        props = model.get_lineage_properties()
                    case _:
                        raise ValueError(f"Unknown feature type: {f_type}")
                first_feat_written = False
                for prop in props.values():
                    if prop.identifier not in cell_props:
                        continue  # no values on spots, edges or tracks
                    if prop.identifier == "name" and f_type != "EdgeFeatures":
                        continue  # display name of spots and tracks, not a feature
                    trackmate_feat = _convert_prop_to_feat(prop)
                    if trackmate_feat:
                        if first_feat_written:
                            xf.write(f"\n{' ' * 8}")
                        else:
                            first_feat_written = True
                        xf.write(ET.Element("Feature", trackmate_feat))
                xf.write(f"\n{' ' * 6}")
        xf.write(f"\n{' ' * 4}")


def _value_to_str(
    value: Any,
) -> str:
    """
    Convert a value to its associated string.

    Indeed, ``ET.write()`` method only accepts to write strings.
    However, TrackMate is only able to read Spot, Edge and Track
    features that can be parsed as numeric by Java. A missing value (None)
    is thus written as NaN, like TrackMate does.

    Parameters
    ----------
    value : Any
        Value to convert to string.

    Returns
    -------
    str
        The string equivalent of `value`.
    """
    if value is None:
        return "NaN"
    elif isinstance(value, bool):
        return "1" if value else "0"
    elif isinstance(value, numbers.Number):
        if math.isnan(value):
            return "NaN"
        elif math.isinf(value):
            if value > 0:
                return "Infinity"
            else:
                return "-Infinity"
        else:
            return str(value)
    elif isinstance(value, str):
        return value
    else:
        return str(value)


def _get_exported_keys(model: Model) -> dict[str, set[str]]:
    """
    Return the keys of the attributes to write for spots, edges and tracks.

    These are the properties declared in the FeatureDeclarations tag, plus the
    attributes that TrackMate reads without declaration: the ID and name of spots,
    and the name of tracks. The other attributes of cells, links and lineages are
    not exported.

    Parameters
    ----------
    model : Model
        Model prepared for the export.

    Returns
    -------
    dict[str, set[str]]
        The keys of the attributes to write, by property type (``"node"``,
        ``"edge"`` and ``"lineage"``).

    Warns
    -----
    PycellinWarning
        If some attributes have no property declaration, and so are not exported.
    """
    exported_keys = {
        "node": {"ID", "name"},
        "edge": set(),
        "lineage": {"name"},
    }
    cell_props = model.get_cell_lineage_properties()
    for prop_type, props in (
        ("node", model.get_node_properties()),
        ("edge", model.get_edge_properties()),
        ("lineage", model.get_lineage_properties()),
    ):
        # Only the properties of cell lineages are declared, see
        # _write_FeatureDeclarations().
        exported_keys[prop_type].update(
            prop_id for prop_id in props if prop_id in cell_props
        )

    # Attributes written in another way, or not at all on purpose.
    handled_keys = {
        "node": {"TRACK_ID", "cell_contour"},
        "edge": set(),
        "lineage": {"Model", "FilteredTrack"},
    }
    ignored: dict[str, set[str]] = {"node": set(), "edge": set(), "lineage": set()}
    for lin in model.data.cell_lineages.values():
        attrs_dicts = {
            "node": [attrs for _, attrs in lin.nodes(data=True)],
            "edge": [attrs for _, _, attrs in lin.edges(data=True)],
            "lineage": [lin.graph],
        }
        for prop_type, dicts in attrs_dicts.items():
            known = exported_keys[prop_type] | handled_keys[prop_type]
            for attrs in dicts:
                ignored[prop_type].update(key for key in attrs if key not in known)
    element_names = {"node": "cells", "edge": "links", "lineage": "lineages"}
    ignored_str = ", ".join(
        f"'{key}' ({element_names[prop_type]})"
        for prop_type, keys in ignored.items()
        for key in sorted(keys)
    )
    if ignored_str:
        warnings.warn(
            f"Not exporting attributes that have no property declaration: "
            f"{ignored_str}.",
            PycellinWarning,
            stacklevel=_find_stack_level(),
        )
    return exported_keys


def _create_Spot(
    lineage: CellLineage,
    node: int,
    keys: set[str],
) -> ET._Element:
    """
    Create an XML Spot Element representing a node of a Lineage.

    Parameters
    ----------
    lineage : CellLineage
        Lineage containing the node to create.
    node : int
        ID of the node in the lineage.
    keys : set[str]
        Keys of the node attributes to write, see ``_get_exported_keys()``. The cell
        contour is written in any case, as the ROI of the spot.

    Returns
    -------
    ET._Element
        The newly created Spot Element.
    """
    n_attr = {k: _value_to_str(v) for k, v in lineage.nodes[node].items() if k in keys}
    # A cell without contour may have None, e.g. when loaded from a TrackMate file.
    contour = lineage.nodes[node].get("cell_contour")
    if contour is not None:
        n_attr["ROI_N_POINTS"] = str(len(contour))
        # The text of a Spot is the coordinates of its ROI points, in a flattened list.
        coords = [item for pt in contour for item in pt]
    else:
        # No segmentation mask, so we set the ROI_N_POINTS to 0.
        n_attr["ROI_N_POINTS"] = "0"

    el_node = ET.Element("Spot", n_attr)
    if contour is not None:
        el_node.text = " ".join(map(str, coords))
    return el_node


def _write_AllSpots(
    xf: ET.xmlfile,
    data: dict[int, CellLineage],
    keys: set[str],
) -> None:
    """
    Write the nodes/spots data into an XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    data : dict[int, CellLineage]
        Cell lineages containing the data to write.
    keys : set[str]
        Keys of the node attributes to write, see ``_get_exported_keys()``.
    """
    xf.write(f"\n{' ' * 4}")
    lineages = data.values()
    nb_nodes = sum([len(lin) for lin in lineages])
    with xf.element("AllSpots", {"nspots": str(nb_nodes)}):
        # For each frame, nodes can be spread over several lineages
        # so we first need to identify all of the existing frames.
        frames = set()  # type: set[int]
        for lin in lineages:
            frames.update(nx.get_node_attributes(lin, "FRAME").values())

        # Then at each frame, we can find the nodes and write its data.
        for frame in frames:
            xf.write(f"\n{' ' * 6}")
            with xf.element("SpotsInFrame", {"frame": str(frame)}):
                for lin in lineages:
                    nodes = [n for n in lin.nodes() if lin.nodes[n]["FRAME"] == frame]
                    for node in nodes:
                        xf.write(f"\n{' ' * 8}")
                        xf.write(_create_Spot(lin, node, keys))
                xf.write(f"\n{' ' * 6}")
        xf.write(f"\n{' ' * 4}")


def _write_AllTracks(
    xf: ET.xmlfile,
    data: dict[int, CellLineage],
    track_keys: set[str],
    edge_keys: set[str],
) -> None:
    """
    Write the tracks data into an XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    data : dict[int, CellLineage]
        Cell lineages containing the data to write.
    track_keys : set[str]
        Keys of the lineage attributes to write, see ``_get_exported_keys()``.
    edge_keys : set[str]
        Keys of the edge attributes to write, see ``_get_exported_keys()``.
    """
    xf.write(f"\n{' ' * 4}")
    with xf.element("AllTracks"):
        for lineage in data.values():
            # We have track tags to add only for tracks with several spots,
            # so one-node lineages are to be ignored. They are identified by their
            # size rather than by their negative ID, which is only a convention.
            if len(lineage) < 2:
                continue

            # Track tags.
            xf.write(f"\n{' ' * 6}")
            t_attr = {
                k: _value_to_str(v) for k, v in lineage.graph.items() if k in track_keys
            }
            with xf.element("Track", t_attr):
                # Edge tags.
                for edge in lineage.edges.data():
                    xf.write(f"\n{' ' * 8}")
                    e_attr = {
                        k: _value_to_str(v)
                        for k, v in edge[2].items()
                        if k in edge_keys
                    }
                    xf.write(ET.Element("Edge", e_attr))
                xf.write(f"\n{' ' * 6}")
        xf.write(f"\n{' ' * 4}")


def _write_track_id(xf: ET.xmlfile, lineage: CellLineage) -> None:
    """
    Write a track ID to the XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    lineage : CellLineage
        Cell lineage containing the data to write.

    Raises
    ------
    KeyError
        If a lineage with several cells does not have a ``TRACK_ID`` attribute.
    """
    if len(lineage) < 2:
        # We don't want to write the track ID for one-node lineages.
        return
    try:
        track_id = lineage.graph["TRACK_ID"]
    except KeyError as err:
        raise KeyError("The lineage does not have a TRACK_ID attribute.") from err
    xf.write(f"\n{' ' * 6}")
    t_attr = {"TRACK_ID": str(track_id)}
    xf.write(ET.Element("TrackID", t_attr))


def _write_FilteredTracks(
    xf: ET.xmlfile,
    data: dict[int, CellLineage],
    has_FilteredTracks: bool,
) -> None:
    """
    Write the filtered tracks data into an XML file.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    data : dict[int, CellLineage]
        Cell lineages containing the data to write.
    has_FilteredTracks : bool
        Flag indicating if the model contains filtered tracks.
    """
    xf.write(f"\n{' ' * 4}")
    with xf.element("FilteredTracks"):
        if has_FilteredTracks:
            for lineage in data.values():
                # A lineage without the flag, e.g. added or split off in Pycellin,
                # is visible.
                if lineage.graph.get("FilteredTrack", True):
                    _write_track_id(xf, lineage)
        else:
            # If there are no filtered tracks, we need to add all the tracks
            # because TrackMate only displays tracks that are in this tag.
            for lineage in data.values():
                _write_track_id(xf, lineage)
        xf.write(f"\n{' ' * 4}")
    xf.write(f"\n{' ' * 2}")


def _update_nodes(lin: CellLineage, frame_prop: str) -> set[int]:
    """
    Update the node properties in the lineage to match TrackMate requirements.

    Parameters
    ----------
    lin : CellLineage
        Lineage whose nodes to update.
    frame_prop : str
        Name of the property corresponding to the frame/timepoint.

    Returns
    -------
    set[int]
        Set of node IDs that are missing ``POSITION_X`` or ``POSITION_Y``.
    """
    nodes_with_missing_pos = set()

    for node, data in lin.nodes(data=True):
        data["ID"] = data.pop("cell_id")
        data["FRAME"] = data.pop(frame_prop)
        # Cells keep the visibility they were loaded with, e.g. hidden by the spot
        # filters of TrackMate. The others are visible.
        if data.get("VISIBILITY") is None:
            data["VISIBILITY"] = 1
        try:
            data.pop("lineage_id")  # TM needs it only on the tracks, not on the spots
        except KeyError:
            pass  # lineage_id should be present, but better be safe than sorry
        try:
            data.pop("timepoint")  # internal Pycellin property
        except KeyError:
            # If frame_prop is timepoint, it has already been popped
            # and we can ignore the KeyError.
            pass
        try:
            data["name"] = data.pop("cell_name")
        except KeyError:
            pass  # not a mandatory property
        # Position properties.
        has_missing_pos = False
        for axis in ["X", "Y", "Z"]:
            try:
                data[f"POSITION_{axis}"] = data.pop(f"cell_{axis.lower()}")
            except KeyError:
                # This POSITION_ is mandatory in TrackMate for x, y and z dimensions.
                if axis in ["X", "Y"]:
                    has_missing_pos = True
                    # We set a default value, otherwise TrackMate will crash.
                    data[f"POSITION_{axis}"] = 0.0
                else:
                    # We add the missing z dimension.
                    data[f"POSITION_{axis}"] = 0.0

        if has_missing_pos:
            nodes_with_missing_pos.add(node)

    return nodes_with_missing_pos


def _update_edges(lin: CellLineage) -> None:
    """
    Update the edge properties in the lineage to match TrackMate requirements.

    Parameters
    ----------
    lin : CellLineage
        Lineage whose edges to update.
    """
    for source_node, target_node, data in lin.edges(data=True):
        # Mandatory TrackMate properties.
        # Create if they don't exist. Update if they exist, for consistency.
        data["SPOT_SOURCE_ID"] = source_node
        data["SPOT_TARGET_ID"] = target_node
        # Position properties.
        for axis in ["X", "Y", "Z"]:
            try:
                data[f"EDGE_{axis}_LOCATION"] = data.pop(f"link_{axis.lower()}")
            except KeyError:
                pass  # not mandatory


def _update_lineages(lin: CellLineage) -> None:
    """
    Update the lineage properties to match TrackMate requirements.

    Parameters
    ----------
    lin : CellLineage
        Lineage whose graph to update.
    """
    # Mandatory TrackMate property.
    lin.graph["TRACK_ID"] = lin.graph.pop("lineage_id")

    try:
        lin.graph["name"] = lin.graph.pop("lineage_name")
    except KeyError:
        pass  # not mandatory
    # Position properties.
    for axis in ["X", "Y", "Z"]:
        try:
            lin.graph[f"TRACK_{axis}_LOCATION"] = lin.graph.pop(
                f"lineage_{axis.lower()}"
            )
        except KeyError:
            pass  # not mandatory


def _get_time_interval(model: Model) -> float:
    """
    Return the time between two frames written in the TrackMate file.

    It is the ``timeinterval`` of the TrackMate settings kept in the model metadata,
    when the model was read from a TrackMate file, else the time step of the model,
    or 1.0 if the model has none.

    Parameters
    ----------
    model : Model
        Model to write.

    Returns
    -------
    float
        Time between two frames, in the time unit of the file.
    """
    settings = model.model_metadata.to_dict().get("Settings")
    if settings:
        image_data = ET.fromstring(settings).find("ImageData")
        if image_data is not None and image_data.get("timeinterval"):
            return float(image_data.get("timeinterval"))
    return model.model_metadata.time_step or 1.0


def _add_missing_time_and_quality(
    lin: CellLineage, time_interval: float
) -> tuple[int, int]:
    """
    Give a ``POSITION_T`` and a ``QUALITY`` to the spots that have none.

    TrackMate computes features such as the duration and speed of tracks from
    ``POSITION_T``, and their mean quality from ``QUALITY``, e.g. after a link is
    deleted in TrackScheme: spots without them make it fail. Spots without
    ``POSITION_T`` get the time of their frame, as TrackMate computes it, and spots
    without ``QUALITY`` get -1, the quality TrackMate gives spots added by hand.

    Parameters
    ----------
    lin : CellLineage
        Lineage whose nodes to update, with their ``FRAME`` already set.
    time_interval : float
        Time between two frames, as written in the file.

    Returns
    -------
    tuple[int, int]
        Number of spots given a ``POSITION_T``, and number given a ``QUALITY``.
    """
    num_times = num_qualities = 0
    for _, data in lin.nodes(data=True):
        if data.get("POSITION_T") is None:
            data["POSITION_T"] = data["FRAME"] * time_interval
            num_times += 1
        if data.get("QUALITY") is None:
            data["QUALITY"] = -1.0
            num_qualities += 1
    return num_times, num_qualities


def _update_model_data(
    model: Model,
    frame_prop: str,
    id_mapping: dict[int, dict[int, int]] | None = None,
) -> None:
    """
    Update the data in the model to match TrackMate requirements.

    Parameters
    ----------
    model : Model
        Model whose data to update.
    frame_prop : str
        Name of the property corresponding to the frame/timepoint.
    id_mapping : dict[int, dict[int, int]] | None, default=None
        Mapping of the old node IDs to the new ones for each lineage, as returned by
        ``_relabel_nodes()``, if the nodes were relabeled.

    Warns
    -----
    PycellinWarning
        If some cells are missing x and/or y coordinates, in which case they are set
        to 0.0. It names the cells by their ID in the model, i.e. before relabeling.

    Notes
    -----
    Spots without ``POSITION_T`` or ``QUALITY`` get one, as TrackMate needs them,
    and a message at the info level says how many.
    """
    # Track cells with missing position properties: {lineage_id: set of cell IDs}.
    missing_positions = {}
    mapping = id_mapping or {}
    time_interval = _get_time_interval(model)
    num_times = num_qualities = 0

    for lin_id, lin in model.data.cell_lineages.items():
        nodes_with_missing_pos = _update_nodes(lin, frame_prop)
        if nodes_with_missing_pos:
            old_ids = {new: old for old, new in mapping.get(lin_id, {}).items()}
            missing_positions[lin.graph["lineage_id"]] = {
                old_ids.get(node, node) for node in nodes_with_missing_pos
            }
        times, qualities = _add_missing_time_and_quality(lin, time_interval)
        num_times += times
        num_qualities += qualities
        _update_edges(lin)
        _update_lineages(lin)

    if num_times or num_qualities:
        added = []
        if num_times:
            spots = "spot" if num_times == 1 else "spots"
            added.append(
                f"a POSITION_T computed from FRAME and the time interval "
                f"({time_interval}) for {num_times} {spots}"
            )
        if num_qualities:
            spots = "spot" if num_qualities == 1 else "spots"
            added.append(f"a QUALITY of -1 for {num_qualities} {spots}")
        logger.info(
            "TrackMate needs a POSITION_T and a QUALITY on every spot. Added "
            + " and ".join(added)
            + "."
        )

    # Show a single summary warning at the end if any positions are missing.
    if missing_positions:
        msg_parts = []
        for lineage_id, cell_ids in missing_positions.items():
            cells_str = ", ".join(str(c) for c in sorted(cell_ids))
            cells = "cell" if len(cell_ids) == 1 else "cells"
            msg_parts.append(f"  lineage {lineage_id}: {cells} {cells_str}")
        msg = (
            "Missing mandatory x and/or y coordinates, defaulting to 0.0 for:\n"
            + "\n".join(msg_parts)
        )
        warnings.warn(msg, PycellinWarning, stacklevel=_find_stack_level())


def _warn_cycle_props_left_out(model: Model) -> None:
    """
    Warn about the cycle properties that the export leaves out, if any.

    Only the properties of cell lineages are exported, see
    ``_write_FeatureDeclarations()``, so cycle properties are left out unless they
    were propagated to the cells first. As for GEFF, the properties named are the
    cell and link properties with values on cycle lineages only.

    Parameters
    ----------
    model : Model
        Model to export, after the propagation of cycle properties, if any.

    Warns
    -----
    PycellinWarning
        If some cell or link properties have values on cycle lineages only.
    """
    if not model.data.cycle_lineages:
        return
    cycle_node_props, cycle_edge_props, _ = _get_props_from_data(
        model.data.cycle_lineages.values()
    )
    cell_node_props, cell_edge_props, _ = _get_props_from_data(
        model.data.cell_lineages.values()
    )
    node_props_md = model.props_metadata._get_prop_dict_from_prop_type(
        PropertyType.NODE
    ).keys()
    edge_props_md = model.props_metadata._get_prop_dict_from_prop_type(
        PropertyType.EDGE
    ).keys()
    left_out = sorted(
        ((node_props_md & cycle_node_props) - cell_node_props)
        | ((edge_props_md & cycle_edge_props) - cell_edge_props)
    )
    if left_out:
        warnings.warn(
            _get_cycle_props_message(left_out),
            PycellinWarning,
            stacklevel=_find_stack_level(),
        )


def _remove_non_numeric_props(model: Model) -> None:
    """
    Completely remove non-numeric properties from the model.

    The properties from TrackMate are kept, and so is ``name`` on cells or lineages,
    the display name of spots or tracks.

    Parameters
    ----------
    model : Model
        Model to modify.

    Notes
    -----
    This is necessary because TrackMate does not support non-numeric features.
    Boolean features are considered numeric and are converted to integers
    (1 for True, 0 for False).

    A warning is logged if some properties are not numeric and will not be exported
    to TrackMate. This is the case for properties with string, list, or other
    non-numeric values that TrackMate cannot handle. Cycle properties that were not
    propagated are removed without being named, since they are not exported
    anyway.
    """
    to_remove = [
        name
        for name, prop in model.get_properties().items()
        if prop.provenance != "TrackMate" and not _is_numeric_dtype(prop.dtype)
    ]
    # The only exception is 'name' which is a string property that TrackMate can handle
    # as the display name of a spot or a track, but not of a link.
    to_remove = [
        name
        for name in to_remove
        if name != "name" or model.get_property(name).prop_type == PropertyType.EDGE
    ]
    if to_remove:
        # Cycle properties not propagated to the cells are not exported anyway, see
        # _write_FeatureDeclarations(), and _warn_cycle_props_left_out() names those
        # with values.
        cell_props = model.get_cell_lineage_properties()
        to_name = [name for name in to_remove if name in cell_props]
        for name in to_remove:
            try:
                model.remove_property(name)
            except ProtectedPropertyError:
                model.props_metadata._unprotect_prop(name)
                model.remove_property(name)
        if to_name:
            plural = len(to_name) > 1
            msg = (
                f"Ignoring propert{'ies' if plural else 'y'}: "
                f"{', '.join(to_name)}. {'They are' if plural else 'It is'} "
                f"not numeric and won't be supported by TrackMate."
            )
            logger.warning(msg)


def _rename_prop_to_feature(
    props_md: PropsMetadata, prop_id: str, feature: str
) -> None:
    """
    Rename a property to the TrackMate feature that it is written as.

    Parameters
    ----------
    props_md : PropsMetadata
        Properties metadata to modify.
    prop_id : str
        Identifier of the property to rename.
    feature : str
        Name of the TrackMate feature.

    Raises
    ------
    KeyError
        If the `prop_id` property is missing in the properties metadata.
    ValueError
        If another property already has the name of the feature.
    """
    if (
        feature != prop_id
        and prop_id in props_md.properties
        and feature in props_md.properties
    ):
        raise ValueError(
            f"The model has a '{feature}' property, but TrackMate's {feature} "
            f"feature is written from '{prop_id}'. Rename or remove '{feature}' to "
            "export the model to TrackMate."
        )
    props_md._change_prop_identifier(prop_id, feature)


def _rename_props(props_md: PropsMetadata, frame_prop: str) -> None:
    """
    Rename some properties in the properties metadata to match TrackMate requirements.

    Parameters
    ----------
    props_md : PropsMetadata
        Properties metadata to modify.
    frame_prop : str
        Name of the property corresponding to the frame/timepoint.

    Raises
    ------
    ValueError
        If the model already has a ``TRACK_ID`` property, or a ``FRAME`` property
        other than `frame_prop`.
    """
    props_md._unprotect_prop("lineage_id")
    _rename_prop_to_feature(props_md, "lineage_id", "TRACK_ID")
    props_md._change_prop_description("TRACK_ID", "Track ID")

    if frame_prop != "FRAME":
        props_md._unprotect_prop(frame_prop)
        _rename_prop_to_feature(props_md, frame_prop, "FRAME")


def _remove_props(props_md: PropsMetadata) -> None:
    """
    Remove some properties from the properties metadata.

    Parameters
    ----------
    props_md : PropsMetadata
        Properties metadata to modify.

    Notes
    -----
    While TrackMate has these features (maybe under a different name but in that
    case renaming comes later), they are absent from the FeatureDeclarations tag
    in the TrackMate XML file.
    """
    props_md._unprotect_prop("cell_id")
    props_md._remove_prop("cell_id")
    if props_md._has_prop("timepoint"):
        # If no frame-like properties were found in _rename_props(), the timepoint
        # property is used and renamed to FRAME. So no need to remove it in this case.
        props_md._unprotect_prop("timepoint")
        props_md._remove_prop("timepoint")
    for prop in ["cell_name", "lineage_name", "FilteredTrack", "cell_contour"]:
        try:
            props_md._remove_prop(prop)
        except KeyError:
            # Classic TrackMate property but not mandatory.
            pass


def _add_mandatory_props(props_md: PropsMetadata) -> None:
    """
    Add mandatory properties to the properties metadata.

    This is necessary because TrackMate requires some features to be present
    in the model, even if they are not used in Pycellin.

    Parameters
    ----------
    props_md : PropsMetadata
        Properties metadata to modify.
    """
    if not props_md._has_prop("SPOT_SOURCE_ID"):
        source_prop = Property(
            identifier="SPOT_SOURCE_ID",
            name="SPOT_SOURCE_ID",
            description="Source spot ID",
            provenance="TrackMate",
            prop_type="edge",
            lineage_type="cell",
            dtype="int",
            unit="NONE",
        )
        props_md._add_prop(source_prop)
    if not props_md._has_prop("SPOT_TARGET_ID"):
        target_prop = Property(
            identifier="SPOT_TARGET_ID",
            name="SPOT_TARGET_ID",
            description="Target spot ID",
            provenance="TrackMate",
            prop_type="edge",
            lineage_type="cell",
            dtype="int",
            unit="NONE",
        )
        props_md._add_prop(target_prop)
    if not props_md._has_prop("VISIBILITY"):
        visibility_prop = Property(
            identifier="VISIBILITY",
            name="VISIBILITY",
            description="Visibility",
            provenance="TrackMate",
            prop_type="node",
            lineage_type="cell",
            dtype="int",
            unit="NONE",
        )
        props_md._add_prop(visibility_prop)
    # Spots without them get one in _add_missing_time_and_quality().
    if not props_md._has_prop("POSITION_T"):
        time_prop = Property(
            identifier="POSITION_T",
            name="T",
            description="Time of the spot",
            provenance="TrackMate",
            prop_type="node",
            lineage_type="cell",
            dtype="float",
        )
        props_md._add_prop(time_prop)
    if not props_md._has_prop("QUALITY"):
        quality_prop = Property(
            identifier="QUALITY",
            name="Quality",
            description="Quality of the detection, -1 for spots added by hand",
            provenance="TrackMate",
            prop_type="node",
            lineage_type="cell",
            dtype="float",
        )
        props_md._add_prop(quality_prop)


def _update_location_props(props_md: PropsMetadata) -> None:
    """
    Update location properties in the metadata to match TrackMate requirements.

    This function renames the ``cell_x``, ``cell_y``, ``cell_z``, ``link_x``,
    ``link_y``, ``link_z``, ``lineage_x``, ``lineage_y``, and ``lineage_z``
    properties to their TrackMate matching features. A missing ``cell_z`` property
    gets a ``POSITION_Z`` declaration instead, since the spots are then written with
    a ``POSITION_Z`` of 0.

    Parameters
    ----------
    props_md : PropsMetadata
        Properties metadata to modify.

    Raises
    ------
    KeyError
        If the ``cell_x`` or ``cell_y`` property is missing in the properties
        metadata.
    ValueError
        If a property already has the name of the TrackMate feature that a location
        property is written as, e.g. ``POSITION_X`` for ``cell_x``, or if there is
        a ``POSITION_Z`` property but no ``cell_z``.
    """
    for axis in ["x", "y", "z"]:
        try:
            _rename_prop_to_feature(
                props_md, f"cell_{axis}", f"POSITION_{axis.upper()}"
            )
        except KeyError:
            # This property is mandatory in TrackMate for x, y and z dimensions.
            if axis in ["x", "y"]:
                raise KeyError(
                    f"Missing property: cell_{axis}. Cannot build TrackMate "
                    f"feature POSITION_{axis.upper()}."
                )
            else:
                # Without cell_z, the spots are written with a POSITION_Z of 0, which
                # would replace the values of a POSITION_Z property.
                if "POSITION_Z" in props_md.properties:
                    raise ValueError(
                        "The model has a 'POSITION_Z' property, but TrackMate's "
                        "POSITION_Z feature is written from 'cell_z', or as 0 without "
                        "it. If 'POSITION_Z' holds the z coordinates of the cells, "
                        "rename it to 'cell_z'. Otherwise, rename or remove it to "
                        "export the model to TrackMate."
                    )
                # We add the missing z dimension.
                props_md._add_prop(
                    Property(
                        identifier=f"POSITION_{axis.upper()}",
                        name=f"POSITION_{axis.upper()}",
                        description=f"Cell {axis.upper()} coordinate",
                        provenance="TrackMate",
                        prop_type="node",
                        lineage_type="cell",
                        dtype="float",
                        unit="pixel",
                    )
                )
        try:
            _rename_prop_to_feature(
                props_md, f"link_{axis}", f"EDGE_{axis.upper()}_LOCATION"
            )
        except KeyError:
            pass  # not mandatory
        try:
            _rename_prop_to_feature(
                props_md, f"lineage_{axis}", f"TRACK_{axis.upper()}_LOCATION"
            )
        except KeyError:
            pass  # not mandatory


def _update_props_metadata(model: Model, frame_prop: str) -> None:
    """
    Update the properties metadata in the model to match TrackMate requirements.

    Parameters
    ----------
    model : Model
        Model whose metadata to update.
    frame_prop : str
        Name of the property corresponding to the frame/timepoint.

    Raises
    ------
    KeyError
        If the ``cell_x`` or ``cell_y`` property is missing in the properties
        metadata.
    ValueError
        If a property already has the name of the TrackMate feature that another
        property is written as, e.g. ``TRACK_ID`` for ``lineage_id``, or if there is
        a ``POSITION_Z`` property but no ``cell_z``.
    """
    _rename_props(model.props_metadata, frame_prop)
    _remove_props(model.props_metadata)
    # TRACK_ID comes from lineage_id which is stored both as a node property
    # and a lineage property. TrackMate only needs it on the lineages so we update
    # the property type.
    model.props_metadata.properties["TRACK_ID"].prop_type = PropertyType.LINEAGE
    _add_mandatory_props(model.props_metadata)
    _update_location_props(model.props_metadata)


def _add_radius_prop(model: Model) -> None:
    """
    Add a radius property to the model if it does not exist.

    This is necessary because TrackMate requires a radius feature for the spots
    in order to be able to draw them as circles.
    If the radius property is not present, we add it with a default value of 1.0
    for all nodes.

    Parameters
    ----------
    model : Model
        Model to modify.

    Raises
    ------
    ValueError
        If the model has a ``RADIUS`` property besides the radius property found
        first, e.g. ``radius``.
    """
    # Check if there is already a radius property in the registered properties.
    props = model.get_properties()
    radius_prop_name = None
    for prop_name, prop in props.items():
        if prop_name.lower() == "radius" and prop.prop_type == PropertyType.NODE:
            radius_prop_name = prop_name
            break

    # If yes, rename it to RADIUS if necessary, in both metadata and data.
    if radius_prop_name is not None:
        if radius_prop_name != "RADIUS":
            _rename_prop_to_feature(model.props_metadata, radius_prop_name, "RADIUS")
            for lin in model.data.cell_lineages.values():
                _update_node_prop_key(
                    lin,
                    old_key=radius_prop_name,
                    new_key="RADIUS",
                    set_default_if_missing=True,
                    default_value=1.0,
                )
    else:
        # If not, create the RADIUS property in the metadata.
        radius_prop = Property(
            identifier="RADIUS",
            name="Radius",
            description="Radius",
            provenance="TrackMate",
            prop_type="node",
            lineage_type="cell",
            dtype="float",
            unit=model.get_space_unit(),
        )
        model.props_metadata._add_prop(radius_prop)

    # Ensure all nodes have the RADIUS property set to 1.0 if missing.
    for lin in model.data.cell_lineages.values():
        for node in lin.nodes():
            if "RADIUS" not in lin.nodes[node]:
                lin.nodes[node]["RADIUS"] = 1.0


def _relabel_nodes(model: Model) -> dict[int, dict[int, int]]:
    """
    Relabel the nodes and return the mapping of old to new node IDs of each lineage.

    This is necessary because TrackMate requires unique spot IDs across all lineages.
    If the model has non-unique node IDs, we relabel them in place to ensure uniqueness.

    Parameters
    ----------
    model : Model
        Model whose nodes to relabel.

    Returns
    -------
    dict[int, dict[int, int]]
        A mapping of old node IDs to new node IDs for each lineage.
        The outer dictionary keys are the lineage IDs, and the inner dictionaries
        map old node IDs to new node IDs. It is empty if the node IDs are already
        unique.

    Notes
    -----
    A warning is logged if duplicate node IDs are found, in which case all nodes
    will be relabeled to ensure uniqueness. The previous IDs are kept in the
    ``pycellin_cell_id`` property.
    """
    # Count the occurrences of each node ID in the data.
    count_ids: Counter[int] = Counter()
    for lin in model.data.cell_lineages.values():
        count_ids.update(list(lin.nodes()))
    dupes = [item for item, count in count_ids.items() if count > 1]

    if not dupes:
        # All node IDs are unique, no need to relabel.
        return {}

    # Relabel the nodes.
    full_mapping: dict[int, dict[int, int]] = {}  # {lin_id: {old_node_id: new_node_id}}
    new_id = 0
    logger.debug(f"Duplicate node IDs found: {dupes}")
    logger.warning(
        "Relabeling nodes to ensure unique IDs across all lineages export. "
        "Previous IDs are preserved in 'pycellin_cell_id' for reference."
    )
    for lin_id, lin in model.data.cell_lineages.items():
        mapping: dict[int, int] = {}  # {old_node_id: new_node_id}
        full_mapping[lin_id] = mapping
        for node in lin.nodes():
            mapping[node] = new_id
            new_id += 1
        _relabel_nodes_in_place(lin, mapping)

        # The relabeling must be propagated to the cell_id property.
        for node in lin.nodes():
            lin.nodes[node]["pycellin_cell_id"] = lin.nodes[node]["cell_id"]
            lin.nodes[node]["cell_id"] = node

        # SPOT_SOURCE_ID and SPOT_TARGET_ID are updated / created later
        # in _update_edges().

    # Manual update of the specific node property cell_name
    # when it has a TrackMate syntax: "ID{cell_name}"".
    if model.has_property("cell_name"):
        for lin_id, lin in model.data.cell_lineages.items():
            for node in lin.nodes():
                if "cell_name" in lin.nodes[node]:
                    old_id = lin.nodes[node]["pycellin_cell_id"]
                    new_id = lin.nodes[node]["cell_id"]
                    if lin.nodes[node]["cell_name"] == f"ID{old_id}":
                        lin.nodes[node]["cell_name"] = f"ID{new_id}"

    # Update of the model in case some other properties refer
    # to the node IDs (for example cycle_ids).
    prop = Property(
        identifier="pycellin_cell_id",
        name="Pycellin cell ID",
        description="Original cell ID before relabeling for TrackMate export",
        provenance="Pycellin",
        prop_type="node",
        lineage_type="cell",
        dtype="int",
    )
    model.props_metadata._add_prop(prop)
    model.prepare_full_data_update()
    model.update()

    return full_mapping


def _prepare_model_for_export(
    model: Model,
    propagate: bool,
) -> None:
    """
    Prepare a Pycellin model for export to TrackMate format.

    This function updates the model to match TrackMate requirements
    and removes non-numeric properties that TrackMate cannot handle.

    Parameters
    ----------
    model : Model
        Model to prepare for export.
    propagate : bool
        Whether to propagate the cycle properties before preparing the model.

    Raises
    ------
    KeyError
        If neither a frame-like property nor ``timepoint`` is present on all nodes.
        If the ``cell_x`` or ``cell_y`` property is missing.
    ValueError
        If `propagate` is True and the model has no cycle lineages.
        If a property already has the name of the TrackMate feature that another
        property is written as, e.g. ``TRACK_ID`` for ``lineage_id``, or if there is
        a ``POSITION_Z`` property but no ``cell_z``.
    """
    # TrackMate needs unique spot IDs across all lineages.
    id_mapping = _relabel_nodes(model)
    if propagate:
        model.propagate_cycle_properties()
    _warn_cycle_props_left_out(model)

    frame_prop = _identify_frame_prop(model)
    _add_radius_prop(model)
    _update_props_metadata(model, frame_prop)
    _update_model_data(model, frame_prop, id_mapping)
    _remove_non_numeric_props(model)


def _write_Settings(
    xf: ET.xmlfile,
    model: Model,
    image_path: str | Path | None = None,
    image_path_field: str | None = None,
    image_shape: tuple[int, int, int, int, int] | None = None,
    image_shape_field: str | None = None,
) -> None:
    """
    Write the Settings XML tag into a TrackMate XML file.

    The settings of a TrackMate file, kept in the model metadata when the model was
    loaded from it, are written as they are: the image parameters are then ignored.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    model : Model
        Model containing the data to write.
    image_path : str | Path | None, default=None
        Path to the image file associated with the model.
        If provided, will be used instead of `image_path_field`.
    image_path_field : str | None, default=None
        Name of the model metadata field that contains the image path.
        Not needed if `image_path` is provided.
    image_shape : tuple[int, int, int, int, int] | None, default=None
        Shape of the image associated with the model, in the format (T, C, Z, Y, X).
        If provided, will be used instead of `image_shape_field`.
    image_shape_field : str | None, default=None
        Name of the model metadata field that contains the image shape.
        Not needed if `image_shape` is provided.
    """
    metadata = model.model_metadata.to_dict()
    if "Settings" in metadata:
        xml_element = ET.fromstring(metadata["Settings"])
        xf.write(xml_element)
        return

    if image_path is None:
        if image_path_field is None:
            image_path = ""
        else:
            image_path = metadata.get(image_path_field, "")
    if not image_path:
        filename = ""
        folder = ""
    else:
        filename = str(Path(image_path).name)
        folder = str(Path(image_path).parent)

    if image_shape is None:
        if image_shape_field is None:
            image_shape = (0, 0, 0, 0, 0)
        else:
            image_shape = metadata.get(image_shape_field, (0, 0, 0, 0, 0))
    if not image_shape:
        n_frames = "0"  # T
        # TrackMate doesn't need the number of channels.
        n_slices = "0"  # Z
        height = "0"  # Y
        width = "0"  # X
    else:
        n_frames = str(image_shape[0])
        n_slices = str(image_shape[2])
        height = str(image_shape[3])
        width = str(image_shape[4])

    with xf.element("Settings"):
        xf.write("\n    ")
        img_data = ET.Element(
            "ImageData",
            {
                "filename": filename,
                "folder": folder,
                "width": width,
                "height": height,
                "nslices": n_slices,
                "nframes": n_frames,
                "pixelwidth": str(metadata.get("pixel_width", 1.0) or 1.0),
                "pixelheight": str(metadata.get("pixel_height", 1.0) or 1.0),
                "voxeldepth": str(metadata.get("pixel_depth", 1.0) or 1.0),
                "timeinterval": str(_get_time_interval(model)),
            },
        )
        xf.write(img_data)
        xf.write("\n    ")
        xf.write(ET.Element("InitialSpotFilter"))
        xf.write("\n    ")
        xf.write(ET.Element("SpotFilterCollection"))
        xf.write("\n    ")
        xf.write(ET.Element("TrackerSettings", {"TRACKER_NAME": "MANUAL_TRACKER"}))
        xf.write("\n    ")
        xf.write(ET.Element("TrackFilterCollection"))
        xf.write("\n  ")


def _write_metadata_tag(
    xf: ET.xmlfile,
    metadata: dict[str, Any],
    tag: str,
) -> None:
    """
    Write the specified XML tag into a TrackMate XML file.

    If the tag is not present in the metadata, an empty tag will be
    written.

    Parameters
    ----------
    xf : ET.xmlfile
        Context manager for the XML file to write.
    metadata : dict[str, Any]
        Dictionary that may contain the metadata to write.
    tag : str
        XML tag to write.
    """
    if tag in metadata:
        xml_element = ET.fromstring(metadata[tag])
        xf.write(xml_element)
    else:
        xf.write(ET.Element(tag))


def _get_trackmate_unit(
    unit: str | None, model_unit: str | None, dimension: str, default: str
) -> str:
    """
    Return the unit to write in the TrackMate file for one dimension.

    Parameters
    ----------
    unit : str | None
        Unit given by the user, used if not None.
    model_unit : str | None
        Unit of the model, used if `unit` is None.
    dimension : str
        ``"space"`` or ``"time"``, for the warning.
    default : str
        Unit used, with a warning, if neither `unit` nor `model_unit` is given.

    Returns
    -------
    str
        The unit to write.

    Warns
    -----
    PycellinWarning
        If neither `unit` nor `model_unit` is given, so that `default` is written.
    """
    if unit is not None:
        return unit
    if model_unit:
        return model_unit
    warnings.warn(
        f"The model has no {dimension} unit: writing '{default}' as the TrackMate "
        f"{dimension} unit. Give `{dimension}_unit` to choose it.",
        PycellinWarning,
        stacklevel=_find_stack_level(),
    )
    return default


def write_trackmate_xml(
    model: Model,
    path: str | Path,
    *,
    space_unit: str | None = None,
    time_unit: str | None = None,
    image_path: str | Path | None = None,
    image_path_field: str | None = None,
    image_shape: tuple[int, int, int, int, int] | None = None,
    image_shape_field: str | None = None,
    propagate_cycle_props: bool = False,
) -> None:
    """
    Write an XML file readable by TrackMate from a Pycellin model.

    The model is not modified: the export works on a copy.

    Parameters
    ----------
    model : Model
        The Pycellin model containing the data to write.
    path : str | Path
        Path of the XML file to write.
    space_unit : str | None, default=None
        Spatial unit of the TrackMate model, e.g. ``"µm"``. If None, the space unit
        of the model is used, or ``"pixel"``, with a warning, if the model has none.
    time_unit : str | None, default=None
        Temporal unit of the TrackMate model, e.g. ``"min"``. If None, the time unit
        of the model is used, or ``"frame"``, with a warning, if the model has none.
    image_path : str | Path | None, default=None
        Path to the image file associated with the model.
        If provided, will be used instead of `image_path_field`.
    image_path_field : str | None, default=None
        Name of the model metadata field that contains the image path.
        Not needed if `image_path` is provided.
    image_shape : tuple[int, int, int, int, int] | None, default=None
        Shape of the image associated with the model, in the format (T, C, Z, Y, X).
        If provided, will be used instead of `image_shape_field`.
        Not needed to open the XML in TrackMate, but useful for MATLAB scripting
        and the like.
    image_shape_field : str | None, default=None
        Name of the model metadata field that contains the image shape.
        Not needed if `image_shape` is provided. Not needed to open the XML in
        TrackMate, but useful for MATLAB scripting and the like.
    propagate_cycle_props : bool, default=False
        If True, cycle properties will be propagated to cell lineages before export.
        Useful if you want to export the cycle properties to TrackMate
        and have them accessible in the tracks. If False, cycle properties are not
        exported, since TrackMate has no cycle lineages, and a warning names them.

    Raises
    ------
    UpdateRequiredError
        If the model requires an update.
    KeyError
        If the model has no ``cell_x`` or ``cell_y`` property.
    ValueError
        If `propagate_cycle_props` is True and the model has no cycle lineages.
        If the model has a property with the name of a TrackMate feature that
        Pycellin writes from another property, e.g. ``TRACK_ID``, written from
        ``lineage_id``, or ``POSITION_Z``, written from ``cell_z`` (as 0 without
        it).
        If only some cells have a frame and their frames can't be deduced, see Notes.

    Warns
    -----
    PycellinWarning
        If the model has no space or time unit and none is given, see `space_unit`
        and `time_unit`.
        If cycle properties are left out, see `propagate_cycle_props`.
        If some cells have no ``cell_x`` or ``cell_y`` value: they are written at 0.
        If cells, links or lineages have attributes without a property declaration:
        these attributes are not exported.

    Warnings
    --------
    Quantitative analysis of cell cycle properties should not be done on cell
    lineages after propagation of cycle properties, UNLESS you account for the
    number of cells in each cell cycle (``cycle_num_cells``). Otherwise you will
    introduce a bias in your quantification.
    Indeed, after propagation, cycle properties (like interdivision time) become
    over-represented in long cell cycles since these properties are propagated on each
    node of the cell cycle in cell lineages, whereas they are stored only once
    per cell cycle on the cycle node in cycle lineages.

    Notes
    -----
    TrackMate has a single spatial unit and a single temporal unit for all its
    features, while each Pycellin property has its own unit. The values are written
    as they are, without conversion: check that the units of the properties match
    `space_unit` and `time_unit`, e.g. with `Model.get_properties_per_unit()`.

    The image parameters are ignored when the model has the settings of a TrackMate
    file, e.g. when it was loaded with `read_trackmate_xml`: these settings are
    written as they are.

    TrackMate only supports numeric features. Non-numeric properties (strings,
    lists, polygons...) are not exported, except TrackMate's own properties and
    ``name`` on cells or lineages, written as the display name of spots or tracks
    that have no ``cell_name`` or ``lineage_name``. Boolean properties are exported
    as integers (1 for True, 0 for False).
    Attributes of cells, links and lineages without a property declaration are not
    exported either, and a warning names them.
    For example, a location tag added by `Model.add_location_tag` with `tag_names`
    holds strings and is not exported: add it without `tag_names` to keep the
    integer tags.

    The ``FRAME`` of the spots comes from the frame property of the model, a node
    property called ``frame`` in any case, e.g. TrackMate's ``FRAME``. Cells without
    frame, e.g. added with `Model.add_cell`, get their timepoint plus the difference
    between frame and timepoint of the other cells, which must be the same for all of
    them. Without frame property, the frames are the timepoints, which start at 0 at
    the earliest cell.

    TrackMate computes features such as the duration and speed of tracks from the
    ``POSITION_T`` of the spots, and their mean quality from ``QUALITY``, e.g. after
    an edit in TrackScheme. Spots without them, e.g. from a model read with
    `read_ctc` or `from_trackpy`, get the time of their frame, ``FRAME`` times the
    time interval of the file, and a quality of -1, as TrackMate gives spots added by
    hand.

    The messages about what TrackMate can't store, e.g. properties left out because
    they are not numeric, are logged with the `logging` module, while the problems
    that the arguments or the model can avoid are issued as
    `~pycellin.exceptions.PycellinWarning`.
    """
    _check_up_to_date(model)
    # We don't want to modify the original model.
    model_copy = copy.deepcopy(model)

    tm_units = {
        "spatialunits": _get_trackmate_unit(
            space_unit, model_copy.get_space_unit(), "space", "pixel"
        ),
        "timeunits": _get_trackmate_unit(
            time_unit, model_copy.get_time_unit(), "time", "frame"
        ),
    }
    if hasattr(model_copy.model_metadata, "trackmate_version"):
        tm_version = model_copy.model_metadata.trackmate_version
    else:
        tm_version = "unknown"
    has_FilteredTrack = model_copy.has_property("FilteredTrack")
    _prepare_model_for_export(model_copy, propagate_cycle_props)
    exported_keys = _get_exported_keys(model_copy)

    with ET.xmlfile(path, encoding="utf-8", close=True) as xf:
        xf.write_declaration()
        with xf.element("TrackMate", {"version": tm_version}):
            xf.write("\n  ")
            _write_metadata_tag(xf, model_copy.model_metadata.to_dict(), "Log")
            xf.write("\n  ")
            with xf.element("Model", tm_units):
                _write_FeatureDeclarations(xf, model_copy)
                _write_AllSpots(
                    xf, model_copy.data.cell_lineages, exported_keys["node"]
                )
                _write_AllTracks(
                    xf,
                    model_copy.data.cell_lineages,
                    exported_keys["lineage"],
                    exported_keys["edge"],
                )
                _write_FilteredTracks(
                    xf, model_copy.data.cell_lineages, has_FilteredTrack
                )
            xf.write("\n  ")
            _write_Settings(
                xf,
                model_copy,
                image_path,
                image_path_field,
                image_shape,
                image_shape_field,
            )

            xf.write("\n  ")
            for tag in ["GUIState", "DisplaySettings"]:
                _write_metadata_tag(xf, model_copy.model_metadata.to_dict(), tag)
                if tag == "DisplaySettings":
                    xf.write("\n")
                else:
                    xf.write("\n  ")


if __name__ == "__main__":
    """
    Quick demo with sample data.
    """
    import tempfile

    from pycellin.io.geff.reader import read_geff

    geff_in = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Ecoli_growth_on_agar_pad.geff"
    )
    model = read_geff(
        geff_in,
        lineage_id_prop="lineage_id",
        cell_id_prop="cell_id",
        reference_time_prop="POSITION_T",
    )

    print(model)
    print("Model metadata:")
    print(model.model_metadata)

    with tempfile.TemporaryDirectory() as tmp_dir:
        xml_out = Path(tmp_dir) / "output.xml"
        write_trackmate_xml(model, xml_out)
