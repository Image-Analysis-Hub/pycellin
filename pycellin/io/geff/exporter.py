#!/usr/bin/env python3

"""
exporter.py

This module is part of the pycellin package.
It provides functionality to export a pycellin model to the GEFF format.

References:
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
from pycellin.classes.exceptions import ProtectedPropertyError
from pycellin.custom_types import PropertyType
from pycellin.io.utils import _check_up_to_date, _remove_orphaned_metadata
from pycellin.utils import _normalize_dtype

logger = logging.getLogger(__name__)

# Cell property that holds the tracklet IDs written by export_GEFF(tracklets=True).
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
        A dictionary mapping node IDs to the list of lineage indices they belong to.
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

    Parameters
    ----------
    lineages : list[CellLineage]
        List of lineage graphs to relabel in place.
    overlaps : dict[int, list[int]]
        Dictionary mapping overlapping node IDs to the list of lineage indices they belong to.
    """
    next_available_id = _get_next_available_id(lineages)
    for nid, lids in sorted(overlaps.items()):
        for lid in lids[1:]:
            mapping = {nid: next_available_id}
            nx.relabel_nodes(lineages[lid], mapping, copy=False)
            next_available_id += 1


def _solve_node_overlaps(lineages: list[CellLineage]) -> None:
    """
    Detect and resolve overlapping node IDs across lineages by reassigning unique IDs.

    Parameters
    ----------
    lineages : list[CellLineage]
        List of lineage graphs to check and modify in place.
    """
    overlaps = _find_node_overlaps(lineages)
    if overlaps:
        _relabel_nodes(lineages, overlaps)


def _to_geff_dtype(dtype: str) -> str:
    """
    Return the GEFF spelling of a property data type.

    Parameters
    ----------
    dtype : str
        Data type of a pycellin property.

    Returns
    -------
    str
        "str" for strings, since GEFF spells the string data type "str", else
        `dtype` unchanged.
    """
    if _normalize_dtype(dtype) == "string":
        return "str"
    return dtype


def _remove_unsupported_props(model: Model) -> None:
    """
    Remove the cell and link properties whose data type GEFF cannot store.

    GEFF stores booleans, numbers and strings, as single values or as
    variable-length arrays (e.g. cell contours), but not data types such as
    `list[int]` or shapely geometries. Lineage properties are not checked, since
    they are not exported.

    Parameters
    ----------
    model : Model
        Model to modify.

    Warns
    -----
    If some properties have a data type that GEFF cannot store. They are removed
    from the model and won't be exported.
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
    for lineage in model.data.cell_data.values():
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
        Declaration of the 'tracklet_id' property.
    """
    return Property(
        identifier=_TRACKLET_PROP,
        name="Tracklet ID",
        description=(
            "Identifier of the tracklet of the cell, i.e. of its cell cycle: "
            "ID of the last cell of the tracklet"
        ),
        provenance="pycellin",
        prop_type="node",
        lin_type="CellLineage",
        dtype="int",
    )


def _get_tracklet_ids(lineage: CellLineage) -> dict[int, int]:
    """
    Return the tracklet ID of each cell of a lineage.

    GEFF defines a tracklet as a maximal path whose links each join a cell with
    a single child to a cell with a single parent. Without fusions, the tracklets
    are the cell cycles; with a fusion, a new tracklet starts at the merged cell.
    A tracklet is identified by the ID of its last cell, as a cell cycle is by
    its 'cycle_id'.

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
    Write the tracklet ID of each cell in the 'tracklet_id' cell property.

    Tracklet IDs are cell IDs, so they are unique across lineages only once the
    node overlaps are solved. An existing 'tracklet_id' property is replaced.

    Parameters
    ----------
    model : Model
        Model to modify, with cell IDs unique across lineages.

    Warns
    -----
    If some cells already had a 'tracklet_id' value that differs from their
    tracklet ID.
    """
    num_changed = 0
    for lineage in model.data.cell_data.values():
        for cid, tracklet_id in _get_tracklet_ids(lineage).items():
            attrs = lineage.nodes[cid]
            if _TRACKLET_PROP in attrs and attrs[_TRACKLET_PROP] != tracklet_id:
                num_changed += 1
            attrs[_TRACKLET_PROP] = tracklet_id
    model.props_metadata.props[_TRACKLET_PROP] = _create_tracklet_property()
    if num_changed:
        logger.warning(
            "With tracklets=True, the GEFF file has the tracklet IDs computed at "
            f"export, which differ from the '{_TRACKLET_PROP}' values of "
            f"{num_changed} cell{'s' if num_changed > 1 else ''} of the model."
        )


def _get_default_space_axes(model: Model) -> list[str]:
    """
    Return the coordinate properties to export as space axes by default.

    These are 'cell_x' and 'cell_y', plus 'cell_z' when it is declared. GEFF doesn't
    allow missing values on axes, so a coordinate is only exported as an axis when
    every cell has a value for it: without complete 'cell_x' and 'cell_y', no space
    axis is exported.

    Parameters
    ----------
    model : Model
        The model to export, without None values.

    Returns
    -------
    list[str]
        The coordinate properties, in x, y, z order.

    Warns
    -----
    If 'cell_x', 'cell_y' or 'cell_z' is declared but some cells have no value
    for it, so that it can't be exported as an axis.
    """
    node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
    if "cell_x" not in node_props or "cell_y" not in node_props:
        return []
    declared = [key for key in ("cell_x", "cell_y", "cell_z") if key in node_props]
    cells = [
        attrs
        for lin in model.data.cell_data.values()
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


def _build_axes(
    node_props: dict[str, Property],
    time_axes: list[str],
    space_axes: list[str] | None,
    channel_axes: list[str] | None,
) -> list[geff_spec.Axis]:
    """
    Build a list of Axis objects for GEFF metadata.

    The axes are ordered as in OME-Zarr: time, then channel, then space axes in reverse 
    order (z, y, x).

    Parameters
    ----------
    node_props : dict[str, Property]
        Dictionary of node properties from the model, used to validate the axes_mapping.
    time_axes : list[str]
        List of property names that Geff will consider as time axes.
        These should be properties in the model that represent time (e.g., "timepoint").
    space_axes : list[str] | None, optional
        The properties of the x, y and optionally z coordinates, in that order
        (e.g., "cell_x", "cell_y", "cell_z"). If None or empty, no spatial axes
        will be included in the GEFF metadata.
    channel_axes : list[str] | None, optional
        List of property names that Geff will consider as channel axes.
        These should be properties in the model that represent different channels
        or modalities (e.g., "chan_1", "chan_2"). If None, no channel axes will be
        included in the GEFF metadata.

    Returns
    -------
    list[geff_spec.Axis]
        List of Geff Axis objects describing spatial and temporal dimensions.
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
                    f"Unknown node property '{prop_name}', cannot be mapped to channel axis."
                )
            axes.append(
                geff_spec.Axis(
                    name=prop_name,
                    type="channel",
                )
            )
    if space_axes is not None:
        for prop_name in reversed(space_axes):
            if prop_name not in node_props:
                raise ValueError(
                    f"Unknown node property '{prop_name}', cannot be mapped to space axis."
                )
            axes.append(
                geff_spec.Axis(
                    name=prop_name,
                    type="space",
                    unit=node_props[prop_name].unit,
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
    var_length_props: list[str] | None = None,
) -> tuple[dict[str, geff_spec.PropMetadata], dict[str, geff_spec.PropMetadata]]:
    """
    Build property metadata for GEFF from a pycellin model.

    Parameters
    ----------
    properties : dict[str, Property]
        Dictionary of property identifiers to Property objects.
    var_length_props : list[str] | None, optional
        List of property identifiers that are variable in length (i.e., their values
        are lists or arrays). If None, no properties are considered variable length.

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
            varlength=prop_id in var_length_props if var_length_props else False,
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
    var_length_props: list[str] | None = None,
    tracklets: bool = False,
) -> geff.GeffMetadata:
    """
    Build GEFF metadata from a pycellin model.

    Parameters
    ----------
    model : Model
        The pycellin model to extract metadata from.
    time_axes : str | list[str] | None, optional
        List of property names that Geff will consider as time axes.
        These should be properties in the model that represent time (e.g., "timepoint").
        If None, the model's reference time property will be used as the only time axis.
        If a list is provided, the order of the property names in the list will
        determine the order of both the axes and display hint in the GEFF metadata.
        The time display hint will be set to the first time axis in the list.
    space_axes : list[str] | None, optional
        The properties of the x, y and optionally z coordinates, in that order,
        that Geff will consider as space axes. If None, 'cell_x' and 'cell_y' are
        used, plus 'cell_z' when it is declared, as long as every cell has a value
        for them. An empty list exports no space axes. The space axes are written in
        OME-Zarr order (z, y, x), and the display hints are set to x (horizontal),
        y (vertical) and z (depth).
    channel_axes : list[str] | None, optional
        List of property names that Geff will consider as channel axes.
        These should be properties in the model that represent different channels
        or modalities (e.g., "chan_1", "chan_2"). If None, no channel axes will be
        included in the GEFF metadata.
    var_length_props : list[str] | None, optional
        List of property identifiers that are variable in length (i.e., their values
        are lists or arrays). If None, no properties are considered variable length.
    tracklets : bool, optional
        Whether to declare the 'tracklet_id' cell property as the GEFF tracklet
        property. The cells must already have it, see `_add_tracklet_ids()`.
        Default is False.

    Returns
    -------
    geff.GeffMetadata
        The GEFF metadata object.
    """
    # Generic metadata.
    node_props = model.props_metadata._get_prop_dict_from_prop_type("node")
    if time_axes is None:
        time_axes = [model.reference_time_property]
    elif isinstance(time_axes, str):
        time_axes = [time_axes]
    if space_axes is None:
        space_axes = _get_default_space_axes(model)
    axes = _build_axes(
        node_props=node_props,
        time_axes=time_axes,
        space_axes=space_axes,
        channel_axes=channel_axes,
    )
    display_hints = _build_display_hints(
        time_axis=time_axes[0],
        space_axes=space_axes,
    )

    # Property metadata.
    props = model.get_cell_lineage_properties()
    node_props_md, edge_props_md = _build_props_metadata(props, var_length_props)

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


def export_GEFF(
    model: Model,
    geff_out: str | Path,
    time_axes: str | list[str] | None = None,
    space_axes: list[str] | None = None,
    channel_axes: list[str] | None = None,
    variable_length_props: list[str] | None = None,
    tracklets: bool = False,
    zarr_format: Literal[2, 3] = 2,
) -> Model:
    """
    Export a pycellin model to GEFF format.

    Parameters
    ----------
    model : Model
        The pycellin model to export.
    geff_out : str | Path
        Path to the output GEFF file.
    time_axes : str | list[str] | None, optional
        List of property names that Geff will consider as time axes.
        These should be properties in the model that represent time (e.g., "timepoint").
        If None, the model's reference time property will be used as the only time axis.
        If a list is provided, the order of the property names in the list will
        determine the order of both the axes and display hint in the GEFF metadata.
        The time display hint will be set to the first time axis in the list.
    space_axes : list[str] | None, optional
        The properties of the x, y and optionally z coordinates, in that order,
        that Geff will consider as space axes. If None, 'cell_x' and 'cell_y' are
        used, plus 'cell_z' when it is declared, as long as every cell has a value
        for them (GEFF axes can't have missing values). An empty list exports no
        space axes. The space axes are written in OME-Zarr order (z, y, x), and the
        display hints are set to x (horizontal), y (vertical) and z (depth).
    channel_axes : list[str] | None, optional
        List of property names that Geff will consider as channel axes.
        These should be properties in the model that represent different channels
        or modalities (e.g., "chan_1", "chan_2"). If None, no channel axes will be
        included in the GEFF metadata. They are written between the time and the
        space axes, as in OME-Zarr.
    variable_length_props : list[str] | None, optional
        List of property identifiers that are variable in length (i.e., their values
        are lists or arrays). If None, no properties are considered variable length.
    tracklets : bool, optional
        Whether to write the tracklets in a 'tracklet_id' cell property, declared
        as the GEFF tracklet property. A tracklet is a cell cycle, identified like
        'cycle_id' by the ID of its last cell; with a fusion, a new tracklet starts
        at the merged cell. The tracklets are computed at export from the cell
        lineages, so they don't need cycle lineages and are always up to date. An
        existing 'tracklet_id' cell property is replaced in the GEFF file, with a
        warning if some of its values differ. Default is False.
    zarr_format : Literal[2, 3], optional
        The Zarr format version to use for the GEFF file. Default is 2.

    Returns
    -------
    Model
        The model that was exported, which is a copy of the input model with
        any necessary modifications for GEFF compatibility. The original input model
        is not modified.

    Raises
    ------
    UpdateRequiredError
        If the model requires an update.
    ValueError
        If the model contains no lineage data.
        If `tracklets` is True and the model has a 'tracklet_id' property that
        isn't only a cell property.
    RuntimeError
        If the GEFF export process fails.

    Notes
    -----
    Only cell and link properties are exported: lineage properties are not, and
    cycle properties only once propagated to the cells with
    `Model.propagate_cycle_properties()`. A propagated 'cycle_id' is written like
    any other property: use `tracklets=True` to declare the tracklets in the GEFF
    file. Properties whose data type GEFF cannot store, such as `list[int]` or
    shapely geometries, are not exported either, and a warning names them. None
    values are written as missing values.
    """
    _check_up_to_date(model)
    if not model.data.cell_data:
        raise ValueError("Model contains no lineage data to export.")
    if tracklets:
        prop = model.get_property(_TRACKLET_PROP)
        if prop is not None and prop.prop_type != PropertyType.NODE:
            raise ValueError(
                f"Can't write the tracklets in a '{_TRACKLET_PROP}' cell property: "
                f"the model has a '{_TRACKLET_PROP}' property that isn't only a cell "
                "property. Rename it, or export with tracklets=False."
            )

    try:
        # We don't want to modify the original model.
        model_copy = copy.deepcopy(model)

        # GEFF can store neither some data types nor None values.
        _remove_unsupported_props(model_copy)
        _remove_none_values(model_copy)
        # For GEFF compatibility, we need to ensure that there are no property metadata
        # entries that don't correspond to any actual property in the data.
        _remove_orphaned_metadata(model_copy)
        # All the lineages must also be in the same graph. However, some nodes can
        # have the same identifier across different lineages.
        lineages = list(model_copy.data.cell_data.values())
        _solve_node_overlaps(lineages)
        if tracklets:
            # Tracklet IDs are cell IDs, now unique across lineages.
            _add_tracklet_ids(model_copy)
        geff_graph = nx.compose_all(lineages)

        metadata = _build_geff_metadata(
            model=model_copy,
            time_axes=time_axes,
            space_axes=space_axes,
            channel_axes=channel_axes,
            var_length_props=variable_length_props,
            tracklets=tracklets,
        )

        geff.write(
            geff_graph,
            geff_out,
            metadata=metadata,
            zarr_format=zarr_format,
            structure_validation=True,
            overwrite=True,
        )

    except Exception as e:
        raise RuntimeError(f"Failed to export GEFF file to '{geff_out}': {e}.") from e

    return model_copy


if __name__ == "__main__":
    """
    Quick demo with sample data.
    """
    import tempfile

    from pycellin.io.trackmate.loader import load_TrackMate_XML

    xml_in = (
        Path(__file__).resolve().parents[3]
        / "sample_data"
        / "Ecoli_growth_on_agar_pad.xml"
    )
    model = load_TrackMate_XML(xml_in)

    print(model)
    print("Model metadata:")
    print(model.model_metadata)

    with tempfile.TemporaryDirectory() as tmp_dir:
        geff_out = Path(tmp_dir) / "output.geff"
        export_GEFF(
            model,
            geff_out,
            space_axes=["cell_x", "cell_y", "cell_z"],
            variable_length_props=["cell_contour"],
        )
