#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
exporter.py

This module is part of the pycellin package.
It provides functionality to export a pycellin model to the GEFF format.

References:
- geff GitHub: https://github.com/live-image-tracking-tools/geff
- geff Documentation: https://live-image-tracking-tools.github.io/geff/latest/
"""

import copy

import networkx as nx
from geff import write_nx
from geff.metadata_schema import Axis, DisplayHint, GeffMetadata, PropMetadata

from pycellin.classes import CellLineage, Model, Property


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
            if nid in node_to_lineages:  # Overlap found
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
    next_ids = [lin._get_next_available_node_ID() for lin in lineages]
    return max(next_ids)


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
    """
    next_available_id = _get_next_available_id(lineages)
    for nid, lids in overlaps.items():
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
        print("Overlapping node IDs found:")
        for nid, lids in overlaps.items():
            print(f"  Node ID {nid} in lineages {lids}")
        _relabel_nodes(lineages, overlaps)

        # Verify no more overlaps
        # TODO: remove this, it's only for debug, or put in verbose
        overlaps = _find_node_overlaps(lineages)
        if overlaps:
            print("Overlapping node IDs found after relabeling:")
            for nid, lids in overlaps.items():
                print(f"  Node ID {nid} in lineages {lids}")
        else:
            print("No overlapping node IDs found after relabeling.")

    else:
        print("No overlapping node IDs found.")


def _build_axes(
    has_x: bool,
    has_y: bool,
    has_z: bool,
    has_t: bool,
    space_unit: str | None,
    time_unit: str | None,
) -> list[Axis]:
    """
    Build a list of Axis objects for GEFF metadata.

    Parameters
    ----------
    has_x : bool
        Whether the x-axis is present.
    has_y : bool
        Whether the y-axis is present.
    has_z : bool
        Whether the z-axis is present.
    has_t : bool
        Whether the time axis is present.
    space_unit : str | None
        Unit for spatial axes (e.g., "micrometer").
    time_unit : str | None
        Unit for time axis (e.g., "second").

    Returns
    -------
    list[Axis]
        List of Axis objects representing spatial and temporal dimensions.
    """
    axes = []
    if has_x:
        axes.append(Axis(name="cell_x", type="space", unit=space_unit))
    if has_y:
        axes.append(Axis(name="cell_y", type="space", unit=space_unit))
    if has_z:
        axes.append(Axis(name="cell_z", type="space", unit=space_unit))
    if has_t:
        axes.append(Axis(name="frame", type="time", unit=time_unit))
    return axes


def _build_display_hints(
    has_x: bool,
    has_y: bool,
    has_z: bool,
    has_t: bool,
) -> DisplayHint | None:
    """
    Build display hints for GEFF metadata.

    Parameters
    ----------
    has_x : bool
        Whether the x-axis is present.
    has_y : bool
        Whether the y-axis is present.
    has_z : bool
        Whether the z-axis is present.
    has_t : bool
        Whether the time axis is present.

    Returns
    -------
    DisplayHint | None
        DisplayHint object if x and y axes are present, otherwise None.
    """
    if has_x and has_y:
        display_hints = DisplayHint(display_horizontal="cell_x", display_vertical="cell_y")
        if has_z:
            display_hints.display_depth = "cell_z"
        if has_t:
            display_hints.display_time = "frame"
    else:
        display_hints = None
    return display_hints


def _build_props_metadata(
    properties: dict[str, Property],
) -> tuple[dict[str, PropMetadata], dict[str, PropMetadata]]:
    """
    Build property metadata for GEFF from a pycellin model.

    Parameters
    ----------
    properties : dict[str, Property]
        Dictionary of property identifiers to Property objects.

    Returns
    -------
    tuple[dict[str, PropMetadata], dict[str, PropMetadata]]
        A tuple containing two dictionaries:
        - Node properties metadata
        - Edge properties metadata

    Raises
    ------
    ValueError
        If an unknown property type is encountered.
    """
    node_props_md: dict[str, PropMetadata] = {}
    edge_props_md: dict[str, PropMetadata] = {}

    for prop_id, prop in properties.items():
        prop_md = PropMetadata(
            identifier=prop_id,
            dtype=prop.dtype,
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
                pass  # not supported in GEFF 0.5.0
            case _:
                raise ValueError(f"Unknown property type: {prop.prop_type}")

    return node_props_md, edge_props_md


def _build_geff_metadata(model: Model) -> GeffMetadata:
    """
    Build GEFF metadata from a pycellin model.

    Parameters
    ----------
    model : Model
        The pycellin model to extract metadata from.

    Returns
    -------
    GeffMetadata
        The GEFF metadata object.
    """
    # Generic metadata
    has_x = model.has_property("cell_x")
    has_y = model.has_property("cell_y")
    has_z = model.has_property("cell_z")
    has_t = model.has_property("frame")
    axes = _build_axes(
        has_x=has_x,
        has_y=has_y,
        has_z=has_z,
        has_t=has_t,
        space_unit=model.get_space_unit(),
        time_unit=model.get_time_unit(),
    )
    display_hints = _build_display_hints(
        has_x=has_x,
        has_y=has_y,
        has_z=has_z,
        has_t=has_t,
    )

    # Property metadata
    props = model.get_cell_lineage_properties()
    node_props_md, edge_props_md = _build_props_metadata(props)

    # Define identifiers of lineage and cell cycle
    track_node_props = {"lineage": "lineage_ID"}
    if model.has_cycle_data():
        track_node_props["tracklet"] = "cycle_ID"

    return GeffMetadata(
        directed=True,
        axes=axes,
        display_hints=display_hints,
        track_node_props=track_node_props,
        node_props_metadata=node_props_md,
        edge_props_metadata=edge_props_md,
    )


def export_GEFF(model: Model, geff_out: str) -> None:
    """
    Export a pycellin model to GEFF format.

    Parameters
    ----------
    model : Model
        The pycellin model to export.
    geff_out : str
        Path to the output GEFF file.
    """
    # We don't want to modify the original model.
    model_copy = copy.deepcopy(model)
    lineages = list(model_copy.data.cell_data.values())
    for graph in lineages:
        print(len(graph.nodes), len(graph.edges))

    # TODO: remove when GEFF can handle variable length properties
    if model_copy.has_property("ROI_coords"):
        model_copy.remove_property("ROI_coords")

    # For GEFF compatibility, we need to put all the lineages in the same graph,
    # but some nodes can have the same identifier across different lineages.
    _solve_node_overlaps(lineages)
    geff_graph = nx.compose_all(lineages)
    print(len(geff_graph))

    metadata = _build_geff_metadata(model_copy)
    print(metadata)

    write_nx(
        geff_graph,
        geff_out,
        metadata=metadata,
    )

    del model_copy


if __name__ == "__main__":
    xml_in = "sample_data/Ecoli_growth_on_agar_pad.xml"
    # xml_in = "sample_data/Celegans-5pc-17timepoints.xml"
    # xml_in = "sample_data/FakeTracks.xml"
    # ctc_in = "sample_data/FakeTracks_TMtoCTC.txt"
    # ctc_in = "sample_data/Ecoli_growth_on_agar_pad_TMtoCTC.txt"
    # geff_out = "E:/Janelia_Cell_Trackathon/test_pycellin_geff/test.geff"
    geff_out = (
        "/media/lxenard/data/Janelia_Cell_Trackathon/test_pycellin_geff/pycellin_to_geff.geff"
    )

    # Remove existing folder
    import os
    import shutil

    if os.path.exists(geff_out):
        shutil.rmtree(geff_out)

    # Load data
    from pycellin.io.cell_tracking_challenge.loader import load_CTC_file
    from pycellin.io.trackmate.loader import load_TrackMate_XML

    model = load_TrackMate_XML(xml_in)
    # model = load_CTC_file(ctc_in)
    # model.add_cycle_data()
    print(model)
    print(model.get_cell_lineage_properties().keys())
    print(model.data.cell_data.keys())
    # To test overlapping node IDs
    prop_values = {"cell_x": 10, "cell_y": 15, "cell_z": 20}
    model.add_cell(lid=0, cid=9510, frame=0, prop_values=prop_values)
    model.add_cell(lid=1, cid=9510, frame=0, prop_values=prop_values)
    model.add_cell(lid=1, cid=9509, frame=0, prop_values=prop_values)
    model.add_cell(lid=2, cid=9498, frame=0, prop_values=prop_values)

    export_GEFF(model, geff_out)
