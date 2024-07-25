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

    lineages = model.coredata.data
    # Removing one-node lineages.
    lineages = [lineage for lineage in lineages.values() if len(lineage) > 1]
    for lin in lineages:
        cell_cycles = []
        for cc in lin.get_cell_cycles(keep_incomplete_cell_cycles=True):
            gaps = _find_gaps(lin, cc)
            if gaps:
                print(gaps)
                for gap in gaps:
                    pass
                    # We cut the cc at each gap and add it to the list of cell cycles.
            else:
                cell_cycles.append(cc)
        print(cell_cycles)

        lin_id = lin.graph["lineage_ID"]
        if lin_id == 0:
            # What value can I use to replace this ID 0?
            pass
        else:
            pass
            # Iterate over each cc and write to file line by line.


if __name__ == "__main__":

    xml_in = "sample_data/FakeTracks.xml"
    ctc_out = "sample_data/FakeTracks_exported_CTC.xml"

    model = load_TrackMate_XML(xml_in, keep_all_spots=True, keep_all_tracks=True)
    export_CTC(model, ctc_out)
