#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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


def _find_gaps(lineage: CellLineage, cell_cycle: list[int]) -> list[tuple[int, int]]:
    """
    Find missing frames in the cell cycle.

    Parameters
    ----------
    lineage : CellLineage
        The lineage object to which the cell cycle belongs.
    cell_cycle : list[int]
        A list of node IDs.

    Returns
    -------
    list[tuple[int, int]]
        A list of tuples, where each tuple contains the IDs of the nodes that
        are separated by a gap in the cell cycle.
    """
    frames = [(lineage.nodes[node]["frame"], node) for node in cell_cycle]
    frames.sort(key=lambda x: x[0])

    missing_frames = []
    for i in range(len(frames) - 1):
        frame, node = frames[i]
        next_frame, next_node = frames[i + 1]
        if next_frame - frame > 1:
            missing_frames.append((node, next_node))

    return missing_frames


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
            gaps = _find_gaps(lin, cc)
            if gaps:
                print(gaps)
                for gap in gaps:
                    # We cut the cc at each gap and add it to the list of cell cycles.
                    # current_track_label += 1
                    pass
            else:
                track = {
                    "B": lin.nodes[cc[0]]["frame"],
                    "E": lin.nodes[cc[-1]]["frame"],
                    "B_node": cc[0],
                    "E_node": cc[-1],
                }
                ctc_tracks[current_track_label] = track
                node_to_parent_track[track["E_node"]] = current_track_label
                current_track_label += 1
        # print("ctc_tracks", ctc_tracks)
        # print("node_to_parent_track", node_to_parent_track)

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
