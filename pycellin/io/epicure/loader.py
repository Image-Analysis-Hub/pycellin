#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from itertools import pairwise
import numpy as np
from pathlib import Path
import pickle

import networkx as nx
from skimage import measure
import tifffile as tiff

from pycellin.classes import CellLineage, Data, Feature, FeaturesDeclaration, Model
import pycellin.classes.feature as pcf


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


def _extract_label_coord_array(
    stack_array: np.ndarray,
) -> np.ndarray:
    """
    Extract the labels and their coordinates from a 3D numpy array.

    Parameters
    ----------
    stack_array : np.ndarray
        A 3D numpy array representing a stack of labels.

    Returns
    -------
    np.ndarray
        A numpy array where each row is a label and the coordinates of its centroid.
    """
    nb_row = 0
    all_props = []
    properties = ["label", "centroid"]
    for frame in range(stack_array.shape[0]):
        props = measure.regionprops_table(stack_array[frame], properties=properties)
        props["frame"] = [frame] * len(props["label"])
        all_props.append(props)
        nb_row += len(props["label"])
    # Reorganize the data as a numpy array with columns: label, pos_t, pos_x, pos_y.
    # This is the EpiCure format.
    props_array = np.zeros((nb_row, 4))
    props_array[:, 0] = np.concatenate([props["label"] for props in all_props])
    props_array[:, 1] = np.concatenate([props["frame"] for props in all_props])
    props_array[:, 2] = np.concatenate([props["centroid-1"] for props in all_props])
    props_array[:, 3] = np.concatenate([props["centroid-0"] for props in all_props])
    return props_array


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


def _add_all_nodes_from_coord_array(
    graph: nx.DiGraph,
    coord_array: np.ndarray,
) -> None:
    """
    Add one node per label to the graph.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which the nodes will be added.
    coord_array : np.ndarray
        A numpy array where each row is a label and the coordinates of its centroid.
    """
    # Labels are not unique across frames, so we need to create a unique
    # node ID for each label.
    current_nid = 0  # Unique node ID.

    for label, frame, pos_x, pos_y in coord_array:
        graph.add_node(
            current_nid,
            frame=int(frame),
            label=int(label),
            cell_ID=current_nid,
            location=(pos_x, pos_y),
        )
        current_nid += 1


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


def _add_same_label_edges_from_coord_array(
    graph: nx.DiGraph,
    label_array: np.ndarray,
) -> None:
    """
    Add edges between nodes having the same label in consecutive frames.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which the edges will be added.
    label_array : np.ndarray
        A numpy array where the rows are the labels and their frames.
    """
    frames = np.unique(label_array[:, 1]).astype(int)
    for current_frame, next_frame in pairwise(frames):
        current_nodes = [
            node for node in graph.nodes if graph.nodes[node]["frame"] == current_frame
        ]
        next_nodes = [
            node for node in graph.nodes if graph.nodes[node]["frame"] == next_frame
        ]
        for node in current_nodes:
            label = graph.nodes[node]["label"]
            next_node = [
                n
                for n in next_nodes
                if graph.nodes[n]["label"] == label
                and graph.nodes[n]["frame"] == next_frame
            ]
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
        # print(daughter_cell, mother_cells)

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
            # print("daughter_cell:", daughter_cell_nid)

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
                    # print("mother_cell:", mother_cell_nid)

                    # Then we can add the edge to the graph.
                    graph.add_edge(mother_cell_nid, daughter_cell_nid)

                else:
                    print(f"Mother cell {mother_cell} not found in label image.")
        else:
            print(f"Daughter cell {daughter_cell} not found in label image.")


def _add_groups(
    graph: nx.DiGraph,
    groups: dict[str, list[int]],
) -> None:
    """
    Add the groups to the nodes in the graph.

    Parameters
    ----------
    graph : nx.DiGraph
        The graph to which the groups will be added.
    groups : dict[str, list[int]]
        A dictionary where the keys are the group names and the values are
        lists of the labels of the cells in the corresponding group.
    """
    for group_name, group in groups.items():
        for label in group:
            # We need to find the nodes corresponding to the labels.
            nodes = [
                node for node in graph.nodes if graph.nodes[node]["label"] == label
            ]
            for nid in nodes:
                graph.nodes[nid]["group"] = group_name


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

    # Adding a unique lineage_ID to each lineage.
    for i, lin in enumerate(lineages):
        lin.graph["lineage_ID"] = i
        # for node in lin.nodes:
        #     lin.nodes[node]["lineage_ID"] = i

    return lineages


def _check_for_fusions(
    lineages: list[CellLineage],
) -> None:
    """
    Check if there are fusions in the lineages and notify the user.

    Parameters
    ----------
    lineages : list[CellLineage]
        The lineages to check for fusions.
    """
    fusion_dict = {}
    for lin in lineages:
        fusions = lin.get_fusions()
        if len(fusions) > 0:
            fusion_dict[lin.graph["lineage_ID"]] = lin.get_fusions()
    if fusion_dict:
        # TODO: switch to a true warning for consistency with the rest of Pycellin.
        cell_txt = f"{'s' if len(fusion_dict) > 1 else ''}"
        fusion_txt = "\n".join(
            f"  Lineage {lin_id} => cell IDs: {fusions}"
            for lin_id, fusions in fusion_dict.items()
        )
        print(
            f"WARNING: Cell fusion{cell_txt} detected!! "
            f"Since Pycellin does not support fusions, it is advised to "
            f"deal with them before any other processing. Be especially "
            f"careful with tracking related features. Crashes and incorrect "
            f"results can occur.\n"
            f"Fusion{cell_txt} location:\n"
            f"{fusion_txt}"
        )


def _build_lineages(
    stack_array: np.ndarray,
    epidata: dict,
) -> list[CellLineage]:
    """
    Build Pycellin cell lineages from EpiCure data.

    Parameters
    ----------
    stack_array : np.ndarray
        A 3D numpy array representing a stack of labels.
    epidata : dict
        The EpiCure data dictionary.

    Returns
    -------
    list[CellLineage]
        The built cell lineages.
    """
    # TODO: extract ROI to have access to morphology.
    # labels_dict = _extract_labels(stack_array)
    # Extracting all the labels and their space and time coordinates.
    coord_array = _extract_label_coord_array(stack_array)

    # Populating the graph with nodes and edges.
    graph = nx.DiGraph()
    # _add_all_nodes(graph, labels_dict)
    _add_all_nodes_from_coord_array(graph, coord_array)
    # Adding edges between identical labels in consecutive frames.
    # _add_same_label_edges(graph, labels_dict)
    _add_same_label_edges_from_coord_array(graph, coord_array[:, 0:2])
    # Adding edges between mother and daughter cells.
    _add_division_edges(graph, epidata["Graph"])
    # TODO: parse the other fields in the pickle file and save the data somewhere
    # (will be useful for exporter).
    _add_groups(graph, epidata["Group"])

    # For now all the lineages are in the same graph.
    # Pycellin expects one lineage per graph so we need to split the graph
    # into its connected components.
    lineages = _split_graph_into_lineages(graph)
    _check_for_fusions(lineages)  # Pycellin DOES NOT support fusion events.

    return lineages


def _build_metadata(
    pickle_path: str,
    label_img_path: str,
    epimetadata: dict,
) -> dict:
    """
    Build the Pycellin metadata dictionary.

    Parameters
    ----------
    pickle_path : str
        The path to the pickle file.
    label_img_path : str
        The path to the label image file.
    epidata : dict
        The EpiCure metadata dictionary.

    Returns
    -------
    dict
        The built metadata dictionary.
    """
    metadata = {}
    metadata["name"] = Path(pickle_path).stem
    metadata["pickle_location"] = pickle_path
    metadata["label_img_location"] = label_img_path
    metadata["provenance"] = "EpiCure"
    metadata["space_unit"] = epimetadata["UnitXY"]
    metadata["time_unit"] = epimetadata["UnitT"]
    metadata["date"] = datetime.now()
    return metadata


def _build_features_declaration(unit: str) -> FeaturesDeclaration:
    """
    Build the Pycellin features declaration.

    Parameters
    ----------
    unit : str
        The unit of the spatial coordinates.

    Returns
    -------
    FeaturesDeclaration
        The built features declaration.
    """
    feat_declaration = FeaturesDeclaration()
    # Common node features.
    feat_declaration._add_feature(pcf.frame_Feature("EpiCure"))
    feat_declaration._add_feature(pcf.cell_ID_Feature("Pycellin"))
    feat_declaration._add_feature(pcf.cell_coord_Feature(unit, "x", "EpiCure"))
    feat_declaration._add_feature(pcf.cell_coord_Feature(unit, "y", "EpiCure"))
    feat_declaration._add_feature(pcf.lineage_ID_Feature("Pycellin"))

    # EpiCure specific node features.
    label_feat = Feature(
        name="label",
        description="Identifier of the cell in EpiCure",
        provenance="EpiCure",
        feat_type="node",
        lin_type="CellLineage",
        data_type="int",
        unit=None,
    )
    group_feat = Feature(
        name="group",
        description="Name of the group to which the cell belongs",
        provenance="EpiCure",
        feat_type="node",
        lin_type="CellLineage",
        data_type="str",
        unit=None,
    )
    feat_declaration._add_feature(label_feat)
    feat_declaration._add_feature(group_feat)

    return feat_declaration


def _load_from_napari(
    coord_array: np.ndarray,
    epigraph: dict[int, list[int]],
) -> Model:
    """
    Load EpiCure data from a napari session into a Pycellin model.

    Parameters
    ----------
    coord_array : np.ndarray
        A numpy array where the rows are the labels and their frames.
    epigraph : dict[int, list[int]]
        A dictionary where the keys are the labels of the daughter cells
        and the values are lists of the labels of the mother cells.

    Returns
    -------
    Model
        A Pycellin model of the data.
    """
    # Populating the graph with nodes and edges.
    graph = nx.DiGraph()
    _add_all_nodes_from_coord_array(graph, coord_array)
    # Adding edges between identical labels in consecutive frames.
    _add_same_label_edges_from_coord_array(graph, coord_array[:, 0:2])
    # Adding edges between mother and daughter cells.
    _add_division_edges(graph, epigraph["Graph"])
    # Pycellin expects one lineage per graph so we need to split the graph
    # into its connected components.
    lineages = _split_graph_into_lineages(graph)
    _check_for_fusions(lineages)  # Pycellin DOES NOT support fusion events.
    data = Data({lin.graph["lineage_ID"]: lin for lin in lineages})

    # No metadata nor units for now.
    # TODO: need to add an argument to get the data from EpiMetaData
    # metadata = _build_metadata(pickle_path, label_img_path, epidata["EpiMetaData"])
    metadata = {}
    # feat_declaration = _build_features_declaration(epidata["EpiMetaData"]["UnitXY"])
    feat_declaration = FeaturesDeclaration()
    model = Model(metadata, feat_declaration, data)

    return model


def load_EpiCure_data(
    pickle_path: str,
    label_img_path: str,
) -> Model:
    """
    Load EpiCure data into a Pycellin model.

    Parameters
    ----------
    pickle_path : str
        The path to the exported EpiCure pickle file.
    label_img_path : str
        The path to the exported EpiCure label image file.

    Returns
    -------
    Model
        A Pycellin model of the data.
    """
    # Load the data from the label stack tiff and the pickle file.
    stack_array = tiff.imread(label_img_path).astype(np.uint32)
    print(stack_array.shape)
    with open(pickle_path, "rb") as f:
        epidata = pickle.load(f)

    # Build the Pycellin model.
    lineages = _build_lineages(stack_array, epidata)
    data = Data({lin.graph["lineage_ID"]: lin for lin in lineages})
    metadata = _build_metadata(pickle_path, label_img_path, epidata["EpiMetaData"])
    feat_declaration = _build_features_declaration(epidata["EpiMetaData"]["UnitXY"])
    model = Model(metadata, feat_declaration, data)

    return model


if __name__ == "__main__":

    epi_file = "/mnt/data/Code/EpiCure_small_example/epics/013_crop_epidata.pkl"
    stack_file = "/mnt/data/Code/EpiCure_small_example/epics/013_crop_labels.tif"

    model = load_EpiCure_data(epi_file, stack_file)
    print(model)
    # print(model.metadata)

    # for lin in model.data.cell_data.values():
    #     print(lin.nodes(data="group"))

    print(model.feat_declaration)
    # lin0 = model.data.cell_data[0]

    # print(lin0.nodes(data=True))
