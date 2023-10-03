#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

import morphology
import IO


## Accessing elements ##


def get_node_attributes_names(graph: nx.DiGraph) -> list[str]:
    """Return a list of the attributes used for nodes.

    Args:
        graph (nx.DiGraph): Graph on which to work.

    Returns:
        list[str]: Names of the attributes used for nodes.
    """
    # node_attributes = set([k for n in graph.nodes for k in graph.nodes[n].keys()])
    for node in graph.nodes:
        # By construction, each and every node has the same set of attributes,
        # only their values change. So we get the first node, whichever it is,
        # and get its attributes. There's no need to do it for every node.
        node_attributes = list(graph.nodes[node].keys())
        break
    return node_attributes


def get_root(graph):
    if len(graph) == 1:
        root = [n for n in graph.nodes()]
        assert len(root) == 1
    else:
        root = [
            n
            for n in graph.nodes()
            if graph.in_degree(n) == 0 and graph.out_degree(n) != 0
        ]
        assert len(root) == 1
    return root[0]


def get_leaves(graph):
    leaves = [
        n for n in graph.nodes() if graph.in_degree(n) != 0 and graph.out_degree(n) == 0
    ]
    return leaves


def get_divisions(graph, nodes=[]):
    if not nodes:
        nodes = graph.nodes()
    divisions = [n for n in nodes if graph.out_degree(n) > 1]
    return divisions


def get_branch(graph, root, leave):
    return nx.shortest_path(graph, source=root, target=leave)


##


def is_root(graph, node):
    if graph.in_degree(node) == 0 and graph.out_degree(node) != 0:
        return True
    else:
        return False


def is_leaf(graph, node):
    if graph.in_degree(node) != 0 and graph.out_degree(node) == 0:
        return True
    else:
        return False


def is_division(graph, node):
    if graph.in_degree(node) <= 1 and graph.out_degree(node) > 1:
        return True
    else:
        return False


def get_generations(graph, keep_incomplete_gens=False, debug=False):
    """Find all the generation segments of a graph.

    A generation is a tree segment that starts at the root or at a
    branching node, ends at a branching node or at a leaf, and doesn't
    include any other branching.

    Args:
        graph (nx.DiGraph): Graph on which to work.
        keep_incomplete_gens (bool, optional): True to keep the first
            and last generations, False otherwise. Defaults to False.
        debug (bool, optional): True to display debug messages. False
            otherwise. Defaults to False.

    Returns:
        list(list(int)): List of nodes for each generation.
    """

    if keep_incomplete_gens:
        end_nodes = get_divisions(graph) + get_leaves(graph)
    else:
        end_nodes = get_divisions(graph)  # Includes the root if it's a div.
    if debug:
        print("End nodes:", end_nodes)

    generations = []
    for node in end_nodes:
        gen = get_generation(graph, node)
        if not keep_incomplete_gens and get_root(graph) in gen:
            continue
        generations.append(gen)
        if debug:
            print("Generation:", gen)

    return generations


def get_generation(graph, node):
    gen = [node]
    start = False
    end = False

    if is_root(graph, node):
        start = True
    if is_division(graph, node) or is_leaf(graph, node):
        end = True

    if not start:
        predecessors = list(graph.predecessors(node))
        assert len(predecessors) == 1
        while not is_division(graph, *predecessors) and not is_root(
            graph, *predecessors
        ):
            # While not the generation birth.
            gen.append(*predecessors)
            predecessors = list(graph.predecessors(*predecessors))
            err = (
                f"Node {node} in {graph.graph['name']} has "
                f"{len(predecessors)} predecessors."
            )
            assert len(predecessors) == 1, err
        if is_root(graph, *predecessors) and not is_division(graph, *predecessors):
            gen.append(*predecessors)
        gen.reverse()  # We built it from the end.

    if not end:
        successors = list(graph.successors(node))
        err = (
            f"Node {node} in {graph.graph['name']} has "
            f"{len(successors)} successors."
        )
        assert len(successors) == 1, err
        while not is_division(graph, *successors) and not is_leaf(graph, *successors):
            gen.append(*successors)
            successors = list(graph.successors(*successors))
            err = (
                f"Node {node} in {graph.graph['name']} has "
                f"{len(successors)} successors."
            )
            assert len(successors) == 1, err
        gen.append(*successors)

    return gen


## Adding new cell features.


def add_generation_ID(graph):
    # Updating the nodes attribute.
    for n in graph:
        # A graph containing only one node does not have a TRACK_ID.
        # And it can't have a GEN_ID either.
        if "TRACK_ID" in graph.nodes[n]:
            track_ID = graph.nodes[n]["TRACK_ID"]
            gen_end_node = get_generation(graph, n)[-1]
            gen_ID = f"{track_ID}_{gen_end_node}"
            graph.nodes[n]["GEN_ID"] = gen_ID

    # Updating the graph attribute.
    graph.graph["Model"]["SpotFeatures"]["GEN_ID"] = {
        "feature": "GEN_ID",
        "name": "Generation ID",
        "shortname": "Gen. ID",
        "dimension": "NONE",
        "isint": "false",
    }


def add_width_and_length(graph, pixel_size=0.06568, skel_algo="zhang", tolerance=0.5):
    # Updating the nodes attributes.
    for n in graph:
        width, length = morphology.get_width_and_length(
            graph, n, pixel_size, skel_algo, tolerance
        )
        graph.nodes[n]["WIDTH"] = width
        graph.nodes[n]["LENGTH"] = length

    # Updating the graph attributes.
    graph.graph["Model"]["SpotFeatures"]["WIDTH"] = {
        "feature": "WIDTH",
        "name": "Width",
        "shortname": "Width",
        "dimension": "LENGTH",
        "isint": "false",
    }
    graph.graph["Model"]["SpotFeatures"]["LENGTH"] = {
        "feature": "LENGTH",
        "name": "Length",
        "shortname": "Length",
        "dimension": "LENGTH",
        "isint": "false",
    }


# def add_node_attributes(
#     graph,
#     attributes=None,
#     morphology=True,
#     tracking=True,
#     pixel_size=0.06568,
#     skel_algo="zhang",
#     tolerance=0.5,
# ):
#     """Compute and add new nodes attributes in a graph.

#     Args:
#         graph (nx.DiGraph): Graph on which to work.
#         attributes (list(str), optional): List of attributes to add to the
#             nodes. Defaults to None. If None, all attributes will be added,
#             depending on `morphology` and `tracking` values.
#         morphology (bool, optional): If `attributes` is set to None, True
#             to add morphological features to the nodes. Defaults to True.
#         tracking (bool, optional): If `attributes` is set to None, True
#             to add tracking related features to the nodes. Defaults to True.
#     """
#     # TODO: ajouter dans les docstrings une section détaillant les features.
#     # TODO: ajouter dans les docstrings les arguments manquants.

#     if attributes is None:
#         if morphology:
#             add_width_and_length(graph)
#         if tracking:
#             add_generation_ID(graph)
#             add_generation_level(graph)
#             add_generation_completeness(graph)
#             add_division_time(graph)
#             add_phase(graph)
#             add_absolute_age(graph)
#             add_relative_age(graph)
#             add_area_increment(graph)
#     else:
#         add_attr = {
#             "WIDTH": add_width_and_length,
#             "LENGTH": add_width_and_length,
#             "GEN_ID": add_generation_ID,
#             "GEN_LVL": add_generation_level,
#             "GEN_COMPLETE": add_generation_completeness,
#             "DIV_TIME": add_division_time,
#             "PHASE": add_phase,
#             "ABSOLUTE_AGE": add_absolute_age,
#             "RELATIVE_AGE": add_relative_age,
#             "GROWTH_RATE": add_area_increment(),
#         }

#         dimensions_done = False
#         for attr in attributes:
#             if not dimensions_done and (attr == "WIDTH" or attr == "LENGTH"):
#                 add_attr[attr](graph, pixel_size, skel_algo, tolerance)
#                 dimensions_done = True
#             else:
#                 add_attr[attr](graph)


## Dataframes

# TODO : add file name/path to the graph attributes


def reduce_memory_footprint(df):
    before = sum(df.memory_usage(deep=True))

    df.FILENAME = df.FILENAME.astype("category", copy=False)
    if "TRACK_ID" in df.columns:
        df.TRACK_ID = df.TRACK_ID.astype("category", copy=False)
    if "PHASE" in df.columns:
        df.PHASE = df.PHASE.astype("category", copy=False)
    if "TRAJ_ID" in df.columns:
        df.TRAJ_ID = df.TRAJ_ID.astype("category", copy=False)

    df.name = df.name.astype("string", copy=False)

    df.VISIBILITY = pd.to_numeric(df.VISIBILITY, downcast="unsigned")
    for column in df.select_dtypes(include=[int]):
        df[column] = pd.to_numeric(df[column], downcast="unsigned")

    for column in df.select_dtypes(include=[float]):
        df[column] = pd.to_numeric(df[column], downcast="float")
    # print(df.dtypes)

    after = sum(df.memory_usage(deep=True))
    print(f"In-memory footprint reduced from {before} to {after} bytes.")


def get_nodes_df(graphs, filepaths):
    list_df = []
    nb_nodes = 0
    for graph, filepath in zip(graphs, filepaths):
        # print(graph)
        nb_nodes += len(graph)
        tmp_df = pd.DataFrame(dict(graph.nodes(data=True)).values())
        filename = Path(filepath).stem
        to_remove = filename.find("_Track")
        if to_remove != -1:
            filename = filename[:to_remove]
        tmp_df["FILENAME"] = [filename] * len(graph)
        list_df.append(tmp_df)

    df = pd.concat(list_df, ignore_index=True)
    assert nb_nodes == len(df)
    reduce_memory_footprint(df)
    return df


# def get_trajectory_df(graph, filepath):

#     list_df = []
#     root = get_root(graph)
#     track_id = graph.nodes[root]['TRACK_ID']

#     for leaf in get_leaves(graph):
#         traj = nx.shortest_path(graph, source=root, target=leaf)
#         traj_graph = graph.subgraph(traj)
#         tmp_df = pd.DataFrame(dict(traj_graph.nodes(data=True)).values())
#         tmp_df['TRAJ_ID'] = f'{track_id}_{leaf}'
#         list_df.append(tmp_df)

#     df = pd.concat(list_df, ignore_index=True)
#     filename = filepath.stem
#     to_remove = filename.find('_Track')
#     filename = filename[:to_remove]
#     df['FILENAME'] = [filename] * df.shape[0]
#     reduce_memory_footprint(df)
#     return df


def get_trajectories_df(graphs, filepaths):
    list_df = []
    for graph, filepath in zip(graphs, filepaths):
        root = get_root(graph)
        track_id = graph.nodes[root]["TRACK_ID"]
        filename = filepath.stem
        to_remove = filename.find("_Track")
        filename = filename[:to_remove]

        for leaf in get_leaves(graph):
            traj = nx.shortest_path(graph, source=root, target=leaf)
            traj_graph = graph.subgraph(traj)
            tmp_df = pd.DataFrame(dict(traj_graph.nodes(data=True)).values())
            tmp_df["TRAJ_ID"] = f"{track_id}_{leaf}"
            tmp_df["FILENAME"] = [filename] * tmp_df.shape[0]
            list_df.append(tmp_df)

    df = pd.concat(list_df, ignore_index=True)
    reduce_memory_footprint(df)
    return df


def get_nb_bacteria_df(df_nodes):
    """_summary_

    Args:
        df_nodes (pd.Dataframe): Nodes dataframe, with or without additional
            features.

    Returns:
        pd.Dataframe: A 2-column df (FRAME, NB_BACTERIA) holding the number
            of bacteria found at each frame.
    """

    if "FILENAME" in df_nodes.columns:
        df = df_nodes.groupby("FILENAME", as_index=False)["FRAME"].value_counts()
        df.rename(columns={"count": "NB_BACTERIA"}, inplace=True)
        df.sort_values(by=["FRAME"], inplace=True)
    else:
        df = df_nodes["FRAME"].value_counts(sort=False)
        df.rename("NB_BACTERIA", inplace=True)
        df.sort_index(inplace=True)
        df = pd.DataFrame(df)
        # df.reset_index(names=['FRAME'], inplace=True) # pandas 1.5
        df.reset_index(inplace=True)
        df.rename(columns={"index": "FRAME"}, inplace=True)

    return df


def display_lineage(graph):
    pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog="dot")
    plt.figure(figsize=(12, 12))
    nx.draw(graph, pos, with_labels=True, arrows=False, font_weight="bold")
    plt.show()


if __name__ == "__main__":
    pass
