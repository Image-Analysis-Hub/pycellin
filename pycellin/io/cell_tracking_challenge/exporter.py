#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
exporter.py

This module is part of the Pycellin package.

This module provides functions to export Pycellin models to Cell Tracking Challenge
(CTC) tracking files. It includes a function to export a Pycellin model to a CTC file
and helper functions to build CTC tracks from a lineage.

References:
- CTC website: https://celltrackingchallenge.net/
- CTC tracking annotations conventions:
https://public.celltrackingchallenge.net/documents/Naming%20and%20file%20content%20conventions.pdf
"""

from pycellin.classes.exceptions import FusionError
from pycellin.classes.model import Model
from pycellin.classes.lineage import CellLineage


# TODO: need to extensively test this.
# TODO: check beforehand for fusions and gap just after division. No need to start
# the CTC file creation if we know it will fail.


def _sort_nodes_by_frame(
    lineage: CellLineage,
    nodes: list[int],
) -> list[int]:
    """
    Sort the nodes by ascending frame.

    Parameters
    ----------
    lineage : CellLineage
        The lineage object to which the nodes belongs.
    nodes : list[int]
        A list of nodes ID to order by ascending frame.

    Returns
    -------
    list[int]
        A list of nodes ID, ordered by ascending frame.
    """
    sorted_list = [(node, lineage.nodes[node]["frame"]) for node in nodes]
    sorted_list.sort(key=lambda x: x[1])
    return [node for node, _ in sorted_list]


def _find_gaps(
    lineage: CellLineage,
    sorted_nodes: list[int],
) -> list[tuple[int, int]]:
    """
    Find the temporal gaps in an ordered list of nodes.

    Parameters
    ----------
    lineage : CellLineage
        The lineage object to which the nodes belongs.
    sorted_nodes : list[int]
        A list of nodes ID, ordered by ascending frame.

    Returns
    -------
    list[tuple[int, int]]
        A list of tuples, where each tuple contains the IDs of the nodes that
        are separated by a gap in the ordered list of nodes.
    """
    gap_nodes = []
    for i in range(len(sorted_nodes) - 1):
        frame = lineage.nodes[sorted_nodes[i]]["frame"]
        next_frame = lineage.nodes[sorted_nodes[i + 1]]["frame"]
        if next_frame - frame > 1:
            gap_nodes.append((sorted_nodes[i], sorted_nodes[i + 1]))

    return gap_nodes


def _add_track(
    lineage: CellLineage,
    sorted_nodes: list[int],
    ctc_tracks: dict[int, dict[str, int]],
    node_to_parent_track: dict[int, int],
    current_track_label: int,
) -> int:
    """
    Add a CTC track to the CTC output.

    Parameters
    ----------
    lineage : CellLineage
        The lineage object to which the nodes belongs.
    sorted_nodes : list[int]
        A list of nodes ID, ordered by ascending frame.
    ctc_tracks : dict[int, dict[str, int]]
        A dictionary containing the CTC tracks of the lineage.
    node_to_parent_track : dict[int, int]
        A dictionary mapping the nodes to their parent CTC track.
    current_track_label : int
        The current track label.

    Returns
    -------
    int
        The updated current track label.
    """
    track = {
        "B": lineage.nodes[sorted_nodes[0]]["frame"],
        "E": lineage.nodes[sorted_nodes[-1]]["frame"],
        "B_node": sorted_nodes[0],
        "E_node": sorted_nodes[-1],
    }
    ctc_tracks[current_track_label] = track
    node_to_parent_track[track["E_node"]] = current_track_label
    return current_track_label + 1


def _build_CTC_tracks(
    lineage: CellLineage,
    ctc_tracks: dict[int, dict[str, int]],
    node_to_parent_track: dict[int, int],
    current_track_label: int,
) -> int:
    """
    Build the CTC tracks from the lineage.

    Parameters
    ----------
    lineage : CellLineage
        The lineage object we want to build tracks from.
    ctc_tracks : dict[int, dict[str, int]]
        A dictionary containing the CTC tracks of the lineage.
    node_to_parent_track : dict[int, int]
        A dictionary mapping the nodes to their parent CTC track.
    current_track_label : int
        The current track label.

    Returns
    -------
    int
        The updated current track label.

    Raises
    ------
    FusionError
        If a fusion event is detected in the lineage.
    """
    if len(lineage) == 1:
        current_track_label = _add_track(
            lineage,
            list(lineage.nodes),
            ctc_tracks,
            node_to_parent_track,
            current_track_label,
        )
    else:
        try:
            cell_cycles = lineage.get_cell_cycles(keep_incomplete_cell_cycles=True)
        except FusionError as err:
            raise FusionError(
                err.node_ID,
                lineage.graph["lineage_ID"],
                f"CTC do not support fusion events. {err.message}",
            ) from err
        for cc in cell_cycles:
            sorted_nodes = _sort_nodes_by_frame(lineage, cc)
            gaps = _find_gaps(lineage, sorted_nodes)
            if gaps:
                track_start_i = 0
                for gap in gaps:
                    track_end_i = sorted_nodes.index(gap[0])
                    current_track_label = _add_track(
                        lineage,
                        sorted_nodes[track_start_i : track_end_i + 1],
                        ctc_tracks,
                        node_to_parent_track,
                        current_track_label,
                    )
                    track_start_i = sorted_nodes.index(gap[1])
                current_track_label = _add_track(
                    lineage,
                    sorted_nodes[track_start_i:],
                    ctc_tracks,
                    node_to_parent_track,
                    current_track_label,
                )
            else:
                current_track_label = _add_track(
                    lineage,
                    sorted_nodes,
                    ctc_tracks,
                    node_to_parent_track,
                    current_track_label,
                )
    return current_track_label


def _add_parent_track(
    lineage: CellLineage,
    track_info: dict[str, int],
    node_to_parent_track: dict[int, int],
) -> None:
    """
    Add the parent track label to the CTC track information.

    Parameters
    ----------
    lineage : CellLineage
        The lineage object from which we are building CTC tracks.
    track_info : dict[str, int]
        A dictionary containing the CTC track information.
    node_to_parent_track : dict[int, int]
        A dictionary mapping the nodes to their parent CTC track.
    """
    parent_nodes = list(lineage.predecessors(track_info["B_node"]))
    assert_msg = (
        f"Node {track_info['B_node']} has more than 1 parent node "
        f"({len(parent_nodes)} nodes) in lineage of ID "
        f"{lineage.graph['lineage_ID']}. Incorrect lineage topology: "
        f"Pycellin and CTC do not support fusion events."
    )
    assert len(parent_nodes) <= 1, assert_msg
    if parent_nodes:
        track_info["P"] = node_to_parent_track[parent_nodes[0]]
    else:
        track_info["P"] = 0


def export_CTC_file(
    model: Model,
    ctc_file_out: str,
) -> None:
    """
    Export lineage data from a Model to CTC tracking file format.

    The CTC tracking format does not support fusion events and does not allow
    gaps right after division events.

    Parameters
    ----------
    model : Model
        The model from which we want to export the CTC file.
    ctc_file_out : str
        The path to the CTC file to write.
    -----
    """
    lineages = [lineage for lineage in model.data.cell_data.values()]
    current_track_label = 1  # 0 is kept for no parent track
    tracks_to_write = []
    for lin in lineages:
        ctc_tracks = {}
        node_to_parent_track = {}
        current_track_label = _build_CTC_tracks(
            lin, ctc_tracks, node_to_parent_track, current_track_label
        )
        for track_label, track_info in ctc_tracks.items():
            _add_parent_track(lin, track_info, node_to_parent_track)
            txt = (
                f"{track_label} {track_info['B']} "
                f"{track_info['E']} {track_info['P']}\n"
            )
            tracks_to_write.append(txt)

    with open(ctc_file_out, "w") as file:
        file.writelines(tracks_to_write)


if __name__ == "__main__":

    xml_in = "sample_data/FakeTracks.xml"
    # xml_in = "sample_data/Ecoli_growth_on_agar_pad_with_fusions.xml"
    ctc_in = "sample_data/FakeTracks_TMtoCTC.txt"
    ctc_out = "sample_data/results/FakeTracks_exported_CTC_from_CTC.txt"

    from pycellin.io.trackmate.loader import load_TrackMate_XML

    model = load_TrackMate_XML(xml_in)

    # from pycellin.io.cell_tracking_challenge.loader import load_CTC_file
    # model = load_CTC_file(ctc_in)

    export_CTC_file(model, ctc_out)
