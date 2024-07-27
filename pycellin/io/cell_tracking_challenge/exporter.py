#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from pycellin.classes.lineage import CellLineage
from pycellin.io.trackmate.loader import load_TrackMate_XML


def sort_nodes_by_frame(
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
        A list of nodes to order by ascending frame.

    Returns
    -------
    list[int]
        A list of nodes ordered by ascending frame.
    """
    sorted_list = [(node, lineage.nodes[node]["frame"]) for node in nodes]
    print(sorted_list)
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
        if next_frame - frame > 1:
            gap_nodes.append((sorted_nodes[i], sorted_nodes[i + 1]))

    return gap_nodes


def _add_track(
    lineage: CellLineage,
    sorted_nodes: list[int],
    ctc_tracks: dict[int, dict[str, int]],
    node_to_parent_track: dict[int, int],
    current_track_label: int,
):
    """
    Add a CTC track to the CTC output.

    Parameters
    ----------
    lineage : CellLineage
        The lineage object to which the nodes belongs.
    sorted_nodes : list[int]
        A list of nodes ordered by ascending frame.
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
    print(track)
    ctc_tracks[current_track_label] = track
    node_to_parent_track[track["E_node"]] = current_track_label
    return current_track_label + 1


def export_CTC(model, ctc_file_out):

    # L B E P

    lineages = model.coredata.data
    # Removing one-node lineages.
    # TODO: actually CTC can deal with one-node lineage, so I need to deal
    # with this kind of special cases when everything else will work.
    lineages = [lineage for lineage in lineages.values()]
    current_track_label = 1  # 0 is kept for no parent track
    for lin in lineages:
        print(lin)
        ctc_tracks = {}
        node_to_parent_track = {}

        if len(lin) == 1:
            # print("ONE_NODE LINEAGE")
            current_track_label = _add_track(
                lin,
                list(lin.nodes),
                ctc_tracks,
                node_to_parent_track,
                current_track_label,
            )
        else:
            for cc in lin.get_cell_cycles(keep_incomplete_cell_cycles=True):
                # print(cc)
                sorted_nodes = sort_nodes_by_frame(lin, cc)
                print(sorted_nodes)
                gaps = _find_gaps(lin, sorted_nodes)
                if gaps:
                    print("Gaps found in cell cycle:", cc)
                    print("gaps:", gaps)
                    track_start_i = 0
                    for gap in gaps:
                        track_end_i = sorted_nodes.index(gap[0])
                        current_track_label = _add_track(
                            lin,
                            sorted_nodes[track_start_i : track_end_i + 1],
                            ctc_tracks,
                            node_to_parent_track,
                            current_track_label,
                        )
                        track_start_i = sorted_nodes.index(gap[1])
                    current_track_label = _add_track(
                        lin,
                        sorted_nodes[track_start_i:],
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

        print(ctc_tracks)

        for track_label, track_info in ctc_tracks.items():
            parent_nodes = list(lin.predecessors(track_info["B_node"]))
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


if __name__ == "__main__":

    xml_in = "sample_data/FakeTracks.xml"
    ctc_out = "sample_data/FakeTracks_exported_CTC.xml"

    model = load_TrackMate_XML(xml_in, keep_all_spots=True, keep_all_tracks=True)
    export_CTC(model, ctc_out)
