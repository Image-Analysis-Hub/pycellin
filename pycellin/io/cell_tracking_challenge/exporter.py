#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools
import math
from typing import Any, Union

from lxml import etree as ET
import networkx as nx

from pycellin.classes.model import Model
from pycellin.classes.feature import FeaturesDeclaration, Feature
from pycellin.classes.data import CoreData
from pycellin.classes.lineage import CellLineage
from pycellin.io.trackmate.loader import load_TrackMate_XML

# TODO: Need to check with TM but I think I need to scrap the lineage_ID.
# It is not used in the same way as TM and Pycellin in the CTC format.
# https://public.celltrackingchallenge.net/documents/Naming%20and%20file%20content%20conventions.pdf
# https://imagej.net/plugins/trackmate/actions/trackmate-ctc-exporter


def sort_nodes_by_frame(
    lineage: CellLineage, nodes: list[int]
) -> tuple[list[int], list[int]]:
    """
    Sort the nodes by ascending frame.

    Parameters
    ----------
    lineage : CellLineage
        The lineage object to which the nodes belongs.
    nodes : list[int]
        A list of nodes to order by ascending frame.

    Returns
    -------
    tuple[list[int], list[int]]
        A tuple containing the ordered nodes and their corresponding frames.
    """
    sorted_list = [(node, lineage.nodes[node]["frame"]) for node in nodes]
    sorted_list.sort(key=lambda x: x[1])
    nodes = [node for node, frame in sorted_list]
    frames = [frame for node, frame in sorted_list]
    return nodes, frames


def _find_gaps(lineage: CellLineage, sorted_nodes: list[int]) -> list[tuple[int, int]]:
    """
    Find the temporal gaps in an ordered list of nodes.

    Parameters
    ----------
    lineage : CellLineage
        The lineage object to which the nodes belongs.
    sorted_nodes : list[tuple[int, int]]
        A list of tuples, where each tuple contains the frame of the node and
        the ID of the node, ordered by ascending frame.

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
        # frame, node = sorted_nodes[i]
        # next_frame, next_node = sorted_nodes[i + 1]
        if next_frame - frame > 1:
            gap_nodes.append((sorted_nodes[i], sorted_nodes[i + 1]))
            # gap_nodes.append(sorted_nodes[i + 1])

    return gap_nodes


def _add_track(
    lineage, sorted_nodes, ctc_tracks, node_to_parent_track, current_track_label
):
    track = {
        "B": lineage.nodes[sorted_nodes[0]]["frame"],
        "E": lineage.nodes[sorted_nodes[-1]]["frame"],
        "B_node": sorted_nodes[0],
        "E_node": sorted_nodes[-1],
    }
    ctc_tracks[current_track_label] = track
    node_to_parent_track[track["E_node"]] = current_track_label
    return current_track_label + 1


def export_CTC(model, ctc_file_out):

    # L B E P

    lineages = model.coredata.data
    # Removing one-node lineages.
    # TODO: actually CTC can deal with one-node lineage, so I need to deal
    # with this kind of special cases when everything else will work.
    lineages = [lineage for lineage in lineages.values() if len(lineage) > 1]
    current_track_label = 1  # 0 is kept for no parent track
    for lin in lineages:
        print(lin)
        ctc_tracks = {}
        node_to_parent_track = {}
        for cc in lin.get_cell_cycles(keep_incomplete_cell_cycles=True):
            # print(cc)
            sorted_nodes, frames = sort_nodes_by_frame(lin, cc)
            gaps = _find_gaps(lin, sorted_nodes)
            if gaps:
                print("Gaps found in cell cycle:", cc)
                print("gaps:", gaps)
                start_i = 0
                for gap in gaps:
                    end_i = sorted_nodes.index(gap[0])
                    current_track_label = _add_track(
                        lin,
                        sorted_nodes[start_i : end_i + 1],
                        ctc_tracks,
                        node_to_parent_track,
                        current_track_label,
                    )
                    start_i = sorted_nodes.index(gap[1])
                current_track_label = _add_track(
                    lin,
                    sorted_nodes[start_i:],
                    ctc_tracks,
                    node_to_parent_track,
                    current_track_label,
                )
            else:
                current_track_label = _add_track(
                    lin,
                    sorted_nodes,
                    ctc_tracks,
                    node_to_parent_track,
                    current_track_label,
                )

        for track_label, track_info in ctc_tracks.items():
            # print(track_label, track_info)
            parent_nodes = list(lin.predecessors(track_info["B_node"]))
            # Pycellin and CTC do not support multiple parents.
            assert_msg = (
                f"Node {track_info['B_node']} has more than 1 parent node "
                f"({len(parent_nodes)} nodes) in lineage of ID "
                f"{lin.graph['lineage_ID']}. Incorrect lineage topology: "
                f"Pycellin and CTC do not support merge events."
            )
            assert len(parent_nodes) <= 1, assert_msg
            if parent_nodes:
                track_info["P"] = node_to_parent_track[parent_nodes[0]]
            else:
                track_info["P"] = 0
            print(
                f"{track_label} {track_info['B']} {track_info['E']} {track_info['P']}"
            )

        # print("ctc_tracks", ctc_tracks)
        # print()


if __name__ == "__main__":

    xml_in = "sample_data/FakeTracks.xml"
    ctc_out = "sample_data/FakeTracks_exported_CTC.xml"

    model = load_TrackMate_XML(xml_in, keep_all_spots=True, keep_all_tracks=True)
    export_CTC(model, ctc_out)
