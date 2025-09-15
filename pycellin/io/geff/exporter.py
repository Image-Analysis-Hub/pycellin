#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
exporter.py

References:
- geff GitHub: https://github.com/live-image-tracking-tools/geff
- geff Documentation: https://live-image-tracking-tools.github.io/geff/latest/
"""

import copy

from geff.metadata_schema import Axis, DisplayHint, GeffMetadata
from geff import write_nx
import networkx as nx
from zmq import has

from pycellin.classes import Model, CellLineage


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
    axes = []
    has_x = model.has_property("cell_x")
    has_y = model.has_property("cell_y")
    has_z = model.has_property("cell_z")
    has_t = model.has_property("frame")
    # Axes
    if has_x:
        axes.append(Axis(name="cell_x", type="space", unit=model.get_space_unit()))
    if has_y:
        axes.append(Axis(name="cell_y", type="space", unit=model.get_space_unit()))
    if has_z:
        axes.append(Axis(name="cell_z", type="space", unit=model.get_space_unit()))
    if has_t:
        axes.append(Axis(name="frame", type="time", unit=model.get_time_unit()))
    # Display hints
    if has_x and has_y:
        display_hints = DisplayHint(display_horizontal="cell_x", display_vertical="cell_y")
        if has_z:
            display_hints.display_depth = "cell_z"
        if has_t:
            display_hints.display_time = "frame"

    # Create metadata with minimal required parameters
    # Note: Using empty lists/None for required but unused parameters
    metadata = GeffMetadata(
        directed=True,
        axes=axes,
        display_hints=display_hints,
    )

    # Property metadata
    # TODO cf create_or_update_metadata() in io_utils and PropMetadata in metadata_schema

    return metadata


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

    # TODO: this is debug
    model_copy.remove_property("ROI_coords")
    # model_copy.add_cell(lid=0, cid=9510)
    # model_copy.add_cell(lid=1, cid=9510)
    # model_copy.add_cell(lid=1, cid=9509)
    # model_copy.add_cell(lid=2, cid=9498)

    # For GEFF compatibility, we need to put all the lineages in the same graph,
    # but some nodes can have the same identifier...
    _solve_node_overlaps(lineages)
    geff_graph = nx.compose_all(lineages)
    print(len(geff_graph))

    metadata = _build_geff_metadata(model_copy)
    print(metadata)

    write_nx(
        geff_graph,
        geff_out,
        metadata=metadata,
        # axis_names=["cell_x", "cell_y", "cell_z", "frame"],
        # axis_units=["um", "um", "um", "s"],
        # zarr_format=2,
    )

    del model_copy


if __name__ == "__main__":
    xml_in = "sample_data/Ecoli_growth_on_agar_pad.xml"
    # xml_in = "sample_data/Celegans-5pc-17timepoints.xml"
    # xml_in = "sample_data/FakeTracks.xml"
    # ctc_in = "sample_data/FakeTracks_TMtoCTC.txt"
    # ctc_in = "sample_data/Ecoli_growth_on_agar_pad_TMtoCTC.txt"
    # geff_out = "C:/Users/lxenard/Documents/Janelia_Cell_Trackathon/test_pycellin_geff/test.zarr"
    geff_out = "E:/Janelia_Cell_Trackathon/test_pycellin_geff/test.geff"

    from pycellin.io.trackmate.loader import load_TrackMate_XML
    from pycellin.io.cell_tracking_challenge.loader import load_CTC_file

    model = load_TrackMate_XML(xml_in)
    # model = load_CTC_file(ctc_in)
    print(model)
    # print(model.get_cell_lineage_properties().keys())
    print(model.data.cell_data.keys())

    export_GEFF(model, geff_out)
