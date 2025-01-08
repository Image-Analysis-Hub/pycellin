#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pickle

import networkx as nx
import tifffile as tiff

from pycellin.classes import Model, CellLineage


def _extract_labels(
    stack_array: np.ndarray,
) -> dict[int, list[int]]:
    """
    Extract the labels and their temporality from a 3D numpy array.

    Parameters
    ----------
    stack_array : np.ndarray
        A 3D numpy array representing a stack of labels.

    Returns
    -------
    dict[int, list[int]]
        A dictionary where the keys are the frame numbers and the values are
        lists of the labels present in the corresponding frame.
    """
    all_labels = {
        i: [int(label) for label in set(stack_array[i].flatten()) if label != 0]
        for i in range(stack_array.shape[0])
    }
    return all_labels


def _add_all_nodes(
    graph: nx.DiGraph,
    labels_dict: dict[int, list[int]],
) -> None:
    """
    Add one node per label to the graph.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which the nodes will be added.
    labels_dict : dict[int, list[int]]
        A dictionary of labels per frame. The keys are the frame numbers
        and the values are lists of the labels present in the corresponding frame.
    """
    # Labels are not unique across frames, so we need to create a unique
    # node ID for each label.
    current_nid = 0  # Unique node ID.
    for frame, labels in labels_dict.items():
        nois = list(range(current_nid, current_nid + len(labels)))
        assert len(labels) == len(nois)
        current_nid += len(labels)
        nodes = [
            (nid, {"frame": frame, "label": label, "cell_ID": nid})
            for label, nid in zip(labels, nois)
        ]
        graph.add_nodes_from(nodes)


def _add_same_label_edges(
    graph: nx.DiGraph,
    labels_dict: dict[int, list[int]],
) -> None:
    """
    Add edges between nodes having the same label in consecutive frames.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which the edges will be added.
    labels_dict : dict[int, list[int]]
        A dictionary of labels per frame. The keys are the frame numbers
        and the values are lists of the labels present in the corresponding frame.
    """
    nb_frames = len(labels_dict)
    for frame in range(nb_frames - 1):
        current_nodes = [
            node for node in graph.nodes if graph.nodes[node]["frame"] == frame
        ]
        next_nodes = [
            node for node in graph.nodes if graph.nodes[node]["frame"] == frame + 1
        ]
        for node in current_nodes:
            label = graph.nodes[node]["label"]
            if label in labels_dict[frame + 1]:
                next_node = [n for n in next_nodes if graph.nodes[n]["label"] == label]
                assert len(next_node) <= 1
                if next_node:
                    graph.add_edge(node, next_node[0])


def _add_division_edges(
    graph: nx.DiGraph,
    graph_data: dict[int, list[int]],
) -> None:
    """
    Add edges between mother and daughter cells in the graph.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which the edges will be added.
    graph_data : dict[int, list[int]]
        A dictionary where the keys are the labels of the daughter cells
        and the values are lists of the labels of the mother cells.
    """
    for daughter_cell, mother_cells in graph_data.items():
        print(daughter_cell, mother_cells)

        # What we have here are labels, not cell IDs.
        # So we need to find the corresponding cell IDs.
        candidate_daughter_cell = [
            (node, frame)
            for node, frame in graph.nodes(data="frame")
            if graph.nodes[node]["label"] == daughter_cell
        ]
        # assert len(candidate_daughter_cell) > 0, print(candidate_daughter_cell)
        if len(candidate_daughter_cell) > 0:
            # The daughter cell involved in the division is the one with
            # the lowest frame. So we are looking for the first time
            # the label appears in the image.
            candidate_daughter_cell.sort(key=lambda x: x[1])
            daughter_cell_nid = candidate_daughter_cell[0][0]
            print("daughter_cell:", daughter_cell_nid)

            for mother_cell in mother_cells:
                # Same as above but with the mother cell.
                candidate_mother_cell = [
                    (node, frame)
                    for node, frame in graph.nodes(data="frame")
                    if graph.nodes[node]["label"] == mother_cell
                ]
                # assert len(candidate_mother_cell) > 0, print(candidate_mother_cell)
                if len(candidate_mother_cell) > 0:
                    candidate_mother_cell.sort(key=lambda x: x[1], reverse=True)
                    mother_cell_nid = candidate_mother_cell[0][0]
                    print("mother_cell:", mother_cell_nid)

                    # Then we can add the edge to the graph.
                    graph.add_edge(mother_cell_nid, daughter_cell_nid)

                else:
                    print(f"Mother cell {mother_cell} not found in label image.")
        else:
            print(f"Daughter cell {daughter_cell} not found in label image.")


def _split_graph_into_lineages(
    graph: nx.DiGraph,
) -> list[CellLineage]:
    """
    Split a graph into several subgraphs, each representing a lineage.

    Parameters
    ----------
    lineage : nx.DiGraph
        The graph to split.

    Returns
    -------
    list[CellLineage]
        A list of subgraphs, each representing a lineage.
    """
    # One subgraph is created per lineage, so each subgraph is
    # a connected component of `graph`.
    lineages = [
        CellLineage(graph.subgraph(c).copy())
        for c in nx.weakly_connected_components(graph)
    ]
    del graph  # Redondant with the subgraphs.

    # Adding a unique lineage_ID to each lineage and their nodes.
    for i, lin in enumerate(lineages):
        lin.graph["lineage_ID"] = i
        for node in lin.nodes:
            lin.nodes[node]["lineage_ID"] = i

    return lineages


def load_EpiCure_data(
    pickle_path: str,
    label_img_path: str,
) -> Model:

    # Nodes are extracted from the tif stack of labels.
    stack_array = tiff.imread(label_img_path)
    print(stack_array.shape)
    # For now just getting the nodes, no features like position, ROI or area.
    # TODO: extract features.
    labels_dict = _extract_labels(stack_array)
    # print(labels_dict)

    # Populating the graph with nodes and edges.
    graph = nx.DiGraph()
    _add_all_nodes(graph, labels_dict)
    print(graph)
    # Adding edges between identical labels in consecutive frames.
    _add_same_label_edges(graph, labels_dict)
    # Adding edges between mother and daughter cells by parsing the pickle file.
    with open(pickle_path, "rb") as f:
        epidata = pickle.load(f)
    graph_data = epidata["Graph"]
    _add_division_edges(graph, graph_data)
    # TODO: parse the other fields in the pickle file and save the data somewhere

    # For now all the lineages are in the same graph.
    # Pycellin expects one lineage per graph so we need to split the graph
    # into its connected components.
    lineages = _split_graph_into_lineages(graph)
    print("Nb lineages:", len(lineages))
    print(lineages[0])
    print(lineages[0].graph)


if __name__ == "__main__":

    epi_file = "/mnt/data/Code/EpiCure_small_example/epics/013_crop_epidata.pkl"
    stack_file = "/mnt/data/Code/EpiCure_small_example/epics/013_crop_labels.tif"

    load_EpiCure_data(epi_file, stack_file)
