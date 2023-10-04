#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Optional

import matplotlib.pyplot as plt
import networkx as nx


### Accessing elements ###


def get_root(graph: nx.DiGraph) -> int:
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


def get_leaves(graph: nx.DiGraph) -> list[int]:
    leaves = [
        n for n in graph.nodes() if graph.in_degree(n) != 0 and graph.out_degree(n) == 0
    ]
    return leaves


def get_divisions(graph: nx.DiGraph, nodes: Optional[list[int]] = None) -> list[int]:
    if nodes is None:
        nodes = graph.nodes()
    return [n for n in nodes if graph.out_degree(n) > 1]


def get_branch(graph: nx.DiGraph, root: int, leave: int) -> list[int]:
    return nx.shortest_path(graph, source=root, target=leave)


def get_generation(graph: nx.DiGraph, node: int) -> list[int]:
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


def get_generations(
    graph: nx.DiGraph, keep_incomplete_gens: bool = False, debug: bool = False
):
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


### Predicates ###


def is_root(graph: nx.DiGraph, node: int):
    if graph.in_degree(node) == 0 and graph.out_degree(node) != 0:
        return True
    else:
        return False


def is_leaf(graph: nx.DiGraph, node: int):
    if graph.in_degree(node) != 0 and graph.out_degree(node) == 0:
        return True
    else:
        return False


def is_division(graph: nx.DiGraph, node: int):
    if graph.in_degree(node) <= 1 and graph.out_degree(node) > 1:
        return True
    else:
        return False


### Not so random stuff ###


def display_lineage(graph: nx.DiGraph):
    pos = nx.drawing.nx_agraph.graphviz_layout(graph, prog="dot")
    plt.figure(figsize=(12, 12))
    nx.draw(graph, pos, with_labels=True, arrows=False, font_weight="bold")
    plt.show()


def get_node_attributes_names(graph: nx.DiGraph) -> list[str]:
    """Return a list of the attributes used for nodes.

    Args:
        graph (nx.DiGraph): Graph on which to work.

    Returns:
        list[str]: Names of the attributes used for nodes.
    """
    # node_attributes = set([k for n in graph.nodes for k in graph.nodes[n].keys()])
    node_attributes = list()
    for node in graph.nodes:
        # By construction, each and every node has the same set of attributes,
        # only their values change. So we get the first node, whichever it is,
        # and get its attributes. There's no need to do it for every node.
        node_attributes = list(graph.nodes[node].keys())
        break
    return node_attributes


if __name__ == "__main__":
    pass
