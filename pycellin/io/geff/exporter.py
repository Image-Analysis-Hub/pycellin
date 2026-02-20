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
import tempfile
from pathlib import Path
from typing import Literal

import geff
import geff_spec
import networkx as nx

from pycellin.classes import CellLineage, Model, Property
from pycellin.io.utils import _remove_orphaned_metadata

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
            if lineage_max > max_node_id:
                max_node_id = lineage_max

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


def _build_axes(
    node_props: dict[str, Property],
    time_axes: list[str],
    space_axes: list[str] | None,
    channel_axes: list[str] | None,
) -> list[geff_spec.Axis]:
    """
    Build a list of Axis objects for GEFF metadata.

    Parameters
    ----------
    node_props : dict[str, Property]
        Dictionary of node properties from the model, used to validate the axes_mapping.
    time_axes : list[str]
        List of property names that Geff will consider as time axes.
        These should be properties in the model that represent time (e.g., "timepoint").
    space_axes : list[str] | None, optional
        List of property names that Geff will consider as space axes.
        These should be properties in the model that represent spatial coordinates
        (e.g., "cell_x", "cell_y", "cell_z"). If None, no spatial axes will be included
        in the GEFF metadata, and no display hints for spatial dimensions will be set.
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
    if space_axes is not None:
        for prop_name in space_axes:
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
        List of space axis names in order of horizontal, vertical, and depth dimensions.
        If None or if fewer than 2 space axes are provided, no display hints will
        be set for spatial dimensions (cf Geff specification).

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

    Raises
    ------
    ValueError
        If an unknown property type is encountered.
    """
    node_props_md: dict[str, geff_spec.PropMetadata] = {}
    edge_props_md: dict[str, geff_spec.PropMetadata] = {}

    for prop_id, prop in properties.items():
        if prop.dtype.lower() == "string":
            dtype = "str"
        else:
            dtype = prop.dtype

        prop_md = geff_spec.PropMetadata(
            identifier=prop_id,
            dtype=dtype,
            varlength=prop_id in var_length_props if var_length_props else False,
            unit=prop.unit,
            name=prop.name,
            description=prop.description,
        )
        match prop.prop_type:
            case "node":
                node_props_md[prop_id] = prop_md
            case "edge":
                edge_props_md[prop_id] = prop_md
            case "lineage":
                pass  # need geffception for lineage and cycle props
            case _:
                raise ValueError(f"Unknown property type: {prop.prop_type}")

    return node_props_md, edge_props_md


def _build_geff_metadata(
    model: Model,
    time_axes: str | list[str] | None = None,
    space_axes: list[str] | None = None,
    channel_axes: list[str] | None = None,
    var_length_props: list[str] | None = None,
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
        List of property names that Geff will consider as space axes.
        These should be properties in the model that represent spatial coordinates
        (e.g., "cell_x", "cell_y", "cell_z"). If None, no spatial axes will be included
        in the GEFF metadata, and no display hints for spatial dimensions will be set.
        If provided, the order of the property names in the list will determine
        the order of both the axes and the display hints in the GEFF metadata.
        Display hints will be set for the first three space axes as horizontal,
        vertical, and depth dimensions, respectively.
    channel_axes : list[str] | None, optional
        List of property names that Geff will consider as channel axes.
        These should be properties in the model that represent different channels
        or modalities (e.g., "chan_1", "chan_2"). If None, no channel axes will be
        included in the GEFF metadata.
    var_length_props : list[str] | None, optional
        List of property identifiers that are variable in length (i.e., their values
        are lists or arrays). If None, no properties are considered variable length.

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

    # Define identifiers of lineage and cell cycle.
    track_node_props = {"lineage": "lineage_ID"}
    if model.has_cycle_data():
        track_node_props["tracklet"] = "cycle_ID"

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
    geff_out: str,
    time_axes: str | list[str] | None = None,
    space_axes: list[str] | None = None,
    channel_axes: list[str] | None = None,
    variable_length_props: list[str] | None = None,
    zarr_format: Literal[2, 3] = 2,
) -> Model:
    """
    Export a pycellin model to GEFF format.

    Parameters
    ----------
    model : Model
        The pycellin model to export.
    geff_out : str
        Path to the output GEFF file.
    time_axes : str | list[str] | None, optional
        List of property names that Geff will consider as time axes.
        These should be properties in the model that represent time (e.g., "timepoint").
        If None, the model's reference time property will be used as the only time axis.
        If a list is provided, the order of the property names in the list will
        determine the order of both the axes and display hint in the GEFF metadata.
        The time display hint will be set to the first time axis in the list.
    space_axes : list[str] | None, optional
        List of property names that Geff will consider as space axes.
        These should be properties in the model that represent spatial coordinates
        (e.g., "cell_x", "cell_y", "cell_z"). If None, no spatial axes will be included
        in the GEFF metadata, and no display hints for spatial dimensions will be set.
        If provided, the order of the property names in the list will determine
        the order of both the axes and the display hints in the GEFF metadata.
        Display hints will be set for the first three space axes as horizontal,
        vertical, and depth dimensions, respectively.
    channel_axes : list[str] | None, optional
        List of property names that Geff will consider as channel axes.
        These should be properties in the model that represent different channels
        or modalities (e.g., "chan_1", "chan_2"). If None, no channel axes will be
        included in the GEFF metadata.
    variable_length_props : list[str] | None, optional
        List of property identifiers that are variable in length (i.e., their values
        are lists or arrays). If None, no properties are considered variable length.
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
    ValueError
        If the model contains no lineage data.
    RuntimeError
        If the GEFF export process fails.
    """
    if not model.data.cell_data:
        raise ValueError("Model contains no lineage data to export.")

    try:
        # We don't want to modify the original model.
        model_copy = copy.deepcopy(model)

        # For GEFF compatibility, we need to ensure that there are no property metadata
        # entries that don't correspond to any actual property in the data.
        _remove_orphaned_metadata(model_copy)
        # All the lineages must also be in the same graph. However, some nodes can
        # have the same identifier across different lineages.
        lineages = list(model_copy.data.cell_data.values())
        _solve_node_overlaps(lineages)
        geff_graph = nx.compose_all(lineages)

        metadata = _build_geff_metadata(
            model=model_copy,
            time_axes=time_axes,
            space_axes=space_axes,
            channel_axes=channel_axes,
            var_length_props=variable_length_props,
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

    from pycellin.io.trackmate.loader import load_TrackMate_XML

    xml_in = "sample_data/Ecoli_growth_on_agar_pad.xml"
    model = load_TrackMate_XML(xml_in)

    with tempfile.TemporaryDirectory() as tmp_dir:
        geff_out = Path(tmp_dir) / "output.geff"
        export_GEFF(
            model,
            geff_out,
            space_axes=["cell_x", "cell_y"],
            variable_length_props=["ROI_coords"],
        )
