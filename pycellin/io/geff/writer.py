#!/usr/bin/env python3

"""
Writer for GEFF files.

References
----------
- geff GitHub: https://github.com/live-image-tracking-tools/geff
- geff Documentation: https://live-image-tracking-tools.github.io/geff/latest/
"""

import copy
import logging
from pathlib import Path
from typing import Literal

import geff
import geff_spec
import networkx as nx

from pycellin.classes import CellLineage, Model, Property
from pycellin.custom_types import PropertyType
from pycellin.exceptions import ProtectedPropertyError
from pycellin.io.utils import _check_up_to_date, _remove_orphaned_metadata
from pycellin.utils import _normalize_dtype

logger = logging.getLogger(__name__)

#: Cell property that holds the tracklet IDs written by write_geff(tracklets=True).
_TRACKLET_PROP = "tracklet_id"

# TODO: geffception for cycle and lineage props


def _find_node_overlaps(lineages: list[CellLineage]) -> dict[int, list[int]]:
    """
    Find overlapping node IDs across lineages.

    Parameters
    ----------
    lineages : list[CellLineage]
        List of lineage graphs.

    Returns
    -------
    dict[int, list[int]]
        A dictionary mapping the node IDs found in several lineages to the list of
        indices of these lineages.
    """
    node_to_lineages: dict[int, int] = {}
    overlaps: dict[int, list[int]] = {}

    for lin_index, lin in enumerate(lineages):
        for nid in lin.nodes:
            if nid in node_to_lineages:  # overlap found
                if nid not in overlaps:
                    overlaps[nid] = [node_to_lineages[nid], lin_index]
                else:
                    overlaps[nid].append(lin_index)
            else:
                node_to_lineages[nid] = lin_index

    return overlaps


def _get_next_available_id(lineages: list[CellLineage]) -> int:
    """
    Get the next available node ID across all lineages.

    Parameters
    ----------
    lineages : list[CellLineage]
        List of lineage graphs to check.

    Returns
    -------
    int
        The next available node ID.
    """
    if not lineages:
        return 0

    max_node_id = -1
    for lineage in lineages:
        if lineage.nodes:
            lineage_max = max(lineage.nodes)
            max_node_id = max(max_node_id, lineage_max)

    return max_node_id + 1


def _relabel_nodes(
    lineages: list[CellLineage],
    overlaps: dict[int, list[int]],
) -> None:
    """
    Relabel nodes in each lineage to ensure unique IDs across all lineages.

    The ``cell_id`` of a relabeled node is its new ID.

    Parameters
    ----------
    lineages : list[CellLineage]
        List of lineage graphs to relabel in place.
    overlaps : dict[int, list[int]]
        Dictionary mapping overlapping node IDs to the list of lineage indices they
        belong to.
    """
    next_available_id = _get_next_available_id(lineages)
    for nid, lids in sorted(overlaps.items()):
        for lid in lids[1:]:
            mapping = {nid: next_available_id}
            nx.relabel_nodes(lineages[lid], mapping, copy=False)
            node_data = lineages[lid].nodes[next_available_id]
            if "cell_id" in node_data:
                node_data["cell_id"] = next_available_id
            next_available_id += 1


def _solve_node_overlaps(lineages: list[CellLineage]) -> bool:
    """
    Detect and resolve overlapping node IDs across lineages by reassigning unique IDs.

    When some IDs change, every node keeps its previous ID in a ``pycellin_cell_id``
    attribute, as for a TrackMate export.

    Parameters
    ----------
    lineages : list[CellLineage]
        List of lineage graphs to check and modify in place.

    Returns
    -------
    bool
        True if some node IDs changed, False otherwise.
    """
    overlaps = _find_node_overlaps(lineages)
    if not overlaps:
        return False
    for lineage in lineages:
        for node, data in lineage.nodes(data=True):
            data["pycellin_cell_id"] = node
    _relabel_nodes(lineages, overlaps)
    return True


def _create_previous_id_property() -> Property:
    """
    Create the declaration of the ``pycellin_cell_id`` cell property.

    Returns
    -------
    Property
        Declaration of the ``pycellin_cell_id`` property, which holds the IDs of the
        cells in the model when the export has to change some of them.
    """
    return Property(
        identifier="pycellin_cell_id",
        name="Pycellin cell ID",
        description="Original cell ID before relabeling for GEFF export",
        provenance="Pycellin",
        prop_type="node",
        lineage_type="cell",
        dtype="int",
    )


def _to_geff_dtype(dtype: str) -> str:
    """
    Return the GEFF spelling of a property data type.

    Parameters
    ----------
    dtype : str
        Data type of a Pycellin property.

    Returns
    -------
    str
        ``"str"`` for strings, since GEFF spells the string data type ``"str"``,
        else `dtype` unchanged.
    """
    if _normalize_dtype(dtype) == "string":
        return "str"
    return dtype


def _remove_unsupported_props(model: Model) -> None:
    """
    Remove the cell and link properties whose data type GEFF cannot store.

    GEFF stores booleans, numbers and strings, as single values or as
    variable-length arrays (e.g. cell contours), but not data types such as
    ``list[int]`` or shapely geometries. Lineage properties are not checked, since
    they are not exported.

    Parameters
    ----------
    model : Model
        Model to modify.

    Notes
    -----
    A warning is logged if some properties have a data type that GEFF cannot store.
    They are removed from the model and won't be exported.
    """
    unsupported = {}
    for prop_id, prop in model.get_cell_lineage_properties().items():
        if not prop.prop_type & (PropertyType.NODE | PropertyType.EDGE):
            continue
        try:
            geff_spec.PropMetadata(identifier=prop_id, dtype=_to_geff_dtype(prop.dtype))
        except ValueError:  # pydantic's ValidationError is a ValueError.
            unsupported[prop_id] = prop.dtype
    if not unsupported:
        return

    for prop_id in unsupported:
        try:
            model.remove_property(prop_id)
        except ProtectedPropertyError:
            model.props_metadata._unprotect_prop(prop_id)
            model.remove_property(prop_id)
    props_str = ", ".join(
        f"'{prop_id}' (dtype '{dtype}')" for prop_id, dtype in unsupported.items()
    )
    logger.warning(
        f"Ignoring propert{'ies' if len(unsupported) > 1 else 'y'} with a data type "
        f"that GEFF cannot store: {props_str}."
    )


def _remove_none_values(model: Model) -> None:
    """
    Remove the None values of cell and link properties.

    GEFF has no None value: geff writes a key absent from a cell or a link as a
    missing value, but fails on a None value.

    Parameters
    ----------
    model : Model
        Model to modify.
    """
    for lineage in model.data.cell_lineages.values():
        attrs_dicts = [attrs for _, attrs in lineage.nodes(data=True)]
        attrs_dicts += [attrs for _, _, attrs in lineage.edges(data=True)]
        for attrs in attrs_dicts:
            for key in [key for key, value in attrs.items() if value is None]:
                del attrs[key]


def _create_tracklet_property() -> Property:
    """
    Create the declaration of the cell property that holds the tracklet IDs.

    Returns
    -------
    Property
        Declaration of the ``tracklet_id`` property.
    """
    return Property(
        identifier=_TRACKLET_PROP,
        name="Tracklet ID",
        description=(
            "Identifier of the tracklet of the cell, i.e. of its cell cycle: "
            "ID of the last cell of the tracklet"
        ),
        provenance="Pycellin",
        prop_type="node",
        lineage_type="cell",
        dtype="int",
    )


def _get_tracklet_ids(lineage: CellLineage) -> dict[int, int]:
    """
    Return the tracklet ID of each cell of a lineage.

    GEFF defines a tracklet as a maximal path whose links each join a cell with
    a single child to a cell with a single parent. Without fusions, the tracklets
    are the cell cycles; with a fusion, a new tracklet starts at the merged cell.
    A tracklet is identified by the ID of its last cell, as a cell cycle is by
    its ``cycle_id``.

    Parameters
    ----------
    lineage : CellLineage
        The lineage whose tracklets to identify.

    Returns
    -------
    dict[int, int]
        The tracklet ID of each cell, by cell ID.
    """
    tracklet_ids = {}
    for cid in lineage.nodes:
        parents = list(lineage.predecessors(cid))
        if len(parents) == 1 and lineage.out_degree(parents[0]) == 1:
            continue  # The cell extends the tracklet of its parent.
        tracklet = [cid]
        while lineage.out_degree(tracklet[-1]) == 1:
            child = next(iter(lineage.successors(tracklet[-1])))
            if lineage.in_degree(child) != 1:
                break
            tracklet.append(child)
        for cell in tracklet:
            tracklet_ids[cell] = tracklet[-1]
    return tracklet_ids


def _add_tracklet_ids(model: Model) -> None:
    """
    Write the tracklet ID of each cell in the ``tracklet_id`` cell property.

    Tracklet IDs are cell IDs, so they are unique across lineages only once the
    node overlaps are solved. An existing ``tracklet_id`` property is replaced.

    Parameters
    ----------
    model : Model
        Model to modify, with cell IDs unique across lineages.

    Notes
    -----
    A warning is logged if some cells already had a ``tracklet_id`` value that
    differs from their tracklet ID.
    """
    num_changed = 0
    for lineage in model.data.cell_lineages.values():
        for cid, tracklet_id in _get_tracklet_ids(lineage).items():
            attrs = lineage.nodes[cid]
            if _TRACKLET_PROP in attrs and attrs[_TRACKLET_PROP] != tracklet_id:
                num_changed += 1
            attrs[_TRACKLET_PROP] = tracklet_id
    model.props_metadata.properties[_TRACKLET_PROP] = _create_tracklet_property()
    if num_changed:
        logger.warning(
            "With tracklets=True, the GEFF file has the tracklet IDs computed at "
            f"export, which differ from the '{_TRACKLET_PROP}' values of "
            f"{num_changed} cell{'s' if num_changed > 1 else ''} of the model."
        )


def _get_default_space_axes(model: Model) -> list[str]:
    """
    Return the coordinate properties to export as space axes by default.

    These are ``cell_x`` and ``cell_y``, plus ``cell_z`` when it is declared. GEFF
    doesn't allow missing values on axes, so a coordinate is only exported as an
    axis when every cell has a value for it: without complete ``cell_x`` and
    ``cell_y``, no space axis is exported.

    Parameters
    ----------
    model : Model
        The model to export, without None values.

    Returns
    -------
    list[str]
        The coordinate properties, in x, y, z order.

    Notes
    -----
    A warning is logged if ``cell_x``, ``cell_y`` or ``cell_z`` is declared but some
    cells have no value for it, so that it can't be exported as an axis.
    """
    node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
    if "cell_x" not in node_props or "cell_y" not in node_props:
        return []
    declared = [key for key in ("cell_x", "cell_y", "cell_z") if key in node_props]
    cells = [
        attrs
        for lin in model.data.cell_lineages.values()
        for _, attrs in lin.nodes(data=True)
    ]
    incomplete = {
        key: count
        for key in declared
        if (count := sum(key not in attrs for attrs in cells)) > 0
    }
    if not incomplete:
        return declared
    counts_str = ", ".join(f"'{key}' ({count})" for key, count in incomplete.items())
    if "cell_x" in incomplete or "cell_y" in incomplete:
        space_axes = []
        consequence = "the GEFF file has no space axes"
    else:
        space_axes = ["cell_x", "cell_y"]
        consequence = "the GEFF file has no z axis"
    logger.warning(
        f"Some cells have no value for {counts_str}, so {consequence}: GEFF axes "
        "can't have missing values. Give these cells coordinates, or choose other "
        "properties with space_axes."
    )
    return space_axes


def _convert_coordinates_to_pixels(
    model: Model, space_axes: list[str]
) -> dict[str, tuple[float, str | None]]:
    """
    Convert the space axes of a model into pixels, where the pixel size is known.

    GEFF gives the pixel size as the scale of a space axis whose values are in
    pixels. The values of each space axis are divided by the pixel size of their
    coordinate (`pixel_width` for x, `pixel_height` for y, `pixel_depth` for z), when
    the model metadata gives it. The property then has the unit ``"pixel"`` and the
    data type ``"float"``.

    Parameters
    ----------
    model : Model
        The model to export, modified in place.
    space_axes : list[str]
        The properties of the x, y and optionally z coordinates, in that order.

    Returns
    -------
    dict[str, tuple[float, str | None]]
        ``{property: (pixel size, unit before the conversion)}`` for each converted
        property.
    """
    node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
    scales = {}
    size_fields = ("pixel_width", "pixel_height", "pixel_depth")
    for prop_id, size_field in zip(space_axes, size_fields):
        size = getattr(model.model_metadata, size_field)
        # An unknown property is reported by _build_axes().
        if size is None or prop_id not in node_props:
            continue
        for lin in model.data.cell_lineages.values():
            for _, attrs in lin.nodes(data=True):
                if prop_id in attrs:
                    attrs[prop_id] = attrs[prop_id] / size
        prop = node_props[prop_id]
        scales[prop_id] = (size, prop.unit)
        prop.unit = "pixel"
        prop.dtype = "float"
    return scales


def _build_axes(
    node_props: dict[str, Property],
    time_axes: list[str],
    space_axes: list[str] | None,
    channel_axes: list[str] | None,
    scales: dict[str, tuple[float, str | None]] | None = None,
) -> list[geff_spec.Axis]:
    """
    Build a list of ``geff_spec.Axis`` objects for GEFF metadata.

    The axes are ordered as in OME-Zarr: time, then channel, then space axes in reverse
    order (z, y, x).

    Parameters
    ----------
    node_props : dict[str, Property]
        Dictionary of node properties from the model, used to validate the axes.
    time_axes : list[str]
        List of property names that Geff will consider as time axes.
        These should be properties in the model that represent time (e.g.,
        ``timepoint``).
    space_axes : list[str] | None
        The properties of the x, y and optionally z coordinates, in that order
        (e.g., ``cell_x``, ``cell_y``, ``cell_z``). If None or empty, no spatial axes
        will be included in the GEFF metadata.
    channel_axes : list[str] | None
        List of property names that Geff will consider as channel axes.
        These should be properties in the model that represent different channels
        or modalities (e.g., ``chan_1``, ``chan_2``). If None, no channel axes will
        be included in the GEFF metadata.
    scales : dict[str, tuple[float, str | None]] | None, default=None
        The scale and scaled unit of the space axes in pixels, by property, as
        returned by ``_convert_coordinates_to_pixels()``. If None, no axis has a
        scale.

    Returns
    -------
    list[geff_spec.Axis]
        List of Geff Axis objects describing spatial and temporal dimensions.

    Raises
    ------
    ValueError
        If a time, channel or space axis is not a node property of the model.
    """
    axes = []
    for prop_name in time_axes:
        if prop_name not in node_props:
            raise ValueError(
                f"Unknown node property '{prop_name}', cannot be mapped to time axis."
            )
        axes.append(
            geff_spec.Axis(
                name=prop_name,
                type="time",
                unit=node_props[prop_name].unit,
            )
        )
    if channel_axes is not None:
        for prop_name in channel_axes:
            if prop_name not in node_props:
                raise ValueError(
                    f"Unknown node property '{prop_name}', cannot be mapped to "
                    "channel axis."
                )
            axes.append(
                geff_spec.Axis(
                    name=prop_name,
                    type="channel",
                )
            )
    if space_axes is not None:
        scales = scales or {}
        for prop_name in reversed(space_axes):
            if prop_name not in node_props:
                raise ValueError(
                    f"Unknown node property '{prop_name}', cannot be mapped to "
                    "space axis."
                )
            scale, scaled_unit = scales.get(prop_name, (None, None))
            axes.append(
                geff_spec.Axis(
                    name=prop_name,
                    type="space",
                    unit=node_props[prop_name].unit,
                    scale=scale,
                    scaled_unit=scaled_unit,
                )
            )
    return axes


def _build_display_hints(
    time_axis: str,
    space_axes: list[str] | None,
) -> geff_spec.DisplayHint | None:
    """
    Build display hints for GEFF metadata.

    Parameters
    ----------
    time_axis : str
        Name of the time axis.
    space_axes : list[str] | None
        List of space axis names in order of horizontal, vertical, and depth dimensions,
        i.e. x, y, z. If None or if fewer than 2 space axes are provided, no display
        hints will be set (cf Geff specification).

    Returns
    -------
    geff_spec.DisplayHint | None
        Geff display hints for spatial and temporal dimensions. Returns None if no
        valid display hints can be created.
    """
    if space_axes is None or len(space_axes) < 2:
        return None

    display_hints = geff_spec.DisplayHint(
        display_horizontal=space_axes[0],
        display_vertical=space_axes[1],
        display_depth=space_axes[2] if len(space_axes) > 2 else None,
        display_time=time_axis,
    )
    return display_hints


def _build_props_metadata(
    properties: dict[str, Property],
) -> tuple[dict[str, geff_spec.PropMetadata], dict[str, geff_spec.PropMetadata]]:
    """
    Build property metadata for GEFF from the properties of a Pycellin model.

    Parameters
    ----------
    properties : dict[str, Property]
        Dictionary of property identifiers to `Property` objects.

    Returns
    -------
    tuple[dict[str, geff_spec.PropMetadata], dict[str, geff_spec.PropMetadata]]
        A tuple containing two dictionaries:

        - node properties metadata
        - edge properties metadata
    """
    node_props_md: dict[str, geff_spec.PropMetadata] = {}
    edge_props_md: dict[str, geff_spec.PropMetadata] = {}

    for prop_id, prop in properties.items():
        prop_md = geff_spec.PropMetadata(
            identifier=prop_id,
            dtype=_to_geff_dtype(prop.dtype),
            unit=prop.unit,
            name=prop.name,
            description=prop.description,
        )

        # Lineage values are not exported yet (need geffception for lineage and cycle
        # props), but node and edge values of multi-type properties are.
        if prop.prop_type & PropertyType.NODE:
            node_props_md[prop_id] = prop_md
        if prop.prop_type & PropertyType.EDGE:
            edge_props_md[prop_id] = prop_md

    return node_props_md, edge_props_md


def _build_geff_metadata(
    model: Model,
    time_axes: str | list[str] | None = None,
    space_axes: list[str] | None = None,
    channel_axes: list[str] | None = None,
    tracklets: bool = False,
    scales: dict[str, tuple[float, str | None]] | None = None,
) -> geff.GeffMetadata:
    """
    Build GEFF metadata from a Pycellin model.

    Parameters
    ----------
    model : Model
        The Pycellin model to extract metadata from.
    time_axes : str | list[str] | None, default=None
        Property name or list of property names that Geff will consider as time
        axes. These should be properties in the model that represent time (e.g.,
        ``timepoint``).
        If None, the model's reference time property will be used as the only time axis.
        If a list is provided, the order of the property names in the list will
        determine the order of both the axes and display hint in the GEFF metadata.
        The time display hint will be set to the first time axis in the list.
    space_axes : list[str] | None, default=None
        The properties of the x, y and optionally z coordinates, in that order,
        that Geff will consider as space axes. If None, ``cell_x`` and ``cell_y``
        are used, plus ``cell_z`` when it is declared, as long as every cell has a
        value for them. An empty list exports no space axes. The space axes are
        written in OME-Zarr order (z, y, x), and the display hints are set to x
        (horizontal), y (vertical) and z (depth).
    channel_axes : list[str] | None, default=None
        List of property names that Geff will consider as channel axes.
        These should be properties in the model that represent different channels
        or modalities (e.g., ``chan_1``, ``chan_2``). If None, no channel axes will
        be included in the GEFF metadata.
    tracklets : bool, default=False
        Whether to declare the ``tracklet_id`` cell property as the GEFF tracklet
        property. The cells must already have it, see ``_add_tracklet_ids()``.
    scales : dict[str, tuple[float, str | None]] | None, default=None
        The scale and scaled unit of the space axes in pixels, by property, as
        returned by ``_convert_coordinates_to_pixels()``. If None, no axis has a
        scale.

    Returns
    -------
    geff.GeffMetadata
        The GEFF metadata object.

    Raises
    ------
    ValueError
        If a time, channel or space axis is not a node property of the model, or is
        given twice.
    """
    # Generic metadata.
    node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
    if time_axes is None:
        time_axes = [model.reference_time_prop]
    elif isinstance(time_axes, str):
        time_axes = [time_axes]
    if space_axes is None:
        space_axes = _get_default_space_axes(model)
    axes = _build_axes(
        node_props=node_props,
        time_axes=time_axes,
        space_axes=space_axes,
        channel_axes=channel_axes,
        scales=scales,
    )
    display_hints = _build_display_hints(
        time_axis=time_axes[0],
        space_axes=space_axes,
    )

    # Property metadata.
    props = model.get_cell_lineage_properties()
    node_props_md, edge_props_md = _build_props_metadata(props)

    # Identifiers of lineages and tracklets.
    track_node_props = {"lineage": "lineage_id"}
    if tracklets:
        track_node_props["tracklet"] = _TRACKLET_PROP

    return geff.GeffMetadata(
        directed=True,
        axes=axes,
        display_hints=display_hints,
        track_node_props=track_node_props,
        node_props_metadata=node_props_md,
        edge_props_metadata=edge_props_md,
    )


def write_geff(
    model: Model,
    path: str | Path,
    *,
    time_axes: str | list[str] | None = None,
    space_axes: list[str] | None = None,
    channel_axes: list[str] | None = None,
    tracklets: bool = False,
    propagate_cycle_props: bool = False,
    zarr_format: Literal[2, 3] = 2,
) -> None:
    """
    Export a Pycellin model to GEFF format.

    The model is not modified: the export works on a copy.

    Parameters
    ----------
    model : Model
        The Pycellin model to export.
    path : str | Path
        Path to the output GEFF file.
    time_axes : str | list[str] | None, default=None
        Property name or list of property names that Geff will consider as time
        axes. These should be properties in the model that represent time (e.g.,
        ``timepoint``).
        If None, the model's reference time property will be used as the only time axis.
        If a list is provided, the order of the property names in the list will
        determine the order of both the axes and display hint in the GEFF metadata.
        The time display hint will be set to the first time axis in the list.
    space_axes : list[str] | None, default=None
        The properties of the x, y and optionally z coordinates, in that order,
        that Geff will consider as space axes. If None, ``cell_x`` and ``cell_y``
        are used, plus ``cell_z`` when it is declared, as long as every cell has a
        value for them (GEFF axes can't have missing values). An empty list exports
        no space axes. The space axes are written in OME-Zarr order (z, y, x), and
        the display hints are set to x (horizontal), y (vertical) and z (depth).
        Their values are written in pixels when the pixel size is known, see Notes.
    channel_axes : list[str] | None, default=None
        List of property names that Geff will consider as channel axes.
        These should be properties in the model that represent different channels
        or modalities (e.g., ``chan_1``, ``chan_2``). If None, no channel axes will
        be included in the GEFF metadata. They are written between the time and
        the space axes, as in OME-Zarr.
    tracklets : bool, default=False
        Whether to write the tracklets in a ``tracklet_id`` cell property, declared
        as the GEFF tracklet property. A tracklet is a cell cycle, identified like
        ``cycle_id`` by the ID of its last cell; with a fusion, a new tracklet
        starts at the merged cell. The tracklets are computed at export from the
        cell lineages, so they don't need cycle lineages and are always up to date.
        An existing ``tracklet_id`` cell property is replaced in the GEFF file, with
        a warning if some of its values differ.
    propagate_cycle_props : bool, default=False
        If True, cycle properties will be propagated to cell lineages before export,
        on the copy of the model. Useful if you want to export the cycle properties
        to GEFF, which has no cycle lineages. If False, cycle properties are not
        exported, and a warning names them.
    zarr_format : Literal[2, 3], default=2
        The Zarr format version to use for the GEFF file.

    Raises
    ------
    UpdateRequiredError
        If the model requires an update.
    ValueError
        If the model contains no lineage data.
        If `tracklets` is True and the model has a ``tracklet_id`` property that
        isn't only a cell property.
        If `propagate_cycle_props` is True and the model has no cycle lineages.
        If a property given in `time_axes`, `space_axes` or `channel_axes` is not a
        cell property, or is given twice.
    RuntimeError
        If geff fails to write the file.

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
    Only cell and link properties are exported: lineage properties are not, and
    cycle properties only once propagated to the cells, with `propagate_cycle_props`
    or `Model.propagate_cycle_properties()`. A warning names the cycle properties
    left out. A propagated ``cycle_id`` is written like any other property: use
    ``tracklets=True`` to declare the tracklets in the GEFF file. Properties whose
    data type GEFF cannot store, such as ``list[int]`` or shapely geometries, are not
    exported either, and a warning names them. Properties without any value, e.g.
    those that TrackMate declares without using them, are left out as well. None
    values are written as missing values. Properties with a variable length, such as
    ``cell_contour``, need nothing special: geff detects them from their values.

    GEFF needs cell IDs that are unique across lineages, while Pycellin only needs
    them unique within a lineage. Repeated IDs are changed in the file, with a
    warning, and the IDs of the cells in the model are then kept in the
    ``pycellin_cell_id`` property.

    GEFF gives the pixel size as the scale of a space axis whose values are in
    pixels. So the space axes are written in pixels, as their values divided by the
    pixel size from the model metadata (`pixel_width` for x, `pixel_height` for y,
    `pixel_depth` for z), with this pixel size as scale and the unit of the
    coordinates as scaled unit. `read_geff` converts them back. A space axis whose
    pixel size is None is written as it is. The other properties, such as areas or
    speeds, keep their units. Converting the coordinates into pixels and back can
    change the last digit of some values.
    """
    _check_up_to_date(model)
    if not model.data.cell_lineages:
        raise ValueError("Model contains no lineage data to export.")
    if tracklets:
        prop = model.get_property(_TRACKLET_PROP)
        if prop is not None and prop.prop_type != PropertyType.NODE:
            raise ValueError(
                f"Can't write the tracklets in a '{_TRACKLET_PROP}' cell property: "
                f"the model has a '{_TRACKLET_PROP}' property that isn't only a cell "
                "property. Rename it, or export with tracklets=False."
            )

    # We don't want to modify the original model.
    model_copy = copy.deepcopy(model)
    if propagate_cycle_props:
        model_copy.propagate_cycle_properties()

    # GEFF can store neither some data types nor None values.
    _remove_unsupported_props(model_copy)
    _remove_none_values(model_copy)
    # For GEFF compatibility, we need to ensure that there are no property metadata
    # entries that don't correspond to any actual property in the data.
    _remove_orphaned_metadata(model_copy)
    # All the lineages must also be in the same graph. However, some nodes can
    # have the same identifier across different lineages.
    lineages = list(model_copy.data.cell_lineages.values())
    if _solve_node_overlaps(lineages):
        model_copy.props_metadata._add_prop(_create_previous_id_property())
        logger.warning(
            "Some cell IDs are used in several lineages, so these cells get new IDs "
            "in the GEFF file, which needs unique IDs. The IDs of the cells in the "
            "model are kept in the 'pycellin_cell_id' property."
        )
    if tracklets:
        # Tracklet IDs are cell IDs, now unique across lineages.
        _add_tracklet_ids(model_copy)
    if space_axes is None:
        space_axes = _get_default_space_axes(model_copy)
    # GEFF gives the pixel size as the scale of a space axis in pixels.
    scales = _convert_coordinates_to_pixels(model_copy, space_axes)
    geff_graph = nx.compose_all(lineages)

    metadata = _build_geff_metadata(
        model=model_copy,
        time_axes=time_axes,
        space_axes=space_axes,
        channel_axes=channel_axes,
        tracklets=tracklets,
        scales=scales,
    )

    try:
        geff.write(
            geff_graph,
            path,
            metadata=metadata,
            zarr_format=zarr_format,
            structure_validation=True,
            overwrite=True,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to export GEFF file to '{path}': {e}") from e


if __name__ == "__main__":
    """
    Quick demo with sample data.
    """
    import tempfile

    from pycellin.io.trackmate.reader import read_trackmate_xml

    xml_in = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Ecoli_growth_on_agar_pad.xml"
    )
    model = read_trackmate_xml(xml_in)

    print(model)
    print("Model metadata:")
    print(model.model_metadata)

    with tempfile.TemporaryDirectory() as tmp_dir:
        geff_out = Path(tmp_dir) / "output.geff"
        write_geff(
            model,
            geff_out,
            space_axes=["cell_x", "cell_y", "cell_z"],
        )
